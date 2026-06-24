"""
Read-only CasePrep registry service for surgeon review APIs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from caseprep.registry.constants import INDICATIONS_TRANSITIONAL_WARNING, REQUIRED_SECTIONS
from caseprep.registry.dto import (
    ProcedureDetailDTO,
    ProcedureSummaryDTO,
    RegistryHealthDTO,
    RegistryIndexDTO,
    ValidationWarningDTO,
)
from caseprep.registry.mappers import (
    build_clinical_sections,
    build_source_dtos,
    excerpt_review_notes,
    load_aliases,
)
from caseprep.registry.validation import (
    collect_module_text,
    cross_region_warnings,
    is_low_coverage,
    modules_from_payload,
    modules_have_content,
    placeholder_hits,
    score_modules,
    section_has_content,
)

BASE_DIR = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = BASE_DIR / "data" / "caseprep" / "procedures"
REGISTRY_INDEX_PATH = BASE_DIR / "data" / "caseprep" / "registry_index.json"

_SLUG_PATTERN = re.compile(r"^[a-z0-9_]+$")


class ProcedureNotFoundError(Exception):
    """Raised when a registry procedure slug cannot be resolved."""


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


def list_procedure_folders() -> List[Path]:
    if not REGISTRY_ROOT.exists():
        return []
    return sorted(
        [path for path in REGISTRY_ROOT.iterdir() if path.is_dir()],
        key=lambda path: path.name,
    )


def _load_manifest(folder: Path) -> Optional[Dict[str, Any]]:
    return _load_json(folder / "manifest.json")


def _certified_payload_exists(folder: Path) -> bool:
    payload_path = folder / "certified_payload.json"
    return payload_path.exists() and payload_path.is_file()


def compute_is_live(manifest: Dict[str, Any], folder: Path) -> bool:
    return bool(
        manifest.get("runtime_enabled")
        and manifest.get("content_status") == "certified"
        and manifest.get("review_status") == "certified"
        and not manifest.get("deprecated")
        and _certified_payload_exists(folder)
    )


def _resolve_modules(folder: Path) -> Tuple[Dict[str, Any], bool]:
    modules = _load_json(folder / "modules.json", {}) or {}
    used_payload_fallback = False

    if not modules_have_content(modules):
        payload = _load_json(folder / "certified_payload.json")
        if payload:
            modules = modules_from_payload(payload)
            used_payload_fallback = True

    return modules, used_payload_fallback


def _load_sources(folder: Path, payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sources = _read_jsonl(folder / "sources.jsonl")
    if sources:
        return sources

    if not payload:
        return []

    urls = payload.get("source_urls") or []
    rows: List[Dict[str, Any]] = []
    for url in urls:
        if isinstance(url, str) and url.strip():
            rows.append(
                {
                    "source_type": "orthobullets",
                    "url": url.strip(),
                    "title": payload.get("procedure_name"),
                    "consumed": True,
                }
            )
    return rows


def _count_open_validation_warnings(warnings: List[ValidationWarningDTO]) -> int:
    return sum(1 for warning in warnings if warning.severity in {"warning", "blocking"})


def build_validation_warnings(
    *,
    slug: str,
    manifest: Dict[str, Any],
    modules: Dict[str, Any],
    sources: List[Dict[str, Any]],
    folder: Path,
    coverage_score: int,
) -> List[ValidationWarningDTO]:
    warnings: List[ValidationWarningDTO] = []
    body_region = str(manifest.get("body_region") or "")
    content_status = str(manifest.get("content_status") or "")
    would_be_live_without_payload = bool(
        manifest.get("runtime_enabled")
        and content_status == "certified"
        and manifest.get("review_status") == "certified"
        and not manifest.get("deprecated")
    )

    if would_be_live_without_payload and not _certified_payload_exists(folder):
        warnings.append(
            ValidationWarningDTO(
                code="missing_certified_payload",
                severity="blocking",
                section_key=None,
                message=(
                    f"{manifest.get('display_name') or slug} is marked certified for runtime "
                    "but the certified payload file is missing."
                ),
            )
        )

    module_text = collect_module_text(modules)
    for pattern in placeholder_hits(module_text):
        warnings.append(
            ValidationWarningDTO(
                code="placeholder_detected",
                severity="warning",
                section_key=None,
                message=f"Placeholder language detected: '{pattern}'.",
                detail=pattern,
            )
        )

    for message in cross_region_warnings(body_region, module_text):
        warnings.append(
            ValidationWarningDTO(
                code="cross_region_term",
                severity="warning",
                section_key=None,
                message=message,
            )
        )

    if is_low_coverage(coverage_score, content_status):
        warnings.append(
            ValidationWarningDTO(
                code="low_coverage",
                severity="warning" if content_status != "certified" else "blocking",
                section_key=None,
                message=f"Coverage score {coverage_score} is below the expected threshold.",
            )
        )

    for section_key in REQUIRED_SECTIONS:
        if not section_has_content(modules.get(section_key)):
            if section_key == "indications" and INDICATIONS_TRANSITIONAL_WARNING:
                warnings.append(
                    ValidationWarningDTO(
                        code="missing_indications_transition",
                        severity="warning",
                        section_key=section_key,
                        message=(
                            "Indications section is empty. Required for new certification; "
                            "existing certified procedures are in a transitional grace period."
                        ),
                    )
                )
            else:
                warnings.append(
                    ValidationWarningDTO(
                        code="empty_required_section",
                        severity="warning",
                        section_key=section_key,
                        message=f"The required section '{section_key.replace('_', ' ')}' is empty.",
                    )
                )

    if content_status in {"certified", "complete", "partial"} and not sources:
        warnings.append(
            ValidationWarningDTO(
                code="missing_sources",
                severity="warning",
                section_key="sources",
                message="No source references are linked to this procedure.",
            )
        )

    return warnings


def _summary_from_manifest(
    folder: Path,
    manifest: Dict[str, Any],
    *,
    include_validation: bool = False,
) -> ProcedureSummaryDTO:
    slug = str(manifest.get("slug") or folder.name)
    modules, _ = _resolve_modules(folder)
    payload = _load_json(folder / "certified_payload.json")
    coverage_score = int(manifest.get("coverage_score") or score_modules(modules, payload))

    open_validation_count = 0
    if include_validation:
        sources = _load_sources(folder, payload)
        warnings = build_validation_warnings(
            slug=slug,
            manifest=manifest,
            modules=modules,
            sources=sources,
            folder=folder,
            coverage_score=coverage_score,
        )
        open_validation_count = _count_open_validation_warnings(warnings)

    return ProcedureSummaryDTO(
        slug=slug,
        display_name=str(manifest.get("display_name") or slug),
        specialty=str(manifest.get("specialty") or "unknown"),
        body_region=str(manifest.get("body_region") or "unknown"),
        procedure_family=str(manifest.get("procedure_family") or "general"),
        content_status=str(manifest.get("content_status") or "missing"),
        review_status=str(manifest.get("review_status") or "unreviewed"),
        coverage_score=coverage_score,
        is_live=compute_is_live(manifest, folder),
        deprecated=bool(manifest.get("deprecated")),
        replacement_slug=manifest.get("replacement_slug"),
        has_modules=modules_have_content(modules),
        open_validation_count=open_validation_count,
    )


def get_health() -> RegistryHealthDTO:
    folders = list_procedure_folders()
    registry_available = REGISTRY_ROOT.exists() and bool(folders)

    if not registry_available:
        return RegistryHealthDTO(
            status="unavailable",
            registry_available=False,
            procedure_count=0,
            certified_count=0,
            index_generated_at=None,
        )

    certified_count = 0
    for folder in folders:
        manifest = _load_manifest(folder)
        if manifest and compute_is_live(manifest, folder):
            certified_count += 1

    index = _load_json(REGISTRY_INDEX_PATH, {}) or {}
    index_generated_at = index.get("generated_at")

    status = "ok"
    if not index_generated_at:
        status = "degraded"

    return RegistryHealthDTO(
        status=status,
        registry_available=True,
        procedure_count=len(folders),
        certified_count=certified_count,
        index_generated_at=index_generated_at,
    )


def get_index() -> RegistryIndexDTO:
    index = _load_json(REGISTRY_INDEX_PATH, {}) or {}
    folders = {folder.name: folder for folder in list_procedure_folders()}

    procedures: List[ProcedureSummaryDTO] = []
    counts_by_content_status: Dict[str, int] = {}
    counts_by_review_status: Dict[str, int] = {}

    index_rows = index.get("procedures") or []
    if index_rows:
        for row in index_rows:
            slug = str(row.get("slug") or "").strip()
            folder = folders.get(slug)
            if not folder:
                continue
            manifest = _load_manifest(folder)
            if not manifest:
                continue
            summary = _summary_from_manifest(folder, manifest, include_validation=True)
            procedures.append(summary)
            counts_by_content_status[summary.content_status] = (
                counts_by_content_status.get(summary.content_status, 0) + 1
            )
            counts_by_review_status[summary.review_status] = (
                counts_by_review_status.get(summary.review_status, 0) + 1
            )
    else:
        for folder in folders.values():
            manifest = _load_manifest(folder)
            if not manifest:
                continue
            summary = _summary_from_manifest(folder, manifest, include_validation=True)
            procedures.append(summary)
            counts_by_content_status[summary.content_status] = (
                counts_by_content_status.get(summary.content_status, 0) + 1
            )
            counts_by_review_status[summary.review_status] = (
                counts_by_review_status.get(summary.review_status, 0) + 1
            )

    procedures.sort(key=lambda row: row.display_name.lower())

    if not counts_by_content_status and index.get("counts_by_content_status"):
        counts_by_content_status = dict(index.get("counts_by_content_status") or {})
    if not counts_by_review_status and index.get("counts_by_review_status"):
        counts_by_review_status = dict(index.get("counts_by_review_status") or {})

    return RegistryIndexDTO(
        generated_at=index.get("generated_at"),
        counts_by_content_status=counts_by_content_status,
        counts_by_review_status=counts_by_review_status,
        procedures=procedures,
    )


def get_procedure_detail(slug: str, *, include_validation: bool = False) -> ProcedureDetailDTO:
    normalized = (slug or "").strip().lower()
    if not normalized or not _SLUG_PATTERN.match(normalized):
        raise ProcedureNotFoundError(slug)

    folder = REGISTRY_ROOT / normalized
    if not folder.is_dir():
        raise ProcedureNotFoundError(slug)

    manifest = _load_manifest(folder)
    if not manifest:
        raise ProcedureNotFoundError(slug)

    modules, _ = _resolve_modules(folder)
    payload = _load_json(folder / "certified_payload.json")
    aliases_obj = _load_json(folder / "aliases.json", {}) or {}
    sources = _load_sources(folder, payload)
    review_notes = None
    review_notes_path = folder / "review_notes.md"
    if review_notes_path.exists():
        review_notes = review_notes_path.read_text(encoding="utf-8")

    coverage_score = int(manifest.get("coverage_score") or score_modules(modules, payload))
    sections = build_clinical_sections(modules, sources)
    source_dtos = build_source_dtos(sources, modules)

    validation_warnings: List[ValidationWarningDTO] = []
    if include_validation:
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
        review_notes_excerpt=excerpt_review_notes(review_notes),
        runtime_enabled=bool(manifest.get("runtime_enabled")),
    )