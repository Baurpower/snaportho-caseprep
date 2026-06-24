"""
QA scoring for factory-drafted modules.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from caseprep.registry.constants import (
    MODULE_SECTIONS,
    PLACEHOLDER_PATTERNS,
    REQUIRED_SECTIONS,
)
from caseprep.registry.validation import (
    collect_module_text,
    cross_region_warnings,
    placeholder_hits,
    score_modules,
    section_has_content,
)
from caseprep.factory.compiler import is_study_checklist_postop
from caseprep.factory.schemas import ExtractedKnowledge, GenerationMeta


_GENERIC_PIMP = re.compile(
    r"key (approach|structure) for this case|primary structure at risk\?",
    re.IGNORECASE,
)


def _sar_complete(rows: List[Any]) -> Tuple[int, int]:
    ok = 0
    total = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        total += 1
        fields = ("structure", "why_at_risk", "how_to_avoid_injury", "consequence_of_injury")
        if all(str(row.get(f, "")).strip() for f in fields):
            ok += 1
    return ok, total


def _source_grounding(modules: Dict[str, Any], knowledge: ExtractedKnowledge) -> float:
    if not knowledge.source_refs:
        return 20.0
    sar = modules.get("structures_at_risk") or []
    with_refs = sum(
        1 for row in sar if isinstance(row, dict) and (row.get("source_refs") or knowledge.source_refs)
    )
    sar_score = (with_refs / max(len(sar), 1)) * 40.0
    has_sources = 30.0 if knowledge.source_refs else 0.0
    setup_len = len(modules.get("setup_positioning") or [])
    setup_score = min(30.0, setup_len * 5.0)
    return min(100.0, sar_score + has_sources + setup_score)


def score_generated_modules(
    modules: Dict[str, Any],
    knowledge: ExtractedKnowledge,
    manifest: Dict[str, Any],
) -> GenerationMeta:
    body_region = str(manifest.get("body_region") or "")
    text = collect_module_text(modules)

    blocking: List[str] = []
    warnings: List[str] = []
    actions: List[str] = []

    # Placeholders
    for pattern in placeholder_hits(text):
        blocking.append(f"Placeholder language detected: '{pattern}'")
        actions.append(f"Replace placeholder text matching '{pattern}'.")

    # Required sections
    for key in REQUIRED_SECTIONS:
        if not section_has_content(modules.get(key)):
            blocking.append(f"Required section empty: {key}")
            actions.append(f"Author content for section '{key}'.")

    # SAR completeness
    sar_ok, sar_total = _sar_complete(modules.get("structures_at_risk") or [])
    if sar_total < 3:
        blocking.append(f"structures_at_risk has {sar_total} entries; need at least 3.")
        actions.append("Add at least 3 complete structures_at_risk entries.")
    elif sar_ok < sar_total:
        warnings.append(f"{sar_total - sar_ok} SAR entries missing required fields.")

    # Post-op study checklist contamination
    postop = modules.get("postop_plan") or []
    if is_study_checklist_postop([str(v) for v in postop]):
        blocking.append("postop_plan contains night-before study checklist content.")
        actions.append("Rewrite postop_plan as clinical postoperative protocol bullets.")

    # Cross-region
    for msg in cross_region_warnings(body_region, text):
        warnings.append(msg)

    # Pimp quality
    pimp = modules.get("attending_pimp_questions") or []
    generic_pimp = 0
    for item in pimp:
        blob = item if isinstance(item, str) else f"{item.get('question', '')} {item.get('answer', '')}"
        if _GENERIC_PIMP.search(blob):
            generic_pimp += 1
    if generic_pimp:
        warnings.append(f"{generic_pimp} generic pimp question(s) detected.")

    # Low extraction confidence
    if knowledge.confidence_score < 0.35:
        warnings.append(
            f"Low extraction confidence ({knowledge.confidence_score}); sparse source library."
        )
        actions.append("Add or link orthobullets sources before certification.")

    for w in knowledge.extraction_warnings:
        warnings.append(f"Extraction: {w}")

    source_grounding = _source_grounding(modules, knowledge)
    coverage = score_modules(modules)
    structural = float(coverage)

    sar_score = min(100.0, (sar_ok / max(sar_total, 1)) * 100.0)
    layer_count = len(modules.get("surgical_layers") or [])
    landmark_count = len(modules.get("approach_landmarks") or [])
    or_preparedness = min(100.0, sar_score * 0.5 + min(layer_count, 3) / 3.0 * 25.0 + min(landmark_count, 4) / 4.0 * 25.0)

    setup_count = len(modules.get("setup_positioning") or [])
    pitfall_count = len(modules.get("pitfalls") or [])
    resident_utility = min(100.0, setup_count * 8.0 + pitfall_count * 10.0)

    pimp_count = len(pimp)
    attending = min(100.0, max(0.0, pimp_count * 15.0 - generic_pimp * 20.0))

    clinical_accuracy = min(100.0, source_grounding * 0.6 + sar_score * 0.4)
    hallucination_risk = max(0.0, 100.0 - source_grounding)

    overall = (
        source_grounding * 0.20
        + structural * 0.15
        + clinical_accuracy * 0.20
        + or_preparedness * 0.15
        + resident_utility * 0.10
        + attending * 0.10
        + (100.0 - hallucination_risk) * 0.10
    )

    if blocking:
        overall = min(overall, 69.0)

    return GenerationMeta(
        procedure_id=str(manifest.get("slug") or knowledge.procedure_id),
        generated_at=knowledge.extracted_at,
        source_grounding_score=round(source_grounding, 1),
        structural_completeness_score=round(structural, 1),
        clinical_accuracy_score=round(clinical_accuracy, 1),
        or_preparedness_score=round(or_preparedness, 1),
        resident_utility_score=round(resident_utility, 1),
        attending_relevance_score=round(attending, 1),
        hallucination_risk_score=round(hallucination_risk, 1),
        overall_quality_score=round(overall, 1),
        coverage_score=coverage,
        blocking_issues=blocking,
        warnings=warnings,
        suggested_revision_actions=actions,
        review_status="needs_review",
        runtime_promoted=False,
        certified=False,
    )