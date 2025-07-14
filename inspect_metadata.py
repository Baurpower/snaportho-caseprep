import os
import json
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI

# ── Load credentials ──
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX")

# ── Initialize clients ──
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

# ── Dummy vector (required for Pinecone query) ──
def embed_text(text: str):
    return [0.0] * 1536  # Use a dummy zero vector since we're just browsing metadata

# ── Query Pinecone and print metadata ──
if __name__ == "__main__":
    print("🔍 Inspecting metadata in Pinecone...")

    dummy_vector = embed_text("orthopaedic surgery")

    results = index.query(
        vector=dummy_vector,
        top_k=50,
        include_metadata=True
    )["matches"]

    print(f"📦 Retrieved {len(results)} vectors:")
    for i, item in enumerate(results, 1):
        meta = item.get("metadata", {})
        print(f"{i:02d}. ID: {item['id']}")
        print(f"     Specialty: {meta.get('specialty')}")
        print(f"     Region:    {meta.get('region')}")
        print(f"     Procedure: {meta.get('procedure')}")
        print("")
