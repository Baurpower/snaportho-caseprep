import os, json
from dotenv import load_dotenv
from tqdm import tqdm
from openai import OpenAI
from pinecone import Pinecone

# ── STEP 0: Load ENV ─────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID   = os.getenv("OPENAI_PROJECT_ID")
PINECONE_API_KEY    = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX")

if not all([OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_INDEX_NAME]):
    raise ValueError("❌ Missing one or more required environment variables.")

client = OpenAI(api_key=OPENAI_API_KEY, project=OPENAI_PROJECT_ID)
pc     = Pinecone(api_key=PINECONE_API_KEY)
index  = pc.Index(PINECONE_INDEX_NAME)

# ── Config ───────────────────────────────────────────────────
INPUT_JSONL  = "output_vectorversion_pp.jsonl"
EMBED_MODEL  = "text-embedding-3-small"  # 1536-dim

# ── STEP 1: Load JSONL flashcards ────────────────────────────
records = []

with open(INPUT_JSONL, 'r') as infile:
    for i, line in enumerate(infile):
        try:
            card = json.loads(line)
            q = card.get("question", "").strip()
            a = card.get("answer", "").strip()
            info = card.get("additional_info", "").strip()

            full_text = f"Q: {q}\nA: {a}"
            if info:
                full_text += f"\nNote: {info}"

            meta = card.get("metadata", {})

            # Flatten metadata + force lowercase for consistency
            flat_meta = {
                "text": full_text,
                "specialty": meta.get("specialty", "").lower(),
                "region": meta.get("region", "").lower(),
                "diagnosis": meta.get("diagnosis", "").lower(),
                "procedure": meta.get("procedure", "").lower(),
                "source": "Pocket Pimped"
            }

            card_id = f"pp-{i}"
            records.append((card_id, full_text, flat_meta))

        except Exception as e:
            print(f"⚠️ Failed to parse line {i}: {e}")

print(f"✅ Prepared {len(records):,} records from {INPUT_JSONL}")

# ── STEP 2: Embed and Upsert ────────────────────────────────
for card_id, text, meta in tqdm(records, desc="🔼 Uploading to Pinecone"):
    try:
        enriched_text = (
            f"{text}\n"
            f"Specialty: {meta.get('specialty', '')}\n"
            f"Region: {meta.get('region', '')}\n"
            f"Diagnosis: {meta.get('diagnosis', '')}\n"
            f"Procedure: {meta.get('procedure', '')}"
        )

        emb = client.embeddings.create(
            model=EMBED_MODEL,
            input=enriched_text
        ).data[0].embedding

        meta["text"] = enriched_text  # 👈 Makes sure metadata view reflects embedded content

        index.upsert([(card_id, emb, meta)])
    except Exception as e:
        print(f"⚠️  Error uploading {card_id}: {e}")
