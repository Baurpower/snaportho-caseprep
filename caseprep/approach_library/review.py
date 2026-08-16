"""Append-only, hash-bound independent-agent reviews for approach packets."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .schema import REQUIRED_REVIEW_ROLES, content_hash, validate_packet

ROOT = Path(__file__).resolve().parents[2]
REVIEW_DIR = ROOT / "data/approach_library/reviews"


def review_path(approach_id: str) -> Path:
    return REVIEW_DIR / f"{approach_id}.jsonl"


def review_records(packet: Dict[str, Any]) -> List[Dict[str, Any]]:
    path = review_path(str(packet.get("approach_id") or ""))
    if not path.exists():
        return []
    digest = content_hash(packet)
    records: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("content_hash") == digest and row.get("role") in REQUIRED_REVIEW_ROLES:
            records.append(row)
    return records


def attach_review_state(packet: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(packet)
    records = review_records(result)
    passed_roles = sorted(
        {
            str(row["role"])
            for row in records
            if row.get("decision") == "pass" and row.get("reviewer_id")
        }
    )
    review = dict(result.get("review") or {})
    review.update(
        {
            "content_hash": content_hash(result),
            "required_roles": sorted(REQUIRED_REVIEW_ROLES),
            "completed_roles": passed_roles,
            "artifacts": records,
            "status": "agent_review_pending",
        }
    )
    result["review"] = review
    gate = validate_packet(result, require_reviews=True)
    review["publication_gate"] = gate
    if gate["passed"]:
        review["status"] = "agent_reviewed"
        result["content_status"] = "published"
    return result


def record_review(
    packet: Dict[str, Any],
    *,
    role: str,
    reviewer_id: str,
    decision: str,
    findings: Iterable[Dict[str, Any]] = (),
    summary: str = "",
) -> Dict[str, Any]:
    if role not in REQUIRED_REVIEW_ROLES:
        raise ValueError(f"Unsupported review role: {role}")
    if decision not in {"pass", "fail"}:
        raise ValueError("decision must be pass or fail")
    findings_list = list(findings)
    if decision == "pass" and any(
        row.get("severity") in {"high", "critical"} and not row.get("resolved")
        for row in findings_list
    ):
        raise ValueError("A passing review cannot contain unresolved high/critical findings")
    artifact = {
        "schema_version": "brobot_approach_agent_review_v1",
        "approach_id": packet["approach_id"],
        "content_hash": content_hash(packet),
        "role": role,
        "reviewer_id": reviewer_id,
        "decision": decision,
        "summary": summary,
        "findings": findings_list,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    path = review_path(packet["approach_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(artifact, ensure_ascii=False, sort_keys=True) + "\n")
    return artifact
