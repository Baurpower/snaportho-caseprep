"""
Write service for the CasePrep registry: section edits and certification.

Edits write directly to modules.json section-by-section. The file is the
content source of truth. Supabase stores only reviewer decisions.

Atomic write pattern: write temp file then rename over target so a crash
mid-write never leaves a partial file.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from caseprep.registry.constants import (
    CLINICAL_SECTION_ORDER,
    MODULE_SECTIONS,
    REQUIRED_SECTIONS,
)
from caseprep.registry.dto import (
    ClinicalSectionDTO,
    ProcedureDetailDTO,
    ValidationWarningDTO,
)
from caseprep.registry.mappers import build_clinical_sections, build_source_dtos
from caseprep.registry.validation import score_modules, section_has_content
from caseprep.factory.audit_log import AUDIT_LOG_PATH, record_audit_event
from caseprep.factory.generation_meta import load_generation_meta
from caseprep.factory.paths import GENERATION_META_FILENAME
from caseprep.services.registry_read_service import (
    BASE_DIR,
    REGISTRY_ROOT,
    ProcedureNotFoundError,
    _certified_payload_exists,
    _load_json,
    _load_manifest,
    _load_sources,
    _read_jsonl,
    _resolve_modules,
    build_validation_warnings,
    compute_is_live,
    load_aliases,
    excerpt_review_notes,
)

# Best-effort, non-fatal: regenerates registry_index.json / alias_index.json /
# certified_payloads_export.jsonl from on-disk procedure folders. Read-only
# with respect to procedure content; safe to call after any manifest change
# that could affect live counts/exports.
_BUILD_REGISTRY_INDEX_SCRIPT = BASE_DIR / "scripts" / "caseprep" / "build_registry_index.py"


def _rebuild_registry_index() -> bool:
    if not _BUILD_REGISTRY_INDEX_SCRIPT.exists():
        return False
    try:
        result = subprocess.run(
            [sys.executable, str(_BUILD_REGISTRY_INDEX_SCRIPT)],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False

_SLUG_PATTERN = __import__("re").compile(r"^[a-z0-9_]+$")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write JSON to a temp file then rename over target for atomic replacement."""
    dir_ = path.parent
    fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _items_to_section_value(section_key: str, items: List[Dict[str, Any]]) -> Any:
    """
    Convert a list of ClinicalSectionItem dicts back to the native modules.json
    shape for a given section_key.
    """
    if section_key in {
        "indications",
        "setup_positioning",
        "approach_landmarks",
        "pitfalls",
        "postop_plan",
        "implant_strategy",
        "reduction_or_fluoro_checkpoints",
    }:
        return [item["text"] for item in items if item.get("kind") == "bullet" and item.get("text")]

    if section_key == "attending_pimp_questions":
        result = []
        for item in items:
            if item.get("kind") == "pimp_question":
                q = (item.get("question") or "").strip()
                a = (item.get("answer") or "").strip()
                if q:
                    result.append({"question": q, "answer": a})
        return result

    if section_key == "structures_at_risk":
        result = []
        for item in items:
            if item.get("kind") == "structure_at_risk":
                entry: Dict[str, Any] = {
                    "structure": item.get("structure", ""),
                    "why_at_risk": item.get("why_at_risk", ""),
                    "how_to_avoid_injury": item.get("how_to_avoid_injury", ""),
                    "consequence_of_injury": item.get("consequence_of_injury", ""),
                }
                if item.get("approach_context"):
                    entry["approach_context"] = item["approach_context"]
                if item.get("source_urls"):
                    entry["source_urls"] = item["source_urls"]
                result.append(entry)
        return result

    if section_key == "surgical_layers":
        result = []
        for item in items:
            if item.get("kind") == "surgical_layer":
                entry = {
                    "layer_name": item.get("layer_name", ""),
                    "what_user_should_know": item.get("what_user_should_know", ""),
                    "key_structures": item.get("key_structures") or [],
                    "structures_at_risk": item.get("structures_at_risk") or [],
                    "surgical_relevance": item.get("surgical_relevance", ""),
                }
                if item.get("source_urls"):
                    entry["source_urls"] = item["source_urls"]
                result.append(entry)
        return result

    return []


def update_section(
    slug: str,
    section_key: str,
    items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Replace one section in modules.json with the provided items list.

    Returns:
        {
            "section": ClinicalSectionDTO,
            "validation_warnings": List[ValidationWarningDTO],
            "coverage_score": int,
        }

    Raises ProcedureNotFoundError if slug is unknown.
    Raises ValueError if section_key is not a valid module section.
    """
    normalized = (slug or "").strip().lower()
    if not normalized or not _SLUG_PATTERN.match(normalized):
        raise ProcedureNotFoundError(slug)

    if section_key not in MODULE_SECTIONS:
        raise ValueError(f"Invalid section_key: '{section_key}'")

    folder = REGISTRY_ROOT / normalized
    if not folder.is_dir():
        raise ProcedureNotFoundError(slug)

    manifest = _load_manifest(folder)
    if not manifest:
        raise ProcedureNotFoundError(slug)

    # Load current modules (create empty dict if missing)
    modules_path = folder / "modules.json"
    modules: Dict[str, Any] = _load_json(modules_path, {}) or {}

    # Convert incoming items back to native format and replace section
    new_value = _items_to_section_value(section_key, items)
    modules[section_key] = new_value

    # Atomic write modules.json
    _atomic_write_json(modules_path, modules)

    # Recompute coverage and update manifest
    payload = _load_json(folder / "certified_payload.json")
    coverage_score = score_modules(modules, payload)

    manifest["coverage_score"] = coverage_score
    manifest["last_reviewed_at"] = _now_iso()
    _atomic_write_json(folder / "manifest.json", manifest)

    # Rebuild section DTO and validation warnings for the response
    sources = _load_sources(folder, payload)
    sections = build_clinical_sections(modules, sources)
    updated_section = next((s for s in sections if s.key == section_key), None)
    if updated_section is None:
        # Fallback: return empty section DTO
        updated_section = ClinicalSectionDTO(
            key=section_key,
            label=section_key,
            content_type="bullet_list",
            is_required=section_key in REQUIRED_SECTIONS,
            is_empty=True,
            coverage_weight=0,
            items=[],
        )

    validation_warnings = build_validation_warnings(
        slug=normalized,
        manifest=manifest,
        modules=modules,
        sources=sources,
        folder=folder,
        coverage_score=coverage_score,
    )

    return {
        "section": updated_section,
        "validation_warnings": validation_warnings,
        "coverage_score": coverage_score,
    }


def _resolve_normalized_slug(slug: str) -> str:
    normalized = (slug or "").strip().lower()
    if not normalized or not _SLUG_PATTERN.match(normalized):
        raise ProcedureNotFoundError(slug)
    return normalized


def _build_detail_dto(normalized: str, manifest: Dict[str, Any], folder: Path) -> ProcedureDetailDTO:
    """Assemble the full ProcedureDetailDTO for a procedure after a write."""
    modules, _ = _resolve_modules(folder)
    payload = _load_json(folder / "certified_payload.json")
    aliases_obj = _load_json(folder / "aliases.json", {}) or {}
    sources = _load_sources(folder, payload)
    review_notes_text: Optional[str] = None
    review_notes_path = folder / "review_notes.md"
    if review_notes_path.exists():
        review_notes_text = review_notes_path.read_text(encoding="utf-8")

    coverage_score = int(manifest.get("coverage_score") or score_modules(modules, payload))
    sections = build_clinical_sections(modules, sources)
    source_dtos = build_source_dtos(sources, modules)
    validation_warnings = build_validation_warnings(
        slug=normalized,
        manifest=manifest,
        modules=modules,
        sources=sources,
        folder=folder,
        coverage_score=coverage_score,
    )

    return ProcedureDetailDTO(
        slug=normalized,
        display_name=str(manifest.get("display_name") or normalized),
        specialty=str(manifest.get("specialty") or "unknown"),
        body_region=str(manifest.get("body_region") or "unknown"),
        procedure_family=str(manifest.get("procedure_family") or "general"),
        content_status=str(manifest.get("content_status") or "missing"),
        review_status=str(manifest.get("review_status") or "unreviewed"),
        version=str(manifest.get("version") or "0.0.0"),
        coverage_score=coverage_score,
        is_live=compute_is_live(manifest, folder),
        deprecated=bool(manifest.get("deprecated")),
        replacement_slug=manifest.get("replacement_slug"),
        reviewer=manifest.get("reviewer"),
        certified_at=manifest.get("certified_at"),
        last_reviewed_at=manifest.get("last_reviewed_at"),
        aliases=load_aliases(aliases_obj if isinstance(aliases_obj, dict) else None),
        sections=sections,
        sources=source_dtos,
        validation_warnings=validation_warnings,
        review_notes_excerpt=excerpt_review_notes(review_notes_text),
        runtime_enabled=bool(manifest.get("runtime_enabled")),
    )


def certify_procedure(
    slug: str,
    certified_by: str,
    notes: Optional[str] = None,
) -> ProcedureDetailDTO:
    """
    Mark a procedure certified in manifest.json.

    Sets content_status, review_status, reviewer, certified_at,
    last_reviewed_at. Does NOT set runtime_enabled or touch
    certified_payload.json — certification is a review marker only.

    Raises ProcedureNotFoundError if slug is unknown.
    """
    normalized = _resolve_normalized_slug(slug)

    folder = REGISTRY_ROOT / normalized
    if not folder.is_dir():
        raise ProcedureNotFoundError(slug)

    manifest = _load_manifest(folder)
    if not manifest:
        raise ProcedureNotFoundError(slug)

    previous_status = manifest.get("review_status")

    now = _now_iso()
    manifest["content_status"] = "certified"
    manifest["review_status"] = "certified"
    manifest["reviewer"] = certified_by
    manifest["certified_at"] = now
    manifest["last_reviewed_at"] = now
    if notes:
        manifest["review_notes"] = notes

    # runtime_enabled remains whatever it was — do not touch it here
    _atomic_write_json(folder / "manifest.json", manifest)

    record_audit_event(
        actor=certified_by,
        action="certify",
        slug=normalized,
        previous_status=previous_status,
        new_status=manifest.get("review_status"),
        previous_runtime_enabled=bool(manifest.get("runtime_enabled")),
        new_runtime_enabled=bool(manifest.get("runtime_enabled")),
        changed_files=[str(folder / "manifest.json")],
    )

    return _build_detail_dto(normalized, manifest, folder)


def approve_procedure(
    slug: str,
    approved_by: str,
    notes: Optional[str] = None,
) -> ProcedureDetailDTO:
    """
    Mark a procedure 'approved' (human sign-off ahead of certify/promote).

    Refuses when generation_meta.json reports blocking QA issues. Does NOT
    set content_status='certified' or runtime_enabled — approve is a
    lighter-weight gate than certify, intended for the review -> approve ->
    certify -> promote workflow.

    Raises ProcedureNotFoundError if slug is unknown.
    Raises ValueError if blocking QA issues are present.
    """
    normalized = _resolve_normalized_slug(slug)

    folder = REGISTRY_ROOT / normalized
    if not folder.is_dir():
        raise ProcedureNotFoundError(slug)

    manifest = _load_manifest(folder)
    if not manifest:
        raise ProcedureNotFoundError(slug)

    if not approved_by or not str(approved_by).strip():
        raise ValueError("approved_by (human actor identifier) is required")

    meta = load_generation_meta(folder / GENERATION_META_FILENAME)
    blocking_issues = list(meta.blocking_issues) if meta else []
    if blocking_issues:
        raise ValueError(
            f"Cannot approve {normalized}: {len(blocking_issues)} blocking QA "
            f"issue(s) present: {'; '.join(blocking_issues)}"
        )

    previous_status = manifest.get("review_status")
    now = _now_iso()
    manifest["review_status"] = "approved"
    manifest["reviewer"] = approved_by
    manifest["last_reviewed_at"] = now
    if notes:
        manifest["review_notes"] = notes

    _atomic_write_json(folder / "manifest.json", manifest)

    record_audit_event(
        actor=approved_by,
        action="approve",
        slug=normalized,
        previous_status=previous_status,
        new_status=manifest.get("review_status"),
        previous_runtime_enabled=bool(manifest.get("runtime_enabled")),
        new_runtime_enabled=bool(manifest.get("runtime_enabled")),
        qa_score=meta.overall_quality_score if meta else None,
        blocking_issues_count=len(blocking_issues),
        changed_files=[str(folder / "manifest.json")],
    )

    return _build_detail_dto(normalized, manifest, folder)


def promote_to_runtime(
    slug: str,
    promoted_by: str,
    override_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Flip runtime_enabled=true for an already-certified procedure that has
    an existing certified_payload.json on disk.

    This function never compiles or writes certified_payload.json itself —
    that happens via `compile --promote` (caseprep.factory.compiler), a
    separate, independently audited step. promote_to_runtime only ever
    flips the runtime flag, and only after re-validating that the
    procedure is actually safe to serve.

    Raises ProcedureNotFoundError if slug is unknown.
    Raises ValueError if promotion preconditions are not met and no
    override_reason was supplied (refusal is the safe default).
    """
    normalized = _resolve_normalized_slug(slug)

    folder = REGISTRY_ROOT / normalized
    if not folder.is_dir():
        raise ProcedureNotFoundError(slug)

    manifest = _load_manifest(folder)
    if not manifest:
        raise ProcedureNotFoundError(slug)

    if not promoted_by or not str(promoted_by).strip():
        raise ValueError("promoted_by (human actor identifier) is required")

    previous_status = manifest.get("review_status")
    previous_runtime_enabled = bool(manifest.get("runtime_enabled"))

    reasons: List[str] = []
    if manifest.get("review_status") != "certified":
        reasons.append(
            f"review_status is '{manifest.get('review_status')}', requires 'certified'"
        )
    if manifest.get("content_status") != "certified":
        reasons.append(
            f"content_status is '{manifest.get('content_status')}', requires 'certified'"
        )
    if manifest.get("deprecated"):
        reasons.append("procedure is marked deprecated")
    if not _certified_payload_exists(folder):
        reasons.append("certified_payload.json does not exist for this procedure")

    meta = load_generation_meta(folder / GENERATION_META_FILENAME)
    blocking_issues = list(meta.blocking_issues) if meta else []
    if blocking_issues:
        reasons.append(f"{len(blocking_issues)} blocking QA issue(s) present")

    modules, _ = _resolve_modules(folder)
    payload = _load_json(folder / "certified_payload.json")
    coverage_score = int(manifest.get("coverage_score") or score_modules(modules, payload))
    sources = _load_sources(folder, payload)
    validation_warnings = build_validation_warnings(
        slug=normalized,
        manifest=manifest,
        modules=modules,
        sources=sources,
        folder=folder,
        coverage_score=coverage_score,
    )
    blocking_validation = [w for w in validation_warnings if w.severity == "blocking"]
    if blocking_validation:
        reasons.append(
            f"{len(blocking_validation)} blocking validation warning(s): "
            + "; ".join(w.message for w in blocking_validation)
        )

    override_used = False
    if reasons:
        if override_reason and str(override_reason).strip():
            override_used = True
        else:
            raise ValueError(
                f"Promotion refused for {normalized}: {'; '.join(reasons)}. "
                "Pass an override_reason to override (audited)."
            )

    manifest["runtime_enabled"] = True
    manifest["promoted_by"] = promoted_by
    manifest["promoted_at"] = _now_iso()
    if override_used:
        manifest["last_promotion_override_reason"] = override_reason

    _atomic_write_json(folder / "manifest.json", manifest)

    action = "override_promote" if override_used else "promote_runtime"
    audit_entry = record_audit_event(
        actor=promoted_by,
        action=action,
        slug=normalized,
        previous_status=previous_status,
        new_status=manifest.get("review_status"),
        previous_runtime_enabled=previous_runtime_enabled,
        new_runtime_enabled=True,
        qa_score=meta.overall_quality_score if meta else None,
        blocking_issues_count=len(blocking_issues),
        override_used=override_used,
        override_reason=override_reason if override_used else None,
        changed_files=[str(folder / "manifest.json")],
    )

    index_rebuilt = _rebuild_registry_index()

    detail = _build_detail_dto(normalized, manifest, folder)

    return {
        "slug": normalized,
        "previous_status": previous_status,
        "new_status": manifest.get("review_status"),
        "runtime_enabled": True,
        "validation_result": "blocked" if blocking_validation and not override_used else "passed",
        "validation_warnings": validation_warnings,
        "warnings": [w.message for w in validation_warnings if w.severity == "warning"],
        "override_used": override_used,
        "override_reason": override_reason if override_used else None,
        "registry_index_rebuilt": index_rebuilt,
        "audit_entry_id": audit_entry["id"],
        "audit_log_path": str(AUDIT_LOG_PATH),
        "detail": detail,
    }
