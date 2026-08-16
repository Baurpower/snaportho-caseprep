#!/usr/bin/env python3
"""Read-only CasePrep v3 coverage and review-gate report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from caseprep.services.packet_v3 import normalize_packet, validate_review_gate  # noqa: E402


def main() -> None:
    rows = []
    for folder in sorted((ROOT / "data/caseprep/procedures").iterdir()):
        manifest_path = folder / "manifest.json"
        payload_path = folder / "certified_payload.json"
        if not manifest_path.exists() or not payload_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not manifest.get("runtime_enabled"):
            continue
        packet = normalize_packet(json.loads(payload_path.read_text(encoding="utf-8")))
        gate = validate_review_gate(packet or {})
        coverage = (packet or {}).get("approach_coverage") or {}
        rows.append(
            {
                "procedure_id": manifest.get("slug"),
                "review_status": ((packet or {}).get("review") or {}).get("status"),
                "known_approaches": coverage.get("known_count", 0),
                "complete_approaches": coverage.get("complete_count", 0),
                "approach_gaps": coverage.get("gap_count", 0),
                "gate_passed": gate["passed"],
                "failures": gate["failures"],
            }
        )
    summary = {
        "live_packets": len(rows),
        "agent_reviewed": sum(row["review_status"] == "agent_reviewed" for row in rows),
        "packets_with_approach_gaps": sum(row["approach_gaps"] > 0 for row in rows),
        "review_gate_passed": sum(row["gate_passed"] for row in rows),
        "rows": rows,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
