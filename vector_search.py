import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI
from typing import List, Dict, Any, Optional

from query_refiner import refine_query  # make sure it exists


# ── ENV & CLIENTS ─────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX")

if not all([OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_INDEX_NAME]):
    raise ValueError("❌ Missing OPENAI_API_KEY, PINECONE_API_KEY, or PINECONE_INDEX")

client = OpenAI(api_key=OPENAI_API_KEY, project=OPENAI_PROJECT_ID)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

EMBED_MODEL = "text-embedding-3-small"
from typing import List, Dict, Any, Optional, Tuple
import hashlib

TOP_K_STRICT = 50
TOP_K_RELAX  = 75
TOP_K_BROAD  = 100
MIN_SCORE = 0.55
NO_FILTER_MIN_UNIQUE = 10   # only run no_filter if we have <= 10 unique hits
TARGET_RESULTS = 40   # stop early when we have enough good unique snippets


def embed_text(txt: str) -> List[float]:
    return client.embeddings.create(model=EMBED_MODEL, input=txt).data[0].embedding


def payload_to_embedding_text(p: dict) -> str:
    """
    Better embedding input:
    - Use the expanded natural language search_text primarily
    - Append canonical slugs as anchors
    """
    if not isinstance(p, dict):
        return str(p)

    search_text = (p.get("search_text") or p.get("raw_prompt") or "").strip()
    specialties = " ".join(p.get("specialties", []))
    region = (p.get("region") or "").strip()
    subregion = (p.get("subregion") or "").strip()
    diagnoses = " ".join(p.get("diagnoses", []))
    procedures = " ".join(p.get("procedures", []))

    anchors = " | ".join([
        f"specialties {specialties}".strip(),
        f"region {region}".strip(),
        f"subregion {subregion}".strip(),
        f"diagnoses {diagnoses}".strip(),
        f"procedures {procedures}".strip(),
    ])

    if search_text:
        return f"{search_text} || {anchors}"
    return anchors


def _sig_for_item(text: str) -> str:
    """Stable signature for dedupe (better than first N words)."""
    norm = " ".join((text or "").lower().split())
    return hashlib.md5(norm.encode("utf-8")).hexdigest()


def _score_matches(matches: List[dict]) -> List[dict]:
    out: List[dict] = []
    for m in matches:
        score = float(m.get("score", 0) or 0)
        meta = m.get("metadata") or {}
        text = (meta.get("text") or "").replace("\n", " ").strip()

        if score < MIN_SCORE or not text:
            continue

        out.append({
            "id": m.get("id"),  # if Pinecone provides it
            "text": text,
            "source": meta.get("source"),
            "specialty": meta.get("specialty"),
            "region": meta.get("region"),
            "subregion": meta.get("subregion"),
            "diagnoses": meta.get("diagnoses") or [],
            "procedures": meta.get("procedures") or [],
            "score": score,
        })
    return out


def _dedupe_keep_best(items: List[dict], limit: int = 200) -> List[dict]:
    best: Dict[str, dict] = {}

    for it in items:
        # prefer ID if available
        if it.get("id"):
            key = f"id:{it['id']}"
        else:
            key = f"sig:{_sig_for_item(it.get('text', ''))}"

        if key not in best or it.get("score", 0) > best[key].get("score", 0):
            best[key] = it

    merged = sorted(best.values(), key=lambda x: x.get("score", 0), reverse=True)
    return merged[:limit]


def _pinecone_query(vec: List[float], filt: Optional[Dict[str, Any]], top_k: int) -> List[dict]:
    kwargs: Dict[str, Any] = {
        "vector": vec,
        "top_k": top_k,
        "include_metadata": True,
    }
    if filt:
        kwargs["filter"] = filt

    resp = index.query(**kwargs)
    matches = resp.get("matches", []) or []
    return _score_matches(matches)


def _build_and_filter(refined: dict,
                      use_region=True,
                      use_subregion=True,
                      use_dx=True,
                      use_proc=True,
                      use_specialty=True) -> Optional[Dict[str, Any]]:
    """
    Build a SINGLE AND filter with available fields.
    Returns None if no constraints are selected.
    """
    if not isinstance(refined, dict):
        return None

    region = (refined.get("region") or "").strip()
    subregion = (refined.get("subregion") or "").strip()
    diagnoses = refined.get("diagnoses") or []
    procedures = refined.get("procedures") or []
    specialties = [s.lower() for s in (refined.get("specialties") or []) if isinstance(s, str)]

    clauses: List[Dict[str, Any]] = []

    if use_proc and procedures:
        clauses.append({"procedures": {"$in": procedures}})
    if use_dx and diagnoses:
        clauses.append({"diagnoses": {"$in": diagnoses}})
    if use_subregion and subregion:
        clauses.append({"subregion": {"$in": [subregion]}})
    if use_region and region:
        clauses.append({"region": {"$in": [region]}})
    if use_specialty and specialties:
        clauses.append({"specialty": {"$in": specialties}})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def get_case_snippets(refined_query: dict) -> List[dict]:
    vec = embed_text(payload_to_embedding_text(refined_query))

    ladder: List[Tuple[str, Optional[Dict[str, Any]], int]] = []

    ladder.append(("strict", _build_and_filter(refined_query, True, True, True, True, True), TOP_K_STRICT))
    ladder.append(("drop_specialty", _build_and_filter(refined_query, True, True, True, True, False), TOP_K_STRICT))
    ladder.append(("drop_dx", _build_and_filter(refined_query, True, True, False, True, False), TOP_K_RELAX))
    ladder.append(("drop_proc", _build_and_filter(refined_query, True, True, False, False, False), TOP_K_RELAX))
    ladder.append(("region+specialty", _build_and_filter(refined_query, True, False, False, False, True), TOP_K_BROAD))
    ladder.append(("region_only", _build_and_filter(refined_query, True, False, False, False, False), TOP_K_BROAD))

    all_hits: List[dict] = []

    print("🎯 Using payload tokens:", {
        "specialties": [s.lower() for s in (refined_query.get("specialties") or []) if isinstance(s, str)],
        "region": refined_query.get("region"),
        "subregion": refined_query.get("subregion"),
        "diagnoses": refined_query.get("diagnoses") or [],
        "procedures": refined_query.get("procedures") or [],
    })

    merged: List[dict] = []

    # run guarded ladder first
    for label, filt, top_k in ladder:
        print(f"\n🔎 Pinecone query [{label}] top_k={top_k} filter={filt}")
        hits = _pinecone_query(vec, filt, top_k=top_k)
        print(f"   → {len(hits)} raw hits (>= {MIN_SCORE})")

        all_hits.extend(hits)
        merged = _dedupe_keep_best(all_hits, limit=200)
        print(f"   → {len(merged)} unique merged hits so far")

        if len(merged) >= TARGET_RESULTS:
            return merged

    # ✅ Only run no_filter if we still have <= 10 unique results
    if len(merged) <= NO_FILTER_MIN_UNIQUE:
        print(f"\n⚠️ Only {len(merged)} unique hits (<= {NO_FILTER_MIN_UNIQUE}). Running NO FILTER fallback...")
        hits = _pinecone_query(vec, None, top_k=TOP_K_BROAD)
        print(f"   → {len(hits)} raw hits (>= {MIN_SCORE})")
        all_hits.extend(hits)

    else:
        print(f"\n🛑 Skipping NO FILTER fallback (already {len(merged)} unique hits > {NO_FILTER_MIN_UNIQUE}).")

    return _dedupe_keep_best(all_hits, limit=200)

# ── INTERACTIVE TEST ──────────────────────────────────────────
if __name__ == "__main__":
    print("🔍 Vector Search Interface (with Query Refinement & Metadata Filter)")
    while True:
        raw_query = input("\nEnter a surgical case prompt (or 'q' to quit): ").strip()
        if raw_query.lower() in {"q", "quit", "exit"}:
            break

        refined_query = refine_query(raw_query)
        print(f"\n🛠️ Refined query: {refined_query}\n")

        results = get_case_snippets(refined_query)

        if results:
            print(f"\n✅ Top {len(results)} results:\n")
            for i, r in enumerate(results, 1):
                print(f"{i}. {r}\n")
        else:
            print("❌ No matches found.")
