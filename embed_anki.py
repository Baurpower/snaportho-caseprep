import os, json, textwrap
from dotenv import load_dotenv
import pinecone
from openai import OpenAI

# ── ENV & CLIENTS ────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID   = os.getenv("OPENAI_PROJECT_ID")
PINECONE_API_KEY    = os.getenv("PINECONE_API_KEY")
PINECONE_ENV        = os.getenv("PINECONE_ENVIRONMENT")  # Add this to your .env if not already
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX")

print("🔑 OpenAI Key Loaded:", OPENAI_API_KEY[:10] + "…")
client = OpenAI(api_key=OPENAI_API_KEY, project=OPENAI_PROJECT_ID)

# Initialize Pinecone
pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)
index = pinecone.Index(PINECONE_INDEX_NAME)

EMBED_MODEL = "text-embedding-3-small"
GPT_MODEL   = "gpt-4o-mini"
TOP_K       = 15
MIN_SCORE   = 0.3

# ── EMBED ────────────────────────────────────────────────────
def _embed(txt: str):
    return client.embeddings.create(model=EMBED_MODEL, input=txt).data[0].embedding

# ── GPT GROUPING ─────────────────────────────────────────────
def _group_with_gpt(query: str, snippets: list[str]) -> str:
    cards_json = json.dumps(snippets, indent=2)
    system = (
        "You are an orthopedic surgery tutor. "
        "For the given surgical case, bucket each flashcard snippet into exactly one "
        "of three headings:\n"
        "1. Key Anatomy to Review\n"
        "2. Common Pimp Questions\n"
        "3. Other Useful Facts\n\n"
        "Return clean Markdown bullets under each heading."
    )
    user = f"Case: {query}\nFlashcards (JSON list):\n{cards_json}"
    chat = client.chat.completions.create(
        model=GPT_MODEL,
        temperature=0.4,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    )
    return chat.choices[0].message.content.strip()

# ── PUBLIC FUNCTION --------------------------------------------------------
def case_prep_lookup(user_query: str) -> str:
    vec = _embed(user_query)
    matches = index.query(vector=vec, top_k=TOP_K, include_metadata=True).matches
    snippets = [
        m.metadata.get("text", "").replace("\n", " ").strip()
        for m in matches if m.score >= MIN_SCORE
    ]
    if not snippets:
        return "**No matches found – try rephrasing.**"
    return _group_with_gpt(user_query, snippets)

# ── CLI TEST LOOP ----------------------------------------------------------
if __name__ == "__main__":
    while True:
        prompt = input("\n🩺  Enter case (or 'quit'): ").strip()
        if prompt.lower() in {"quit", "exit"}:
            break
        print("\n" + textwrap.dedent(case_prep_lookup(prompt)))
