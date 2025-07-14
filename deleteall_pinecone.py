import os
from dotenv import load_dotenv
from pinecone import Pinecone

# ── STEP 0: Load ENV ─────────────────────────────────────────
load_dotenv()
PINECONE_API_KEY    = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX")

# ── STEP 1: Connect to Pinecone ─────────────────────────────
pc = Pinecone(api_key=PINECONE_API_KEY)

# ── STEP 2: Delete All Vectors from the Index ───────────────
index = pc.Index(PINECONE_INDEX_NAME)
print(f"✅ Connected to Pinecone index: {PINECONE_INDEX_NAME}")

try:
    # This deletes *all* vectors
    index.delete(delete_all=True)
    print("🧹 All vectors deleted successfully.")
except Exception as e:
    print(f"❌ Deletion failed: {e}")
