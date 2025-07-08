# vector_search.py

import os
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI
from typing import List


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
TOP_K = 40
MIN_SCORE = 0.4

# ── EMBED ─────────────────────────────────────────────────────
def embed_text(txt: str):
    return client.embeddings.create(model=EMBED_MODEL, input=txt).data[0].embedding

# ── SCORE + FILTER ────────────────────────────────────────────
def _score_matches(query: str, matches: List[dict]) -> List[str]:
    filtered = [m for m in matches if m["score"] >= MIN_SCORE and m["metadata"].get("text")]
    seen = set()
    clean_snips = []

    for m in filtered:
        snippet = m["metadata"]["text"].replace("\n", " ").strip()
        sig = " ".join(snippet.lower().split(" ")[:8])
        if sig not in seen:
            seen.add(sig)
            clean_snips.append(snippet)

    return clean_snips[:12]

# ── MAIN EXPORT FUNCTION ──────────────────────────────────────
def get_case_snippets(user_query: str) -> List[str]:
    vec = embed_text(user_query)
    matches = index.query(vector=vec, top_k=TOP_K, include_metadata=True)["matches"]
    return _score_matches(user_query, matches)
