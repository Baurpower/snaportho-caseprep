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
from typing import Any, Dict, List, Optional, Tuple

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


def _normalize(text: str) -> str:
    """Lowercase, remove punctuation, collapse whitespace."""
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _get_display_for_slug(slug: Optional[str]) -> str:
    if not slug:
        return ""
    d = SLUG_TO_DEF.get(slug)
    return d.display_name if d else slug


def resolve_procedure(prompt: str, openai_client: Optional[Any] = None) -> Dict[str, Any]:
    """
    Multi-stage procedure resolver. Returns canonical slug + metadata.
    Router/playbook downstream MUST use only the returned procedure_slug (never raw prompt).
    """
    original = (prompt or "").strip()
    norm = _normalize(original)

    print("ANATOMY INPUT:", original)

    match_method = "none"
    match_score: Optional[float] = None
    canonical_slug: Optional[str] = None

    # Precompute normalized alias sets for speed
    alias_map: Dict[str, List[str]] = {}
    for p in REGISTRY:
        alias_map[p.slug] = [_normalize(a) for a in ([p.display_name] + p.aliases)]

    # ---------------- Stage A: Exact Alias Match ----------------
    for slug, norms in alias_map.items():
        if norm in norms:
            match_method = "alias"
            match_score = 100.0
            canonical_slug = slug
            print("MATCH METHOD:", match_method)
            print("MATCH SCORE:", match_score)
            print("CANONICAL PROCEDURE:", canonical_slug)
            return {
                "procedure_slug": canonical_slug,
                "canonical_display_name": _get_display_for_slug(canonical_slug),
                "match_method": match_method,
                "match_score": match_score,
                "confidence": 1.0,
                "suggested_matches": [],
            }

    # ---------------- Stage B: Contains Match (best match, not first) ----------------
    best_contain: Tuple[Optional[str], float, str] = (None, 0.0, "")
    for slug, norms in alias_map.items():
        for a in norms:
            if a and a in norm:
                # prefer longer (more specific) alias matches; bonus for explicit approach hints
                quality = len(a)
                if "anterior" in a or "posterior" in a or "direct" in a:
                    quality += 10
                if quality > best_contain[1]:
                    best_contain = (slug, quality, a)
    if best_contain[0]:
        match_method = "contains"
        match_score = 95.0
        canonical_slug = best_contain[0]
        print("MATCH METHOD:", match_method)
        print("MATCH SCORE:", match_score)
        print("CANONICAL PROCEDURE:", canonical_slug)
        return {
            "procedure_slug": canonical_slug,
            "canonical_display_name": _get_display_for_slug(canonical_slug),
            "match_method": match_method,
            "match_score": match_score,
            "confidence": 0.95,
            "suggested_matches": [],
        }

    # ---------------- Stage C: Fuzzy Match (rapidfuzz) ----------------
    if fuzz is not None:
        best_slug = None
        best_score = 0.0
        for slug, norms in alias_map.items():
            for a in norms:
                if not a:
                    continue
                # WRatio is strong for abbreviations + word order differences
                sc = fuzz.WRatio(norm, a)
                if sc > best_score:
                    best_score = sc
                    best_slug = slug
        if best_slug and best_score >= 85:
            match_method = "fuzzy"
            match_score = float(best_score)
            canonical_slug = best_slug
            print("MATCH METHOD:", match_method)
            print("MATCH SCORE:", match_score)
            print("CANONICAL PROCEDURE:", canonical_slug)
            return {
                "procedure_slug": canonical_slug,
                "canonical_display_name": _get_display_for_slug(canonical_slug),
                "match_method": match_method,
                "match_score": match_score,
                "confidence": min(1.0, best_score / 100.0),
                "suggested_matches": [],
            }

    # ---------------- Stage D: GPT Fallback Classifier ----------------
    # Only if A/B/C produced nothing confident.
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
            allowed_str = "\n".join(allowed_lines[:80])  # safety
            sys_prompt = (
                "You are an orthopaedic procedure classifier. "
                "Given a case description, return ONLY the single best matching procedure_slug "
                "from the allowed list. Output strict JSON: "
                '{"procedure_slug": "<one of the slugs>", "confidence": <0.0-1.0>}. '
                "If uncertain, use low confidence. Never invent slugs."
            )
            user_msg = f"Case description:\n{original}\n\nAllowed procedures (slug - name):\n{allowed_str}\n\nReturn JSON only."

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
            if cand in SLUG_TO_DEF and conf >= 0.8:
                gpt_slug = cand
                gpt_conf = conf
        except Exception:
            gpt_slug = None
            gpt_conf = 0.0

    if gpt_slug:
        match_method = "gpt"
        match_score = gpt_conf * 100.0
        canonical_slug = gpt_slug
        print("MATCH METHOD:", match_method)
        print("MATCH SCORE:", match_score)
        print("CANONICAL PROCEDURE:", canonical_slug)
        return {
            "procedure_slug": canonical_slug,
            "canonical_display_name": _get_display_for_slug(canonical_slug),
            "match_method": match_method,
            "match_score": match_score,
            "confidence": gpt_conf,
            "suggested_matches": [],
        }

    # ---------------- No confident resolution ----------------
    print("MATCH METHOD:", match_method)
    print("MATCH SCORE:", 0)
    print("CANONICAL PROCEDURE:", "unknown")

    # Build suggested matches: best fuzzy (even if <85) or top common certified displays
    suggested: List[str] = []
    if fuzz is not None:
        scored: List[Tuple[float, str]] = []
        for slug, norms in alias_map.items():
            for a in norms:
                if a:
                    sc = fuzz.WRatio(norm, a)
                    scored.append((sc, slug))
        scored.sort(reverse=True)
        seen = set()
        for sc, sl in scored:
            if sl not in seen:
                seen.add(sl)
                suggested.append(_get_display_for_slug(sl))
            if len(suggested) >= 5:
                break
    if not suggested:
        # Fallback to a few very common certified ones
        for s in ["tha_posterior", "tka", "distal_radius_fracture_orif", "acl_reconstruction", "hip_hemiarthroplasty"]:
            dn = _get_display_for_slug(s)
            if dn:
                suggested.append(dn)

    return {
        "procedure_slug": None,
        "canonical_display_name": "",
        "match_method": "none",
        "match_score": 0.0,
        "confidence": 0.0,
        "suggested_matches": suggested,
    }


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
