"""
Pinecone-backed Miller Gold Anatomy Retriever (Phase 2).

Queries the dedicated namespace in the existing Pinecone index.

Returns identical chunk shape to anatomy_retriever.py for drop-in use:
  {"id", "score", "text", "source_quote", "page", "heading", "region", "subregion",
   "quality_tier", "metadata_trust", ...}

Env:
  PINECONE_API_KEY, PINECONE_INDEX
  ANATOMY_PINECONE_NAMESPACE (default: anatomy_miller_gold_v1)
  OPENAI_API_KEY (for query embedding, text-embedding-3-small)

Fallback: caller (main.py) should catch errors and fallback to local.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
EMBED_MODEL = "text-embedding-3-small"
DEFAULT_NAMESPACE = "anatomy_miller_gold_v1"
TOP_K_POOL = 30
MIN_SCORE = 0.30  # slightly lower than local for Pinecone ANN variance
FINAL_TOP_K = 8

# Reuse the region guess / boost logic from local retriever (copy small helpers to keep independent)
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

def _get_pinecone_index():
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX")
    if not api_key or not index_name:
        raise RuntimeError("Missing PINECONE_API_KEY or PINECONE_INDEX")
    pc = Pinecone(api_key=api_key)
    return pc.Index(index_name)

def _get_openai_client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY required for query embedding")
    return OpenAI(api_key=key, project=os.getenv("OPENAI_PROJECT_ID"))

def _embed_query(client: OpenAI, text: str) -> List[float]:
    resp = client.embeddings.create(model=EMBED_MODEL, input=[text.strip()])
    return resp.data[0].embedding

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

    q_score = _quality_order.get(qt, 0)
    boost += (q_score - 1) * 0.03

    if region and any(r in region for r in guessed_regions):
        boost += 0.08
    if sub and any(r in sub for r in guessed_regions):
        boost += 0.04

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
    namespace: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not case_prompt or not case_prompt.strip():
        return []

    ns = namespace or os.getenv("ANATOMY_PINECONE_NAMESPACE", DEFAULT_NAMESPACE)
    index = _get_pinecone_index()
    oai = _get_openai_client()

    vector = _embed_query(oai, case_prompt)

    # Query the anatomy namespace (no metadata filter at query time for simplicity; post-filter)
    resp = index.query(
        vector=vector,
        top_k=TOP_K_POOL,
        include_metadata=True,
        namespace=ns,
    )
    matches = resp.get("matches", []) or []

    prompt_l = case_prompt.lower()
    guessed = _guess_regions(case_prompt)

    candidates: List[Dict[str, Any]] = []
    seen = set()

    for m in matches:
        score = float(m.get("score", 0.0))
        if score < MIN_SCORE:
            continue

        meta = m.get("metadata") or {}
        text = meta.get("text", "") or ""
        quote = meta.get("source_quote", "") or ""

        sig = _normalize_text(text or quote)[:120]
        if sig in seen:
            continue
        seen.add(sig)

        boosted = score + _score_boost(meta, prompt_l, guessed)

        chunk = {
            "id": m.get("id"),
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

    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates[:top_k]

def get_anatomy_retrieval_info() -> Dict[str, Any]:
    try:
        ns = os.getenv("ANATOMY_PINECONE_NAMESPACE", DEFAULT_NAMESPACE)
        index = _get_pinecone_index()
        stats = index.describe_index_stats()
        ns_info = (stats.namespaces or {}).get(ns, {})
        return {
            "namespace": ns,
            "index": os.getenv("PINECONE_INDEX"),
            "vector_count_in_ns": ns_info.get("vector_count"),
            "min_score": MIN_SCORE,
        }
    except Exception as e:
        return {"error": str(e)}
