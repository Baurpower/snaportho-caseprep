#!/usr/bin/env python3
"""
Build registry indexes from data/caseprep/procedures/.

Run: python3 scripts/caseprep/build_registry_index.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from registry_lib import (  # noqa: E402
    utc_now_iso,
    ALIAS_INDEX_PATH,
    CERTIFIED_EXPORT_PATH,
    REGISTRY_INDEX_PATH,
    REGISTRY_ROOT,
    list_procedure_folders,
    load_json,
    load_manifest,
    normalize_alias,
)


def main() -> int:
    folders = list_procedure_folders()
    if not folders:
        print(f"No folders under {REGISTRY_ROOT}")
        return 1

    by_content: Counter = Counter()
    by_review: Counter = Counter()
    procedures_meta: List[Dict[str, Any]] = []
    alias_map: Dict[str, str] = {}
    collisions: List[Dict[str, Any]] = []
    export_rows: List[Dict[str, Any]] = []

    for folder in folders:
        manifest = load_manifest(folder)
        if not manifest:
            print(f"WARN: missing manifest in {folder.name}")
            continue
        slug = manifest.get("slug", folder.name)
        by_content[manifest.get("content_status", "unknown")] += 1
        by_review[manifest.get("review_status", "unknown")] += 1
        procedures_meta.append(
            {
                "slug": slug,
                "display_name": manifest.get("display_name"),
                "specialty": manifest.get("specialty"),
                "body_region": manifest.get("body_region"),
                "content_status": manifest.get("content_status"),
                "review_status": manifest.get("review_status"),
                "coverage_score": manifest.get("coverage_score"),
                "runtime_enabled": manifest.get("runtime_enabled"),
                "deprecated": manifest.get("deprecated"),
            }
        )

        aliases_obj = load_json(folder / "aliases.json", {}) or {}
        alias_candidates = [manifest.get("display_name", "")] + list(
            aliases_obj.get("aliases") or []
        )
        alias_candidates.append(slug.replace("_", " "))
        for raw in alias_candidates:
            norm = normalize_alias(raw)
            if not norm:
                continue
            if norm in alias_map and alias_map[norm] != slug:
                collisions.append(
                    {"alias": norm, "existing": alias_map[norm], "collision": slug}
                )
            else:
                alias_map[norm] = slug

        payload_path = folder / "certified_payload.json"
        if (
            manifest.get("runtime_enabled")
            and manifest.get("content_status") == "certified"
            and manifest.get("review_status") == "certified"
            and payload_path.exists()
        ):
            payload = load_json(payload_path)
            if payload:
                export_rows.append(payload)

    registry_index = {
        "generated_at": utc_now_iso(),
        "total_procedures": len(procedures_meta),
        "counts_by_content_status": dict(by_content),
        "counts_by_review_status": dict(by_review),
        "procedures": procedures_meta,
        "alias_collisions": collisions,
    }

    alias_index = {
        "generated_at": registry_index["generated_at"],
        "alias_to_slug": alias_map,
        "collision_count": len(collisions),
        "collisions": collisions,
    }

    REGISTRY_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRY_INDEX_PATH.open("w", encoding="utf-8") as f:
        json.dump(registry_index, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with ALIAS_INDEX_PATH.open("w", encoding="utf-8") as f:
        json.dump(alias_index, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with CERTIFIED_EXPORT_PATH.open("w", encoding="utf-8") as f:
        for row in export_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("=== Registry Index Built ===")
    print(f"registry_index.json: {REGISTRY_INDEX_PATH}")
    print(f"alias_index.json: {ALIAS_INDEX_PATH} ({len(alias_map)} aliases)")
    print(f"certified_payloads_export.jsonl: {len(export_rows)} rows")
    print(f"content_status counts: {dict(by_content)}")
    if collisions:
        print(f"WARN: {len(collisions)} alias collisions (see registry_index.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())