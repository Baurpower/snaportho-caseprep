"""Deterministic clinical intent extraction for CasePrep routing and retrieval."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable


REGION_KEYWORDS = {
    "shoulder": {"shoulder", "glenoid", "rotator", "proximal humerus", "biceps tenodesis"},
    "elbow": {"elbow", "olecranon", "triceps", "radial head", "distal humerus", "distal biceps"},
    "wrist": {"wrist", "carpal", "distal radius", "scaphoid", "tfcc"},
    "hand": {"hand", "thumb", "finger", "metacarpal", "phalange", "ganglion"},
    "hip": {"hip", "acetabul", "femoral neck", "intertroch", "subtroch"},
    "knee": {"knee", "tka", "acl", "menisc", "patella", "quadriceps", "mpfl"},
    "leg": {"tibia", "tibial", "fibula", "fibular", "pilon"},
    "ankle": {"ankle", "malleol", "tillaux", "chaput", "talus"},
    "foot": {"foot", "calcane", "lisfranc", "plantar", "hallux"},
    "spine": {"spine", "cervical", "thoracic", "lumbar", "scoliosis", "fusion"},
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
    "operative": r"\b(orif|fixation|repair|reconstruction|replacement|arthroplasty|fusion|nail(?:ing)?|imn|release|excision|removal|tenodesis|debridement|debreidment)\b",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def infer_regions(text: str) -> list[str]:
    lowered = _clean(text)
    scored = []
    for region, keywords in REGION_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in lowered)
        if score:
            scored.append((score, region))
    scored.sort(key=lambda row: (-row[0], row[1]))
    return [region for _score, region in scored]


def extract_prompt_profile(text: str) -> Dict[str, Any]:
    lowered = _clean(text)
    modifiers = [name for name, pattern in MODIFIER_PATTERNS.items() if re.search(pattern, lowered)]
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
        "regions": infer_regions(text),
        "region": (infer_regions(text) or [None])[0],
        "modifiers": modifiers,
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
