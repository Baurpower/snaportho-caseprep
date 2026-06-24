#!/usr/bin/env python3
"""
Phase 1: Build local anatomy gold index using production embedding model.

- Loads the copied gold corpus (pinecone_ready preferred).
- Embeds "text" (or fallback) using text-embedding-3-small.
- Saves numpy + json artifacts for fast local cosine retrieval.
- No Pinecone involvement.

Usage (after setting OPENAI_API_KEY):
  python scripts/build_local_anatomy_gold_index.py

Or with explicit path:
  python scripts/build_local_anatomy_gold_index.py --gold data/anatomy_miller_gold_v1/anatomy_gold_v1_pinecone_ready.jsonl

Outputs under:
  data/anatomy_miller_gold_v1/local_index/
    embeddings.npy
    ids.json
    metas.json
    manifest.json
"""

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

# ── Paths (relative to workspace root) ─────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_GOLD = BASE_DIR / "data" / "anatomy_miller_gold_v1" / "anatomy_gold_v1_pinecone_ready.jsonl"
DEFAULT_INDEX_DIR = BASE_DIR / "data" / "anatomy_miller_gold_v1" / "local_index"

EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536
BATCH_SIZE = 100  # safe for OpenAI

def load_gold_records(gold_path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if not gold_path.exists():
        raise FileNotFoundError(f"Gold corpus not found: {gold_path}")
    with gold_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            records.append(rec)
    return records

def get_text_field(rec: Dict[str, Any]) -> str:
    """Prefer pinecone_ready 'text'; fallback to canonical_fact or source_quote."""
    if "text" in rec and rec["text"]:
        return rec["text"]
    if "canonical_fact" in rec and rec["canonical_fact"]:
        return rec["canonical_fact"]
    if "source_quote" in rec and rec["source_quote"]:
        return rec["source_quote"]
    # last resort
    return str(rec.get("id", ""))

def compute_source_hash(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]

def embed_batch(client: OpenAI, texts: List[str]) -> List[List[float]]:
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]

def main():
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD,
                        help="Path to gold JSONL (pinecone_ready preferred)")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_INDEX_DIR,
                        help="Directory for local index artifacts")
    parser.add_argument("--dry-run", action="store_true",
                        help="Load and count only; do not call OpenAI")
    args = parser.parse_args()

    gold_path = args.gold.resolve()
    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"📥 Loading gold corpus: {gold_path}")
    records = load_gold_records(gold_path)
    print(f"   → {len(records)} records")

    if args.dry_run:
        print("✅ Dry run complete (no embeddings generated).")
        return

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set in environment or .env")
        print("   Set it (e.g. export OPENAI_API_KEY=sk-...) and re-run.")
        return

    project = os.getenv("OPENAI_PROJECT_ID")
    client = OpenAI(api_key=api_key, project=project)

    print(f"🧠 Embedding with {EMBED_MODEL} (dim={EMBED_DIM}) in batches of {BATCH_SIZE}...")

    ids: List[str] = []
    embeddings: List[List[float]] = []
    metas: List[Dict[str, Any]] = []

    texts_for_embed: List[str] = []
    for rec in records:
        text = get_text_field(rec).strip()
        if not text:
            continue
        texts_for_embed.append(text)
        ids.append(rec.get("id", f"unknown-{len(ids)}"))

        meta = {
            "text": text,
            "source_quote": rec.get("source_quote", ""),
            "page": rec.get("page"),
            "heading": rec.get("heading", ""),
            "section_path": rec.get("section_path", ""),
            "source": rec.get("source", "miller"),
            "corpus_version": rec.get("corpus_version", "gold_v1"),
            "region": rec.get("metadata", {}).get("region"),
            "subregion": rec.get("metadata", {}).get("subregion"),
            "quality_tier": rec.get("metadata", {}).get("quality_tier"),
            "metadata_trust": rec.get("metadata", {}).get("metadata_trust"),
            "specialty": rec.get("metadata", {}).get("specialty"),
            "structures_at_risk": rec.get("metadata", {}).get("structures_at_risk", []),
            "approach_terms": rec.get("metadata", {}).get("approach_terms", []),
        }
        metas.append(meta)

    # Embed in batches with progress
    all_embs: List[List[float]] = []
    for i in tqdm(range(0, len(texts_for_embed), BATCH_SIZE), desc="Embedding"):
        batch = texts_for_embed[i : i + BATCH_SIZE]
        try:
            embs = embed_batch(client, batch)
            all_embs.extend(embs)
        except Exception as e:
            print(f"❌ Embedding batch failed at {i}: {e}")
            print("   Aborting build. Check API key/quota.")
            return

    embeddings = all_embs
    assert len(embeddings) == len(ids) == len(metas), "Mismatch after embedding"

    # Save artifacts
    np.save(out_dir / "embeddings.npy", np.array(embeddings, dtype=np.float32))
    (out_dir / "ids.json").write_text(json.dumps(ids, indent=2), encoding="utf-8")
    (out_dir / "metas.json").write_text(json.dumps(metas, indent=2), encoding="utf-8")

    manifest = {
        "corpus_path": str(gold_path),
        "record_count": len(records),
        "indexed_count": len(embeddings),
        "embedding_model": EMBED_MODEL,
        "embedding_dim": EMBED_DIM,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_hash": compute_source_hash(gold_path),
        "text_field_used": "text" if "text" in records[0] else "fallback",
        "index_files": ["embeddings.npy", "ids.json", "metas.json"],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"✅ Local index built successfully.")
    print(f"   Output: {out_dir}")
    print(f"   Records: {len(embeddings)}")
    print(f"   Manifest: {manifest}")

if __name__ == "__main__":
    main()
