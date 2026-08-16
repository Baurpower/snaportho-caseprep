"""Append-only, hash-bound second-agent review records for CasePrep v3."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from caseprep.factory.paths import procedure_dir
from caseprep.services import curated_content_store
from caseprep.services.packet_v3 import AGENT_REVIEW_ROLES, normalize_packet, reviewable_content_hash


def record_review(
    slug: str,
    *,
    reviewer_id: str,
    role: str,
    decision: str,
    findings: List[Dict[str, Any]],
    model: str,
    prompt_version: str,
) -> Dict[str, Any]:
    """Record an independent review. Passing reviews cannot contain open high/critical findings."""
    if role not in AGENT_REVIEW_ROLES:
        raise ValueError(f"Unknown review role: {role}")
    if decision not in {"pass", "fail"}:
        raise ValueError("decision must be 'pass' or 'fail'")
    if not reviewer_id.strip() or not model.strip() or not prompt_version.strip():
        raise ValueError("reviewer_id, model, and prompt_version are required")
    if decision == "pass" and any(
        finding.get("severity") in {"critical", "high"}
        and finding.get("status", "open") != "resolved"
        for finding in findings
    ):
        raise ValueError("A passing review cannot contain open high/critical findings")

    legacy = curated_content_store.get_legacy_payload(slug)
    packet = normalize_packet(legacy)
    if not packet:
        raise FileNotFoundError(f"No curated packet exists for {slug}")
    row = {
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "procedure_id": slug,
        "content_hash": reviewable_content_hash(packet),
        "reviewer_id": reviewer_id,
        "reviewer_type": "independent_agent",
        "role": role,
        "decision": decision,
        "findings": findings,
        "model": model,
        "prompt_version": prompt_version,
    }
    path = procedure_dir(slug) / "agent_reviews_v3.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    return row
