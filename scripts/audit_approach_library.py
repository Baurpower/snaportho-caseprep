#!/usr/bin/env python3
"""Audit inventory completeness separately from clinical publication readiness."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from caseprep.approach_library import ApproachLibrary
from caseprep.approach_library.schema import validate_packet


def main() -> int:
    library = ApproachLibrary()
    sources = list(library.source_pages().values())
    packets = list(library.packets().values())
    duplicate_urls = len(sources) - len({row.get("url") for row in sources})
    publication_results = {
        packet["approach_id"]: validate_packet(library.get(packet["approach_id"]) or packet)
        for packet in packets
    }
    published = sorted(key for key, result in publication_results.items() if result["passed"])
    source_index_only = [packet for packet in packets if packet.get("content_status") == "source_indexed"]
    authored = [
        packet
        for packet in packets
        if packet.get("runtime_fields")
        or packet.get("content_status") in {"agent_review_pending", "published"}
    ]
    strict_native = [
        packet
        for packet in authored
        if packet.get("authoring_provenance", {}).get("method") == "local_codex_curated"
    ]
    migrated = [packet for packet in authored if packet.get("runtime_fields")]
    mappings = library.mappings()
    report = {
        "source_pages": len(sources),
        "provider_counts": dict(Counter(str(row.get("provider") or "unknown") for row in sources)),
        "domain_counts": dict(Counter(str(row.get("clinical_domain") or "unknown") for row in sources)),
        "duplicate_source_urls": duplicate_urls,
        "canonical_packets": len(packets),
        "source_index_only_packets": len(source_index_only),
        "authored_clinical_packets": len(authored),
        "strict_native_authored_packets": len(strict_native),
        "migrated_authored_packets": len(migrated),
        "procedure_mappings": len(mappings),
        "mapped_procedures": len({row.get("procedure_id") for row in mappings}),
        "publication_ready": len(published),
        "published_ids": published,
        "inventory_gate_passed": (
            len(sources) >= 600
            and sum(row.get("provider") == "ao_surgery_reference" for row in sources) >= 500
            and sum(row.get("provider") == "orthobullets" for row in sources) >= 60
            and duplicate_urls == 0
        ),
        "safety_note": "Source-indexed records are discoverable but cannot be published as clinical guidance.",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["inventory_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
