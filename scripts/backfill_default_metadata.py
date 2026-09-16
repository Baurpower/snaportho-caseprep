#!/usr/bin/env python3
"""Backfill + normalize metadata for the default namespace (PocketPimp + Millers Q&A)
in the `ankiv3` Pinecone index. Metadata-only updates (index.update) — no re-embedding.

Phases:
  --source-collection   Deterministic source_collection from `source`. (no API)
  --extract             LLM (gpt-4o-mini) extract procedures + diagnoses from Q&A,
                        normalized to a cleaned controlled vocab.
  --apply               Actually write to Pinecone (default is dry-run: sidecar only).

Sidecar (proposals) is written to scripts/backfill_default_proposals.json so an
--extract dry-run can be reviewed before --extract --apply reads it back.

Controlled vocab is derived from the already-authored tags in the index, cleaned and
deduped via SYNONYMS below. The LLM is told to prefer these slugs.
"""
from __future__ import annotations
import argparse, json, os, re, sys, time
from collections import Counter
from pathlib import Path
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

NS = ""  # default namespace
SCHEMA_VERSION = "ankiv3-meta-v1"
MODEL = "gpt-4o-mini"
BATCH = 6
SIDECAR = Path(__file__).resolve().parent / "backfill_default_proposals.json"

# --- source -> source_collection (deterministic) ---------------------------
# Values MUST match rag_retrieval.py canonical constants:
#   POCKET_PIMP_SOURCE_COLLECTION = "pocket_pimped"
SOURCE_COLLECTION = {
    "pocket pimped": "pocket_pimped",
    "pocketpimp": "pocket_pimped",
    "millers": "millers",
    "miller": "millers",
}

# --- vocab normalization ---------------------------------------------------
def norm_slug(v: str) -> str:
    s = str(v).strip().lower()
    s = re.sub(r"[\s/]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

# explicit merges (messy authored variants -> canonical)
PROC_SYNONYMS = {
    "total_hip_arthroplasty": "tha",
    "revision_total_hip_arthroplasty": "revision_tha",
    "total_knee_arthroplasty": "tka",
    "revision_total_knee_arthroplasty": "revision_tka",
    "femoral_nail": "femoral_shaft_imn",
    "humeral_nailing": "humeral_imn",
    "achilles_repair": "achilles_tendon_repair",
    "labral_repair": "labral_repair_shoulder",
    "dfr": "distal_femur_replacement",
}
DIAG_SYNONYMS = {
    "legg_calve_perthes": "legg_calve_perthes_disease",
    "leggcalveperthes": "legg_calve_perthes_disease",
    "legg_calve_perthes_disese": "legg_calve_perthes_disease",
    "slipped_capital_femoral_epiphysis": "scfe",
    "developmental_dysplasia": "ddh",
    "developmental_dysplasia_of_the_hip": "ddh",
}

def canon_proc(v: str) -> str:
    s = norm_slug(v)
    return PROC_SYNONYMS.get(s, s)

def canon_diag(v: str) -> str:
    s = norm_slug(v)
    return DIAG_SYNONYMS.get(s, s)


def load_cards(idx):
    ids = []
    for page in idx.list(namespace=NS):
        ids.extend(page if isinstance(page, list) else [page])
    cards = {}
    for i in range(0, len(ids), 100):
        res = idx.fetch(ids=ids[i:i+100], namespace=NS)
        vectors = res.vectors if hasattr(res, "vectors") else res["vectors"]
        for vid, rec in vectors.items():
            cards[vid] = (rec.metadata if hasattr(rec, "metadata") else rec["metadata"]) or {}
    return cards


def build_vocab(cards):
    procs, diags = Counter(), Counter()
    for md in cards.values():
        for p in (md.get("procedures") or []): procs[canon_proc(p)] += 1
        for d in (md.get("diagnoses") or []): diags[canon_diag(d)] += 1
    proc_vocab = sorted(procs)
    diag_vocab = [d for d, _ in diags.most_common(180)]  # preferred subset
    return proc_vocab, diag_vocab


# --- LLM extraction --------------------------------------------------------
def extract_batch(client, batch, proc_vocab, diag_vocab):
    sys_prompt = (
        "You tag orthopaedic board-review flashcards with structured metadata by reading the "
        "question and answer and returning, for each card:\n"
        "- diagnoses: the specific named clinical condition(s) the card is ABOUT — a fracture, "
        "injury, tumor, syndrome, disease, or named pathology mentioned in the question or answer. "
        "Tag it even if the card asks about anatomy/classification/treatment OF that condition.\n"
        "- procedures: named SURGICAL/operative procedures the card is about (operations only, "
        "e.g. release, reconstruction, ORIF, arthroplasty, fusion, osteotomy, tendon transfer).\n"
        "Return an EMPTY list when there is genuinely none. Leave BOTH empty for pure anatomy, "
        "physiology, biomechanics, measurements, imaging modalities, nerve/artery courses, or "
        "muscle innervation facts with no named condition. Do NOT guess or force a tag; a wrong "
        "tag is worse than an empty list.\n"
        "Use snake_case slugs. PREFER a slug from the provided preferred lists when one fits; "
        "otherwise create a clean, specific snake_case slug. Fractures end in _fx. Max 3 of each, "
        "most-specific first.\n"
        "Examples:\n"
        "  Q 'Where does interdigital neuritis (Morton neuroma) occur?' -> diagnoses:[morton_neuroma], procedures:[]\n"
        "  Q 'How is hemophilic arthropathy treated?' -> diagnoses:[hemophilic_arthropathy], procedures:[synovectomy]\n"
        "  Q 'Cubital tunnel: simple decompression vs transposition?' -> diagnoses:[cubital_tunnel_syndrome], procedures:[cubital_tunnel_release]\n"
        "  Q 'Describe ossification of the carpal bones.' -> diagnoses:[], procedures:[]\n"
        "  Q 'What is the normal carrying angle of the elbow?' -> diagnoses:[], procedures:[]\n"
        "  Q 'What tumor antigen is alpha-fetoprotein?' -> diagnoses:[], procedures:[]  (not orthopaedic-condition specific)\n"
        "Return STRICT JSON: {\"results\":[{\"id\":str,\"procedures\":[str],\"diagnoses\":[str]}]}"
    )
    user = {
        "preferred_procedures": proc_vocab,
        "preferred_diagnoses": diag_vocab,
        "cards": [
            {"id": vid,
             "specialty": md.get("specialty"), "region": md.get("region"),
             "question": (md.get("question") or "")[:800],
             "answer": (md.get("answer") or "")[:800]}
            for vid, md in batch
        ],
    }
    resp = client.chat.completions.create(
        model=MODEL, temperature=0,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": sys_prompt},
                  {"role": "user", "content": json.dumps(user)}],
    )
    data = json.loads(resp.choices[0].message.content)
    usage = resp.usage
    return data.get("results", []), (usage.prompt_tokens, usage.completion_tokens)


def do_extract(cards, apply):
    from openai import OpenAI
    client = OpenAI()
    proc_vocab, diag_vocab = build_vocab(cards)
    proc_set, diag_set = set(proc_vocab), set(diag_vocab)
    items = list(cards.items())
    # Pre-seed every card with cleaned authored tags (curated floor) so a card the
    # LLM batch happens to omit is never left unprocessed.
    proposals = {}
    for vid, md in items:
        ap = [canon_proc(p) for p in (md.get("procedures") or []) if canon_proc(p)]
        ad = [canon_diag(d) for d in (md.get("diagnoses") or []) if canon_diag(d)]
        proposals[vid] = {"procedures": ap, "diagnoses": ad,
                          "metadata_trust": "authored" if (ap or ad) else "llm_backfill_v1"}
    in_tok = out_tok = 0
    new_procs, new_diags = Counter(), Counter()
    t0 = time.time()
    for i in range(0, len(items), BATCH):
        batch = items[i:i+BATCH]
        try:
            results, (pt, ct) = extract_batch(client, batch, proc_vocab, diag_vocab)
        except Exception as e:
            print(f"  batch {i} error: {e}; retrying once")
            time.sleep(2)
            results, (pt, ct) = extract_batch(client, batch, proc_vocab, diag_vocab)
        in_tok += pt; out_tok += ct
        for r in results:
            vid = r.get("id")
            if vid not in cards: continue
            md = cards[vid]
            procs = []
            for p in (r.get("procedures") or [])[:3]:
                cp = canon_proc(p)
                if cp:
                    procs.append(cp)
                    if cp not in proc_set: new_procs[cp] += 1
            diags = []
            for d in (r.get("diagnoses") or [])[:3]:
                cd = canon_diag(d)
                if cd:
                    diags.append(cd)
                    if cd not in diag_set: new_diags[cd] += 1
            # union with cleaned authored tags (curated prior)
            for p in (md.get("procedures") or []):
                cp = canon_proc(p)
                if cp and cp not in procs: procs.append(cp)
            for d in (md.get("diagnoses") or []):
                cd = canon_diag(d)
                if cd and cd not in diags: diags.append(cd)
            had = bool(md.get("procedures") or md.get("diagnoses"))
            proposals[vid] = {
                "procedures": procs, "diagnoses": diags,
                "metadata_trust": "authored_plus_llm_v1" if had else "llm_backfill_v1",
            }
        if (i // BATCH) % 10 == 0:
            print(f"  {min(i+BATCH,len(items))}/{len(items)}  in={in_tok} out={out_tok}")
    cost = in_tok/1e6*0.15 + out_tok/1e6*0.60
    summary = {
        "cards": len(proposals), "in_tokens": in_tok, "out_tokens": out_tok,
        "est_cost_usd": round(cost, 4), "elapsed_s": round(time.time()-t0),
        "new_procedures_not_in_vocab": new_procs.most_common(),
        "new_diagnoses_not_in_vocab": new_diags.most_common(30),
        "with_procedures": sum(1 for p in proposals.values() if p["procedures"]),
        "with_diagnoses": sum(1 for p in proposals.values() if p["diagnoses"]),
    }
    SIDECAR.write_text(json.dumps({"summary": summary, "proposals": proposals}, indent=1))
    print(json.dumps(summary, indent=1))
    print("sidecar written:", SIDECAR)
    if apply:
        apply_extract(proposals)


def set_meta(idx, vid, meta):
    """index.update with graceful handling of empty lists (Pinecone rejects []).
    For an empty list, drop the key and set <key>_none: True instead."""
    clean = {}
    for k, v in meta.items():
        if isinstance(v, list) and len(v) == 0:
            clean[f"{k}_none"] = True
        else:
            clean[k] = v
    idx.update(id=vid, set_metadata=clean, namespace=NS)


def apply_extract(proposals):
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    idx = pc.Index(os.environ["PINECONE_INDEX"])
    n = 0
    for vid, p in proposals.items():
        set_meta(idx, vid, {
            "procedures": p["procedures"],
            "diagnoses": p["diagnoses"],
            "metadata_trust": p["metadata_trust"],
            "schema_version": SCHEMA_VERSION,
        })
        n += 1
        if n % 200 == 0: print(f"  applied {n}/{len(proposals)}")
    print(f"applied metadata to {n} vectors")


def do_source_collection(cards, apply):
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    idx = pc.Index(os.environ["PINECONE_INDEX"])
    mapped = Counter(); unmapped = Counter()
    n = 0
    for vid, md in cards.items():
        src = str(md.get("source") or "").strip().lower()
        sc = SOURCE_COLLECTION.get(src)
        if not sc:
            unmapped[src] += 1
            continue
        mapped[sc] += 1
        if apply:
            # content_type="qa" is required by rag_retrieval's curated-source filter;
            # every default-namespace vector is a Q/A card.
            idx.update(id=vid, set_metadata={"source_collection": sc, "content_type": "qa"},
                       namespace=NS)
            n += 1
            if n % 200 == 0: print(f"  applied {n}")
    print("source_collection mapped:", mapped.most_common(), "unmapped:", unmapped.most_common())
    if apply: print(f"applied source_collection to {n} vectors")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-collection", action="store_true")
    ap.add_argument("--extract", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--apply-sidecar", action="store_true", help="apply proposals from existing sidecar")
    args = ap.parse_args()

    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    idx = pc.Index(os.environ["PINECONE_INDEX"])
    print("loading default-namespace cards...")
    cards = load_cards(idx)
    print(f"loaded {len(cards)} cards")

    if args.apply_sidecar:
        data = json.loads(SIDECAR.read_text())
        apply_extract(data["proposals"]); return
    if args.source_collection:
        do_source_collection(cards, args.apply)
    if args.extract:
        do_extract(cards, args.apply)
    if not (args.source_collection or args.extract):
        sys.exit("pick --source-collection and/or --extract (add --apply to write)")


if __name__ == "__main__":
    main()
