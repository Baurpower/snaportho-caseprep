import os, sys, json, re
from collections import Counter, defaultdict
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
idx = pc.Index(os.environ["PINECONE_INDEX"])

stats = idx.describe_index_stats()
namespaces = list(stats.get("namespaces", {}).keys())

SCOPE_KEYS = ["source", "source_collection", "specialty", "region",
              "diagnosis", "procedure", "procedures", "topic", "title"]

def is_empty(v):
    if v is None: return True
    if isinstance(v, str) and not v.strip(): return True
    if isinstance(v, (list, tuple)) and len(v) == 0: return True
    return False

def id_prefix(vid):
    m = re.match(r"^([a-zA-Z]+)[-_#]", vid)
    return m.group(1) if m else "(none)"

report = {}
for ns in namespaces:
    ns_label = ns if ns else "(default)"
    total = stats["namespaces"][ns].get("vector_count", 0)
    # collect all ids
    ids = []
    for page in idx.list(namespace=ns):
        ids.extend(page if isinstance(page, list) else [page])
    # fetch metadata in batches
    key_present = Counter()
    key_empty = Counter()
    prefixes = Counter()
    values = defaultdict(Counter)
    n_fetched = 0
    for i in range(0, len(ids), 100):
        batch = ids[i:i+100]
        res = idx.fetch(ids=batch, namespace=ns)
        vectors = res.vectors if hasattr(res, "vectors") else res.get("vectors", {})
        for vid, rec in vectors.items():
            n_fetched += 1
            prefixes[id_prefix(vid)] += 1
            md = (rec.metadata if hasattr(rec, "metadata") else rec.get("metadata")) or {}
            allkeys = set(md.keys())
            for k in allkeys:
                key_present[k] += 1
                if is_empty(md.get(k)): key_empty[k] += 1
            for k in SCOPE_KEYS:
                v = md.get(k)
                if is_empty(v): continue
                vals = v if isinstance(v, list) else [v]
                for x in vals:
                    values[k][str(x).lower().strip()[:40]] += 1
    report[ns_label] = {
        "declared_count": total,
        "ids_listed": len(ids),
        "fetched": n_fetched,
        "id_prefixes": prefixes.most_common(),
        "key_present_pct": {k: round(100*c/max(n_fetched,1),1) for k, c in key_present.most_common()},
        "key_empty_count": {k: key_empty[k] for k in key_present if key_empty[k]},
        "scope_values": {k: values[k].most_common(15) for k in SCOPE_KEYS if values[k]},
    }

print(json.dumps(report, indent=1, default=str))
out = os.path.join(os.path.dirname(__file__), "vector_metadata_audit.json")
json.dump(report, open(out, "w"), indent=1, default=str)
print("\nwritten:", out)

# --- contract validation (see docs/vector-metadata-contract.md) ---
def pct(ns, key):
    return report.get(ns, {}).get("key_present_pct", {}).get(key, 0.0)

def covered(ns, key):  # present as value or as _none sentinel
    return round(pct(ns, key) + pct(ns, f"{key}_none"), 1)

checks = []
default = "(default)"
checks.append(("default source_collection = 100%", pct(default, "source_collection") >= 99.9))
checks.append(("default specialty >= 99%", pct(default, "specialty") >= 99.0))
checks.append(("default region >= 99%", pct(default, "region") >= 99.0))
checks.append(("default procedures present-or-sentinel = 100%", covered(default, "procedures") >= 99.9))
checks.append(("default diagnoses present-or-sentinel = 100%", covered(default, "diagnoses") >= 99.9))
an = "anatomy_miller_gold_v1"
checks.append(("anatomy source_collection = 100%", pct(an, "source_collection") >= 99.9))
checks.append(("anatomy specialty >= 99%", pct(an, "specialty") >= 99.0))
checks.append(("anatomy region >= 99%", pct(an, "region") >= 99.0))
rk = "rock-v1"
checks.append(("rock-v1 source_collection = 100%", pct(rk, "source_collection") >= 99.9))

print("\n=== CONTRACT VALIDATION ===")
allok = True
for name, ok in checks:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    allok = allok and ok
print("RESULT:", "ALL PASS" if allok else "FAILURES PRESENT")
sys.exit(0 if allok else 1)
