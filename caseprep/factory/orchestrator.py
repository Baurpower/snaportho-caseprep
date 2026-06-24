"""
Orchestrate: extract → synthesize → QA → manifest update (human review queue).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from caseprep.registry.validation import score_modules
from caseprep.factory.extractor import extract_knowledge, write_extracted_knowledge
from caseprep.factory.generation_meta import write_generation_meta
from caseprep.factory.paths import (
    GENERATION_META_FILENAME,
    MANIFEST_FILENAME,
    MODULES_FILENAME,
    REGISTRY_ROOT,
    procedure_dir,
)
from caseprep.factory.qa_agent import score_generated_modules
from caseprep.factory.reviewer_agent import reviewer_suggestions
from caseprep.factory.schemas import GenerationMeta
from caseprep.factory.synthesizer import synthesize_modules


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def update_manifest_for_review(
    slug: str,
    *,
    meta: GenerationMeta,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Set non-runtime review state after factory generation.

    Never sets certified, review_status=certified, or runtime_enabled=true.
    """
    manifest_path = procedure_dir(slug) / MANIFEST_FILENAME
    manifest = _load_json(manifest_path, {}) or {}
    if not manifest:
        raise FileNotFoundError(f"manifest.json missing for {slug}")

    manifest["content_status"] = "draft"
    manifest["review_status"] = "needs_review"
    manifest["coverage_score"] = meta.coverage_score
    manifest["last_reviewed_at"] = _utc_now_iso()
    manifest["factory_status"] = "needs_review"
    manifest["factory_last_generated_at"] = meta.generated_at
    manifest["factory_overall_quality_score"] = meta.overall_quality_score
    # Explicitly preserve runtime safety
    if manifest.get("runtime_enabled"):
        # Do not disable existing runtime on certified procedures when re-generating draft
        pass
    else:
        manifest["runtime_enabled"] = False

    if not dry_run:
        _write_json(manifest_path, manifest)
    return manifest


def generate_procedure_draft(
    slug: str,
    *,
    dry_run: bool = False,
    use_llm: bool = True,
    force: bool = False,
) -> Dict[str, Any]:
    folder = procedure_dir(slug)
    if not folder.is_dir():
        raise FileNotFoundError(f"Procedure not found: {slug}")

    manifest = _load_json(folder / MANIFEST_FILENAME, {}) or {}
    content_status = str(manifest.get("content_status") or "")
    if content_status == "certified" and not force:
        raise RuntimeError(
            f"{slug} is certified. Use --force to generate a draft without changing runtime."
        )

    knowledge = extract_knowledge(slug, manifest=manifest)
    modules = synthesize_modules(knowledge, manifest=manifest, use_llm=use_llm)
    meta = score_generated_modules(modules, knowledge, manifest)
    suggestions = reviewer_suggestions(modules, knowledge, meta)
    meta.suggested_revision_actions = list(dict.fromkeys(meta.suggested_revision_actions + suggestions))

    result = {
        "slug": slug,
        "dry_run": dry_run,
        "coverage_score": meta.coverage_score,
        "overall_quality_score": meta.overall_quality_score,
        "blocking_issues": meta.blocking_issues,
        "warnings": meta.warnings,
        "extraction_confidence": knowledge.confidence_score,
    }

    if dry_run:
        result["modules_preview"] = {k: len(v) if isinstance(v, list) else 0 for k, v in modules.items()}
        return result

    write_extracted_knowledge(slug, knowledge)
    _write_json(folder / MODULES_FILENAME, modules)
    write_generation_meta(folder / GENERATION_META_FILENAME, meta)
    update_manifest_for_review(slug, meta=meta, dry_run=False)

    return result


def list_batch_candidates(
    *,
    limit: int = 5,
    min_coverage: int = 0,
    max_coverage: int = 84,
    include_certified: bool = False,
) -> List[Dict[str, Any]]:
    if not REGISTRY_ROOT.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for folder in sorted(REGISTRY_ROOT.iterdir()):
        if not folder.is_dir():
            continue
        manifest = _load_json(folder / MANIFEST_FILENAME, {}) or {}
        if not manifest:
            continue
        slug = folder.name
        cs = str(manifest.get("content_status") or "")
        if cs == "certified" and not include_certified:
            continue
        if cs == "deprecated":
            continue
        score = int(manifest.get("coverage_score") or 0)
        if score < min_coverage or score > max_coverage:
            continue
        rows.append(
            {
                "slug": slug,
                "display_name": manifest.get("display_name", slug),
                "content_status": cs,
                "coverage_score": score,
            }
        )
    rows.sort(key=lambda r: (r["coverage_score"], r["slug"]))
    return rows[:limit]