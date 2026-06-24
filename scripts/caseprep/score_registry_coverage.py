#!/usr/bin/env python3
"""
Score procedure coverage from modules.json / certified_payload.json.

Run: python3 scripts/caseprep/score_registry_coverage.py [--check-only]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from registry_lib import (  # noqa: E402
    COVERAGE_WEIGHTS,
    list_procedure_folders,
    load_json,
    load_manifest,
    score_modules,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Print scores without writing manifest.json",
    )
    args = parser.parse_args()

    folders = list_procedure_folders()
    if not folders:
        print("No procedure folders found.")
        return 1

    rows: List[str] = []
    low_certified: List[str] = []

    for folder in folders:
        manifest = load_manifest(folder)
        if not manifest:
            continue
        slug = manifest.get("slug", folder.name)
        modules = load_json(folder / "modules.json", {}) or {}
        payload = load_json(folder / "certified_payload.json")
        score = score_modules(modules, payload)
        rows.append(f"{slug}: {score}")
        if manifest.get("content_status") == "certified" and score < 85:
            low_certified.append(f"{slug} ({score})")
        if not args.check_only:
            manifest["coverage_score"] = score
            write_json(folder / "manifest.json", manifest, force=True)

    print("=== Coverage Scores ===")
    for line in sorted(rows):
        print(line)
    print(f"\nTotal scored: {len(rows)}")
    if low_certified:
        print(f"Certified below 85: {', '.join(low_certified)}")
    else:
        print("No certified procedures below 85.")
    print(f"\nWeights: {COVERAGE_WEIGHTS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())