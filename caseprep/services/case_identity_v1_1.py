from __future__ import annotations

import re
from typing import Any, Dict


def _first(value: Any) -> str | None:
    if isinstance(value, list):
        return str(value[0]) if value else None
    return str(value) if value else None


def build_case_identity(
    prompt: str, resolved: Dict[str, Any], refined: Dict[str, Any]
) -> Dict[str, Any]:
    age_match = re.search(r"\b(\d{1,3})\s*(?:yo|y/o|year[- ]old)\b", prompt, re.I)
    laterality_match = re.search(r"\b(left|right|bilateral)\b", prompt, re.I)
    return {
        "requested_case": prompt,
        "canonical_slug": resolved.get("procedure_slug"),
        "canonical_name": resolved.get("canonical_display_name") or None,
        "diagnosis": _first(refined.get("diagnoses")),
        "approach": resolved.get("requested_approach") or _first(refined.get("approaches")),
        "specialty": _first(refined.get("specialties")),
        "region": refined.get("region") or None,
        "subregion": refined.get("subregion") or None,
        "laterality": laterality_match.group(1).lower() if laterality_match else None,
        "patient_age": int(age_match.group(1)) if age_match else None,
        "resolver_method": resolved.get("match_method") or "none",
        "confidence": float(resolved.get("confidence") or resolved.get("match_score") or 0.0),
        "requires_clarification": bool(resolved.get("requires_clarification")),
        "clarification_reason": resolved.get("clarification_reason"),
    }


def enrich_refined_query(
    refined: Any, resolved: Dict[str, Any], prompt: str
) -> Dict[str, Any]:
    output = dict(refined) if isinstance(refined, dict) else {"search_text": prompt}
    output.setdefault("search_text", prompt)
    output.setdefault("raw_prompt", prompt)
    slug = resolved.get("procedure_slug")
    if slug and not output.get("procedures"):
        output["procedures"] = [slug]
    approach = resolved.get("requested_approach")
    if approach and not output.get("approaches"):
        output["approaches"] = [approach]
    return output
