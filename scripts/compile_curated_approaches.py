#!/usr/bin/env python3
"""Compile concise, locally curated approach definitions into strict packets.

This is intentionally offline. Clinical synthesis is authored in the checked-in
``curated`` JSON files, while this compiler supplies claim identifiers and the
repetitive schema wiring. It never calls an LLM or an external API.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from caseprep.approach_library.schema import (
    CLAIM_BOUND_FIELDS,
    REQUIRED_REVIEW_ROLES,
    SCHEMA_VERSION,
    empty_packet,
    validate_packet,
)

CURATED_DIR = ROOT / "data/approach_library/curated"
AUTHORED_DIR = ROOT / "data/approach_library/authored"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _definitions(paths: Iterable[Path]) -> Iterable[Dict[str, Any]]:
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload if isinstance(payload, list) else payload.get("approaches", [])
        for row in rows:
            row["_definition_file"] = str(path.relative_to(ROOT))
            yield row


def compile_definition(definition: Dict[str, Any]) -> Dict[str, Any]:
    packet = empty_packet(
        definition["approach_id"], definition["name"], region=definition["region"]
    )
    for field in ("aliases", "joint", "bones", "corridor", "procedure_applications"):
        packet[field] = definition.get(field, packet[field])
    packet["schema_version"] = SCHEMA_VERSION
    packet["sources"] = definition["sources"]
    packet["claims"] = []

    for field in CLAIM_BOUND_FIELDS:
        compiled_items = []
        for index, item in enumerate(definition.get("sections", {}).get(field, []), start=1):
            claim_id = f"{_slug(definition['approach_id'])}_{_slug(field)}_{index:02d}"
            text = item.get("text") or item.get("question")
            claim = {
                "claim_id": claim_id,
                "text": item.get("claim") or text,
                "source_ids": item["source_ids"],
                "risk_level": item.get("risk_level", "medium"),
            }
            if item.get("claim_key"):
                claim["claim_key"] = item["claim_key"]
                claim["normalized_value"] = item["normalized_value"]
            packet["claims"].append(claim)
            rendered = {key: value for key, value in item.items() if key not in {
                "source_ids", "risk_level", "claim", "claim_key", "normalized_value"
            }}
            rendered["claim_ids"] = [claim_id]
            compiled_items.append(rendered)
        packet[field] = compiled_items

    packet["resolved_contradiction_keys"] = definition.get("resolved_contradiction_keys", [])
    packet["content_status"] = "agent_review_pending"
    packet["authoring_provenance"] = {
        "method": "local_codex_curated",
        "definition_file": definition["_definition_file"],
        "api_used": False,
    }
    packet["review"] = {
        "status": "agent_review_pending",
        "required_roles": sorted(REQUIRED_REVIEW_ROLES),
        "completed_roles": [],
    }
    gate = validate_packet(packet, require_reviews=False)
    if not gate["passed"]:
        raise ValueError(f"{definition['approach_id']}: " + "; ".join(gate["failures"]))
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--check", action="store_true", help="Validate without writing outputs")
    args = parser.parse_args()
    paths = args.paths or sorted(CURATED_DIR.glob("*.json"))
    packets = [compile_definition(row) for row in _definitions(paths)]
    if not args.check:
        AUTHORED_DIR.mkdir(parents=True, exist_ok=True)
        for packet in packets:
            destination = AUTHORED_DIR / f"{packet['approach_id']}.json"
            destination.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n")
            print(destination.relative_to(ROOT))
    print(f"validated={len(packets)} api_used=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
