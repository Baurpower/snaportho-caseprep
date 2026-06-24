"""
Anatomy Context Builder (Phase 3).

Converts list of chunks (from local or Pinecone retriever) into a stable,
source-backed AnatomyPayload v2.

This payload is designed to be:
- Backward compatible (includes legacy nulls when using Miller path; legacy path populates old fields).
- Clinically useful for ortho case prep.
- Strictly grounded in retrieved Miller gold chunks (no invention).
- Supports strict source mode (default) for verbatim-leaning output.

Output shape (AnatomyPayload v2):

{
  // Legacy/compat fields (populated in legacy anatomy_gpt path; null in Miller path for safety)
  "approachSelection": {...} | null,
  "anatomyQuiz": {...} | null,
  "highYieldAnatomy": {...} | null,

  // Miller gold source-backed fields (core of Phase 3)
  "retrievalMode": "legacy" | "miller_gold_local" | "miller_gold_pinecone",
  "limitedAnatomyContext": bool,
  "relevantAnatomy": string[],      // key facts, relations, planes from chunks
  "structuresAtRisk": string[],     // explicitly supported by Miller sources
  "approachLandmarks": string[],
  "highYieldFacts": string[],       // concise pimp-style facts (not full Q/A)
  "sources": [                      // structured for attribution + future UI
    {
      "id": "miller-...",
      "page": 33,
      "heading": "...",
      "text": "...",
      "source_quote": "...",
      "score": 0.67
    }
  ],
  "retrievalSummary": {
    "chunksUsed": 8,
    "mode": "miller_gold_pinecone",
    "limited": false,
    "regions": ["wrist", "upper_extremity"],
    "warning": "Results may include some nonspecific approach language." | null
  }
}

Rules enforced here:
- Only derive content from provided chunks' text/source_quote + metadata.
- If strict mode (ANATOMY_STRICT_SOURCE_MODE=true, default): prefer near-verbatim quotes; minimal generalization.
- Weak retrieval (< MIN_USEFUL_CHUNKS useful chunks) => limitedAnatomyContext=true + note.
- Dedup similar items.
- Omit sections with no supporting source.
- retrievalSummary always present for transparency.
"""

import os
from typing import Any, Dict, List, Optional

# ── Config ──────────────────────────────────────────────────────────────────
USEFUL_SCORE_THRESHOLD = 0.38
MIN_USEFUL_CHUNKS = 2

ANATOMY_KEYWORDS = [
    "nerve", "artery", "vein", "ligament", "tendon", "muscle", "bone",
    "interval", "plane", "landmark", "tubercle", "notch", "foramen",
    "at risk", "structures at risk", "watershed", "footprint",
    "bundle", "branch", "groove", "fossa", "eminence", "ridge",
    "fcr", "median", "ulnar", "radial", "sciatic", "peroneal", "saphenous",
]

def _is_useful(chunk: Dict[str, Any]) -> bool:
    score = float(chunk.get("score", 0.0) or 0.0)
    if score < USEFUL_SCORE_THRESHOLD:
        return False
    blob = " ".join([
        str(chunk.get("text", "")),
        str(chunk.get("source_quote", "")),
        str(chunk.get("heading", "")),
    ]).lower()
    return any(kw in blob for kw in ANATOMY_KEYWORDS)

def _short_quote(quote: str, max_len: int = 160) -> str:
    q = (quote or "").strip()
    if len(q) <= max_len:
        return q
    # try to cut at sentence/word
    cut = q[:max_len-3]
    for sep in [". ", "; ", ", ", " "]:
        if sep in cut:
            cut = cut.rsplit(sep, 1)[0]
            break
    return cut + "..."

def _get_strict_mode() -> bool:
    val = os.getenv("ANATOMY_STRICT_SOURCE_MODE", "true").lower()
    return val in ("1", "true", "yes", "on")

def _make_structured_source(chunk: Dict[str, Any]) -> Dict[str, Any]:
    page = chunk.get("page")
    # normalize page (sometimes float from json)
    if isinstance(page, float):
        page = int(page) if page.is_integer() else page
    return {
        "id": chunk.get("id"),
        "page": page,
        "heading": chunk.get("heading", ""),
        "text": (chunk.get("text") or "")[:300],
        "source_quote": (chunk.get("source_quote") or "")[:300],
        "score": round(float(chunk.get("score", 0.0) or 0.0), 4),
    }

def _categorize_bullet(bullet: str, chunk: Dict[str, Any], strict: bool) -> str:
    """Assign bullet to best category. In strict mode, be conservative."""
    b_low = bullet.lower()
    page = chunk.get("page")
    src = f" (Miller p.{page})" if page else ""

    # Prefer explicit risk language
    if any(x in b_low for x in ["at risk", "risk of injury", "protect", "injury to", "avoid"]):
        return "structuresAtRisk"
    if any(x in b_low for x in ["landmark", "tubercle", "notch", "groove", "watershed", "eminence", "ridge", "line"]):
        return "approachLandmarks"
    if any(x in b_low for x in ["high yield", "commonly tested", "pimp", "frequently asked"]):
        return "highYieldFacts"

    # Default to relevantAnatomy
    return "relevantAnatomy"

def _extract_bullets_from_chunk(chunk: Dict[str, Any], max_per: int = 3, strict: bool = True) -> List[str]:
    """Extractive + conservative. Strict mode favors source_quote verbatim."""
    text = (chunk.get("text") or "").strip()
    quote = (chunk.get("source_quote") or "").strip()
    page = chunk.get("page")
    src = f" (Miller p.{page})" if page else ""

    base = quote if (strict or not text) else (quote or text)
    if not base:
        return []

    # Split on sentence boundaries
    raw_parts = [p.strip() for p in base.replace(";", ".").split(".") if len(p.strip()) > 10]

    candidates: List[str] = []
    for p in raw_parts[:max_per + 1]:
        if len(p) < 12:
            continue
        # In strict, require it looks like a factual anatomy statement from keywords or length
        if strict:
            if not (any(kw in p.lower() for kw in ANATOMY_KEYWORDS) or len(p) > 40):
                continue
        # Clean lightly
        clean = p
        if not clean.endswith(src):
            clean = clean + src
        candidates.append(clean)
        if len(candidates) >= max_per:
            break
    return candidates

def _dedupe_preserve_order(items: List[str], key_len: int = 90) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in items:
        k = x.lower()[:key_len]
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out

def build_anatomy_context(
    chunks: List[Dict[str, Any]],
    case_prompt: str = "",
) -> Dict[str, Any]:
    """
    Phase 3 builder. Produces AnatomyPayload v2.
    """
    strict = _get_strict_mode()
    useful = [c for c in chunks if _is_useful(c)]
    limited = len(useful) < MIN_USEFUL_CHUNKS

    # Collect raw categorized items + sources
    relevant: List[str] = []
    at_risk: List[str] = []
    landmarks: List[str] = []
    high_yield: List[str] = []
    sources: List[Dict[str, Any]] = []

    source_chunks_used = useful if not limited else chunks[: max(4, MIN_USEFUL_CHUNKS)]

    for c in source_chunks_used:
        # Structured source (even for marginal chunks when limited)
        src_obj = _make_structured_source(c)
        sources.append(src_obj)

        bullets = _extract_bullets_from_chunk(c, max_per=3, strict=strict)
        for b in bullets:
            cat = _categorize_bullet(b, c, strict=strict)
            if cat == "structuresAtRisk":
                at_risk.append(b)
            elif cat == "approachLandmarks":
                landmarks.append(b)
            elif cat == "highYieldFacts":
                high_yield.append(b)
            else:
                relevant.append(b)

        # Surface explicit structures_at_risk from chunk metadata if present (future-proof)
        for s in (c.get("structures_at_risk") or c.get("_structures_at_risk") or []):
            if isinstance(s, str) and s.strip():
                p = c.get("page")
                note = s.strip() + (f" (Miller p.{p})" if p else "")
                at_risk.append(note)

    # Dedup + cap
    relevant = _dedupe_preserve_order(relevant)[:8]
    at_risk = _dedupe_preserve_order(at_risk)[:6]
    landmarks = _dedupe_preserve_order(landmarks)[:6]
    high_yield = _dedupe_preserve_order(high_yield)[:6]
    sources = sources[:8]  # cap sources too

    # Build retrievalSummary
    regions = sorted({c.get("region") for c in source_chunks_used if c.get("region")})[:4]
    warning = None
    if limited:
        warning = "Limited high-quality Miller gold anatomy context for this query. Core facts may be in pimp/other sections."
    elif len(regions) > 1 and any(r in ("unknown", None) for r in regions):
        warning = "Some results may be nonspecific (mixed regions in top chunks)."

    retrieval_summary = {
        "chunksUsed": len(source_chunks_used),
        "mode": "miller_gold_pinecone" if any("pine" in str(c.get("id","")).lower() for c in source_chunks_used) else "miller_gold_local",
        "limited": limited,
        "regions": [r for r in regions if r],
        "warning": warning,
    }

    # Final payload (v2)
    payload: Dict[str, Any] = {
        # Legacy compat (null in Miller path)
        "approachSelection": None,
        "anatomyQuiz": None,
        "highYieldAnatomy": None,

        # Miller v2 fields
        "retrievalMode": "miller_gold_local",  # will be overwritten by caller in main.py for pinecone
        "limitedAnatomyContext": limited,
        "relevantAnatomy": relevant,
        "structuresAtRisk": at_risk,
        "approachLandmarks": landmarks,
        "highYieldFacts": high_yield,
        "sources": sources,
        "retrievalSummary": retrieval_summary,
    }

    if limited and sources:
        # Ensure a clear note
        note = retrieval_summary.get("warning") or "Limited high-quality Miller gold anatomy context retrieved for this query."
        # sources are now objects; put note as a special first "source" if needed, or leave in summary
        # For simplicity, we already have it in retrievalSummary.warning

    return payload

# Convenience helper (used by tests/scripts)
def get_miller_anatomy_context(
    case_prompt: str,
    retriever_top_k: int = 10,
    backend: str = "local",
) -> Dict[str, Any]:
    if backend == "pinecone":
        from anatomy_pinecone_retriever import get_anatomy_chunks
    else:
        from anatomy_retriever import get_anatomy_chunks
    chunks = get_anatomy_chunks(case_prompt, top_k=retriever_top_k)
    ctx = build_anatomy_context(chunks, case_prompt=case_prompt)
    # Let caller override mode if needed
    return ctx
