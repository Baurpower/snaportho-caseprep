"""
Shared constants for the read-only CasePrep registry API.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Tuple

CONTENT_STATUSES: FrozenSet[str] = frozenset(
    {"missing", "draft", "partial", "complete", "certified", "deprecated"}
)

REVIEW_STATUSES: FrozenSet[str] = frozenset(
    {
        "unreviewed",
        "ai_drafted",
        "needs_review",
        "resident_review",
        "attending_review",
        "certified",
        "needs_revision",
        "approved",
    }
)

MODULE_SECTIONS: Tuple[str, ...] = (
    "indications",
    "setup_positioning",
    "approach_landmarks",
    "surgical_layers",
    "structures_at_risk",
    "implant_strategy",
    "reduction_or_fluoro_checkpoints",
    "pitfalls",
    "attending_pimp_questions",
    "postop_plan",
)

# Clinical sections returned by the read API (includes sources).
CLINICAL_SECTION_ORDER: Tuple[str, ...] = MODULE_SECTIONS + ("sources",)

SECTION_LABELS: Dict[str, str] = {
    "indications": "Indications",
    "setup_positioning": "Setup & Positioning",
    "approach_landmarks": "Approach & Landmarks",
    "surgical_layers": "Surgical Layers",
    "structures_at_risk": "Structures at Risk",
    "implant_strategy": "Implant Strategy",
    "reduction_or_fluoro_checkpoints": "Reduction / Fluoro Checkpoints",
    "pitfalls": "Pitfalls",
    "attending_pimp_questions": "Attending Pimp Questions",
    "postop_plan": "Post-op Protocol",
    "sources": "Sources",
}

# Weights sum to 120; score_modules clamps to 100 (same pattern as before).
COVERAGE_WEIGHTS: Dict[str, int] = {
    "indications": 10,
    "setup_positioning": 10,
    "approach_landmarks": 15,
    "surgical_layers": 15,
    "structures_at_risk": 20,
    "implant_strategy": 10,
    "reduction_or_fluoro_checkpoints": 10,
    "pitfalls": 10,
    "attending_pimp_questions": 10,
    "postop_plan": 10,
}

REQUIRED_SECTIONS: FrozenSet[str] = frozenset(
    {
        "indications",
        "setup_positioning",
        "approach_landmarks",
        "surgical_layers",
        "structures_at_risk",
        "pitfalls",
        "attending_pimp_questions",
        "postop_plan",
    }
)

# Certified procedures migrated before indications existed: warn, do not block.
INDICATIONS_TRANSITIONAL_WARNING = True

OPTIONAL_SECTIONS: FrozenSet[str] = frozenset(
    {
        "implant_strategy",
        "reduction_or_fluoro_checkpoints",
    }
)

SECTION_CONTENT_TYPES: Dict[str, str] = {
    "indications": "bullet_list",
    "setup_positioning": "bullet_list",
    "approach_landmarks": "bullet_list",
    "surgical_layers": "structured",
    "structures_at_risk": "structured",
    "implant_strategy": "bullet_list",
    "reduction_or_fluoro_checkpoints": "bullet_list",
    "pitfalls": "bullet_list",
    "attending_pimp_questions": "structured",
    "postop_plan": "bullet_list",
    "sources": "structured",
}

PLACEHOLDER_PATTERNS: List[str] = [
    "see source-backed module",
    "primary structure at risk?",
    "key approach for this case",
    "per map evidence",
]

REGION_FORBIDDEN_TERMS: Dict[str, List[str]] = {
    "hip": ["lister's tubercle", "lister tubercle", "scaphoid fossa", "median nerve at wrist"],
    "knee": ["lister's tubercle", "greater trochanter", "sciatic nerve on quadratus"],
    "wrist": ["greater trochanter", "sciatic nerve", "acetabular component", "femoral neck cut"],
    "shoulder": ["lister's tubercle", "tibial plateau", "ankle syndesmosis"],
    "ankle": ["greater trochanter", "glenohumeral", "lister's tubercle"],
    "spine": ["greater trochanter", "lister's tubercle"],
    "foot": ["greater trochanter", "sciatic nerve on quadratus femoris"],
    "femur": ["lister's tubercle", "glenohumeral joint"],
    "humerus": ["lister's tubercle", "tibial plafond"],
}

REGISTRY_READ_SCHEMA_VERSION = "caseprep_registry_read_v1"

LOW_COVERAGE_THRESHOLD = 85