"""CasePrep v1.1 web packet SSE protocol — single source of truth.

Wire format matches the /api/brobot/chat convention consumed by the web app:

    event: <name>\n
    data: <json>\n
    \n

Event order:
    1. ``meta``                     — always first
    2. ``header``                   — above-the-fold identity + prep chips
       (or ``clarification`` then ``done`` when approach disambiguation is
       required; that path is terminal)
    3. ``section`` (xN)             — emitted as pipelines complete; the client
       renders into fixed layout slots keyed by ``section_id`` so arrival
       order never changes visual order
    *  ``section_error``/``warning`` — non-terminal degradation
    n. ``done``                     — always last on success paths
    *  ``error``                    — fatal only

``source`` / ``confidence`` / ``generated_field_paths`` are internal debug
indicators; the UI hides them from end users.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

STREAM_PROTOCOL_VERSION = 1
ENGINE_NAME = "web_packet_stream"

EVENT_META = "meta"
EVENT_HEADER = "header"
EVENT_CLARIFICATION = "clarification"
EVENT_SECTION = "section"
EVENT_SECTION_ERROR = "section_error"
EVENT_WARNING = "warning"
EVENT_DONE = "done"
EVENT_ERROR = "error"

# Packet layout order (client slot order, not emission order).
SECTION_IDS = (
    "summary",
    "key_takeaways",
    "top_things_to_know",
    "pimp_questions",
    "anatomy",
    "operative_flow",
    "teaching_topics",
    "decision_points",
    "pitfalls",
    "postop",
    "evidence",
    "related_concepts",  # injected web-side from the knowledge graph
    "sources",
)


def sse_event(event: str, data: Dict[str, Any]) -> bytes:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


def meta_event(packet_id: str) -> bytes:
    return sse_event(
        EVENT_META,
        {
            "packet_id": packet_id,
            "caseprep_version": "v1.1",
            "engine": ENGINE_NAME,
            "stream_protocol_version": STREAM_PROTOCOL_VERSION,
        },
    )


def header_event(case: Dict[str, Any], header: Dict[str, Any]) -> bytes:
    return sse_event(EVENT_HEADER, {"case": case, "header": header})


def clarification_event(
    case: Dict[str, Any], reason: str, options: Iterable[Dict[str, Any]]
) -> bytes:
    return sse_event(
        EVENT_CLARIFICATION,
        {"case": case, "clarification_reason": reason, "options": list(options)},
    )


def section_event(
    section_id: str,
    *,
    status: str,
    items: Optional[List[Dict[str, Any]]] = None,
    payload: Optional[Dict[str, Any]] = None,
    source: str = "curated",
    confidence: Optional[float] = None,
    generated_field_paths: Optional[List[str]] = None,
    duration_ms: int = 0,
) -> bytes:
    data: Dict[str, Any] = {
        "section_id": section_id,
        "status": status,
        "source": source,
        "confidence": confidence,
        "generated_field_paths": generated_field_paths or [],
        "duration_ms": duration_ms,
    }
    if items is not None:
        data["items"] = items
    if payload is not None:
        data["payload"] = payload
    return sse_event(EVENT_SECTION, data)


def section_error_event(section_id: str, reason: str) -> bytes:
    return sse_event(EVENT_SECTION_ERROR, {"section_id": section_id, "reason": reason})


def warning_event(message: str) -> bytes:
    return sse_event(EVENT_WARNING, {"message": message})


def done_event(
    pipeline_status: Dict[str, Any], timing: Dict[str, int], warnings: List[str]
) -> bytes:
    return sse_event(
        EVENT_DONE,
        {"pipeline_status": pipeline_status, "timing": timing, "warnings": warnings},
    )


def error_event(message: str) -> bytes:
    return sse_event(EVENT_ERROR, {"message": message})
