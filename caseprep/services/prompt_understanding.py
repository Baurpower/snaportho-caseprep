"""Deterministic clinical intent extraction for CasePrep routing and retrieval."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable


# Patterns are boundary-aware so short orthopaedic abbreviations do not match
# inside ordinary words (for example, ``tka`` in an unrelated token). Scores
# let a specific anatomical phrase beat a nearby joint reference: "tibial
# plateau" is a knee case, while "tibial shaft" is a leg case.
REGION_PATTERNS: Dict[str, tuple[tuple[str, int], ...]] = {
    "shoulder": (
        (r"\bprox(?:imal)?\s+hum(?:erus|eral)\b", 5),
        (r"\b(shoulder|glenoid|rotator cuff|clavicle|acromi(?:on|al))\b", 3),
        (r"\b(rcr|tsa|rtsa|rsa)\b", 3),
        (r"\b(long head )?biceps tenodesis\b", 4),
    ),
    "humerus": (
        (r"\b(humer(?:us|al) shaft|distal humerus|supracondylar humerus)\b", 5),
        (r"\bhumer(?:us|al)\b", 2),
    ),
    "elbow": (
        (r"\b(elbow|olecranon|radial head|distal biceps|distal triceps)\b", 3),
        (r"\b(cubital tunnel|tennis elbow|lateral epicondylitis|ecrb|triceps tendon)\b", 4),
    ),
    "forearm": (
        (r"\b(forearm|monteggia|galeazzi|nightstick)\b", 4),
        (r"\b(radial|radius|ulnar|ulna) shaft\b", 5),
        (r"\bboth[- ]bone forearm\b", 5),
    ),
    "wrist": (
        (r"\b(wrist|carpal|scaphoid|tfcc|colles|druj)\b", 3),
        (r"\bdistal (radius|ulna)\b", 5),
        (r"\b(volar|dorsal)?\s*ganglion(?: cyst)?\b", 3),
    ),
    "hand": (
        (r"\b(hand|thumb|finger|metacarp\w*|phalang\w*)\b", 3),
        (r"\b(dupuytren|trigger (finger|thumb)|a1 pulley|opponensplasty)\b", 4),
        (r"\b(cmc|tmc|lrti|fdp|fpl|epl|eip|zone [1-5])\b", 3),
        (r"\b(flexor tendon|extensor tendon|tendon transfer)\b", 3),
    ),
    "pelvis": (
        (r"\b(pelvis|pelvic|acetabul\w*|periacetabular)\b", 4),
        (r"\b(pao|ilioinguinal|kocher[- ]langenbeck|sacroiliac|si screw)\b", 4),
    ),
    "hip": (
        (r"\b(hip|femoral neck|intertroch\w*|subtroch\w*)\b", 4),
        (r"\b(scfe|perthes|ddh|cephalomedullary|fai)\b", 4),
        (r"\b(tha|hemiarthroplasty)\b", 3),
        (r"\b(total hip arthroplasty|total hip replacement)\b", 6),
    ),
    "femur": (
        (r"\b(femur|femoral) shaft\b", 5),
        (r"\bdistal femur\w*\b", 5),
        (r"\bfemur\b", 2),
    ),
    "knee": (
        (r"\b(knee|tka|acl|menisc\w*|menisectomy|patell\w*|quadriceps|mpfl)\b", 3),
        (r"\b(tibial plateau|proximal tibia|schatzker|high tibial osteotomy|hto)\b", 5),
        (r"\b(total knee arthroplasty|total knee replacement)\b", 6),
    ),
    "leg": (
        (r"\b(leg|tibia(?:l)? shaft|fibula(?:r)? shaft)\b", 4),
        (r"\b(four[- ]compartment fasciotomy|leg compartment syndrome)\b", 5),
        (r"\b(tibia|tibial|fibula|fibular)\b", 2),
    ),
    "ankle": (
        (r"\b(ankle|malleol\w*|bimalleolar|trimalleolar|pilon|plafond|achilles|talus|talar)\b", 3),
        (r"\b(tillaux|chaput|brostrom|atfl|taa)\b", 4),
    ),
    "foot": (
        (r"\b(foot|calcane\w*|lisfranc|plantar|hallux|bunion\w*)\b", 3),
        (r"\b(metatars\w*|metatarsophalangeal|mtp|toe|heel)\b", 3),
    ),
    "spine": (
        (r"\b(spine|spinal|cervical|thoracic|lumbar|scoliosis)\b", 3),
        (r"\b(acdf|tlif|pldf|laminectomy|discectomy|interbody)\b", 4),
    ),
}

MODIFIER_PATTERNS = {
    "anterior": r"\b(anterior|direct anterior|da)\b",
    "posterior": r"\bposterior(?:ly)?\b",
    "infection": r"\b(infect(?:ed|ion)|pji|septic|antibiotic spacer|cement spacer)\b",
    "revision": r"\b(revision|redo|explant|spacer)\b",
    "pediatric": r"\b(pediatric|paediatric|child|adolescent|tillaux|supracondylar)\b",
    "arthroscopic": r"\b(arthroscop\w*|scope|scoped)\b",
    "open": r"\bopen\b",
    "endoscopic": r"\bendoscopic\b",
    "nonoperative": r"\b(nonoperative|non operative|conservative|casting|cast treatment)\b",
    "operative": r"\b(orif|crpp|fixation|repair|reconstruction|replacement|arthroplast\w*|arthrodesis|arthroscop\w*|fusion|osteotomy|nail(?:ing)?|imn|pinning|plating|release|excision|removal|amputation|disarticulation|tenodesis|tenotomy|fasciotomy|fasciectomy|meniscectomy|laminectomy|discectomy|debridement|debreidment|reduction|bone graft(?:ing)?|allograft|autograft|operative|surgery|scope|scoped)\b",
}

# A region alone ("right shoulder", "knee pain") is too broad for accurate
# case preparation. These diagnosis signals are intentionally clinical nouns,
# not symptoms such as pain or swelling, so vague prompts still clarify.
DIAGNOSIS_PATTERN = re.compile(
    r"\b("
    r"fractur\w*|fx|tear|ruptur\w*|arthriti\w*|osteoarthritis|oa|"
    r"infect\w*|pji|septic|syndrome|dislocat\w*|sublux\w*|instability|"
    r"impingement|stenosis|radiculopath\w*|myelopath\w*|scoliosis|deformity|"
    r"dysplasia|ddh|scfe|perthes|nonunion|malunion|avascular necrosis|avn|"
    r"osteochondral defect|ocd|contracture|palsy|neuropath\w*|"
    r"tendinitis|tendonitis|tendinopath\w*|epicondylitis|fasciitis|"
    r"tumou?r|mass|sarcoma|lesion|ganglion|cyst|labral|menisc\w*"
    r")\b",
    re.I,
)

PROCEDURE_SHORTHAND_PATTERN = re.compile(
    r"\b(tha|tka|tsa|rtsa|rsa|taa|uka|acl|mpfl|acdf|tlif|pldf|"
    r"total (hip|knee|shoulder|ankle)|hemiarthroplasty)\b",
    re.I,
)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def infer_regions(text: str) -> list[str]:
    lowered = _clean(text)
    scored: list[tuple[int, str]] = []
    for region, patterns in REGION_PATTERNS.items():
        score = sum(weight for pattern, weight in patterns if re.search(pattern, lowered))
        if score:
            scored.append((score, region))
    scored.sort(key=lambda row: (-row[0], row[1]))
    return [region for _score, region in scored]


def extract_prompt_profile(text: str) -> Dict[str, Any]:
    lowered = _clean(text)
    regions = infer_regions(text)
    modifiers = [name for name, pattern in MODIFIER_PATTERNS.items() if re.search(pattern, lowered)]
    has_procedure_intent = (
        "operative" in modifiers or bool(PROCEDURE_SHORTHAND_PATTERN.search(lowered))
    )
    has_diagnosis_intent = bool(DIAGNOSIS_PATTERN.search(lowered))
    explicit_question = "?" in text or bool(
        re.match(r"^(what|which|when|where|why|how|does|do|is|are)\b", lowered)
        or re.search(r"\b(affect|increases?|decreases?|changes?|opens?|closes?)\s+which\b", lowered)
        or re.search(r"\bwhich\s+(gap|gaps|nerve|structure|structures|approach|implant|ligament)\b", lowered)
    )
    # Multiple major arthroplasties or explicit "vs" represent separate
    # clinical intents; ordinary conjunctions inside a case do not.
    compound = bool(
        re.search(r"\b(total hip|tha)\b.*\b(and|versus|vs)\b.*\b(total knee|tka)\b", lowered)
        or re.search(r"\b(total knee|tka)\b.*\b(and|versus|vs)\b.*\b(total hip|tha)\b", lowered)
        or re.search(r"\bvs\.?\b", lowered)
    )
    return {
        "raw_prompt": text,
        "search_text": text,
        "regions": regions,
        "region": (regions or [None])[0],
        "modifiers": modifiers,
        "has_procedure_intent": has_procedure_intent,
        "has_diagnosis_intent": has_diagnosis_intent,
        "has_clinical_intent": has_procedure_intent or has_diagnosis_intent,
        "explicit_question": explicit_question,
        "compound": compound,
    }


def compatible_with_slug(profile: Dict[str, Any], slug: str | None) -> tuple[bool, list[str]]:
    if not slug:
        return True, []
    modifiers = set(profile.get("modifiers") or [])
    reasons: list[str] = []
    if "anterior" in modifiers and slug == "tha_posterior":
        reasons.append("anterior hip approach cannot use the posterior THA packet")
    if "posterior" in modifiers and slug == "tha_anterior":
        reasons.append("posterior hip approach cannot use the anterior THA packet")
    if "infection" in modifiers and slug in {"tka", "tha_posterior", "tha_anterior"}:
        reasons.append("infection/spacer case cannot use an uncomplicated primary arthroplasty packet")
    if "nonoperative" in modifiers and any(token in slug for token in ("orif", "nail", "repair", "arthroplasty")):
        reasons.append("nonoperative request cannot use an operative packet")
    return not reasons, reasons


def lexical_terms(values: Iterable[str]) -> set[str]:
    stop = {"about", "and", "case", "for", "help", "left", "open", "orif", "prep", "prepare", "repair", "right", "surgery", "the", "with"}
    return {token for value in values for token in re.findall(r"[a-z0-9]+", _clean(value)) if len(token) > 2 and token not in stop}
