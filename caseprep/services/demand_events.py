"""Append-only, best-effort Case Prep demand-event logging."""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

EVENT_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "caseprep"
    / "analytics"
    / "demand_events.jsonl"
)
_LOCK = threading.Lock()


def record_demand_event(
    *,
    raw_request: str,
    resolved: Dict[str, Any],
    curated_hit: bool,
    revision_id: Optional[str],
    payload_hash: Optional[str],
    fallback_used: bool,
    fallback_reason: Optional[str],
    retrieved_source_ids: List[str],
    response_latency_ms: int,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Never raise into the response path."""
    try:
        ctx = context or {}
        dedupe_material = "|".join(
            [
                str(ctx.get("case_prep_session_id") or ctx.get("conversation_id") or ""),
                raw_request.strip().lower(),
                str(payload_hash or fallback_reason or ""),
            ]
        )
        event = {
            "event_id": str(uuid.uuid4()),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "dedupe_key": hashlib.sha256(dedupe_material.encode("utf-8")).hexdigest(),
            "user_id": ctx.get("user_id"),
            "anonymous_session_id": ctx.get("anonymous_session_id"),
            "raw_request": raw_request,
            "canonical_slug": resolved.get("procedure_slug"),
            "canonical_name": resolved.get("canonical_display_name"),
            "entity_kind": resolved.get("entity_kind"),
            "requested_approach": resolved.get("requested_approach"),
            "resolver_method": resolved.get("match_method"),
            "resolver_confidence": resolved.get("confidence"),
            "alternative_matches": resolved.get("suggested_matches") or [],
            "requires_clarification": bool(resolved.get("requires_clarification")),
            "curated_hit": curated_hit,
            "content_revision_id": revision_id,
            "payload_hash": payload_hash,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "retrieved_source_ids": retrieved_source_ids,
            "training_level": ctx.get("training_level"),
            "entry_surface": ctx.get("entry_surface"),
            "conversation_id": ctx.get("conversation_id"),
            "case_prep_session_id": ctx.get("case_prep_session_id"),
            "response_latency_ms": response_latency_ms,
            "user_feedback": ctx.get("user_feedback"),
        }
        EVENT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            with EVENT_PATH.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
        return event
    except Exception as exc:
        print(f"⚠️ CasePrep demand event was not recorded: {exc}")
        return None


def aggregate_demand_events() -> List[Dict[str, Any]]:
    if not EVENT_PATH.exists():
        return []
    grouped: Dict[str, Dict[str, Any]] = {}
    with EVENT_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            event = json.loads(line)
            key = event.get("canonical_slug") or "unresolved"
            row = grouped.setdefault(
                key,
                {
                    "canonical_case": event.get("canonical_name") or key,
                    "unique_users": set(),
                    "total_requests": 0,
                    "repeat_requests": 0,
                    "curated_misses": 0,
                    "fallback_requests": 0,
                    "negative_feedback": 0,
                    "training_level_distribution": {},
                    "last_requested": None,
                },
            )
            identity = event.get("user_id") or event.get("anonymous_session_id")
            if identity:
                if identity in row["unique_users"]:
                    row["repeat_requests"] += 1
                row["unique_users"].add(identity)
            row["total_requests"] += 1
            row["curated_misses"] += int(not event.get("curated_hit"))
            row["fallback_requests"] += int(bool(event.get("fallback_used")))
            row["negative_feedback"] += int(event.get("user_feedback") == "negative")
            level = event.get("training_level") or "unknown"
            row["training_level_distribution"][level] = (
                row["training_level_distribution"].get(level, 0) + 1
            )
            row["last_requested"] = max(
                filter(None, [row["last_requested"], event.get("occurred_at")]),
                default=None,
            )
    output = []
    for row in grouped.values():
        row["unique_users"] = len(row["unique_users"])
        row["fallback_rate"] = (
            row.pop("fallback_requests") / row["total_requests"]
            if row["total_requests"]
            else 0.0
        )
        output.append(row)
    return sorted(output, key=lambda row: row["total_requests"], reverse=True)
