import os, re
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm
from openai import OpenAI          # 1.x SDK
from pinecone import Pinecone

# ── STEP 0: ENV & CLIENTS ────────────────────────────────────
load_dotenv()
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID   = os.getenv("OPENAI_PROJECT_ID")  # optional
PINECONE_API_KEY    = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX")

if not all([OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_INDEX_NAME]):
    raise ValueError("Missing OPENAI_API_KEY, PINECONE_API_KEY, or PINECONE_INDEX")

client = OpenAI(api_key=OPENAI_API_KEY, project=OPENAI_PROJECT_ID)
pc     = Pinecone(api_key=PINECONE_API_KEY)
index  = pc.Index(PINECONE_INDEX_NAME)

# ── Config ──────────────────────────────────────────────────
TXT_FILES   = ["embed_anki_ok_millers.txt"]
EMBED_MODEL = "text-embedding-3-small"   # 1536-dim

# ── Helpers ─────────────────────────────────────────────────
def safe_str(x): return "" if pd.isna(x) else str(x)
def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)                  # remove HTML
    text = re.sub(r"\{\{c\d+::(.*?)\}\}", r"\1", text)    # unwrap cloze
    return re.sub(r"\s+", " ", text).strip()

# ----------------------------------------------------------------
# STEP 1: Load each file, build records
# ----------------------------------------------------------------
records = []
colnames = [f"c{i}" for i in range(19)]  # c0…c18

for file in TXT_FILES:
    try:
        df = pd.read_csv(
            file,
            sep="\t",
            header=None,
            comment="#",
            names=colnames,
            dtype=str,
            keep_default_na=False,
            engine="python"
        )
    except Exception as e:
        print(f"❌ Failed to load {file}: {e}")
        continue

    print(f"✅ Loaded {len(df):,} rows from {file}")
    prefix = os.path.splitext(os.path.basename(file))[0]

    for i, row in df.iterrows():
        front = strip_html(safe_str(row["c0"]))  # first column
        back  = strip_html(safe_str(row["c1"]))  # second column
        tags  = [t for t in strip_html(safe_str(row["c18"])).split() if t]

        # skip only if BOTH sides empty
        if not front and not back:
            continue

        text = f"Q: {front}\nA: {back}" if front else f"A: {back}"
        card_id = f"{prefix}-{i}"

        records.append((card_id, text, {
            "deck":  prefix,
            "tags":  tags,
            "text":  text,
            "source":"anki"
        }))

print(f"🔧 Prepared {len(records):,} total cards")

# ----------------------------------------------------------------
# STEP 2: Embed and upsert
# ----------------------------------------------------------------
for card_id, text, meta in tqdm(records, desc="🔼 Uploading to Pinecone"):
    try:
        emb = client.embeddings.create(model=EMBED_MODEL, input=text).data[0].embedding
        index.upsert([(card_id, emb, meta)])
    except Exception as e:
        print(f"⚠️  Error on {card_id}: {e}")

print("✅ All done – vectors are now stored in Pinecone!")
