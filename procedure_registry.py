"""
Procedure Registry + Robust Resolver for BroBot /anatomy and case-prep.

New flow:
  User Prompt
    -> resolve_procedure(prompt)   # multi-stage, never raw text downstream
    -> canonical_slug (e.g. "tha_posterior")
    -> Playbook Router / Certified Gate (exact slug lookup only)
    -> Anatomy Pipeline / BroBot payload

All 60 procedure_ids from brobot_anatomy_router_v1_4 are canonical slugs.
The 24 certified (in data/anatomy_integration/certified_*.jsonl) are the primary
safe targets for resilient BroBot case-prep.

Resolver is deliberately "resident-to-resident": THA / total hip arthroplasty /
hip replacement / posterior THA / 72 yo ... THA all resolve to tha_posterior
(the most common certified THA playbook). Specific anterior/direct-anterior
resolve to tha_anterior. Hemi variants to hip_hemiarthroplasty.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from rapidfuzz import fuzz
except Exception:  # allow import even if not yet pip-installed; stage C will be skipped
    fuzz = None  # type: ignore


BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class ProcedureDefinition:
    slug: str
    display_name: str
    aliases: List[str]
    specialty: str
    body_region: str


def _load_procedure_aliases() -> List[ProcedureDefinition]:
    """Load canonical aliases from data/anatomy/registry/procedure_aliases.jsonl.
    Falls back to a minimal embedded set (for dev safety if data not present).
    """
    aliases_path = BASE_DIR / "data" / "anatomy" / "registry" / "procedure_aliases.jsonl"
    loaded = []
    if aliases_path.exists():
        try:
            with aliases_path.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        d = json.loads(line)
                        loaded.append(ProcedureDefinition(
                            slug=d["procedure_id"],
                            display_name=d["display_name"],
                            aliases=d.get("aliases", []),
                            specialty=d.get("specialty", "orthopaedics"),
                            body_region=d.get("body_region", "unknown"),
                        ))
            if loaded:
                return loaded
        except Exception as e:
            print(f"⚠️ Failed to load procedure_aliases.jsonl ({e}); using fallback registry.")
    # Minimal fallback (subset of common certified for safety; full data preferred)
    fallback = [
        ProcedureDefinition("distal_radius_fracture_orif", "Distal Radius Fracture ORIF", ["distal radius orif"], "trauma", "wrist"),
        ProcedureDefinition("tha_posterior", "Total Hip Arthroplasty (Posterior Approach)", ["tha", "total hip arthroplasty"], "adult_reconstruction", "hip"),
        ProcedureDefinition("tha_anterior", "Total Hip Arthroplasty (Direct Anterior Approach)", ["direct anterior tha"], "adult_reconstruction", "hip"),
        ProcedureDefinition("tka", "Total Knee Arthroplasty", ["tka", "total knee"], "adult_reconstruction", "knee"),
        ProcedureDefinition("acl_reconstruction", "ACL Reconstruction", ["acl recon"], "sports", "knee"),
    ]
    return fallback


# ---------------------------------------------------------------------------
# Canonical registry loaded from data (or minimal fallback).
# The data/anatomy/registry/procedure_aliases.jsonl is the source of truth.
# ---------------------------------------------------------------------------

REGISTRY: List[ProcedureDefinition] = _load_procedure_aliases()

# (old hardcoded REGISTRY list removed; now loaded from data/anatomy/registry/procedure_aliases.jsonl)

SLUG_TO_DEF: Dict[str, ProcedureDefinition] = {p.slug: p for p in REGISTRY}
ALL_SLUGS: List[str] = [p.slug for p in REGISTRY]
CERTIFIED_SLUGS: set = {p.slug for p in REGISTRY if getattr(p, "is_certified", False) or (hasattr(p, "__dict__") and p.__dict__.get("is_certified"))}
# Fallback to explicit if aliases not yet marked (for safety during transition)
if not CERTIFIED_SLUGS:
    CERTIFIED_SLUGS = {
        "distal_radius_fracture_orif", "hip_hemiarthroplasty", "tha_posterior", "tha_anterior",
        "tka", "acl_reconstruction", "femoral_shaft_fracture_orif", "humeral_shaft_fracture_orif",
        "scfe_pinning", "posterior_lumbar_decompression_fusion", "total_shoulder_arthroplasty",
        "tibial_shaft_fracture_orif", "meniscus_repair", "reverse_shoulder_arthroplasty",
        "lateral_ankle_ligament_repair", "distal_femur_fracture_orif", "pelvis_ring_fracture_orif",
        "supracondylar_humerus_fracture_pediatric", "hallux_valgus_correction", "plantar_fasciitis_release",
        "quadriceps_tendon_repair", "acetabulum_fracture_orif_anterior", "acetabulum_fracture_orif_posterior",
        "monteggia_fracture_orif"
    }


# Resident shorthand and adjective/noun pairs canonicalised token-wise, so an
# alias and a real prompt land on the same spelling ("intertroch fx" and
# "intertrochanteric fracture"). Deliberately curated, never stemmed: "radius"
# and "radial", or "femoral neck" and "femur shaft", are different procedures.
_TOKEN_SYNONYMS = {
    "fx": "fracture",
    "fxs": "fracture",
    "fractures": "fracture",
    "fracure": "fracture",
    "acetabular": "acetabulum",
    "pelvic": "pelvis",
    "meniscal": "meniscus",
    "intertroch": "intertrochanteric",
    "arthroscopic": "arthroscopy",
    "hemi": "hemiarthroplasty",
    "knees": "knee",
    "hips": "hip",
    "shoulders": "shoulder",
    "ankles": "ankle",
    "tendons": "tendon",
    "peds": "pediatric",
    "pediatrics": "pediatric",
}


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, canonicalise shorthand, collapse whitespace."""
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r"[^\w\s]", " ", t)
    tokens = [_TOKEN_SYNONYMS.get(token, token) for token in t.split()]
    return " ".join(tokens).strip()


def _get_display_for_slug(slug: Optional[str]) -> str:
    if not slug:
        return ""
    d = SLUG_TO_DEF.get(slug)
    return d.display_name if d else slug


# ---------------------------------------------------------------------------
# Token matching primitives
#
# Substring containment ("tha" in "what are the tendons that...") and
# rapidfuzz.WRatio over whole prompts (which falls back to partial matching and
# scores ~85 for any prompt sharing one token with an alias) both produced
# confident matches to unrelated procedures. Every stage below therefore works
# on word-boundary tokens and requires the *alias* to be covered by the prompt,
# never the other way around.
# ---------------------------------------------------------------------------

# Tokens that appear across many procedures, plus conversational filler. An
# alias match carried entirely by these is not evidence of anything: "repair",
# "fracture", and "help me prepare for a ..." identify no procedure.
_GENERIC_TOKENS = {
    "a", "an", "and", "approach", "arthroplasty", "arthroscopy", "case", "closed",
    "correction", "distal", "do", "does", "fixation", "for", "fracture", "fractures",
    "fx", "have", "help", "how", "i", "in", "is", "know", "left", "lower", "me",
    "my", "need", "of", "on", "open", "orif", "prep", "prepare", "primary",
    "procedure", "proximal", "release", "repair", "replacement", "reconstruction",
    "revision", "right", "scope", "should", "surgery", "tendon", "the", "to",
    "tomorrow", "upper", "what", "with", "yo",
}

# Token-level typo tolerance ("carpel"/"carpal", "cubical"/"cubital"). Short
# tokens and tokens that disagree on their first two characters are excluded —
# that is what keeps "biceps"/"radius" and "medial"/"lateral" apart.
_TOKEN_FUZZY_MIN = 82.0
_TOKEN_FUZZY_MIN_LEN = 5

# Surgical-approach and laterality words. These are shared across many
# operations ("volar Henry" fixes both a radial shaft and a distal radius
# fracture), so they identify an *approach*, never a *procedure*. They must not
# be the sole evidence that anchors a GPT classifier answer, or a Galeazzi case
# gets served a certified Distal Radius packet on the strength of "volar" alone.
_APPROACH_TOKENS = {
    "anterior", "anterolateral", "anteromedial", "posterior", "posterolateral",
    "posteromedial", "lateral", "medial", "volar", "dorsal", "direct", "open",
    "endoscopic", "percutaneous", "arthroscopic", "mini", "extensile", "limited",
    # Eponymous approaches (not procedures).
    "henry", "thompson", "kocher", "kaplan", "bruner", "hardinge", "moore",
    "southern", "smith", "petersen", "watson", "jones", "langenbeck",
    "ilioinguinal", "stoppa", "kocherlangenbeck",
}

# An alias only fires when nearly all of its tokens are present in the prompt.
_ALIAS_COVERAGE_MIN = 0.8

# Two different procedures scoring within this margin means the prompt did not
# actually disambiguate them; ask instead of guessing.
_AMBIGUITY_MARGIN = 2.0


def _tokens(text: str) -> List[str]:
    return [token for token in _normalize(text).split() if token]


def _specific(tokens: Iterable[str]) -> List[str]:
    return [token for token in tokens if token not in _GENERIC_TOKENS]


def _token_matches(alias_token: str, prompt_tokens: Sequence[str]) -> bool:
    if alias_token in prompt_tokens:
        return True
    if len(alias_token) < _TOKEN_FUZZY_MIN_LEN or fuzz is None:
        return False
    return any(
        len(candidate) >= _TOKEN_FUZZY_MIN_LEN
        and candidate[:2] == alias_token[:2]
        and fuzz.ratio(alias_token, candidate) >= _TOKEN_FUZZY_MIN
        for candidate in prompt_tokens
    )


def _phrase_in(alias: str, norm_prompt: str) -> bool:
    """Whole-word phrase containment: 'tha' must not match 'that'."""
    alias_tokens = _tokens(alias)
    if not alias_tokens:
        return False
    pattern = r"\b" + r"\s+".join(re.escape(token) for token in alias_tokens) + r"\b"
    return re.search(pattern, norm_prompt) is not None


def _alias_coverage(alias_tokens: Sequence[str], prompt_tokens: Sequence[str]) -> float:
    if not alias_tokens:
        return 0.0
    matched = sum(1 for token in alias_tokens if _token_matches(token, prompt_tokens))
    return matched / len(alias_tokens)


def _score_alias(alias: str, norm_prompt: str, prompt_tokens: Sequence[str]) -> float:
    """Return 0.0 when the alias is not evidenced by the prompt.

    A match requires (a) most alias tokens present, and (b) *every* specific
    alias token present. (b) is what separates "distal radius fracture" from
    "distal biceps repair": they share only generic vocabulary, and the one
    token that names the anatomy is absent.
    """
    alias_tokens = _tokens(alias)
    if not alias_tokens:
        return 0.0
    specific_tokens = _specific(alias_tokens)
    if not specific_tokens:
        # A purely generic alias ("repair", "help me prepare for a ...") can
        # never identify a procedure on its own.
        return 0.0
    if not all(_token_matches(token, prompt_tokens) for token in specific_tokens):
        return 0.0
    coverage = _alias_coverage(alias_tokens, prompt_tokens)
    if coverage < _ALIAS_COVERAGE_MIN:
        return 0.0

    # Specificity, not raw string length, ranks candidates: "trimalleolar
    # ankle" must outrank the broader "ankle fracture orif", and "revision
    # total hip" must outrank "total hip".
    score = 15.0 * len(specific_tokens) + 5.0 * len(alias_tokens) + coverage * 5.0
    if _phrase_in(alias, norm_prompt):
        score += 15.0  # contiguous phrase beats scattered tokens
    if any(token in {"anterior", "posterior", "lateral", "direct"} for token in alias_tokens):
        score += 5.0
    return score


def _rank_candidates(norm_prompt: str) -> List[Tuple[float, str, str]]:
    """(score, slug, alias) for every alias the prompt supports, best first."""
    prompt_tokens = _tokens(norm_prompt)
    best_by_slug: Dict[str, Tuple[float, str]] = {}
    for definition in REGISTRY:
        for alias in [definition.display_name, *definition.aliases]:
            score = _score_alias(alias, norm_prompt, prompt_tokens)
            if score <= 0.0:
                continue
            current = best_by_slug.get(definition.slug)
            if current is None or score > current[0]:
                best_by_slug[definition.slug] = (score, alias)
    ranked = [(score, slug, alias) for slug, (score, alias) in best_by_slug.items()]
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return ranked


def _partial_candidates(norm_prompt: str, limit: int = 4) -> List[Tuple[float, str, str]]:
    """Loose "did you mean" candidates for prompts that resolved to nothing.

    Ranked on shared *specific* tokens only, so an unrelated prompt yields no
    suggestions at all rather than a list of the most popular procedures.
    """
    prompt_tokens = set(_specific(_tokens(norm_prompt)))
    if not prompt_tokens:
        return []
    scored: Dict[str, Tuple[float, str]] = {}
    for definition in REGISTRY:
        for alias in [definition.display_name, *definition.aliases]:
            alias_tokens = set(_specific(_tokens(alias)))
            shared = len(alias_tokens & prompt_tokens)
            if not shared:
                continue
            score = 10.0 * shared / max(1, len(alias_tokens))
            current = scored.get(definition.slug)
            if current is None or score > current[0]:
                scored[definition.slug] = (score, alias)
    ranked = [(score, slug, alias) for slug, (score, alias) in scored.items()]
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return ranked[:limit]


def _gpt_answer_is_anchored(slug: str, norm_prompt: str) -> bool:
    """Reject classifier answers with no lexical footing in the prompt.

    The model is prompted to return "none", but when it does guess a neighbour
    ("elbow arthroscopy" for a distal biceps repair, "distal radius ORIF" for a
    Galeazzi) the guess shares only generic or approach vocabulary with what the
    user typed. The anchor must be a *procedure-identifying* word — an anatomy
    noun or the procedure's own name — so approach adjectives ("volar", "henry")
    and generic words are excluded from both sides. Region words still count, so
    "72 yo hip fracture in the OR tomorrow" can reach a hip procedure.
    """
    definition = SLUG_TO_DEF.get(slug)
    if definition is None:
        return False
    prompt_tokens = set(_specific(_tokens(norm_prompt))) - _APPROACH_TOKENS
    if not prompt_tokens:
        return False
    anchors = set(_specific(_tokens(definition.display_name)))
    for alias in definition.aliases:
        anchors |= set(_specific(_tokens(alias)))
    anchors |= set(_specific(_tokens(definition.body_region.replace("_", " "))))
    anchors -= _APPROACH_TOKENS
    return bool(anchors & prompt_tokens)


def _suggestions_for(ranked: Sequence[Tuple[float, str, str]], limit: int = 4) -> List[Dict[str, Any]]:
    return [
        {
            "slug": slug,
            "name": _get_display_for_slug(slug),
            "display_name": _get_display_for_slug(slug),
            "entity_kind": "procedure",
            "confidence": round(min(0.95, score / 60.0), 2),
        }
        for score, slug, _alias in ranked[:limit]
    ]


def _result(
    original: str,
    slug: Optional[str],
    method: str,
    score: float,
    confidence: float,
    *,
    suggested: Optional[List[Dict[str, Any]]] = None,
    requires_clarification: bool = False,
    clarification_reason: Optional[str] = None,
    matched_alias: Optional[str] = None,
) -> Dict[str, Any]:
    print("MATCH METHOD:", method)
    print("MATCH SCORE:", score)
    print("CANONICAL PROCEDURE:", slug or "unknown")
    return {
        "raw_query": original,
        "procedure_slug": slug,
        "canonical_display_name": _get_display_for_slug(slug),
        "entity_kind": "procedure" if slug else None,
        "requested_approach": None,
        "match_method": method,
        "match_score": score,
        "confidence": confidence,
        "matched_alias": matched_alias,
        "suggested_matches": suggested or [],
        "requires_clarification": requires_clarification,
        "clarification_reason": clarification_reason,
    }


def resolve_procedure(prompt: str, openai_client: Optional[Any] = None) -> Dict[str, Any]:
    """
    Multi-stage procedure resolver. Returns canonical slug + metadata.
    Router/playbook downstream MUST use only the returned procedure_slug (never raw prompt).
    """
    original = (prompt or "").strip()
    norm = _normalize(original)

    # Carpal tunnel release is one canonical procedure with approach-specific
    # branches. Generic requests require an explicit approach choice; explicit
    # open/endoscopic requests retain that identity without creating web-owned
    # pseudo-slugs.
    if re.search(r"\b(carpal tunnel (release|surgery)|ctr)\b", norm):
        requested_approach = None
        entity_kind = "procedure"
        requires_clarification = True
        clarification_reason = (
            "Choose open or endoscopic carpal tunnel release so approach-specific "
            "preparation can be shown safely."
        )
        if "endoscopic" in norm:
            requested_approach = "endoscopic"
            entity_kind = "approach"
            requires_clarification = False
            clarification_reason = None
        elif re.search(r"\b(open|mini open)\b", norm):
            requested_approach = "open"
            entity_kind = "approach"
            requires_clarification = False
            clarification_reason = None

        return {
            "raw_query": original,
            "procedure_slug": "carpal_tunnel_release",
            "canonical_display_name": "Carpal Tunnel Release",
            "entity_kind": entity_kind,
            "requested_approach": requested_approach,
            "match_method": "alias" if norm in {"ctr", "carpal tunnel release"} else "contains",
            "match_score": 100.0 if norm in {"ctr", "carpal tunnel release"} else 95.0,
            "confidence": 1.0 if norm in {"ctr", "carpal tunnel release"} else 0.95,
            "suggested_matches": [
                {
                    "slug": "carpal_tunnel_release",
                    "name": "Open Carpal Tunnel Release",
                    "entity_kind": "approach",
                    "approach": "open",
                    "confidence": 1.0,
                },
                {
                    "slug": "carpal_tunnel_release",
                    "name": "Endoscopic Carpal Tunnel Release",
                    "entity_kind": "approach",
                    "approach": "endoscopic",
                    "confidence": 1.0,
                },
            ] if requires_clarification else [],
            "requires_clarification": requires_clarification,
            "clarification_reason": clarification_reason,
        }

    print("ANATOMY INPUT:", original)

    # ---------------- Stage A: Exact Alias Match ----------------
    for definition in REGISTRY:
        if norm in {_normalize(a) for a in [definition.display_name, *definition.aliases]}:
            return _result(original, definition.slug, "alias", 100.0, 1.0, matched_alias=norm)

    # ---------------- Stage B/C: Token-anchored alias ranking ----------------
    # One ranking pass replaces the old substring ("contains") and WRatio
    # ("fuzzy") stages. Method is reported as "contains" when the winning alias
    # appears verbatim as a phrase and "fuzzy" when it was assembled from
    # scattered / near-miss tokens, so downstream confidence gates and the
    # existing test matrix keep their meaning.
    ranked = _rank_candidates(norm)
    if ranked:
        top_score, top_slug, top_alias = ranked[0]
        runner_up = ranked[1] if len(ranked) > 1 else None
        if runner_up and (top_score - runner_up[0]) < _AMBIGUITY_MARGIN:
            # Two procedures are equally well supported by this prompt — e.g.
            # "acetabulum fracture" (anterior vs posterior approach). Guessing
            # here is exactly how a resident gets the wrong packet.
            return _result(
                original,
                None,
                "ambiguous",
                top_score,
                0.0,
                suggested=_suggestions_for(ranked),
                requires_clarification=True,
                clarification_reason=(
                    "That could be more than one procedure. Which one are you preparing for?"
                ),
            )
        exact_phrase = _phrase_in(top_alias, norm)
        method = "contains" if exact_phrase else "fuzzy"
        confidence = 0.95 if exact_phrase else 0.85
        return _result(
            original,
            top_slug,
            method,
            95.0 if exact_phrase else 88.0,
            confidence,
            matched_alias=top_alias,
        )

    # ---------------- Stage D: GPT Fallback Classifier ----------------
    # Only if A/B/C produced nothing. The classifier must be allowed to answer
    # "none": a forced choice over 60 slugs is what turned "distal biceps
    # repair" (not in the registry) into a confident Elbow Arthroscopy packet.
    gpt_slug: Optional[str] = None
    gpt_conf: float = 0.0
    if openai_client is None:
        try:
            from openai import OpenAI

            openai_client = OpenAI()
        except Exception:
            openai_client = None

    if openai_client is not None:
        try:
            allowed_lines = [f"{p.slug} - {p.display_name}" for p in REGISTRY]
            allowed_str = "\n".join(allowed_lines)
            sys_prompt = (
                "You are an orthopaedic procedure classifier for a surgical prep tool. "
                "Given a case description, return the single procedure_slug from the allowed "
                "list that names THE SAME operation the user described.\n"
                'Output strict JSON: {"procedure_slug": "<slug or none>", "confidence": <0.0-1.0>}.\n'
                'Return "none" (confidence 0) unless the described operation is genuinely on '
                "the list. A neighbouring procedure on the same joint is NOT a match: "
                '"distal biceps tendon repair" is not elbow arthroscopy, "shoulder arthroscopy" '
                'is not total shoulder arthroplasty, "ankle fracture" is not distal radius ORIF. '
                "Never invent slugs. Never guess to avoid returning none."
            )
            user_msg = (
                f"Case description:\n{original}\n\n"
                f"Allowed procedures (slug - name):\n{allowed_str}\n\nReturn JSON only."
            )

            resp = openai_client.chat.completions.create(
                model=os.getenv("ANATOMY_CLASSIFIER_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_msg},
                ],
                response_format={"type": "json_object"},
                max_tokens=80,
                temperature=0.0,
            )
            raw = (resp.choices[0].message.content or "").strip()
            data = json.loads(raw)
            cand = (data.get("procedure_slug") or "").strip()
            conf = float(data.get("confidence") or 0.0)
            if cand in SLUG_TO_DEF and conf >= 0.8 and _gpt_answer_is_anchored(cand, norm):
                gpt_slug = cand
                gpt_conf = conf
        except Exception:
            gpt_slug = None
            gpt_conf = 0.0

    if gpt_slug:
        return _result(original, gpt_slug, "gpt", gpt_conf * 100.0, gpt_conf)

    # ---------------- No confident resolution ----------------
    # Suggestions are best-effort only, and are explicitly NOT a resolution:
    # the packet engine treats a null slug as "prep from the user's own words".
    return _result(
        original,
        None,
        "none",
        0.0,
        0.0,
        suggested=_suggestions_for(_partial_candidates(norm)),
    )


def get_procedure_definition(slug: str) -> Optional[ProcedureDefinition]:
    return SLUG_TO_DEF.get(slug)


def is_certified(slug: str) -> bool:
    return slug in CERTIFIED_SLUGS


def list_certified_slugs() -> List[str]:
    return sorted(CERTIFIED_SLUGS)


if __name__ == "__main__":
    # Quick smoke for the success criteria
    tests = [
        "THA",
        "tha",
        "total hip arthroplasty",
        "total hip replacement",
        "hip replacement",
        "primary THA",
        "posterior THA",
        "anterior THA",
        "direct anterior hip replacement",
        "help me prepare for a total hip",
        "72 yo with hip OA undergoing THA",
        "72 year old with end stage hip arthritis scheduled for THA tomorrow",
        "Posterior approach total hip replacement",
        "Review anatomy for direct anterior THA",
    ]
    for t in tests:
        r = resolve_procedure(t)
        print("=>", r["procedure_slug"], r["match_method"], r.get("match_score"))
