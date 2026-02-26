from collections import Counter, defaultdict
from openai import OpenAI
from pinecone import Pinecone
import os
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI

# ── ENV & CLIENTS ─────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX")

client = OpenAI(api_key=OPENAI_API_KEY, project=OPENAI_PROJECT_ID)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

def embed(txt: str):
    return client.embeddings.create(model="text-embedding-3-small", input=txt).data[0].embedding

vec = embed("orthopaedic trauma flashcards metadata audit")

resp = index.query(
    vector=vec,
    top_k=200,
    include_metadata=True
)

matches = resp.get("matches", [])

# 1) what keys exist
key_counts = Counter()
# 2) what values exist for important keys
value_counts = defaultdict(Counter)

for m in matches:
    md = (m.get("metadata") or {})
    for k in md.keys():
        key_counts[k] += 1

    for k in ["specialty", "region", "diagnosis", "procedure", "source"]:
        v = md.get(k)
        if v is None: 
            continue
        # normalize lists vs strings
        if isinstance(v, list):
            for x in v:
                value_counts[k][str(x).lower().strip()] += 1
        else:
            value_counts[k][str(v).lower().strip()] += 1

print("\n=== METADATA KEYS (top) ===")
for k, c in key_counts.most_common(30):
    print(f"{k}: {c}")

for k in ["specialty","region","diagnosis","procedure","source"]:
    print(f"\n=== {k.upper()} VALUES (top 30) ===")
    for v, c in value_counts[k].most_common(30):
        print(f"{v}: {c}")
