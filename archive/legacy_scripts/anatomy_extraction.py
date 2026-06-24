import os
import json
import re
import time
from typing import List, Dict, Any, Set
from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------
# Setup (cheap + responsive)
# ---------------------------
load_dotenv()

# Add a client timeout so you don't hang forever
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=30.0)

# Cheapest fast model for this kind of extraction
MODEL = "gpt-4o-mini"

# SMALL batches so you can watch it work + quit anytime
BATCH_SIZE = 2

# Save progress often so Ctrl+C isn't painful
CHECKPOINT_PATH = "anatomy_checkpoint.json"
CHECKPOINT_EVERY_BATCH = True

# Print raw model output preview for sanity
PRINT_MODEL_PREVIEW = True
MODEL_PREVIEW_CHARS = 400

# ---------------------------
# Helpers
# ---------------------------

def read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    print(f"✅ Loaded {len(rows)} rows from {path}")
    return rows

def normalize_term(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s

def safe_json_loads(model_text: str) -> Dict[str, Any]:
    s = (model_text or "").strip()

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        return json.loads(fence.group(1))

    obj = re.search(r"(\{.*\})", s, flags=re.DOTALL)
    if obj:
        return json.loads(obj.group(1))

    raise json.JSONDecodeError("No JSON object found in model output", s, 0)

def fallback_regex_terms(text: str) -> Set[str]:
    candidates = set()
    patterns = [
        r"\b(glenohumeral joint|acromioclavicular joint|sternoclavicular joint)\b",
        r"\b(glenoid fossa|glenoid|scapula|scapular body)\b",
        r"\b(humeral head|humerus|distal humerus|proximal humerus)\b",
        r"\b(labrum|radial head|supracondylar)\b",
        r"\b(elbow|shoulder|clavicle|acromion|sternum)\b",
        r"\b(subclavian (?:artery|vein)|trachea|superior vena cava|SVC)\b",
        r"\b(posterior fat pad)\b",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            candidates.add(normalize_term(m.group(0)))
    return candidates

def build_record_text(row: Dict[str, Any]) -> str:
    q = row.get("question", "") or ""
    a = row.get("answer", "") or ""
    info = row.get("additional_info", "") or ""
    md = row.get("metadata", {}) or {}

    md_bits = []
    for k in ["region", "subregion"]:  # keep minimal (cheap)
        v = md.get(k, "")
        if v:
            md_bits.append(f"{k}: {v}")

    md_text = "\n".join(md_bits)
    # Keep the payload tight for cost/speed
    return f"QUESTION: {q}\nANSWER: {a}\nINFO: {info}\n{md_text}".strip()

def save_checkpoint(path: str, merged: Dict[int, Set[str]], next_start: int):
    serializable = {
        "next_start": next_start,
        "merged": {str(k): sorted(list(v)) for k, v in merged.items() if v}
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)
    print(f"💾 Saved checkpoint -> {path} (next_start={next_start})")

def load_checkpoint(path: str) -> tuple[int, Dict[int, Set[str]]]:
    if not os.path.exists(path):
        return 0, {}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    next_start = int(data.get("next_start", 0))
    merged_raw = data.get("merged", {}) or {}
    merged: Dict[int, Set[str]] = {int(k): set(v) for k, v in merged_raw.items()}

    print(f"♻️ Loaded checkpoint {path}: resume at index {next_start} ({len(merged)} rows have data)")
    return next_start, merged

# ---------------------------
# GPT Extraction
# ---------------------------

SYSTEM_PROMPT = """Extract anatomic structures from orthopaedic Q/A cards.

Return ONLY anatomic structures (bones, joints, muscles, tendons, ligaments, nerves, vessels, organs).
Exclude radiographic views, eponyms, signs, diagnoses, procedures, and generic terms like "fracture".

Output STRICT JSON:
{"results":[{"id":"string","structures":["string"]}]}
"""

def extract_anatomy_batch(records: List[Dict[str, Any]], batch_label: str = "") -> Dict[str, List[str]]:
    payload = [{"id": r["id"], "text": r["text"]} for r in records]

    user_prompt = {
        "records": payload,
        "reminder": "Return STRICT JSON only. No markdown."
    }

    print(f"\n🚀 {batch_label} sending {len(payload)} records to {MODEL}...")

    t0 = time.time()
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        max_tokens=400,  # keep it cheap; extraction shouldn't need much
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_prompt)}
        ],
    )
    dt = time.time() - t0

    content = resp.choices[0].message.content or ""
    print(f"✅ {batch_label} response received in {dt:.1f}s")

    if PRINT_MODEL_PREVIEW:
        preview = content[:MODEL_PREVIEW_CHARS].replace("\n", "\\n")
        print(f"🧠 {batch_label} model preview: {preview}")

    data = safe_json_loads(content)

    out: Dict[str, List[str]] = {}
    for item in data.get("results", []):
        rid = item.get("id")
        structures = item.get("structures", []) or []
        if rid is None:
            continue
        out[str(rid)] = [
            normalize_term(s) for s in structures
            if isinstance(s, str) and s.strip()
        ]

    # quick batch stats
    extracted_n = sum(len(v) for v in out.values())
    print(f"📦 {batch_label} extracted {extracted_n} structures total")
    return out

def extract_all_anatomy(rows: List[Dict[str, Any]], batch_size: int = BATCH_SIZE) -> Dict[int, List[str]]:
    records = [{"id": str(i), "text": build_record_text(row)} for i, row in enumerate(rows)]

    # Resume support
    start_at, merged_partial = load_checkpoint(CHECKPOINT_PATH)

    merged: Dict[int, Set[str]] = {i: set() for i in range(len(rows))}
    for idx, terms in merged_partial.items():
        if 0 <= idx < len(rows):
            merged[idx].update(terms)

    total = len(records)
    total_batches = (total + batch_size - 1) // batch_size

    print(f"\n🔄 Total rows: {total} | batch_size: {batch_size} | total_batches: {total_batches}")
    print("💡 You can Ctrl+C anytime — progress is checkpointed.\n")

    # start loop at checkpoint point
    for start in range(start_at, total, batch_size):
        end = min(start + batch_size, total)
        batch = records[start:end]
        batch_num = (start // batch_size) + 1
        label = f"[batch {batch_num}/{total_batches} rows {start}-{end-1}]"

        gpt_map = extract_anatomy_batch(batch, batch_label=label)

        for rid, structures in gpt_map.items():
            idx = int(rid)
            merged[idx].update(structures)

        # optional: regex assist (cheap)
        for r in batch:
            idx = int(r["id"])
            merged[idx].update(fallback_regex_terms(r["text"]))

        # save checkpoint after every batch
        if CHECKPOINT_EVERY_BATCH:
            save_checkpoint(CHECKPOINT_PATH, merged, next_start=end)

    # done: remove checkpoint if you want (I leave it)
    return {i: sorted(merged[i]) for i in merged}

def write_outputs(rows: List[Dict[str, Any]], anatomy_map: Dict[int, List[str]], out_jsonl_path: str):
    with open(out_jsonl_path, "w", encoding="utf-8") as f:
        for i, row in enumerate(rows):
            row_out = dict(row)
            row_out["extracted_anatomic_structures"] = anatomy_map.get(i, [])
            f.write(json.dumps(row_out, ensure_ascii=False) + "\n")
    print(f"\n💾 Wrote output file: {out_jsonl_path}")

def summarize_global(anatomy_map: Dict[int, List[str]]) -> List[str]:
    all_terms = set()
    for terms in anatomy_map.values():
        all_terms.update(terms)
    return sorted(all_terms)

# ---------------------------
# Run
# ---------------------------

if __name__ == "__main__":
    in_path = "normalized_pp_v1.jsonl"
    out_path = "pp_anatomy_terms.jsonl"

    rows = read_jsonl(in_path)

    try:
        anatomy_map = extract_all_anatomy(rows, batch_size=BATCH_SIZE)
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user (Ctrl+C). Your checkpoint is saved.")
        raise

    write_outputs(rows, anatomy_map, out_path)

    global_terms = summarize_global(anatomy_map)
    print(f"\n📊 SUMMARY")
    print(f"Processed {len(rows)} rows.")
    print(f"Found {len(global_terms)} unique anatomic structures.\n")

    for t in global_terms:
        print("-", t)

    print(f"\n✅ Done. Output: {out_path}")