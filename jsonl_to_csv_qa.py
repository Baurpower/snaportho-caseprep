import json
import csv
from pathlib import Path

INPUT_JSONL = "normalized_hipknee_facts.jsonl"
OUTPUT_CSV = "normalized_hipknee_facts.csv"

# Columns you want in Excel (edit this list as needed)
COLUMNS = [
    "question",
    "answer",
    "additional_info",
    "metadata.specialty",
    "metadata.region",
    "metadata.subregion",
    "metadata.diagnosis",
    "metadata.procedure",
    "metadata.specialty_raw",
    "metadata.region_raw",
    "metadata.subregion_raw",
    "metadata.diagnosis_raw",
    "metadata.procedure_raw",
]

def get_path(d, path):
    """Get nested values like metadata.region_raw"""
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return ""
        cur = cur[part]
    # Keep arrays/dicts as JSON strings so CSV stays valid
    if isinstance(cur, (dict, list)):
        return json.dumps(cur, ensure_ascii=False)
    return cur

with open(INPUT_JSONL, "r", encoding="utf-8") as f_in, open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f_out:
    writer = csv.DictWriter(f_out, fieldnames=COLUMNS)
    writer.writeheader()

    for line_num, line in enumerate(f_in, start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Bad JSON on line {line_num}: {e}") from e

        row = {col: get_path(obj, col) for col in COLUMNS}
        writer.writerow(row)

print(f"Wrote {OUTPUT_CSV}")
