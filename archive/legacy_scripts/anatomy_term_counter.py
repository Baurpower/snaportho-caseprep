import json
from collections import Counter
import re

INPUT_PATH = "pp_anatomy_terms.jsonl"  # <- your file
OUTPUT_CSV = "anatomy_term_counts.csv"  # optional

def normalize_term(term: str) -> str:
    term = term.strip()
    term = re.sub(r"\s+", " ", term)
    return term.lower()  # normalize to lowercase for counting

def count_anatomic_terms(path: str):
    counter = Counter()

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            terms = row.get("extracted_anatomic_structures", []) or []
            for term in terms:
                counter[normalize_term(term)] += 1

    return counter

def main():
    counter = count_anatomic_terms(INPUT_PATH)

    print(f"\n📊 Found {len(counter)} unique anatomic terms\n")

    print("🔢 Term Frequencies (most common first):\n")
    for term, count in counter.most_common():
        print(f"{term:<30} {count}")

    # Optional: write CSV
    with open(OUTPUT_CSV, "w", encoding="utf-8") as f:
        f.write("term,count\n")
        for term, count in counter.most_common():
            f.write(f"{term},{count}\n")

    print(f"\n💾 Saved counts to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()