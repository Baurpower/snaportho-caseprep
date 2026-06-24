#!/usr/bin/env python3
"""
Validate CasePrep procedure registry folders.

Run: python3 scripts/caseprep/validate_registry.py [--allow-low-coverage]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from registry_lib import (  # noqa: E402
    ALIAS_INDEX_PATH,
    CONTENT_STATUSES,
    MANIFEST_REQUIRED,
    REVIEW_STATUSES,
    collect_text_blobs,
    cross_region_warnings,
    list_procedure_folders,
    load_json,
    load_manifest,
    normalize_alias,
    placeholder_hits,
    section_has_content,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allow-low-coverage",
        action="store_true",
        help="Do not fail certified procedures with coverage_score < 85",
    )
    args = parser.parse_args()

    folders = list_procedure_folders()
    if not folders:
        print("FAIL: no procedure folders found")
        return 1

    errors: List[str] = []
    warnings: List[str] = []
    alias_owner: Dict[str, str] = {}

    for folder in folders:
        slug = folder.name
        manifest_path = folder / "manifest.json"
        if not manifest_path.exists():
            errors.append(f"{slug}: missing manifest.json")
            continue

        manifest = load_manifest(folder)
        if not manifest:
            errors.append(f"{slug}: invalid manifest.json")
            continue

        mslug = manifest.get("slug")
        if mslug != slug:
            errors.append(f"{slug}: folder name != manifest.slug ({mslug})")

        for field in MANIFEST_REQUIRED:
            if field not in manifest:
                errors.append(f"{slug}: manifest missing field {field}")

        cs = manifest.get("content_status")
        rs = manifest.get("review_status")
        if cs not in CONTENT_STATUSES:
            errors.append(f"{slug}: invalid content_status={cs}")
        if rs not in REVIEW_STATUSES:
            errors.append(f"{slug}: invalid review_status={rs}")

        score = manifest.get("coverage_score")
        if not isinstance(score, (int, float)):
            errors.append(f"{slug}: coverage_score must be numeric")
        elif cs == "certified" and score < 85 and not args.allow_low_coverage:
            errors.append(f"{slug}: certified coverage_score {score} < 85")

        if cs == "certified":
            if not (folder / "certified_payload.json").exists():
                errors.append(f"{slug}: certified missing certified_payload.json")
            if not manifest.get("reviewer"):
                errors.append(f"{slug}: certified missing reviewer")
            if not manifest.get("certified_at"):
                errors.append(f"{slug}: certified missing certified_at")

        if manifest.get("deprecated"):
            if not manifest.get("replacement_slug"):
                errors.append(f"{slug}: deprecated missing replacement_slug")

        if manifest.get("runtime_enabled") and cs == "certified":
            payload = load_json(folder / "certified_payload.json")
            if not payload:
                errors.append(f"{slug}: runtime_enabled certified has invalid payload JSON")
            elif not payload.get("procedure_id"):
                errors.append(f"{slug}: payload missing procedure_id")

        aliases_obj = load_json(folder / "aliases.json", {}) or {}
        for raw in [manifest.get("display_name", "")] + list(
            aliases_obj.get("aliases") or []
        ):
            norm = normalize_alias(str(raw))
            if not norm:
                continue
            if norm in alias_owner and alias_owner[norm] != slug:
                errors.append(
                    f"alias collision: '{norm}' -> {alias_owner[norm]} and {slug}"
                )
            else:
                alias_owner[norm] = slug

        blob = collect_text_blobs(folder)
        hits = placeholder_hits(blob)
        if hits and cs == "certified":
            errors.append(f"{slug}: placeholder text in certified content: {hits}")

        region_warns = cross_region_warnings(manifest.get("body_region", ""), blob)
        if region_warns and cs == "certified":
            for w in region_warns:
                warnings.append(f"{slug}: {w}")

        modules = load_json(folder / "modules.json", {}) or {}
        if cs == "certified" and not section_has_content(modules.get("indications")):
            warnings.append(
                f"{slug}: missing indications section (transitional warning — "
                "required for new certification, not blocking during migration)"
            )

        draft_path = folder / "certified_payload.draft.json"
        if (
            draft_path.exists()
            and (folder / "certified_payload.json").exists()
            and manifest.get("runtime_enabled")
        ):
            warnings.append(
                f"{slug}: unpromoted draft exists alongside live certified payload — "
                "review or delete certified_payload.draft.json"
            )

    # Cross-check alias_index if present
    if ALIAS_INDEX_PATH.exists():
        idx = load_json(ALIAS_INDEX_PATH, {}) or {}
        for col in idx.get("collisions") or []:
            errors.append(
                f"alias_index collision: {col.get('alias')} -> {col.get('existing')} vs {col.get('collision')}"
            )

    print("=== Registry Validation ===")
    print(f"Procedures checked: {len(folders)}")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    for e in errors:
        print(f"ERROR: {e}")
    for w in warnings:
        print(f"WARN: {w}")

    if errors:
        print("\nVALIDATION FAILED")
        return 1
    print("\nALL VALIDATION CHECKS PASSED")
    if warnings:
        print(f"({len(warnings)} warnings — review recommended)")
    return 0


if __name__ == "__main__":
    sys.exit(main())