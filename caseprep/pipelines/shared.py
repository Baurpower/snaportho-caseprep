from __future__ import annotations

import hashlib
import re
import time
from typing import Any, Callable, Dict, Iterable, List, Optional


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def stable_id(prefix: str, question: str, answer: str) -> str:
    digest = hashlib.sha1(f"{question}\0{answer}".encode("utf-8")).hexdigest()[:12]
    return f"{prefix}:{digest}"


def source_ids(payload: Optional[Dict[str, Any]]) -> List[str]:
    if not payload:
        return []
    values = payload.get("source_urls") or payload.get("sources") or []
    return [clean(value) for value in values if clean(value)]


def item(
    *,
    prefix: str,
    question: Any,
    answer: Any,
    category: str,
    sources: Iterable[str],
    supporting_detail: Any = "",
    confidence: float = 0.85,
    generated: bool = False,
) -> Optional[Dict[str, Any]]:
    q, a = clean(question), clean(answer)
    if not q or not a:
        return None
    refs = [clean(value) for value in sources if clean(value)]
    return {
        "id": stable_id(prefix, q, a),
        "question": q,
        "answer": a,
        "supporting_detail": clean(supporting_detail),
        "category": category,
        "source_ids": list(dict.fromkeys(refs)),
        "confidence": confidence,
        "generated": generated,
    }


def pipeline_result(
    pipeline_id: str,
    started: float,
    items: List[Dict[str, Any]],
    *,
    sources: Iterable[str] = (),
    warnings: Iterable[str] = (),
    status: Optional[str] = None,
) -> Dict[str, Any]:
    resolved_status = status or ("complete" if items else "unavailable")
    return {
        "pipeline_id": pipeline_id,
        "status": resolved_status,
        "items": items,
        "source_ids": list(dict.fromkeys(clean(value) for value in sources if clean(value))),
        "warnings": [clean(value) for value in warnings if clean(value)],
        "duration_ms": int((time.monotonic() - started) * 1000),
    }


def run_pipeline(
    pipeline_id: str,
    builder: Callable[[], List[Dict[str, Any]]],
    *,
    sources: Iterable[str] = (),
) -> Dict[str, Any]:
    started = time.monotonic()
    try:
        items = builder()
        return pipeline_result(pipeline_id, started, items, sources=sources)
    except Exception as exc:
        return pipeline_result(
            pipeline_id,
            started,
            [],
            sources=sources,
            warnings=[f"{pipeline_id} pipeline failed: {exc}"],
            status="failed",
        )


def parse_qa(value: Any) -> tuple[str, str]:
    text = clean(value)
    match = re.match(r"^Q:\s*(.*?)\s+A:\s*(.*)$", text, re.I)
    return (clean(match.group(1)), clean(match.group(2))) if match else ("", "")

