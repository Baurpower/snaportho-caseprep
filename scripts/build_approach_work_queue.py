#!/usr/bin/env python3
"""Build deterministic, coverage-aware local authoring/review batches."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from caseprep.approach_library import ApproachLibrary
from caseprep.approach_library.schema import empty_packet

OUTPUT = ROOT / "data/approach_library/work_queue"
HUMAN_DOMAINS = {"orthopedic-trauma", "spine", "orthopedics"}


def task_for(source: Dict[str, Any]) -> Dict[str, Any]:
    approach_id = "authored_" + source["source_page_id"]
    template = empty_packet(
        approach_id,
        source["title"],
        region=source.get("anatomic_area") or source.get("region") or "",
    )
    template["sources"] = [
        {
            "source_id": source["source_page_id"],
            "provider": source["provider"],
            "url": source["url"],
            "title": source["title"],
            "use": "primary_discovery_source",
        }
    ]
    return {
        "task_id": "author_" + source["source_page_id"],
        "task_type": "approach_packet_authoring",
        "status": "pending",
        "source_page": source,
        "required_output": template,
        "instructions": [
            "Read the linked source; do not copy source prose or illustrations.",
            "Synthesize original, concise, anatomically precise content into every applicable schema field.",
            "Add at least one independent authoritative source; use PubMed evidence for comparative claims.",
            "Represent every clinical assertion in claims[] with source_ids and risk_level.",
            "Represent each clinical list item as an object with text and claim_ids; plain strings fail validation.",
            "Give comparable claims a claim_key and normalized_value so contradictions can be detected.",
            "Do not infer an operative detail absent from the cited sources.",
            "Mark a field unresolved rather than filling it with generic content.",
            "Do not mark the packet published or agent reviewed.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args()
    all_sources = [
        row
        for row in ApproachLibrary.source_pages().values()
        if row.get("clinical_domain") in HUMAN_DOMAINS
    ]
    authored_packets = [
        packet
        for packet in ApproachLibrary.packets().values()
        if packet.get("content_status") != "source_indexed"
    ]
    covered_source_ids = {
        str(source.get("source_page_id") or source.get("source_id") or "")
        for packet in authored_packets
        for source in packet.get("sources") or []
    }
    covered_urls = {
        str(source.get("url") or "").rstrip("/")
        for packet in authored_packets
        for source in packet.get("sources") or []
        if source.get("url")
    }
    sources = [
        row
        for row in all_sources
        if row["source_page_id"] not in covered_source_ids
        and str(row.get("url") or "").rstrip("/") not in covered_urls
    ]
    sources.sort(key=lambda row: (row.get("clinical_domain", ""), row.get("region", ""), row["url"]))
    tasks = [task_for(source) for source in sources]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    batches: List[Dict[str, Any]] = []
    for offset in range(0, len(tasks), args.batch_size):
        batch_tasks = tasks[offset : offset + args.batch_size]
        batch = {
            "schema_version": "brobot_approach_authoring_batch_v1",
            "batch_id": f"batch_{offset // args.batch_size + 1:03d}",
            "tasks": batch_tasks,
        }
        batches.append(batch)
        (OUTPUT / f"{batch['batch_id']}.json").write_text(
            json.dumps(batch, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    manifest = {
        "schema_version": "brobot_approach_work_queue_v1",
        "human_orthopedic_source_pages": len(all_sources),
        "source_pages_covered_by_authored_packets": len(all_sources) - len(tasks),
        "batch_size": args.batch_size,
        "batch_count": len(batches),
        "pending": len(tasks),
        "excluded_non_caseprep_domains": {
            "cmf": sum(row.get("clinical_domain") == "cmf" for row in ApproachLibrary.source_pages().values()),
            "vet": sum(row.get("clinical_domain") == "vet" for row in ApproachLibrary.source_pages().values()),
        },
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
