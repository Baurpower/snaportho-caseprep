"""
Local-only Miller Gold Anatomy Retriever (Phase 1).

Loads pre-built index from data/anatomy_miller_gold_v1/local_index/
( created by scripts/build_local_anatomy_gold_index.py using text-embedding-3-small ).

Provides get_anatomy_chunks(case_prompt: str, top_k: int = 10) -> List[dict]

Post-filtering (conservative, no hard metadata exclusion on proc/dx):
- cosine >= MIN_SCORE
- dedupe by normalized text / source_quote
- quality_tier preference (high > medium > low)
- soft score boost for region/subregion/approach/term overlap with prompt
- return top N after re-sort

Each returned chunk:
  {
    "id": str,
    "score": float,
    "text": str,
    "source_quote": str,
    "page": int | None,
    "heading": str,
    "region": str | None,
    "subregion": str | None,
    "quality_tier": str | None,
    "metadata_trust": str | None,
  }

Usage behind flag only. No Pinecone.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

# ── Config ──────────────────────────────────────────────────────────────────
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
INDEX_DIR = BASE_DIR / "data" / "anatomy_miller_gold_v1" / "local_index"

EMBED_MODEL = "text-embedding-3-small"
MIN_SCORE = 0.32          # conservative; tune via test reports
TOP_K_POOL = 30           # retrieve more for filtering
FINAL_TOP_K = 8           # after filter/dedupe/boost return this many max

# Simple region keywords for soft boost (subset of query_refiner logic)
REGION_KEYWORDS = {
    "hip": ["hip", "tha", "acetabul", "femoral neck", "intertroch"],
    "knee": ["knee", "tka", "uka", "tibial plateau", "acl", "meniscus"],
    "ankle": ["ankle", "pilon", "talus", "calcane", "achilles", "malleolus"],
    "foot": ["foot", "lisfranc", "metatarsal", "hallux"],
    "wrist": ["wrist", "distal radius", "scaphoid", "tfcc", "carpal"],
    "hand": ["hand", "metacarp", "phalange", "trigger", "cubital"],
    "elbow": ["elbow", "olecranon", "radial head", "cubital"],
    "shoulder": ["shoulder", "proximal humerus", "rotator cuff", "labrum"],
    "spine": ["spine", "cervical", "thoracic", "lumbar"],
    "pelvis": ["pelvis", "acetabular", "sacrum", "iliac", "pelvic ring"],
    "thigh": ["femur", "thigh"],
    "leg": ["tibia", "fibula", "leg"],
    "forearm": ["forearm", "radius", "ulna"],
    "arm": ["humerus", "arm"],
}

_quality_order = {"high": 3, "medium": 2, "low_but_acceptable": 1, None: 0}

def _get_client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY required for local anatomy embedding (query side).")
    proj = os.getenv("OPENAI_PROJECT_ID")
    return OpenAI(api_key=key, project=proj)

def _embed_query(client: OpenAI, text: str) -> np.ndarray:
    resp = client.embeddings.create(model=EMBED_MODEL, input=[text.strip()])
    vec = np.array(resp.data[0].embedding, dtype=np.float32)
    return vec

def _load_index():
    emb_path = INDEX_DIR / "embeddings.npy"
    ids_path = INDEX_DIR / "ids.json"
    metas_path = INDEX_DIR / "metas.json"
    manifest_path = INDEX_DIR / "manifest.json"

    if not (emb_path.exists() and ids_path.exists() and metas_path.exists()):
        raise FileNotFoundError(
            f"Local anatomy index incomplete at {INDEX_DIR}. "
            "Run: python scripts/build_local_anatomy_gold_index.py"
        )

    embeddings = np.load(emb_path).astype(np.float32)  # (N, D)
    with ids_path.open() as f:
        ids: List[str] = json.load(f)
    with metas_path.open() as f:
        metas: List[Dict[str, Any]] = json.load(f)

    manifest = {}
    if manifest_path.exists():
        with manifest_path.open() as f:
            manifest = json.load(f)

    if len(ids) != len(metas) or len(ids) != embeddings.shape[0]:
        raise ValueError("Index files are out of sync (ids/metas/embeddings length mismatch).")

    return embeddings, ids, metas, manifest

def _normalize_text(t: str) -> str:
    return " ".join((t or "").lower().split())

def _guess_regions(prompt: str) -> List[str]:
    p = (prompt or "").lower()
    hits = []
    for region, kws in REGION_KEYWORDS.items():
        if any(kw in p for kw in kws):
            hits.append(region)
    return hits or ["non-anatomic"]

def _score_boost(meta: Dict[str, Any], prompt_lower: str, guessed_regions: List[str]) -> float:
    boost = 0.0
    region = (meta.get("region") or "").lower()
    sub = (meta.get("subregion") or "").lower()
    qt = meta.get("quality_tier")

    # quality preference
    q_score = _quality_order.get(qt, 0)
    boost += (q_score - 1) * 0.03   # high +0.06, medium +0.03

    # region/subregion soft match
    if region and any(r in region for r in guessed_regions):
        boost += 0.08
    if sub and any(r in sub for r in guessed_regions):
        boost += 0.04

    # light keyword overlap on structures/approach/terms (no hard filter)
    text_blob = " ".join([
        str(meta.get("structures_at_risk", [])),
        str(meta.get("approach_terms", [])),
    ]).lower()
    overlap = sum(1 for tok in ["fcr", "median", "sciatic", "rotator", "acl", "mcl", "syndesm", "ulnar", "peroneal"]
                  if tok in prompt_lower and tok in text_blob)
    boost += min(overlap * 0.02, 0.06)

    return boost

def get_anatomy_chunks(
    case_prompt: str,
    top_k: int = FINAL_TOP_K,
    client: Optional[OpenAI] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve top Miller gold anatomy chunks for a case prompt.
    Returns list of dicts with id, score (boosted), text, source_quote, page, etc.
    """
    if not case_prompt or not case_prompt.strip():
        return []

    embeddings, ids, metas, manifest = _load_index()

    if client is None:
        client = _get_client()

    q_vec = _embed_query(client, case_prompt)
    # cosine
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    qn = q_vec / (np.linalg.norm(q_vec) + 1e-12)
    sims = (embeddings / (norms + 1e-12)) @ qn

    # pool
    pool_idx = np.argsort(sims)[::-1][:TOP_K_POOL]

    prompt_l = case_prompt.lower()
    guessed = _guess_regions(case_prompt)

    candidates: List[Dict[str, Any]] = []
    seen = set()

    for idx in pool_idx:
        score = float(sims[idx])
        if score < MIN_SCORE:
            continue

        meta = metas[idx]
        text = meta.get("text", "") or ""
        quote = meta.get("source_quote", "") or ""

        # dedupe
        sig = _normalize_text(text or quote)[:120]
        if sig in seen:
            continue
        seen.add(sig)

        boosted = score + _score_boost(meta, prompt_l, guessed)

        chunk = {
            "id": ids[idx],
            "score": round(boosted, 4),
            "raw_score": round(score, 4),
            "text": text,
            "source_quote": quote,
            "page": meta.get("page"),
            "heading": meta.get("heading", ""),
            "region": meta.get("region"),
            "subregion": meta.get("subregion"),
            "quality_tier": meta.get("quality_tier"),
            "metadata_trust": meta.get("metadata_trust"),
        }
        candidates.append(chunk)

    # final sort by boosted score, take top_k
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates[:top_k]

def get_anatomy_retrieval_info() -> Dict[str, Any]:
    """Lightweight info for logging/debug (no secrets)."""
    try:
        _, _, _, manifest = _load_index()
        return {
            "index_dir": str(INDEX_DIR),
            "record_count": manifest.get("indexed_count"),
            "embedding_model": manifest.get("embedding_model"),
            "min_score": MIN_SCORE,
            "top_k_pool": TOP_K_POOL,
        }
    except Exception as e:
        return {"error": str(e)}
