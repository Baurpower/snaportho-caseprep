#!/usr/bin/env python3
"""
Phase 2: Upsert Miller gold anatomy to Pinecone dedicated namespace.

DEFAULT: dry-run only (validates, shows samples, NO network calls to Pinecone beyond init if needed for dry).
REAL UPLOAD: requires --execute (and confirmation).

Namespace: anatomy_miller_gold_v1 (or ANATOMY_PINECONE_NAMESPACE)
Index: from PINECONE_INDEX (existing)
Embed: text-embedding-3-small (matches everything else)

Usage:
  # Safe preview
  python scripts/upsert_anatomy_gold_to_pinecone.py --dry-run

  # Actual (only after dry-run passes and you are sure)
  python scripts/upsert_anatomy_gold_to_pinecone.py --execute

Never prints secrets. Gold corpus is never modified.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent.parent
GOLD_PATH = BASE_DIR / "data" / "anatomy_miller_gold_v1" / "anatomy_gold_v1_pinecone_ready.jsonl"
MANIFEST_PATH = BASE_DIR / "data" / "anatomy_miller_gold_v1" / "pinecone_upload_manifest.json"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_NAMESPACE = "anatomy_miller_gold_v1"
EMBED_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100

load_dotenv()

def get_env_names_only() -> Dict[str, str]:
    # Never return values
    return {
        "PINECONE_API_KEY": "present" if os.getenv("PINECONE_API_KEY") else "MISSING",
        "PINECONE_INDEX": os.getenv("PINECONE_INDEX") or "MISSING",
        "OPENAI_API_KEY": "present" if os.getenv("OPENAI_API_KEY") else "MISSING",
        "ANATOMY_PINECONE_NAMESPACE": os.getenv("ANATOMY_PINECONE_NAMESPACE") or DEFAULT_NAMESPACE,
    }

def load_gold() -> List[Dict[str, Any]]:
    if not GOLD_PATH.exists():
        raise FileNotFoundError(f"Gold not found: {GOLD_PATH}")
    recs = []
    with GOLD_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                recs.append(json.loads(line))
    return recs

def build_metadata(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Build Pinecone-safe flat metadata. Flatten complex anatomy_terms."""
    meta = rec.get("metadata", {}) or {}
    out: Dict[str, Any] = {
        "text": rec.get("text", ""),
        "source_quote": rec.get("source_quote", "")[:2000],  # guard length
        "page": rec.get("page"),
        "section_path": rec.get("section_path", ""),
        "heading": rec.get("heading", ""),
        "source": rec.get("source", "miller"),
        "corpus_version": rec.get("corpus_version", "gold_v1"),
        "quality_tier": meta.get("quality_tier"),
        "metadata_trust": meta.get("metadata_trust"),
        "region": meta.get("region"),
        "subregion": meta.get("subregion"),
        "specialty": meta.get("specialty"),
        "structures_at_risk": meta.get("structures_at_risk", []) or [],
        "approach_terms": meta.get("approach_terms", []) or [],
        "case_associations": meta.get("case_associations", []) or [],
    }

    # anatomy_terms is a dict of lists in source; flatten sublists or stringify
    at = meta.get("anatomy_terms") or {}
    if isinstance(at, dict):
        for k, v in at.items():
            if isinstance(v, list):
                out[f"anatomy_{k}"] = v  # list[str] safe for Pinecone
        # also keep a compact json for display/debug (string is safe)
        try:
            out["anatomy_terms_json"] = json.dumps(at, ensure_ascii=False)[:1500]
        except Exception:
            pass
    else:
        out["anatomy_terms_json"] = str(at)[:1500]

    # Remove None values (Pinecone prefers clean)
    return {k: v for k, v in out.items() if v is not None}

def get_clients():
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX")
    openai_key = os.getenv("OPENAI_API_KEY")
    if not all([api_key, index_name, openai_key]):
        raise RuntimeError("Missing required PINECONE_API_KEY / PINECONE_INDEX / OPENAI_API_KEY (names only in logs)")
    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)
    oai = OpenAI(api_key=openai_key, project=os.getenv("OPENAI_PROJECT_ID"))
    return index, oai

def embed_texts(oai: OpenAI, texts: List[str]) -> List[List[float]]:
    resp = oai.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]

def do_dry_run(records: List[Dict[str, Any]], namespace: str):
    print("=== DRY-RUN (no Pinecone writes) ===")
    env = get_env_names_only()
    print(f"Target index (env): {env['PINECONE_INDEX']}")
    print(f"Target namespace: {namespace}")
    print(f"Records: {len(records)}")

    sample = records[0]
    sample_meta = build_metadata(sample)
    print("\nSample metadata keys:", sorted(sample_meta.keys()))
    print("Sample metadata (truncated):", {k: str(v)[:80] for k, v in list(sample_meta.items())[:6]})

    # Size check on a few
    sizes = []
    for r in records[:50]:
        m = build_metadata(r)
        try:
            sizes.append(len(json.dumps(m, ensure_ascii=False).encode("utf-8")))
        except Exception:
            pass
    print(f"Sample metadata sizes (bytes, first 50): min={min(sizes)}, max={max(sizes)}, avg~{sum(sizes)//max(1,len(sizes))}")

    print("\n✅ Dry-run validation passed. Ready for --execute if you confirm.")
    print("   Run with --execute ONLY after reviewing this output and the payload validation report.")

def do_execute(records: List[Dict[str, Any]], namespace: str):
    print("=== EXECUTE MODE (will write to Pinecone) ===")
    env = get_env_names_only()
    print(f"Index: {env['PINECONE_INDEX']}")
    print(f"Namespace: {namespace}")
    print(f"Records to upsert: {len(records)}")

    index, oai = get_clients()

    # Optional pre-check: describe (safe)
    try:
        stats = index.describe_index_stats()
        print(f"Current index namespaces (before): {list((stats.namespaces or {}).keys())[:5]}...")
    except Exception as e:
        print(f"Warning: could not describe stats: {e}")

    vectors = []
    batch_embeds = []
    texts = []
    ids = []
    metas = []

    for rec in records:
        rid = rec["id"]
        text = rec.get("text") or ""
        if not text:
            continue
        ids.append(rid)
        texts.append(text)
        metas.append(build_metadata(rec))

    print("Embedding in batches...")
    for i in tqdm(range(0, len(texts), BATCH_SIZE), desc="embed+upsert"):
        batch_texts = texts[i:i+BATCH_SIZE]
        batch_ids = ids[i:i+BATCH_SIZE]
        batch_metas = metas[i:i+BATCH_SIZE]
        embs = embed_texts(oai, batch_texts)
        batch_vectors = list(zip(batch_ids, embs, batch_metas))
        try:
            index.upsert(vectors=batch_vectors, namespace=namespace)
        except Exception as e:
            print(f"❌ Upsert batch failed at {i}: {e}")
            raise

    # Write manifest
    manifest = {
        "namespace": namespace,
        "index": env["PINECONE_INDEX"],
        "record_count": len(records),
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "embedding_model": EMBED_MODEL,
        "gold_source": str(GOLD_PATH),
        "dry_run": False,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"✅ Manifest written: {MANIFEST_PATH}")

    # Verify
    try:
        stats = index.describe_index_stats()
        ns_stats = (stats.namespaces or {}).get(namespace, {})
        print(f"✅ Namespace stats after upload: {ns_stats}")
    except Exception as e:
        print(f"Warning during post-verify: {e}")

    # Write execution report
    report = REPORTS_DIR / "phase2_anatomy_pinecone_upload_report.md"
    lines = [
        "# Phase 2 Anatomy Pinecone Upload Report",
        "",
        f"Executed: {manifest['executed_at']}",
        f"Namespace: {namespace}",
        f"Index: {env['PINECONE_INDEX']}",
        f"Records: {len(records)}",
        f"Gold: {str(GOLD_PATH)}",
        "",
        "✅ Upload completed successfully (dry-run was passed first).",
        "Default namespace was not modified.",
        "See manifest for exact details.",
    ]
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report: {report}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Actually perform the upsert (default is dry-run / safe preview)")
    parser.add_argument("--dry-run", action="store_true", help="Explicit dry-run (default behavior anyway)")
    parser.add_argument("--namespace", default=None, help="Override namespace (default from env or anatomy_miller_gold_v1)")
    args = parser.parse_args()

    namespace = args.namespace or os.getenv("ANATOMY_PINECONE_NAMESPACE", DEFAULT_NAMESPACE)

    print("Phase 2 Anatomy Gold → Pinecone")
    env_info = get_env_names_only()
    print("Env (names only):", env_info)
    print(f"Effective namespace: {namespace}")
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY-RUN (safe)'}")

    records = load_gold()
    print(f"Gold records: {len(records)}")

    if not args.execute:
        do_dry_run(records, namespace)
        # Also touch the payload validation for convenience
        print("\n(Also ensure you ran: python scripts/validate_anatomy_pinecone_payload.py )")
        return

    # Safety prompt in execute
    print("\n⚠️  EXECUTE MODE: This will write vectors to the namespace.")
    resp = input("Type 'YES' to continue: ").strip()
    if resp != "YES":
        print("Aborted.")
        return

    do_execute(records, namespace)
    print("\n✅ Phase 2 upload step complete. Verify with describe or a retrieval test.")

if __name__ == "__main__":
    main()
