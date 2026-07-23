#!/usr/bin/env python3
"""Backfill filterable Pocket Pimp metadata without touching vectors.

Dry-run is the default. Use --apply only after reviewing the summary and a
small --limit cohort. IDs match the existing pp-<sha1> upload convention.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "normalized_pp.jsonl"
CORPUS_VERSION = "pocket_pimped_v1"


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", clean(value).lower()).strip("_")


def values(metadata: Dict[str, Any], singular: str, plural: str) -> List[str]:
    raw = metadata.get(plural)
    if raw is None:
        raw = metadata.get(singular)
    if raw in (None, "", []):
        raw = metadata.get(f"{singular}_raw")
    candidates = raw if isinstance(raw, list) else [raw]
    return list(dict.fromkeys(slug(value) for value in candidates if slug(value)))


def stable_id(question: str, answer: str) -> str:
    digest = hashlib.sha1(f"{question}||{answer}".encode("utf-8")).hexdigest()[:16]
    return f"pp-{digest}"


def metadata_patch(record: Dict[str, Any]) -> Dict[str, Any]:
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    question = clean(record.get("question"))
    answer = clean(record.get("answer"))
    additional_info = clean(record.get("additional_info"))
    return {
        "source": "PocketPimped",
        "source_collection": "pocket_pimped",
        "content_type": "qa",
        "corpus_version": CORPUS_VERSION,
        "question": question,
        "answer": answer,
        "additional_info": additional_info,
        "specialties": values(metadata, "specialty", "specialties"),
        "region": slug(metadata.get("region")),
        "subregion": slug(metadata.get("subregion") or metadata.get("subregion_raw")),
        "diagnoses": values(metadata, "diagnosis", "diagnoses"),
        "procedures": values(metadata, "procedure", "procedures"),
        "concepts": values(metadata, "concept", "concepts"),
    }


def load_updates(path: Path, limit: int | None = None) -> List[Dict[str, Any]]:
    updates: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            patch = metadata_patch(record)
            if not patch["question"] or not patch["answer"]:
                continue
            updates.append(
                {
                    "id": stable_id(patch["question"], patch["answer"]),
                    "metadata": patch,
                    "line_number": line_number,
                }
            )
            if limit is not None and len(updates) >= limit:
                break
    return updates


def summarize(updates: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(updates)
    return {
        "records": len(rows),
        "with_procedure": sum(bool(row["metadata"]["procedures"]) for row in rows),
        "with_diagnosis": sum(bool(row["metadata"]["diagnoses"]) for row in rows),
        "with_region": sum(bool(row["metadata"]["region"]) for row in rows),
        "with_subregion": sum(bool(row["metadata"]["subregion"]) for row in rows),
        "corpus_version": CORPUS_VERSION,
    }


def apply_updates(updates: List[Dict[str, Any]]) -> None:
    from dotenv import load_dotenv
    from pinecone import Pinecone

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX")
    if not api_key or not index_name:
        raise RuntimeError("PINECONE_API_KEY and PINECONE_INDEX are required for --apply")
    index = Pinecone(api_key=api_key).Index(index_name)
    for row in updates:
        index.update(id=row["id"], set_metadata=row["metadata"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--preview", type=int, default=3)
    args = parser.parse_args()

    updates = load_updates(args.input, limit=args.limit)
    output = {
        "mode": "apply" if args.apply else "dry_run",
        "input": str(args.input),
        "summary": summarize(updates),
        "preview": updates[: max(0, args.preview)],
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    if args.apply:
        apply_updates(updates)
        print(json.dumps({"applied": len(updates), "index": os.getenv("PINECONE_INDEX")}))


if __name__ == "__main__":
    main()
