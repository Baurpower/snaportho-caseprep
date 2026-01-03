import os, json
from dotenv import load_dotenv
from tqdm import tqdm
from openai import OpenAI
from pinecone import Pinecone

# ── STEP 0: Load ENV ─────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID   = os.getenv("OPENAI_PROJECT_ID")  # optional
PINECONE_API_KEY    = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX")

if not all([OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_INDEX_NAME]):
    raise ValueError("❌ Missing one or more required environment variables.")

client = OpenAI(api_key=OPENAI_API_KEY, project=OPENAI_PROJECT_ID) if OPENAI_PROJECT_ID else OpenAI(api_key=OPENAI_API_KEY)
pc     = Pinecone(api_key=PINECONE_API_KEY)
index  = pc.Index(PINECONE_INDEX_NAME)

# ── Config ───────────────────────────────────────────────────
INPUT_ROOT  = "data/lower_extremity"                      # <-- folder root
EMBED_MODEL = "text-embedding-3-small"    # 1536-dim
BATCH_SIZE  = 100

# ── STEP 1: Find all JSONL files under data/ ─────────────────
jsonl_files = []
for root, _, files in os.walk(INPUT_ROOT):
    for fn in files:
        if fn.lower().endswith(".jsonl"):
            jsonl_files.append(os.path.join(root, fn))

if not jsonl_files:
    raise FileNotFoundError(f"❌ No .jsonl files found under: {INPUT_ROOT}")

print(f"✅ Found {len(jsonl_files)} .jsonl files under {INPUT_ROOT}")

# ── STEP 2: Load all JSONL records ───────────────────────────
import os, json

# ── Helpers ───────────────────────────────────────────────────
def safe_str(x) -> str:
    return str(x).strip() if x is not None else ""

def as_list_str(x) -> list[str]:
    """
    Always returns list[str]. Safe for Pinecone metadata.
    - None -> []
    - list -> list of non-empty strings
    - str  -> [str] if non-empty
    - other -> [str(other)] if non-empty (or [])
    """
    if x is None:
        return []
    if isinstance(x, list):
        out = []
        for v in x:
            s = safe_str(v)
            if s:
                out.append(s)
        return out
    if isinstance(x, str):
        s = x.strip()
        return [s] if s else []
    s = safe_str(x)
    return [s] if s else []

def lower_list(xs) -> list[str]:
    return [safe_str(x).lower() for x in (xs or []) if safe_str(x)]

def clean_meta(d: dict) -> dict:
    """
    Remove empty values and empty strings inside lists to keep metadata small
    and Pinecone-friendly.
    """
    cleaned = {}
    for k, v in d.items():
        if v in [None, "", [], {}]:
            continue
        if isinstance(v, list):
            vv = [safe_str(x) for x in v if safe_str(x)]
            if not vv:
                continue
            cleaned[k] = vv
        else:
            cleaned[k] = v
    return cleaned

def get_source_ref(meta: dict) -> str:
    src = meta.get("source")
    if isinstance(src, dict):
        return safe_str(src.get("ref"))
    if isinstance(src, str):
        return src.strip()
    return ""


# ── STEP 2: Load JSONL records -> enriched_text + flat_meta ───
# ── STEP 2: Load JSONL records -> enriched_text + SIMPLE metadata ───
records = []
seen_ids = set()

ALLOWED_CATEGORIES = {"osteology", "arthrology", "muscles", "nerves", "vasculature", "approaches"}

def add_line(label: str, value) -> str:
    """
    Clean labeled line builder for enriched_text.
    - list -> comma-joined
    - None/empty -> "Label:"
    - other -> "Label: value"
    """
    if value is None:
        return f"{label}:"
    if isinstance(value, list):
        vv = [safe_str(x) for x in value if safe_str(x)]
        return f"{label}: {', '.join(vv)}" if vv else f"{label}:"
    s = safe_str(value)
    return f"{label}: {s}" if s else f"{label}:"

def _get_bones(meta: dict) -> list[str]:
    """
    Pull bones from meta in a forgiving way.
    Supports:
      - meta["bones"] as list/str
      - meta["bone"] as str
    """
    bones = as_list_str(meta.get("bones"))
    if not bones:
        bones = as_list_str(meta.get("bone"))
    return bones

def _get_category(meta: dict, fallback_type: str = "") -> str:
    """
    Your desired top-level category:
      osteology, arthrology, muscles, nerves, vasculature, approaches

    Prefer meta["category"] if present. Otherwise map from type when possible.
    """
    cat = safe_str(meta.get("category")).lower()
    if cat in ALLOWED_CATEGORIES:
        return cat

    # Optional fallback mapping from "type" if you don't store category yet
    t = (fallback_type or "").lower()
    if any(k in t for k in ["approach", "surgical_approach"]):
        return "approaches"
    if any(k in t for k in ["nerve", "plexus", "root"]):
        return "nerves"
    if any(k in t for k in ["artery", "vein", "vascular", "vessel"]):
        return "vasculature"
    if any(k in t for k in ["muscle"]):
        return "muscles"
    if any(k in t for k in ["ligament", "meniscus", "labrum", "capsule", "cartilage", "arthro"]):
        return "arthrology"
    if any(k in t for k in ["bone", "osteology", "bony"]):
        return "osteology"

    return ""  # leave blank if unknown

for path in jsonl_files:
    with open(path, "r", encoding="utf-8") as infile:
        for i, line in enumerate(infile, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)

                doc_id  = safe_str(obj.get("id"))
                name    = safe_str(obj.get("name"))
                typ     = safe_str(obj.get("type"))
                text    = safe_str(obj.get("text"))
                aliases = as_list_str(obj.get("aliases"))

                meta = obj.get("meta")
                meta = meta if isinstance(meta, dict) else {}

                # Required fields
                if not doc_id:
                    raise ValueError("missing 'id'")
                if not typ:
                    raise ValueError("missing 'type'")
                if not name:
                    raise ValueError("missing 'name'")

                # Ensure global uniqueness across files
                if doc_id in seen_ids:
                    doc_id = f"{doc_id}::{os.path.relpath(path, INPUT_ROOT)}::{i}"
                seen_ids.add(doc_id)

                # ── ONLY the metadata you want ───────────────────────────────
                region        = safe_str(meta.get("region")).lower()
                anatomic_area = safe_str(meta.get("anatomic_area")).lower()
                joint         = safe_str(meta.get("joint")).lower()
                bones         = lower_list(_get_bones(meta))
                category      = _get_category(meta, fallback_type=typ)
                clinical_tags = lower_list(as_list_str(meta.get("clinical_tags")))

                # Store original type as lowercase string (you said you want it)
                typ_l = typ.lower()

                # ── Enriched text (what actually gets embedded) ───────────────
                # Make this THOROUGH: name/aliases + the full description text.
                # Include the simple meta as labels so retrieval benefits from it,
                # but don't bloat with tons of nested meta you don't want.
                enriched_text = "\n".join([
                    add_line("Name", name),
                    add_line("Type", typ_l),
                    add_line("Category", category),
                    add_line("Aliases", aliases),

                    add_line("Region", region),
                    add_line("Anatomic area", anatomic_area),
                    add_line("Joint", joint),
                    add_line("Bones", bones),
                    add_line("Clinical tags", clinical_tags),

                    # This is the important part: the actual content
                    add_line("Core description", text),
                ]).strip()

                # ── Flat Pinecone metadata (filterable) ───────────────────────
                flat_meta = clean_meta({
                    "name": name,
                    "aliases": lower_list(aliases),

                    "region": region or None,
                    "anatomic_area": anatomic_area or None,
                    "bones": bones,              # list[str]
                    "joint": joint or None,

                    "type": typ_l,               # fine-grain type from your JSONL (e.g., anatomy_ligament)
                    "category": category or None, # one of your 6 buckets (if present / mapped)

                    "clinical_tags": clinical_tags, # list[str]
                })

                flat_meta["fact"] = enriched_text

                records.append((doc_id, enriched_text, flat_meta))

            except Exception as e:
                print(f"⚠️ Failed to parse {path}:{i}: {e}")

print(f"✅ Prepared {len(records):,} records from {INPUT_ROOT}")


# ── STEP 3: Embed + Upsert ───────────────────────────────────────────
batch = []

for doc_id, enriched_text, meta in tqdm(records, desc="🔼 Uploading to Pinecone"):
    try:
        emb = client.embeddings.create(
            model=EMBED_MODEL,
            input=enriched_text
        ).data[0].embedding

        # Pinecone upsert: (id, vector, metadata)
        batch.append((doc_id, emb, meta))

        if len(batch) >= BATCH_SIZE:
            index.upsert(vectors=batch)
            batch = []

    except Exception as e:
        print(f"⚠️ Error embedding/upserting {doc_id}: {e}")

if batch:
    index.upsert(vectors=batch)

print("✅ All done – anatomy vectors are now stored in Pinecone!")
