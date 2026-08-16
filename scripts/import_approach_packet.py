#!/usr/bin/env python3
"""Validate and import an agent-authored approach packet as an unpublished draft."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from caseprep.approach_library.schema import SCHEMA_VERSION, validate_packet

AUTHORED_DIR = ROOT / "data/approach_library/authored"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    if packet.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit(f"Expected {SCHEMA_VERSION}")
    if packet.get("content_status") == "published":
        raise SystemExit("Imports cannot self-declare publication")
    gate = validate_packet(packet, require_reviews=False)
    if not gate["passed"]:
        print(json.dumps(gate, indent=2))
        return 1
    packet["content_status"] = "agent_review_pending"
    packet["review"] = {
        "status": "agent_review_pending",
        "required_roles": packet.get("review", {}).get("required_roles", []),
        "completed_roles": [],
    }
    AUTHORED_DIR.mkdir(parents=True, exist_ok=True)
    destination = AUTHORED_DIR / f"{packet['approach_id']}.json"
    destination.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
