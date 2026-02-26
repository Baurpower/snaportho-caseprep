import json
from collections import defaultdict

INPUT_FILE = "normalized_pp_v1.jsonl"

def clean(s):
    if not s:
        return ""
    return str(s).strip().lower()

def extract_multi(meta, base, max_n=10):
    values = []

    # base key (diagnosis, procedure)
    if base in meta:
        v = clean(meta.get(base))
        if v:
            values.append(v)

    # numbered keys (diagnosis1..)
    for i in range(1, max_n + 1):
        key = f"{base}{i}"
        if key in meta:
            v = clean(meta.get(key))
            if v:
                values.append(v)

    return values


regions = set()
subregions = set()
diagnoses = set()
procedures = set()

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    for line in f:
        card = json.loads(line)
        meta = card.get("metadata", {})

        r = clean(meta.get("region"))
        sr = clean(meta.get("subregion"))

        if r:
            regions.add(r)
        if sr:
            subregions.add(sr)

        for d in extract_multi(meta, "diagnosis"):
            diagnoses.add(d)

        for p in extract_multi(meta, "procedure"):
            procedures.add(p)

# Convert to sorted lists
dictionary = {
    "regions": sorted(regions),
    "subregions": sorted(subregions),
    "diagnoses": sorted(diagnoses),
    "procedures": sorted(procedures),
}

OUTPUT_FILE = "metadata_dictionary.json"

with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
    json.dump(dictionary, out, indent=2)

print(f"✅ Dictionary saved to {OUTPUT_FILE}")
