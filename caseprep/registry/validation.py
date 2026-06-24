"""
Validation helpers for read-only registry responses.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from caseprep.registry.constants import (
    COVERAGE_WEIGHTS,
    LOW_COVERAGE_THRESHOLD,
    MODULE_SECTIONS,
    PLACEHOLDER_PATTERNS,
    REGION_FORBIDDEN_TERMS,
    REQUIRED_SECTIONS,
)


def modules_from_payload(payload: Dict[str, Any]) -> Dict[str, List[Any]]:
    setup: List[Any] = list(payload.get("must_know_anatomy") or [])
    if payload.get("procedure_overview"):
        setup = [payload["procedure_overview"]] + setup
    if payload.get("surgical_approach_anatomy"):
        setup = setup + list(payload["surgical_approach_anatomy"])
    return {
        "indications": [],
        "setup_positioning": setup,
        "approach_landmarks": list(payload.get("key_landmarks") or []),
        "surgical_layers": list(payload.get("surgical_layers") or []),
        "structures_at_risk": list(payload.get("structures_at_risk") or []),
        "implant_strategy": list(payload.get("reduction_or_implant_anatomy") or []),
        "reduction_or_fluoro_checkpoints": list(payload.get("fluoroscopy_checkpoints") or []),
        "pitfalls": list(payload.get("common_mistakes") or []),
        "attending_pimp_questions": list(payload.get("attending_pimp_questions") or []),
        "postop_plan": list(payload.get("night_before_review_checklist") or []),
    }


def section_has_content(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, list):
        if not value:
            return False
        for item in value:
            if isinstance(item, str) and item.strip():
                low = item.lower()
                if not any(p in low for p in PLACEHOLDER_PATTERNS):
                    return True
            elif isinstance(item, dict) and item:
                return True
            elif item:
                return True
        return False
    if isinstance(value, str):
        return bool(value.strip()) and not any(
            p in value.lower() for p in PLACEHOLDER_PATTERNS
        )
    return bool(value)


def modules_have_content(modules: Dict[str, Any]) -> bool:
    return any(section_has_content(modules.get(key)) for key in MODULE_SECTIONS)


def score_modules(
    modules: Dict[str, Any],
    payload: Optional[Dict[str, Any]] = None,
) -> int:
    data = modules if modules_have_content(modules) else {}
    if not data and payload:
        data = modules_from_payload(payload)
    total = 0
    for key, weight in COVERAGE_WEIGHTS.items():
        if section_has_content(data.get(key)):
            total += weight
    return min(100, total)


def placeholder_hits(text: str) -> List[str]:
    low = text.lower()
    return [pattern for pattern in PLACEHOLDER_PATTERNS if pattern in low]


def cross_region_warnings(body_region: str, text: str) -> List[str]:
    region = (body_region or "").lower()
    forbidden = REGION_FORBIDDEN_TERMS.get(region, [])
    warnings: List[str] = []
    low = text.lower()
    for term in forbidden:
        if term in low:
            warnings.append(
                f"Possible cross-region term '{term}' for body region {region or 'unknown'}."
            )
    return warnings


def collect_module_text(modules: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in MODULE_SECTIONS:
        value = modules.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.extend(str(v) for v in item.values() if v)
        elif isinstance(value, str):
            parts.append(value)
    return " ".join(parts).lower()


def is_low_coverage(score: int, content_status: str) -> bool:
    if content_status == "certified":
        return score < LOW_COVERAGE_THRESHOLD
    return score < 50