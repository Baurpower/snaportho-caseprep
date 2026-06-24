#!/usr/bin/env python3
"""
Migrate flat data/anatomy certified payloads into per-procedure registry folders.

Run: python3 scripts/caseprep/migrate_flat_payloads_to_registry.py [--force]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from registry_lib import (  # noqa: E402
    empty_modules,
    ALIASES_PATH,
    CERTIFICATION_PATH,
    CERTIFIED_JSONL_PATH,
    PROCEDURES_PATH,
    ROUTER_PATH,
    REGISTRY_ROOT,
    build_manifest,
    modules_from_payload,
    procedure_dir,
    read_jsonl,
    review_notes_template,
    sources_from_payload_and_proc,
    write_json,
    write_jsonl,
    write_text,
)


def load_router_sets() -> tuple:
    router = {}
    if ROUTER_PATH.exists():
        with ROUTER_PATH.open("r", encoding="utf-8") as f:
            router = json.load(f)
    certified = set(router.get("certified_procedure_ids") or [])
    not_cert = set(router.get("not_certified_procedure_ids") or [])
    return certified, not_cert


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()
    force = args.force

    aliases_by_id: Dict[str, Dict[str, Any]] = {
        r["procedure_id"]: r for r in read_jsonl(ALIASES_PATH)
    }
    proc_by_id: Dict[str, Dict[str, Any]] = {
        r["procedure_id"]: r for r in read_jsonl(PROCEDURES_PATH)
    }
    cert_meta: Dict[str, Dict[str, Any]] = {
        r["procedure_id"]: r for r in read_jsonl(CERTIFICATION_PATH)
    }
    payloads: Dict[str, Dict[str, Any]] = {}
    for row in read_jsonl(CERTIFIED_JSONL_PATH):
        pid = row.get("procedure_id")
        if pid:
            payloads[pid] = row

    router_cert, router_not = load_router_sets()
    all_slugs = sorted(set(aliases_by_id) | router_cert | router_not | set(payloads))

    counts = {
        "folders_created": 0,
        "certified_written": 0,
        "partial_written": 0,
        "missing_written": 0,
        "skipped": 0,
        "written": 0,
    }

    for slug in all_slugs:
        folder = procedure_dir(slug)
        folder.mkdir(parents=True, exist_ok=True)
        counts["folders_created"] += 1

        alias_row = aliases_by_id.get(slug, {})
        proc_row = proc_by_id.get(slug)
        display_name = (
            alias_row.get("display_name")
            or (proc_row or {}).get("procedure_name")
            or slug.replace("_", " ").title()
        )
        specialty = alias_row.get("specialty") or "orthopaedics"
        body_region = alias_row.get("body_region") or "unknown"

        is_certified = slug in payloads or slug in router_cert
        partial = (
            not is_certified
            and proc_row is not None
            and int(proc_row.get("case_readiness_score") or 0) >= 3
        )

        cert_record = cert_meta.get(slug, {})
        certified_at = cert_record.get("last_validated")
        payload = payloads.get(slug)

        manifest = build_manifest(
            slug=slug,
            display_name=display_name,
            specialty=specialty,
            body_region=body_region,
            is_certified=is_certified and payload is not None,
            certified_at=certified_at,
            payload=payload,
            proc_row=proc_row,
            partial=partial,
        )

        aliases_obj = {
            "slug": slug,
            "display_name": display_name,
            "aliases": alias_row.get("aliases") or [display_name.lower()],
        }

        actions: List[str] = []
        actions.append(write_json(folder / "manifest.json", manifest, force=force))
        actions.append(write_json(folder / "aliases.json", aliases_obj, force=force))

        if payload:
            actions.append(
                write_json(folder / "certified_payload.json", payload, force=force)
            )
            modules = modules_from_payload(payload)
            actions.append(write_json(folder / "modules.json", modules, force=force))
            sources = sources_from_payload_and_proc(payload, proc_row)
            actions.append(
                write_jsonl(folder / "sources.jsonl", sources, force=force)
            )
            counts["certified_written"] += 1
        else:
            actions.append(write_json(folder / "modules.json", empty_modules(), force=force))
            actions.append(write_jsonl(folder / "sources.jsonl", [], force=force))
            if partial:
                counts["partial_written"] += 1
            else:
                counts["missing_written"] += 1

        notes = review_notes_template(
            slug, display_name, certified=bool(payload), partial=partial
        )
        actions.append(write_text(folder / "review_notes.md", notes, force=force))

        for a in actions:
            if a == "written":
                counts["written"] += 1
            elif a == "skipped":
                counts["skipped"] += 1

    print("=== Migration Summary ===")
    print(f"Registry root: {REGISTRY_ROOT}")
    print(f"Total procedure folders: {len(all_slugs)}")
    print(f"Certified migrated: {counts['certified_written']}")
    print(f"Partial (non-certified): {counts['partial_written']}")
    print(f"Missing (non-certified): {counts['missing_written']}")
    print(f"Files written: {counts['written']}")
    print(f"Files skipped (already exist): {counts['skipped']}")
    print("Done. Run score_registry_coverage.py then build_registry_index.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())