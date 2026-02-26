import os
import json
import hashlib
import sys 
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from tqdm import tqdm
from openai import OpenAI
from pinecone import Pinecone


# ── ENV ─────────────────────────────────────────────────────
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

# ── CONFIG ──────────────────────────────────────────────────
INPUT_JSONL  = "normalized_millers_v1.jsonl"
EMBED_MODEL  = "text-embedding-3-small"   # 1536-dim
SOURCE_NAME  = "Millers"

EMBED_BATCH_SIZE  = 96     # safe default; can raise if you want
UPSERT_BATCH_SIZE = 100    # pinecone upsert batch size


# ── HELPERS ─────────────────────────────────────────────────
def s(val: Any) -> str:
    """Clean string, always returns a string."""
    if val is None:
        return ""
    return str(val).strip()

def lower(val: Any) -> str:
    return s(val).lower()

def stable_id(prefix: str, q: str, a: str) -> str:
    """Stable ID so reruns don't create duplicates."""
    h = hashlib.sha1(f"{q}||{a}".encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{h}"

def gather_multi(meta: Dict[str, Any], base: str, max_n: int = 10) -> List[str]:
    """
    Collect values for keys like:
      diagnosis, diagnosis1..diagnosis5
      procedure, procedure2..procedure3
    Returns list of unique non-empty strings in original order.
    """
    vals: List[str] = []

    # base itself (e.g., "diagnosis")
    if base in meta:
        v = s(meta.get(base))
        if v:
            vals.append(v)

    # numbered variants (diagnosis1..)
    for i in range(1, max_n + 1):
        key = f"{base}{i}"
        if key in meta:
            v = s(meta.get(key))
            if v:
                vals.append(v)

    # de-dupe preserving order
    seen = set()
    out = []
    for v in vals:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out

def build_full_text(q: str, a: str, info: str) -> str:
    txt = f"Q: {q}\nA: {a}"
    if info:
        txt += f"\nNote: {info}"
    return txt

def build_enriched_text(full_text: str, meta_norm: Dict[str, Any]) -> str:
    """
    What you actually embed.
    Keep it consistent across the whole corpus.
    """
    diagnoses = meta_norm.get("diagnoses", [])
    procedures = meta_norm.get("procedures", [])

    # Keep labels minimal + consistent (avoid overly verbose prompts)
    parts = [full_text]

    spec = meta_norm.get("specialty", "")
    reg  = meta_norm.get("region", "")
    subr = meta_norm.get("subregion", "")
    if spec: parts.append(f"Specialty: {spec}")
    if reg:  parts.append(f"Region: {reg}")
    if subr: parts.append(f"Subregion: {subr}")
    if diagnoses: parts.append("Diagnosis: " + ", ".join(diagnoses))
    if procedures: parts.append("Procedure: " + ", ".join(procedures))

    return "\n".join(parts)

def normalize_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize variable schema into a stable Pinecone metadata payload.
    Pinecone metadata should be primitives or list[str].
    """
    diagnoses = gather_multi(meta, "diagnosis", max_n=10)
    procedures = gather_multi(meta, "procedure", max_n=10)

    out: Dict[str, Any] = {
        "source": SOURCE_NAME,
        "specialty": lower(meta.get("specialty")),
        "specialty2": lower(meta.get("specialty2")),
        "region": lower(meta.get("region")),
        "subregion": lower(meta.get("subregion")),
        # store as list[str] for filtering later
        "diagnoses": [d.lower() for d in diagnoses],
        "procedures": [p.lower() for p in procedures],
    }

    # Optional: keep raw original strings too (helpful if you later want exact display)
    # out["specialty_raw"] = s(meta.get("specialty"))
    # out["region_raw"] = s(meta.get("region"))

    return out

def chunked(lst: List[Any], n: int):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]


# ── STEP 1: Load JSONL ──────────────────────────────────────
records: List[Tuple[str, str, str, Dict[str, Any]]] = []
# tuple = (id, full_text, enriched_text, metadata_for_pinecone)

with open(INPUT_JSONL, "r", encoding="utf-8") as infile:
    for i, line in enumerate(infile, start=1):
        line = line.strip()
        if not line:
            continue
        try:
            card = json.loads(line)
            q = s(card.get("question"))
            a = s(card.get("answer"))
            info = s(card.get("additional_info"))

            if not q and not a:
                continue

            meta = card.get("metadata") or {}
            meta_norm = normalize_metadata(meta)

            full_text = build_full_text(q, a, info)
            enriched_text = build_enriched_text(full_text, meta_norm)

            # store the embedded text in metadata so you can inspect in Pinecone dashboard
            meta_norm["text"] = enriched_text
            meta_norm["question"] = q
            meta_norm["answer"] = a

            card_id = stable_id("pp", q, a)
            records.append((card_id, full_text, enriched_text, meta_norm))

        except Exception as e:
            print(f"⚠️ Failed to parse line {i}: {e}", file=sys.stderr)

print(f"✅ Prepared {len(records):,} records from {INPUT_JSONL}")


# ── STEP 2: Embed in batches + Upsert in batches ─────────────
for batch in tqdm(list(chunked(records, EMBED_BATCH_SIZE)), desc="🔼 Embedding+Upserting"):
    ids = [r[0] for r in batch]
    enriched_texts = [r[2] for r in batch]
    metas = [r[3] for r in batch]

    try:
        emb_resp = client.embeddings.create(
            model=EMBED_MODEL,
            input=enriched_texts
        )
        vectors = [d.embedding for d in emb_resp.data]

        # Build pinecone upsert payload
        to_upsert = [(ids[j], vectors[j], metas[j]) for j in range(len(batch))]

        # upsert in smaller chunks if desired
        for up_batch in chunked(to_upsert, UPSERT_BATCH_SIZE):
            index.upsert(up_batch)

    except Exception as e:
        print(f"⚠️ Error embedding/upserting batch starting with {ids[0]}: {e}", file=sys.stderr)

print("✅ Done.")
