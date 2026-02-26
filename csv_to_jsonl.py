#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict


def _clean(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() in {"nan", "none", "null"}:
        return ""
    return s


def _row_to_obj(row: Dict[str, Any]) -> Dict[str, Any]:
    question = _clean(row.get("question"))
    answer = _clean(row.get("answer"))
    additional_info = _clean(row.get("additional_info"))

    metadata: Dict[str, str] = {}
    for k, v in row.items():
        if k and k.startswith("metadata."):
            meta_key = k.split("metadata.", 1)[1]
            metadata[meta_key] = _clean(v)

    return {
        "question": question,
        "answer": answer,
        "additional_info": additional_info,
        "metadata": metadata,
    }


def _detect_encoding(csv_path: Path) -> str:
    """
    Practical, stable detection for CSVs coming from Excel/editor workflows.

    Order matters:
    - Handle BOMs explicitly
    - Prefer UTF-8 (strict) if possible
    - Fall back to cp1252 (common Excel export)
    - Finally latin-1 (never errors)
    """
    raw = csv_path.read_bytes()

    # BOM checks (high confidence)
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"   # UTF-8 with BOM
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return "utf-16"      # UTF-16 with BOM (endian determined by BOM)

    # Try UTF-8 strictly
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass

    # Try cp1252 (Windows Excel “smart quotes”, etc.)
    try:
        raw.decode("cp1252")
        return "cp1252"
    except UnicodeDecodeError:
        pass

    # Last resort: latin-1 always works (may preserve bytes 1:1)
    return "latin-1"


def csv_to_jsonl(csv_path: Path, jsonl_path: Path) -> None:
    chosen_enc = _detect_encoding(csv_path)
    print(f"ℹ️ Using encoding: {chosen_enc}", file=sys.stderr)

    with csv_path.open("r", encoding=chosen_enc, newline="") as f_in, \
         jsonl_path.open("w", encoding="utf-8", newline="\n") as f_out:

        reader = csv.DictReader(f_in)

        for row_idx, row in enumerate(reader, start=1):
            obj = _row_to_obj(row)
            f_out.write(json.dumps(obj, ensure_ascii=False) + "\n")

            if not obj["question"] and not obj["answer"]:
                print(f"Warning: row {row_idx} has empty question+answer", file=sys.stderr)

    # Validation pass
    with jsonl_path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            try:
                json.loads(line)
            except json.JSONDecodeError as e:
                raise SystemExit(f"Invalid JSON on line {i}: {e}") from e


def main(argv: list[str]) -> None:
    if len(argv) != 3:
        raise SystemExit("Usage: python3 csv_to_jsonl.py input.csv output.jsonl")

    csv_path = Path(argv[1]).expanduser().resolve()
    jsonl_path = Path(argv[2]).expanduser().resolve()

    if not csv_path.exists():
        raise SystemExit(f"Input CSV not found: {csv_path}")

    csv_to_jsonl(csv_path, jsonl_path)
    print(f"✅ Wrote JSONL: {jsonl_path}")


if __name__ == "__main__":
    main(sys.argv)
