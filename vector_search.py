import os
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI
from typing import List, Dict, Any, Optional
from query_refiner import refine_query  # ✅ Ensure this module is available

# ── ENV & CLIENTS ─────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX")

client = OpenAI(api_key=OPENAI_API_KEY, project=OPENAI_PROJECT_ID)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

EMBED_MODEL = "text-embedding-3-small"
TOP_K = 100          # reasonable for your use case
MIN_SCORE = 0.52      # can tune later if you want stricter filtering


# ── EMBED ─────────────────────────────────────────────────────
def embed_text(txt: str) -> List[float]:
    """Return embedding vector for the given text."""
    return client.embeddings.create(
        model=EMBED_MODEL,
        input=txt
    ).data[0].embedding


# ── METADATA FILTER BUILDER ───────────────────────────────────
def _build_metadata_filter_from_query(refined_query: str) -> Optional[Dict[str, Any]]:
    """
    Build a Pinecone metadata filter from the refined query.
    - Multiple specialties → specialty: {"$in": [...]}
    - Multiple regions    → region: {"$in": [...]}
    - Specialty + region  → {"$and": [specialty_clause, region_clause]}
    """

    tokens = [t.strip().lower() for t in refined_query.split(",") if t.strip()]
    if not tokens:
        return None

    specialty_map = {
        "recon": "recon",
        "adult reconstruction": "recon",
        "arthroplasty": "recon",

        "trauma": "trauma",
        "sports": "sports",
        "foot & ankle": "footankle",
        "foot and ankle": "footankle",
        "footankle": "footankle",
        "hand": "hand",
        "peds": "peds",
        "pediatrics": "peds",
        "spine": "spine",
        "shoulder": "shoulderelbow",
        "shoulder/elbow": "shoulderelbow",
        "shoulderelbow": "shoulderelbow",
        "onc": "onc",
    }

    region_map = {
        "knee": [
            "knee",
            "lowerextremity::knee",
            "lowerextremity",
            "lowerextremity::lowerextremityknee",
        ],
        "hip": [
            "hip",
            "lowerextremity::hip",
            "pelvis",
        ],
        "ankle": [
            "ankle",
            "footankle",
            "lowerextremity::lowerextremityankle",
        ],
        "foot": [
            "foot",
            "footankle",
            "forefoot",
            "midfoot",
        ],
        # NEW: let 'footankle' act as a region concept too
        "footankle": [
            "footankle",
            "ankle",
            "foot",
            "lowerextremity::lowerextremityankle",
        ],
        "pelvis": [
            "pelvis",
            "acetabulum",
        ],
        "patella": [
            "patella",
        ],
        "elbow": [
            "elbow",
        ],
        "shoulder": [
            "shoulder",
            "shouldergirdle",
            "shoulderelbow",
        ],
        "spine": [
            "spine",
            "thoracic spine",
            "lumbar spine",
            "cervical spine",
        ],
    }

    selected_specialties = set()
    selected_regions = set()

    for t in tokens:
        if t in specialty_map:
            selected_specialties.add(specialty_map[t])
        if t in region_map:
            selected_regions.update(region_map[t])

    clauses: List[Dict[str, Any]] = []

    # Build specialty clause
    if selected_specialties:
        if len(selected_specialties) == 1:
            clauses.append({"specialty": {"$eq": next(iter(selected_specialties))}})
        else:
            clauses.append({"specialty": {"$in": list(selected_specialties)}})

    # Build region clause
    if selected_regions:
        if len(selected_regions) == 1:
            clauses.append({"region": {"$eq": next(iter(selected_regions))}})
        else:
            clauses.append({"region": {"$in": list(selected_regions)}})

    # If nothing matched safely, don't filter
    if not clauses:
        return None

    # If only one clause, no need for $and
    if len(clauses) == 1:
        return clauses[0]

    return {"$and": clauses}


# ── SCORE + FILTER RESULT SNIPPETS ────────────────────────────
def _score_matches(matches: List[dict]) -> List[dict]:
    filtered = [
        m for m in matches
        if m["score"] >= MIN_SCORE and m["metadata"].get("text")
    ]

    seen = set()
    clean_items = []

    for m in filtered:
        meta = m["metadata"]
        raw_text = meta.get("text", "").replace("\n", " ").strip()

        # dedupe signature
        sig = " ".join(raw_text.lower().split(" ")[:8])
        if sig in seen:
            continue
        seen.add(sig)

        item = {
            "text": raw_text,
            "source": meta.get("source"),
            "specialty": meta.get("specialty"),
            "region": meta.get("region"),
            "diagnosis": meta.get("diagnosis"),
            "procedure": meta.get("procedure"),
            "score": m.get("score")
        }

        clean_items.append(item)

    return clean_items[:500]

def _query_with_fallback(vec: List[float], filter_obj: Optional[Dict[str, Any]]) -> List[dict]:
    """
    Run Pinecone query with an optional metadata filter.
    If no snippets are returned with the filter, retry once WITHOUT the filter.
    """
    def run_query(label: str, filt: Optional[Dict[str, Any]] = None) -> List[dict]:
        query_kwargs: Dict[str, Any] = {
            "vector": vec,
            "top_k": TOP_K,
            "include_metadata": True,
        }
        if filt:
            query_kwargs["filter"] = filt
            print(f"\n🔎 Querying Pinecone ({label}) with filter: {filt}")
        else:
            print(f"\n🔎 Querying Pinecone ({label}) with NO filter")

        resp = index.query(**query_kwargs)
        matches = resp.get("matches", [])
        snippets = _score_matches(matches)
        print(f"   → {len(snippets)} snippets after score+dedupe")
        return snippets

    # 1) Try with filter (if we have one)
    if filter_obj:
        snippets = run_query("primary (with filter)", filter_obj)
        if snippets:
            return snippets

        # 2) Fallback: no results with filter → try again without filter
        print("⚠️ No snippets found with metadata filter. Falling back to NO filter...")
        return run_query("fallback (no filter)", None)

    # No filter in the first place → just run once
    return run_query("no filter", None)



# ── MAIN EXPORT FUNCTION ──────────────────────────────────────
def get_case_snippets(refined_query: str) -> List[dict]:
    """
    Given an already-refined query string, embed → query Pinecone
    with an intelligent metadata filter → return cleaned snippets.
    Falls back to NO metadata filter if the filtered query returns
    no usable snippets.
    """
    vec = embed_text(refined_query)

    filter_obj = _build_metadata_filter_from_query(refined_query)

    query_kwargs: Dict[str, Any] = {
        "vector": vec,
        "top_k": TOP_K,
        "include_metadata": True,
    }

    # ---- First pass: with metadata filter (if any) ----
    if filter_obj:
        query_kwargs["filter"] = filter_obj
        print("\n🔎 Using metadata filter:", filter_obj)

    resp = index.query(**query_kwargs)
    matches = resp.get("matches", [])
    snippets = _score_matches(matches)

    # ---- Fallback: retry WITHOUT filter if filter gave nothing ----
    if filter_obj and not snippets:
        print("⚠️ No snippets found with metadata filter. Retrying without filter...")
        # remove filter and re-query
        query_kwargs.pop("filter", None)
        resp = index.query(**query_kwargs)
        matches = resp.get("matches", [])
        snippets = _score_matches(matches)

    return snippets


# ── INTERACTIVE TEST BLOCK ────────────────────────────────────
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
