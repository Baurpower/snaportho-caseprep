# ortho_concepts.py

from __future__ import annotations

import re
from typing import Any


ORTHO_CONCEPTS: list[dict[str, Any]] = [
    {
        "concept_id": "shoulder.reverse_total_arthroplasty",
        "label": "Reverse total shoulder arthroplasty",
        "aliases": [
            "reverse shoulder arthroplasty",
            "reverse total shoulder arthroplasty",
            "reverse tsa",
            "rtsa",
            "rsa",
            "reverse shoulder replacement",
        ],
        "semantic_tags": [
            "shoulder",
            "glenohumeral joint",
            "arthroplasty",
            "reverse implant",
            "total shoulder",
            "glenoid component",
            "proximal humeral replacement",
        ],
        "coding_implications": {
            "strongly_favors": ["23472"],
            "argues_against": ["23470"],
            "do_not_ask": ["total_vs_hemiarthroplasty"],
        },
    },
    {
        "concept_id": "shoulder.hemiarthroplasty",
        "label": "Shoulder hemiarthroplasty",
        "aliases": [
            "shoulder hemiarthroplasty",
            "shoulder hemi",
        ],
        "semantic_tags": [
            "shoulder",
            "arthroplasty",
            "hemiarthroplasty",
            "humeral head",
            "no glenoid component",
        ],
        "coding_implications": {
            "strongly_favors": ["23470"],
            "argues_against": ["23472"],
        },
    },
    {
        "concept_id": "fracture.crpp",
        "label": "Closed reduction percutaneous pinning",
        "aliases": [
            "crpp",
            "closed reduction percutaneous pinning",
            "closed reduction and percutaneous pinning",
            "percutaneous pinning",
            "perc pinning",
            "k wire fixation",
            "k-wire fixation",
            "kwire fixation",
        ],
        "semantic_tags": [
            "closed reduction",
            "percutaneous fixation",
            "pin fixation",
            "k wires",
        ],
        "coding_implications": {
            "do_not_ask": ["open_vs_closed", "implant_type"],
        },
    },
    {
        "concept_id": "long_bone.intramedullary_nail",
        "label": "Intramedullary nail",
        "aliases": [
            "imn",
            "im nail",
            "intramedullary nail",
            "intramedullary nailing",
            "intramedullary fixation",
            "nailing",
            "rod",
            "rodded",
            "locked nail",
            "locking nail",
        ],
        "semantic_tags": [
            "intramedullary implant",
            "intramedullary nail",
            "diaphyseal fixation",
            "load sharing implant",
        ],
        "coding_implications": {
            "do_not_ask": ["implant_type"],
        },
    },
    {
        "concept_id": "hip.cephalomedullary_nail",
        "label": "Cephalomedullary nail",
        "aliases": [
            "cmn",
            "cephalomedullary nail",
            "cephalomedullary nailing",
            "gamma nail",
            "tfna",
            "trochanteric nail",
            "proximal femoral nail",
            "pfn",
            "short imn",
            "long imn",
            "hip nail",
            "intertroch nail",
            "intertrochanteric nail",
        ],
        "semantic_tags": [
            "hip",
            "proximal femur",
            "intertrochanteric",
            "subtrochanteric",
            "intramedullary implant",
            "cephalomedullary fixation",
        ],
        "coding_implications": {
            "do_not_ask": ["implant_type"],
        },
    },
    {
        "concept_id": "hip.total_arthroplasty",
        "label": "Total hip arthroplasty",
        "aliases": [
            "tha",
            "total hip arthroplasty",
            "total hip replacement",
            "hip replacement",
        ],
        "semantic_tags": [
            "hip",
            "arthroplasty",
            "acetabular component",
            "femoral component",
            "total hip",
        ],
    },
    {
        "concept_id": "hip.hemiarthroplasty",
        "label": "Hip hemiarthroplasty",
        "aliases": [
            "hip hemi",
            "hip hemiarthroplasty",
            "hemiarthroplasty hip",
            "femoral head replacement",
            "bipolar hemiarthroplasty",
            "unipolar hemiarthroplasty",
        ],
        "semantic_tags": [
            "hip",
            "arthroplasty",
            "hemiarthroplasty",
            "femoral head",
            "no acetabular component",
        ],
    },
    {
        "concept_id": "distal_radius.fracture",
        "label": "Distal radius fracture",
        "aliases": [
            "distal radius fracture",
            "distal radius fx",
            "drf",
            "colles fracture",
        ],
        "semantic_tags": [
            "wrist",
            "distal radius",
            "fracture",
        ],
        "coding_implications": {
            "requires_question": ["intra_vs_extra_articular", "number_of_fragments"],
        },
    },
    {
        "concept_id": "debridement.irrigation_and_debridement",
        "label": "Irrigation and debridement",
        "aliases": [
            "i&d",
            "i and d",
            "irrigation and debridement",
            "debridement",
            "washout",
        ],
        "semantic_tags": [
            "debridement",
            "irrigation",
            "infection",
            "wound",
        ],
        "coding_implications": {
            "requires_question": ["superficial_vs_deep_vs_bone"],
        },
    },
    {
    "concept_id": "arthroscopy.knee.diagnostic_or_unspecified",
    "label": "Knee arthroscopy, unspecified procedure",
    "aliases": [
        "knee scope",
        "knee arthroscopy",
        "arthroscopic knee surgery",
        "scope knee",
        "diagnostic knee arthroscopy",
    ],
    "semantic_tags": [
        "knee",
        "arthroscopy",
        "meniscus",
        "chondroplasty",
        "synovectomy",
        "loose body removal",
    ],
    "coding_implications": {
        "requires_question": [
            "meniscectomy_vs_meniscus_repair",
            "medial_vs_lateral_vs_both_meniscus",
            "chondroplasty_performed",
            "synovectomy_performed",
            "loose_body_removal_performed",
            "diagnostic_only_vs_surgical"
        ],
    },
},
{
    "concept_id": "arthroscopy.shoulder.diagnostic_or_unspecified",
    "label": "Shoulder arthroscopy, unspecified procedure",
    "aliases": [
        "shoulder scope",
        "shoulder arthroscopy",
        "arthroscopic shoulder surgery",
        "scope shoulder",
        "diagnostic shoulder arthroscopy",
    ],
    "semantic_tags": [
        "shoulder",
        "arthroscopy",
        "rotator cuff",
        "subacromial decompression",
        "biceps tenodesis",
        "labral repair",
        "debridement",
    ],
    "coding_implications": {
        "requires_question": [
            "rotator_cuff_repair_performed",
            "subacromial_decompression_performed",
            "biceps_tenodesis_performed",
            "labral_repair_performed",
            "debridement_performed",
            "distal_clavicle_excision_performed",
            "diagnostic_only_vs_surgical"
        ],
    },
}
]


def _alias_pattern(alias: str) -> re.Pattern:
    escaped = re.escape(alias.lower())
    escaped = escaped.replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", re.IGNORECASE)


def detect_ortho_concepts(text: str) -> list[dict[str, Any]]:
    normalized = text.lower()
    detected: list[dict[str, Any]] = []

    for concept in ORTHO_CONCEPTS:
        matches: list[str] = []

        for alias in concept.get("aliases", []):
            pattern = _alias_pattern(alias)
            if pattern.search(normalized):
                matches.append(alias)

        if matches:
            detected.append({
                "concept_id": concept["concept_id"],
                "label": concept["label"],
                "matched_aliases": matches,
                "semantic_tags": concept.get("semantic_tags", []),
                "coding_implications": concept.get("coding_implications", {}),
            })

    return detected


def concept_positive_terms(detected_concepts: list[dict[str, Any]]) -> list[str]:
    terms: list[str] = []

    for concept in detected_concepts:
        terms.append(concept.get("label", ""))
        terms.extend(concept.get("matched_aliases", []))
        terms.extend(concept.get("semantic_tags", []))

    return list(dict.fromkeys([t for t in terms if t]))


def apply_concept_score_adjustments(
    score: int,
    row: dict[str, Any],
    detected_concepts: list[dict[str, Any]],
) -> int:
    code = str(row.get("code", ""))

    for concept in detected_concepts:
        implications = concept.get("coding_implications", {})

        if code in implications.get("strongly_favors", []):
            score += 150

        if code in implications.get("argues_against", []):
            score -= 150

    return score