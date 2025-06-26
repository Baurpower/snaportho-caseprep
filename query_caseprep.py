import os, json, textwrap
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI
from typing import List
from sentence_transformers import CrossEncoder # type: ignore

# ── ENV & CLIENTS ────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID   = os.getenv("OPENAI_PROJECT_ID")
PINECONE_API_KEY    = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX")

print("🔑 OpenAI Key Loaded:", OPENAI_API_KEY[:10] + "…")
client = OpenAI(api_key=OPENAI_API_KEY, project=OPENAI_PROJECT_ID)
pc     = Pinecone(api_key=PINECONE_API_KEY)
index  = pc.Index(PINECONE_INDEX_NAME)

reranker = CrossEncoder("BAAI/bge-reranker-base")

EMBED_MODEL = "text-embedding-3-small"
GPT_MODEL   = "gpt-4o-mini"
TOP_K       = 30  # more liberal initial fetch
MIN_SCORE   = 0.3

# ── EMBED ────────────────────────────────────────────────────
def _embed(txt: str):
    return client.embeddings.create(model=EMBED_MODEL, input=txt).data[0].embedding

# ── RERANK AND FILTER ───────────────────────────────────────
def _rerank(query: str, matches: List[dict]) -> List[str]:
    pairs  = [(query, m["metadata"].get("text", "")) for m in matches]
    scores = reranker.predict(pairs)
    for m, s in zip(matches, scores):
        m["rerank"] = float(s)

    filtered = [m for m in matches if m["score"] >= MIN_SCORE and m["metadata"].get("text")]
    top      = sorted(filtered, key=lambda x: x["rerank"], reverse=True)[:12]

    seen = set()
    clean_snips = []
    for m in top:
        snippet = m["metadata"]["text"].replace("\n", " ").strip()
        sig     = snippet.lower().split(" ")[:8]  # crude dedup key
        key     = " ".join(sig)
        if key not in seen:
            seen.add(key)
            clean_snips.append(snippet)
    return clean_snips

# ── GPT GROUPING ─────────────────────────────────────────────
def _group_with_gpt(query: str, snippets: List[str]) -> str:
    cards_json = json.dumps(snippets, indent=2)
    system = (
        "You are an orthopedic surgery tutor."
        " Given a case and supporting flashcard text, organize the information into three clear markdown sections:\n"
        "### Key Anatomy to Review\n"
        "### Common Pimp Questions\n"
        "### Other Useful Facts\n"
        "Use bullets. Be direct. No introductory sentences."
    )
    user = f"Case: {query}\nFlashcards (JSON list):\n{cards_json}"
    chat = client.chat.completions.create(
        model=GPT_MODEL,
        temperature=0.3,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ]
    )
    return chat.choices[0].message.content.strip()

# ── PUBLIC FUNCTION --------------------------------------------------------
def case_prep_lookup(user_query: str) -> str:
    vec     = _embed(user_query)
    matches = index.query(vector=vec, top_k=TOP_K, include_metadata=True)["matches"]
    snippets = _rerank(user_query, matches)
    if not snippets:
        return "**No matches found – try rephrasing.**"
    return _group_with_gpt(user_query, snippets)

# ── CLI TEST LOOP ----------------------------------------------------------
if __name__ == "__main__":
    while True:
        prompt = input("\n🩺  Enter case (or 'quit'): ").strip()
        if prompt.lower() in {"quit", "exit"}: break
        print("\n" + textwrap.dedent(case_prep_lookup(prompt)))
