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
        "requires_question": ["primary_vs_revision"],
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
    "coding_implications": {
        "requires_question": ["primary_vs_revision"],
    },
},
{
    "concept_id": "hip.revision_total_arthroplasty",
    "label": "Revision total hip arthroplasty",
    "aliases": [
        "revision tha",
        "revision total hip arthroplasty",
        "revision total hip",
        "revision hip replacement",
        "failed tha",
        "failed total hip",
        "conversion hip arthroplasty",
        "conversion to tha",
        "explant hip arthroplasty",
        "hip component exchange",
        "head liner exchange",
        "head and liner exchange",
        "poly exchange hip",
        "liner exchange hip",
        "acetabular revision",
        "cup revision",
        "femoral stem revision",
        "revision acetabulum",
        "revision femoral component",
    ],
    "semantic_tags": [
        "hip",
        "arthroplasty",
        "revision",
        "component exchange",
        "acetabular component",
        "femoral component",
        "prior implant",
    ],
    "coding_implications": {
        "do_not_ask": ["primary_vs_revision"],
        "requires_question": ["tha_revision_components"],
        "strongly_favors": ["27134", "27137", "27138"],  # depending on component revised
    },
},
{
    "concept_id": "knee.revision_total_arthroplasty",
    "label": "Revision total knee arthroplasty",
    "aliases": [
        "revision tka",
        "revision total knee arthroplasty",
        "revision total knee",
        "revision knee replacement",
        "failed tka",
        "failed total knee",
        "conversion knee arthroplasty",
        "conversion to tka",
        "explant knee arthroplasty",
        "knee component exchange",
        "poly exchange knee",
        "polyethylene exchange knee",
        "liner exchange knee",
        "tibial insert exchange",
        "femoral component revision",
        "tibial component revision",
        "patellar component revision",
        "revision femoral component",
        "revision tibial component",
        "revision patella",
    ],
    "semantic_tags": [
        "knee",
        "arthroplasty",
        "revision",
        "component exchange",
        "femoral component",
        "tibial component",
        "patellar component",
        "polyethylene liner",
        "prior implant",
    ],
    "coding_implications": {
        "do_not_ask": ["primary_vs_revision"],
        "requires_question": ["tka_revision_components"],
        "strongly_favors": ["27486", "27487"],
    },
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
},
{
    "concept_id": "spine.lumbar_decompression_fusion",
    "label": "Lumbar decompression and fusion",
    "aliases": [
        "lumbar decompression and fusion",
        "lumbar decompression fusion",
        "lumbar laminectomy and fusion",
        "lumbar lami fusion",
        "lumbar fusion",
        "posterior lumbar fusion",
        "posterior lumbar decompression and fusion",
        "pldf",
        "lumbar arthrodesis",
        "lumbar decompression with arthrodesis",
        "lumbar decompression with instrumentation",
        "lumbar fusion with decompression",
        "multi level lumbar fusion",
        "multilevel lumbar fusion",
        "3 level lumbar fusion",
        "three level lumbar fusion",
    ],
    "semantic_tags": [
        "lumbar spine",
        "adult spine",
        "decompression",
        "laminectomy",
        "arthrodesis",
        "posterior fusion",
        "posterolateral fusion",
        "interbody fusion",
        "instrumentation",
    ],
    "coding_implications": {
        "strongly_favors": [
            "22612",
            "22614",
            "22630",
            "22632",
            "63047",
            "63048",
            "63017"
        ],
        "argues_against": [
            "22800",
            "22802",
            "22804",
            "22808",
            "22810",
            "22812"
        ],
        "requires_question": [
            "posterolateral_vs_interbody_fusion",
            "number_of_levels_or_interspaces",
            "instrumentation_performed",
            "decompression_type"
        ],
        "do_not_ask": [
            "spinal_region"
        ],
    },
},
{
    "concept_id": "spine.lumbar_interbody_fusion",
    "label": "Lumbar posterior interbody fusion",
    "aliases": [
        "tlif",
        "plif",
        "transforaminal lumbar interbody fusion",
        "posterior lumbar interbody fusion",
        "lumbar interbody fusion",
        "posterior interbody lumbar fusion",
        "interbody cage lumbar",
        "lumbar cage",
    ],
    "semantic_tags": [
        "lumbar spine",
        "interbody fusion",
        "posterior interbody technique",
        "tlif",
        "plif",
        "cage",
    ],
    "coding_implications": {
        "strongly_favors": ["22630", "22632"],
        "argues_against": ["22800"],
        "do_not_ask": [
            "posterolateral_vs_interbody_fusion",
            "spinal_region",
            "instrumentation_performed"
        ],
        "requires_question": [
            "combined_posterolateral_fusion",
            "number_of_levels_or_interspaces"
        ],
    },
},
{
    "concept_id": "spine.lumbar_interbody_posterolateral_fusion",
    "label": "Combined lumbar interbody and posterolateral fusion",
    "aliases": [
        "tlif with posterolateral fusion",
        "plif with posterolateral fusion",
        "tlif and posterolateral fusion",
        "plif and posterolateral fusion",
        "interbody and posterolateral fusion",
        "combined posterior interbody and posterolateral fusion",
        "combined posterior/posterolateral and interbody fusion",
        "circumferential posterior lumbar fusion",
    ],
    "semantic_tags": [
        "lumbar spine",
        "interbody fusion",
        "posterolateral fusion",
        "combined arthrodesis",
    ],
    "coding_implications": {
        "strongly_favors": ["22633", "22634"],
        "argues_against": ["22630", "22632", "22800"],
        "do_not_ask": [
            "combined_posterolateral_fusion",
            "posterolateral_vs_interbody_fusion",
            "spinal_region"
        ],
        "requires_question": ["number_of_levels_or_interspaces"],
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