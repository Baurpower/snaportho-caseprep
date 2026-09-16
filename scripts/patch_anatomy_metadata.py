#!/usr/bin/env python3
"""Phase C: patch anatomy_miller_gold_v1 namespace metadata.
- Set source_collection="miller_anatomy" on all vectors (deterministic).
- Fill the ~39 vectors missing specialty/region via gpt-4o-mini over their text,
  constrained to the controlled vocab. Anatomy sub-fields are left untouched.

Usage: python scripts/patch_anatomy_metadata.py [--apply]   (default dry-run)
"""
from __future__ import annotations
import argparse, json, os
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()
NS = "anatomy_miller_gold_v1"
SOURCE_COLLECTION = "miller_anatomy"
MODEL = "gpt-4o-mini"

SPECIALTIES = ["peds","hand","trauma","sports","onc","footankle","basicscience",
               "shoulderelbow","recon","spine","general"]
REGIONS = ["hip","knee","shoulder","elbow","wrist","hand","ankle","foot","spine",
           "pelvis","forearm","thigh","leg","upper_extremity","lower_extremity","non-anatomic"]


def load(idx):
    ids = []
    for p in idx.list(namespace=NS):
        ids.extend(p if isinstance(p, list) else [p])
    cards = {}
    for i in range(0, len(ids), 100):
        r = idx.fetch(ids=ids[i:i+100], namespace=NS)
        vs = r.vectors if hasattr(r, "vectors") else r["vectors"]
        for vid, rec in vs.items():
            cards[vid] = (rec.metadata if hasattr(rec, "metadata") else rec["metadata"]) or {}
    return cards


def classify(client, batch):
    sys_p = (
        "Classify orthopaedic anatomy study chunks. For each, choose exactly one specialty "
        f"from {SPECIALTIES} and one region from {REGIONS}. Use 'basicscience'/'non-anatomic' "
        "for general/intro/overview material with no specific anatomic region. "
        'Return STRICT JSON {"results":[{"id":str,"specialty":str,"region":str}]}'
    )
    user = {"cards": [{"id": vid, "heading": md.get("heading"),
                       "section_path": md.get("section_path"),
                       "text": (md.get("text") or "")[:900]} for vid, md in batch]}
    resp = client.chat.completions.create(
        model=MODEL, temperature=0, response_format={"type": "json_object"},
        messages=[{"role": "system", "content": sys_p},
                  {"role": "user", "content": json.dumps(user)}])
    return json.loads(resp.choices[0].message.content).get("results", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    idx = pc.Index(os.environ["PINECONE_INDEX"])
    cards = load(idx)
    missing = [(vid, md) for vid, md in cards.items()
               if not md.get("specialty") or not md.get("region")]
    print(f"{len(cards)} anatomy cards; {len(missing)} missing specialty/region")

    fills = {}
    if missing:
        from openai import OpenAI
        client = OpenAI()
        for i in range(0, len(missing), 12):
            for r in classify(client, missing[i:i+12]):
                vid = r.get("id")
                if vid in cards:
                    sp = r.get("specialty") if r.get("specialty") in SPECIALTIES else "basicscience"
                    rg = r.get("region") if r.get("region") in REGIONS else "non-anatomic"
                    fills[vid] = {"specialty": sp, "region": rg}
        print("proposed fills:")
        for vid, f in list(fills.items())[:50]:
            print(" ", vid, f)

    if not args.apply:
        print("\n(dry-run) not writing. re-run with --apply")
        return

    n_sc = 0
    for vid in cards:
        idx.update(id=vid, set_metadata={"source_collection": SOURCE_COLLECTION}, namespace=NS)
        n_sc += 1
        if n_sc % 200 == 0: print(f"  source_collection {n_sc}")
    for vid, f in fills.items():
        idx.update(id=vid, set_metadata={"specialty": f["specialty"], "region": f["region"],
                                         "metadata_trust": "llm_backfill_v1"}, namespace=NS)
    print(f"applied source_collection to {n_sc}; filled specialty/region on {len(fills)}")


if __name__ == "__main__":
    main()
