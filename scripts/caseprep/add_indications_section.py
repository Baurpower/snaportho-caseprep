#!/usr/bin/env python3
"""
Backfill indications: [] into modules.json for procedures missing the section.

Also re-scores coverage_score on each manifest when modules were updated.

Run: python3 scripts/caseprep/add_indications_section.py [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from registry_lib import (  # noqa: E402
    MODULE_SECTIONS,
    list_procedure_folders,
    load_json,
    load_manifest,
    score_modules,
    write_json,
)

POSTOP_PROTOCOL_NOTE = (
    "postop_plan stores Post-op Protocol content (weight-bearing, immobilization, "
    "DVT prophylaxis, activity restrictions, complications to watch, rehab milestones). "
    "It is not a night-before review checklist."
)


def _ordered_modules(modules: Dict[str, Any]) -> Dict[str, Any]:
    """Preserve existing keys; ensure MODULE_SECTIONS order for known keys."""
    ordered: Dict[str, Any] = {}
    for key in MODULE_SECTIONS:
        if key in modules:
            ordered[key] = modules[key]
    for key, value in modules.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def backfill_folder(folder: Path, *, dry_run: bool) -> Tuple[str, bool]:
    slug = folder.name
    modules_path = folder / "modules.json"
    if not modules_path.exists():
        return slug, False

    modules = load_json(modules_path, {}) or {}
    changed = False

    if "indications" not in modules:
        modules["indications"] = []
        changed = True

    if changed:
        modules = _ordered_modules(modules)
        if not dry_run:
            write_json(modules_path, modules, force=True)

    manifest = load_manifest(folder)
    if manifest and changed and not dry_run:
        payload = load_json(folder / "certified_payload.json")
        manifest["coverage_score"] = score_modules(modules, payload)
        write_json(folder / "manifest.json", manifest, force=True)

    return slug, changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing files",
    )
    args = parser.parse_args()

    folders = list_procedure_folders()
    if not folders:
        print("No procedure folders found.")
        return 1

    backfilled: List[str] = []
    for folder in folders:
        slug, changed = backfill_folder(folder, dry_run=args.dry_run)
        if changed:
            backfilled.append(slug)

    print("=== Add Indications Section ===")
    print(f"Procedures scanned: {len(folders)}")
    print(f"Backfilled with indications: []: {len(backfilled)}")
    if backfilled:
        for slug in sorted(backfilled):
            print(f"  - {slug}")
    print(f"\npostop_plan key unchanged; label/docs: {POSTOP_PROTOCOL_NOTE}")
    if args.dry_run:
        print("\nDry run — no files written.")
    else:
        print("\nDone. Run score_registry_coverage.py if you need a full re-score pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())