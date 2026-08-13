#!/usr/bin/env python3
"""Replay privacy-safe real BroBot prompts through v1.1 and summarize packets."""

from __future__ import annotations

import concurrent.futures
import json
import re
import sys
import time
import urllib.request
from collections import Counter
from difflib import SequenceMatcher


ENDPOINT = "https://api.snap-ortho.com/case-prep/web/v1.1/stream"
PROMPTS = [
    "ACL reconstruction",
    "Distal radius fracture",
    "Carpal tunnel release",
    "Distal radius ORIF",
    "Total knee arthroplasty",
    "Olecranon fracture",
    "ORIF ankle",
    "Rotator cuff repair",
    "Total hip posterior approach",
    "MPFL reconstruction",
    "Orif humeral shaft middiaohaseal",
    "undifferentiated pleomorphic sarcoma",
]


def normalized(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def parse_sse(raw: str) -> list[tuple[str, dict]]:
    events = []
    for frame in re.split(r"\r?\n\r?\n", raw):
        name = "message"
        data = []
        for line in frame.splitlines():
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].lstrip())
        if data:
            try:
                events.append((name, json.loads("\n".join(data))))
            except json.JSONDecodeError:
                events.append((name, {"_decode_error": True}))
    return events


def run(prompt: str) -> dict:
    started = time.monotonic()
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps({"prompt": prompt, "training_level": "pgy2", "entry_surface": "quality_audit"}).encode(),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=75) as response:
            events = parse_sse(response.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        return {"prompt": prompt, "fatal": f"{type(exc).__name__}: {exc}"}

    header = next((data for name, data in events if name == "header"), {})
    clarification = next((data for name, data in events if name == "clarification"), None)
    done = next((data for name, data in reversed(events) if name == "done"), {})
    final_sections = {}
    section_errors = {}
    for name, data in events:
        if name == "section":
            final_sections[data.get("section_id", "unknown")] = data
        elif name == "section_error":
            section_errors[data.get("section_id", "unknown")] = data.get("reason")

    items = [item for section in final_sections.values() for item in section.get("items", [])]
    grounded = [item for item in items if not item.get("generated")]
    generated = [item for item in items if item.get("generated")]
    source_counts = Counter(item.get("source") or "unspecified" for item in items)
    confidences = [float(item.get("confidence")) for item in items if isinstance(item.get("confidence"), (int, float))]
    empty_answers = [item.get("id") for item in items if not str(item.get("answer") or "").strip()]
    generic = [
        item.get("id") for item in generated
        if any(phrase in normalized(str(item.get("question", "")) + " " + str(item.get("answer", "")))
               for phrase in ("most common complication", "typical follow up", "usually", "generally"))
    ]
    duplicates = []
    for index, left in enumerate(items):
        left_text = normalized(f"{left.get('question', '')} {left.get('answer', '')}")
        if len(left_text) < 20:
            continue
        for right in items[index + 1:]:
            right_text = normalized(f"{right.get('question', '')} {right.get('answer', '')}")
            ratio = SequenceMatcher(None, left_text, right_text).ratio()
            if ratio >= 0.82:
                duplicates.append([left.get("id"), right.get("id"), round(ratio, 2)])

    return {
        "prompt": prompt,
        "elapsed_ms": round((time.monotonic() - started) * 1000),
        "event_names": [name for name, _ in events],
        "canonical_slug": header.get("case", {}).get("canonical_slug"),
        "canonical_name": header.get("case", {}).get("canonical_name"),
        "certified": header.get("header", {}).get("certified"),
        "clarification": clarification,
        "sections": {key: len(value.get("items", [])) for key, value in final_sections.items()},
        "source_payload_count": len(final_sections.get("sources", {}).get("payload", {}).get("sources", [])),
        "section_errors": section_errors,
        "item_count": len(items),
        "grounded_count": len(grounded),
        "generated_count": len(generated),
        "source_counts": source_counts,
        "min_confidence": min(confidences) if confidences else None,
        "empty_answers": empty_answers,
        "generic_generated_ids": generic,
        "duplicate_pairs": duplicates[:12],
        "warnings": done.get("warnings", []),
        "timing": done.get("timing", {}),
        "generated_samples": [
            {"section": section_id, "question": item.get("question"), "answer": item.get("answer")}
            for section_id, section in final_sections.items()
            for item in section.get("items", []) if item.get("generated")
        ][:8],
        "low_confidence_grounded_samples": [
            {
                "section": section_id,
                "confidence": item.get("confidence"),
                "question": item.get("question"),
                "answer": item.get("answer"),
            }
            for section_id, section in final_sections.items()
            for item in section.get("items", [])
            if not item.get("generated")
            and isinstance(item.get("confidence"), (int, float))
            and item["confidence"] < 0.58
        ][:20],
    }


def main() -> None:
    prompts = sys.argv[1:] or PROMPTS
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(run, prompts))
    json.dump(results, sys.stdout, indent=2, default=list)
    print()


if __name__ == "__main__":
    main()
