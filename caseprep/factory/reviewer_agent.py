"""
Pre-human reviewer suggestions (non-blocking).
"""

from __future__ import annotations

from typing import Any, Dict, List

from caseprep.factory.schemas import ExtractedKnowledge, GenerationMeta


def reviewer_suggestions(
    modules: Dict[str, Any],
    knowledge: ExtractedKnowledge,
    meta: GenerationMeta,
) -> List[str]:
    suggestions: List[str] = []

    if meta.overall_quality_score >= 85 and not meta.blocking_issues:
        suggestions.append("Fast-track candidate: overall QA ≥85 with no blocking issues.")
    else:
        suggestions.append("Standard review: address blocking issues before approval.")

    if len(modules.get("indications") or []) <= 1:
        suggestions.append("Expand indications with procedure-specific clinical criteria.")

    if not modules.get("implant_strategy"):
        suggestions.append("Consider adding implant_strategy if applicable to this procedure.")

    if not modules.get("reduction_or_fluoro_checkpoints"):
        suggestions.append("Add fluoroscopy/reduction checkpoints if fixation or alignment is relevant.")

    if knowledge.confidence_score < 0.5:
        suggestions.append("Source library is thin — attending should verify all anatomy claims.")

    if meta.attending_relevance_score < 60:
        suggestions.append("Strengthen attending_pimp_questions with approach-specific Q/A pairs.")

    return suggestions