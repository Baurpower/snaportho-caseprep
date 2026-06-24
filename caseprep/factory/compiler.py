"""
Compile modules.json → brobot_case_prep_payload_v2 (deterministic).

Default output is certified_payload.draft.json — not runtime.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from caseprep.registry.constants import MODULE_SECTIONS, REQUIRED_SECTIONS
from caseprep.registry.validation import section_has_content
from caseprep.factory.audit_log import AUDIT_LOG_PATH, record_audit_event
from caseprep.factory.generation_meta import load_generation_meta
from caseprep.factory.paths import (
    CERTIFIED_PAYLOAD_FILENAME,
    DRAFT_PAYLOAD_FILENAME,
    GENERATION_META_FILENAME,
    MANIFEST_FILENAME,
    MODULES_FILENAME,
    SOURCES_FILENAME,
    procedure_dir,
)

# review_status values that satisfy promotion eligibility. "approved" lets the
# review -> approve -> certify -> promote CLI workflow gate promotion right
# after a human approves; "certified" covers content already taken through
# the full registry certify_procedure step.
_PROMOTABLE_REVIEW_STATUSES = frozenset({"approved", "certified"})

_APPROACH_LAYER_PREFIXES = (
    "superficial:",
    "deep:",
    "deep joint:",
    "interval:",
    "layer:",
)

_STUDY_CHECKLIST_MARKERS = (
    "review linked modules",
    "memorize key sar",
    "walk through the night-before",
    "practice the 10+ pimp",
    "night-before checklist",
)


class CompilerError(Exception):
    """Raised when modules cannot be compiled safely."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _payload_hash(obj: Dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _is_approach_layer_bullet(text: str) -> bool:
    low = text.strip().lower()
    return any(low.startswith(prefix) for prefix in _APPROACH_LAYER_PREFIXES)


def _split_setup_positioning(
    setup: List[str],
    *,
    existing_overview: Optional[str] = None,
) -> Tuple[str, List[str], List[str]]:
    overview = existing_overview or ""
    must_know: List[str] = []
    approach_anatomy: List[str] = []

    for raw in setup:
        text = (raw or "").strip()
        if not text:
            continue
        low = text.lower()
        if not overview and (
            "certified" in low
            or "source-backed" in low
            or text.endswith(".")
            and len(text) < 180
            and "approach:" not in low
            and not _is_approach_layer_bullet(text)
            and setup.index(raw) == 0
        ):
            overview = text
            continue
        if _is_approach_layer_bullet(text):
            approach_anatomy.append(text)
        else:
            must_know.append(text)

    if not overview and must_know:
        overview = must_know.pop(0)

    return overview, must_know, approach_anatomy


def _normalize_sar(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "structure": str(item.get("structure") or "").strip(),
        "why_at_risk": str(item.get("why_at_risk") or "").strip(),
        "how_to_avoid_injury": str(item.get("how_to_avoid_injury") or "").strip(),
        "consequence_of_injury": str(item.get("consequence_of_injury") or "").strip(),
        **(
            {"approach_context": str(item["approach_context"]).strip()}
            if item.get("approach_context")
            else {}
        ),
        **(
            {"source_refs": [str(u) for u in item["source_refs"] if u]}
            if item.get("source_refs")
            else {}
        ),
    }


def _normalize_layer(item: Dict[str, Any]) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "layer_name": str(item.get("layer_name") or "").strip(),
        "what_user_should_know": str(item.get("what_user_should_know") or "").strip(),
        "key_structures": [str(v).strip() for v in (item.get("key_structures") or []) if str(v).strip()],
        "structures_at_risk": [
            str(v).strip() for v in (item.get("structures_at_risk") or []) if str(v).strip()
        ],
        "surgical_relevance": str(item.get("surgical_relevance") or "").strip(),
    }
    refs = item.get("source_refs") or []
    if refs:
        row["source_refs"] = [str(u) for u in refs if u]
    return row


def _pimp_to_strings(items: List[Any]) -> List[str]:
    out: List[str] = []
    for item in items:
        if isinstance(item, str):
            text = item.strip()
            if text:
                out.append(text)
        elif isinstance(item, dict):
            q = str(item.get("question") or "").strip()
            a = str(item.get("answer") or "").strip()
            if q and a:
                out.append(f"Q: {q} A: {a}")
            elif q:
                out.append(f"Q: {q}")
    return out


def _validate_required_sections(modules: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    for key in REQUIRED_SECTIONS:
        if not section_has_content(modules.get(key)):
            missing.append(key)
    return missing


def compile_modules_to_payload(
    modules: Dict[str, Any],
    *,
    slug: str,
    manifest: Dict[str, Any],
    sources: Optional[List[Dict[str, Any]]] = None,
    existing_payload: Optional[Dict[str, Any]] = None,
    strict: bool = True,
) -> Dict[str, Any]:
    """
    Convert registry modules.json to brobot_case_prep_payload_v2.

    Raises CompilerError when strict=True and required sections are empty.
    """
    if strict:
        missing = _validate_required_sections(modules)
        if missing:
            raise CompilerError(
                f"Missing required sections for compile: {', '.join(missing)}"
            )

    existing = existing_payload or {}
    display_name = str(manifest.get("display_name") or slug)

    setup = [str(v).strip() for v in (modules.get("setup_positioning") or []) if str(v).strip()]
    overview, must_know, approach_anatomy = _split_setup_positioning(
        setup,
        existing_overview=existing.get("procedure_overview"),
    )

    if not overview:
        overview = f"{display_name} — AI-drafted CasePrep modules (pending human review)."

    sar = [
        _normalize_sar(item)
        for item in (modules.get("structures_at_risk") or [])
        if isinstance(item, dict) and item.get("structure")
    ]
    layers = [
        _normalize_layer(item)
        for item in (modules.get("surgical_layers") or [])
        if isinstance(item, dict) and item.get("layer_name")
    ]

    source_urls: List[str] = []
    if sources:
        for row in sources:
            url = str(row.get("url") or "").strip()
            if url and url not in source_urls:
                source_urls.append(url)
    if not source_urls:
        source_urls = list(existing.get("source_urls") or [])

    postop = [
        str(v).strip()
        for v in (modules.get("postop_plan") or [])
        if str(v).strip()
    ]

    payload: Dict[str, Any] = {
        "schema_version": "brobot_case_prep_payload_v2",
        "procedure_id": slug,
        "procedure_name": display_name,
        "case_prep_status": existing.get("case_prep_status", "draft"),
        "procedure_overview": overview,
        "must_know_anatomy": must_know,
        "surgical_approach_anatomy": approach_anatomy,
        "key_landmarks": [
            str(v).strip()
            for v in (modules.get("approach_landmarks") or [])
            if str(v).strip()
        ],
        "surgical_layers": layers,
        "structures_at_risk": sar,
        "reduction_or_implant_anatomy": [
            str(v).strip()
            for v in (modules.get("implant_strategy") or [])
            if str(v).strip()
        ],
        "fluoroscopy_checkpoints": [
            str(v).strip()
            for v in (modules.get("reduction_or_fluoro_checkpoints") or [])
            if str(v).strip()
        ],
        "common_mistakes": [
            str(v).strip() for v in (modules.get("pitfalls") or []) if str(v).strip()
        ],
        "attending_pimp_questions": _pimp_to_strings(
            modules.get("attending_pimp_questions") or []
        ),
        "night_before_review_checklist": postop,
        "source_urls": source_urls,
        "source_confidence": existing.get("source_confidence", "medium"),
        "limitations": existing.get(
            "limitations",
            [
                "Factory-drafted content pending human review; verify before clinical use.",
                "Anatomy-focused case prep only; does not replace attending-specific preferences.",
            ],
        ),
        "anatomy_category": existing.get(
            "anatomy_category", manifest.get("procedure_family", "procedure")
        ),
        "approach_id": existing.get("approach_id", slug),
        "approach_name": existing.get("approach_name", display_name),
        "arthroscopy_or_portal_anatomy": existing.get("arthroscopy_or_portal_anatomy", []),
        "payload_quality_status": "factory_draft",
        "source_status": "factory_extracted",
    }

    indications = [
        str(v).strip() for v in (modules.get("indications") or []) if str(v).strip()
    ]
    if indications:
        payload["indications"] = indications

    if existing.get("validation_warnings"):
        payload["validation_warnings"] = existing["validation_warnings"]
    if existing.get("approach_specific_notes"):
        payload["approach_specific_notes"] = existing["approach_specific_notes"]
    if existing.get("danger_zones"):
        payload["danger_zones"] = existing["danger_zones"]

    return payload


def evaluate_promotion_readiness(
    manifest: Dict[str, Any],
    *,
    folder: Path,
    override_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Decide whether a procedure may have its certified_payload.json
    overwritten ("promoted" from draft to certified content).

    Returns {"eligible": bool, "reasons": [...], "override_used": bool,
    "blocking_issues": [...], "qa_score": Optional[float]}.

    Required-section / compiles-cleanly checks are enforced separately by
    compile_modules_to_payload(strict=True), which always runs before this
    check — this function only covers review-gate and QA-gate concerns.
    """
    reasons: List[str] = []

    review_status = str(manifest.get("review_status") or "")
    if review_status not in _PROMOTABLE_REVIEW_STATUSES:
        reasons.append(
            f"review_status is '{review_status or 'unset'}', requires one of "
            f"{sorted(_PROMOTABLE_REVIEW_STATUSES)}"
        )

    meta = load_generation_meta(folder / GENERATION_META_FILENAME)
    blocking_issues = list(meta.blocking_issues) if meta else []
    if blocking_issues:
        reasons.append(f"{len(blocking_issues)} blocking QA issue(s) present")

    eligible = not reasons
    override_used = False
    if reasons and override_reason and str(override_reason).strip():
        override_used = True
        eligible = True

    return {
        "eligible": eligible,
        "reasons": reasons,
        "override_used": override_used,
        "blocking_issues": blocking_issues,
        "qa_score": meta.overall_quality_score if meta else None,
    }


def compile_procedure(
    slug: str,
    *,
    promote: bool = False,
    dry_run: bool = False,
    strict: bool = True,
    update_manifest_hash: bool = False,
    actor: Optional[str] = None,
    override_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compile on-disk modules.json for a procedure slug.

    Writes certified_payload.draft.json by default. Writing the live
    certified_payload.json (promote=True) is guarded: it requires the
    procedure's review_status to be 'approved' or 'certified' and zero
    blocking QA issues, an identified human actor, and never sets
    runtime_enabled — that is a separate, explicitly audited step
    (see registry_write_service.promote_to_runtime).
    """
    folder = procedure_dir(slug)
    if not folder.is_dir():
        raise CompilerError(f"Procedure folder not found: {slug}")

    modules = _load_json(folder / MODULES_FILENAME, {}) or {}
    manifest = _load_json(folder / MANIFEST_FILENAME, {}) or {}
    sources = _read_jsonl(folder / SOURCES_FILENAME)
    existing_payload = _load_json(folder / CERTIFIED_PAYLOAD_FILENAME)

    payload = compile_modules_to_payload(
        modules,
        slug=slug,
        manifest=manifest,
        sources=sources,
        existing_payload=existing_payload,
        strict=strict,
    )

    readiness: Optional[Dict[str, Any]] = None
    if promote:
        if not actor or not str(actor).strip():
            raise CompilerError(
                "Promoting certified_payload.json requires an explicit human "
                "actor identifier (--actor)."
            )
        readiness = evaluate_promotion_readiness(
            manifest, folder=folder, override_reason=override_reason
        )
        if not readiness["eligible"]:
            raise CompilerError(
                f"Promotion refused for {slug}: {'; '.join(readiness['reasons'])}. "
                "Pass --override-with-reason \"...\" to override (audited)."
            )

    out_name = CERTIFIED_PAYLOAD_FILENAME if promote else DRAFT_PAYLOAD_FILENAME
    out_path = folder / out_name

    result = {
        "slug": slug,
        "output_path": str(out_path),
        "promote": promote,
        "dry_run": dry_run,
        "payload_hash": _payload_hash(payload),
        "procedure_id": payload.get("procedure_id"),
        "override_used": bool(readiness and readiness["override_used"]),
    }

    if dry_run:
        return result

    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    if update_manifest_hash and manifest:
        manifest["source_payload_hash"] = result["payload_hash"]
        manifest["last_reviewed_at"] = _utc_now_iso()
        if promote and readiness and readiness["override_used"]:
            manifest["last_promotion_override_reason"] = override_reason
        with (folder / MANIFEST_FILENAME).open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    if not dry_run:
        if promote:
            action = "override_certify" if readiness and readiness["override_used"] else "certify"
        else:
            action = "compile_draft"
        audit_entry = record_audit_event(
            actor=actor or "unknown",
            action=action,
            slug=slug,
            previous_status=str(manifest.get("review_status") or ""),
            new_status=str(manifest.get("review_status") or ""),
            previous_runtime_enabled=bool(manifest.get("runtime_enabled")),
            new_runtime_enabled=bool(manifest.get("runtime_enabled")),
            qa_score=readiness["qa_score"] if readiness else None,
            blocking_issues_count=len(readiness["blocking_issues"]) if readiness else 0,
            override_used=bool(readiness and readiness["override_used"]),
            override_reason=override_reason if (readiness and readiness["override_used"]) else None,
            changed_files=[str(out_path)],
        )
        result["audit_entry_id"] = audit_entry["id"]
        result["audit_log_path"] = str(AUDIT_LOG_PATH)

    return result


def is_study_checklist_postop(bullets: List[str]) -> bool:
    """Detect night-before study checklist masquerading as post-op protocol."""
    if not bullets:
        return False
    hits = 0
    for bullet in bullets:
        low = bullet.lower()
        if any(marker in low for marker in _STUDY_CHECKLIST_MARKERS):
            hits += 1
    return hits >= 2 or (len(bullets) <= 5 and hits >= 1)