#!/usr/bin/env python3
"""Build the `rock-v1` Pinecone namespace from the promoted ROCK corpus.

Reads the corpus in the web repo (`snaportho-web/data/rock-corpus/`), filters to
canonical chapters + teaching pages, chunks, embeds with text-embedding-3-small,
and upserts into the existing `ankiv3` index under namespace `rock-v1`.

Schema: snaportho-web/docs/education/rock-v1-schema.md

Usage:
    python scripts/build_rock_v1_index.py --dry-run     # chunk + report, NO embed/upsert
    python scripts/build_rock_v1_index.py --apply       # embed + upsert into rock-v1

Env (from .env): PINECONE_API_KEY, PINECONE_INDEX, OPENAI_API_KEY
Optional: ROCK_PINECONE_NAMESPACE (default "rock-v1")
          ROCK_CORPUS_DIR (default ../snaportho-web/data/rock-corpus)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---- config ---------------------------------------------------------------
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536
NAMESPACE = os.getenv("ROCK_PINECONE_NAMESPACE", "rock-v1")
SCHEMA_VERSION = "rock-v1"
SOURCE_COLLECTION = "rock"

# chunking (char-based; ~4 chars/token → ~450 tok target, ~60 tok overlap)
CHUNK_CHARS = 1800
OVERLAP_CHARS = 240
MIN_CHUNK_CHARS = 200

EMBED_BATCH = 128        # texts per OpenAI embedding call
UPSERT_BATCH = 100       # vectors per Pinecone upsert

DEFAULT_CORPUS = Path(__file__).resolve().parents[2] / "snaportho-web" / "data" / "rock-corpus"


# ---- chunking -------------------------------------------------------------
def chunk_chapter(chapter: dict) -> list[dict]:
    """Walk teaching pages in order, emit char-windowed chunks that never cross
    a chapter boundary. Returns list of {chunk_index, text, page_start, page_end}."""
    # ordered (page_no, text) for teaching pages only
    pages = [
        (p.get("pdf_page"), (p.get("text") or "").strip())
        for p in chapter.get("pages", [])
        if not p.get("reference") and (p.get("text") or "").strip()
    ]
    if not pages:
        return []

    # build a flat char stream with page offsets so we can attribute page spans
    segments: list[tuple[int, str]] = []  # (page_no, text)
    for page_no, text in pages:
        segments.append((page_no, text))

    full = "\n".join(t for _, t in segments)
    # precompute char -> page map via cumulative lengths
    bounds: list[tuple[int, int, int]] = []  # (start, end, page_no)
    cursor = 0
    for page_no, text in segments:
        start = cursor
        cursor += len(text)
        bounds.append((start, cursor, page_no))
        cursor += 1  # for the "\n" join

    def page_at(char_idx: int) -> int:
        for start, end, page_no in bounds:
            if start <= char_idx < end:
                return page_no
        return bounds[-1][2]

    chunks: list[dict] = []
    idx = 0
    pos = 0
    n = len(full)
    step = CHUNK_CHARS - OVERLAP_CHARS
    while pos < n:
        end = min(pos + CHUNK_CHARS, n)
        # extend to next whitespace to avoid mid-word cuts
        if end < n:
            nxt = full.find(" ", end)
            if 0 <= nxt <= end + 80:
                end = nxt
        text = full[pos:end].strip()
        if len(text) >= MIN_CHUNK_CHARS:
            chunks.append(
                {
                    "chunk_index": idx,
                    "text": text,
                    "page_start": page_at(pos),
                    "page_end": page_at(max(pos, end - 1)),
                }
            )
            idx += 1
        if end >= n:
            break
        pos += step
    return chunks


# ---- corpus load ----------------------------------------------------------
def load_corpus(corpus_dir: Path):
    catalog = json.loads((corpus_dir / "catalog.json").read_text())
    by_id = {c["id"]: c for c in catalog["chapters"]}
    records = []
    skipped_noncanonical = 0
    skipped_nofile = 0
    for chap in catalog["chapters"]:
        if not chap.get("isCanonical", True):
            skipped_noncanonical += 1
            continue
        cf = corpus_dir / "chapters" / f"{chap['id']}.json"
        if not cf.exists():
            skipped_nofile += 1
            continue
        chapter = json.loads(cf.read_text())
        chunks = chunk_chapter(chapter)
        for ch in chunks:
            records.append(
                {
                    "id": f"{chap['id']}#{ch['chunk_index']:04d}",
                    "embed_text": f"{chap['title']}\n\n{ch['text']}",
                    "metadata": {
                        "schema_version": SCHEMA_VERSION,
                        "source_collection": SOURCE_COLLECTION,
                        "chapter_id": chap["id"],
                        "canonical_id": chap.get("canonicalId", chap["id"]),
                        "title": chap["title"],
                        "url": chap["url"],
                        "chunk_index": ch["chunk_index"],
                        "page_start": ch["page_start"],
                        "page_end": ch["page_end"],
                        "char_len": len(ch["text"]),
                        "text": ch["text"],
                    },
                }
            )
    return records, {
        "skipped_noncanonical": skipped_noncanonical,
        "skipped_nofile": skipped_nofile,
    }


# ---- embed + upsert -------------------------------------------------------
def embed_and_upsert(records, report):
    from openai import OpenAI
    from pinecone import Pinecone

    oai = OpenAI()
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index(os.environ["PINECONE_INDEX"])

    buffer = []
    upserted = 0
    for i in range(0, len(records), EMBED_BATCH):
        batch = records[i : i + EMBED_BATCH]
        resp = oai.embeddings.create(model=EMBED_MODEL, input=[r["embed_text"] for r in batch])
        for r, d in zip(batch, resp.data):
            buffer.append({"id": r["id"], "values": d.embedding, "metadata": r["metadata"]})
        while len(buffer) >= UPSERT_BATCH:
            index.upsert(vectors=buffer[:UPSERT_BATCH], namespace=NAMESPACE)
            upserted += len(buffer[:UPSERT_BATCH])
            buffer = buffer[UPSERT_BATCH:]
        print(f"  embedded {min(i + EMBED_BATCH, len(records))}/{len(records)}  upserted {upserted}")
    if buffer:
        index.upsert(vectors=buffer, namespace=NAMESPACE)
        upserted += len(buffer)
    report["upserted"] = upserted
    print(f"DONE: upserted {upserted} vectors into namespace '{NAMESPACE}'")


# ---- main -----------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true", help="chunk + report, no embed/upsert")
    g.add_argument("--apply", action="store_true", help="embed + upsert into rock-v1")
    ap.add_argument("--corpus", default=os.getenv("ROCK_CORPUS_DIR", str(DEFAULT_CORPUS)))
    args = ap.parse_args()

    corpus_dir = Path(args.corpus)
    if not (corpus_dir / "catalog.json").exists():
        sys.exit(f"corpus not found at {corpus_dir}")

    manifest = json.loads((corpus_dir / "manifest.json").read_text())
    print(f"corpus: {corpus_dir}  checksum={manifest.get('corpusChecksum')}")

    records, skips = load_corpus(corpus_dir)
    chapters_covered = len({r["metadata"]["chapter_id"] for r in records})
    total_chars = sum(r["metadata"]["char_len"] for r in records)
    est_tokens = round(sum(len(r["embed_text"]) for r in records) / 4)
    est_cost = est_tokens / 1_000_000 * 0.02  # text-embedding-3-small: $0.02/1M

    report = {
        "builtAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "apply" if args.apply else "dry-run",
        "namespace": NAMESPACE,
        "index": os.getenv("PINECONE_INDEX"),
        "embedModel": EMBED_MODEL,
        "corpusChecksum": manifest.get("corpusChecksum"),
        "chunks": len(records),
        "chaptersCovered": chapters_covered,
        "totalTeachingChars": total_chars,
        "estTokens": est_tokens,
        "estEmbedCostUSD": round(est_cost, 4),
        **skips,
    }
    print(json.dumps(report, indent=2))

    out = Path(__file__).resolve().parent / "rock_v1_build_report.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"report written: {out}")

    if args.apply:
        confirm = input(f"Upsert {len(records)} vectors into '{NAMESPACE}'? [y/N] ")
        if confirm.strip().lower() != "y":
            sys.exit("aborted")
        embed_and_upsert(records, report)
        out.write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
