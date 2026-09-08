#!/usr/bin/env python3
"""Replay real CasePrep prompts through the latest stream and write a QA report.

The input cohort contains only id, created_at, and prompt from `caseprep_runs`.
User IDs and stored packets are deliberately excluded from both memory and output artifacts.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import statistics
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from caseprep.engines.v1_2_web_stream import VERSION as LATEST_CASEPREP_VERSION
from caseprep.services.prompt_understanding import extract_prompt_profile
from procedure_registry import SLUG_TO_DEF

DEFAULT_ENDPOINT = (
    f"https://api.snap-ortho.com/case-prep/web/{LATEST_CASEPREP_VERSION}/stream"
)
DEFAULT_ENV = Path(__file__).resolve().parents[2] / "snaportho-web" / ".env.local"
EXPECTED_SECTIONS = {
    "summary",
    "key_takeaways",
    "top_things_to_know",
    "pimp_questions",
    "anatomy",
    "teaching_topics",
    "decision_points",
    "pitfalls",
    "postop",
    "operative_flow",
    "evidence",
}


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


def percentile(values: list[int], pct: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * pct)))
    return ordered[index]


def normalized(text: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def fetch_cases(limit: int, env_path: Path) -> list[dict[str, Any]]:
    load_env(env_path)
    base_url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not base_url or not key:
        raise RuntimeError(
            f"Missing SUPABASE_URL/NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in {env_path}"
        )
    query = urllib.parse.urlencode({
        "select": "id,created_at,prompt",
        "prompt": "not.is.null",
        "client_platform": "eq.web",
        "order": "created_at.desc,id.desc",
        "limit": str(limit),
    })
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/rest/v1/caseprep_runs?{query}",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        rows = json.load(response)
    return [
        {"response_id": row["id"], "created_at": row["created_at"], "question": row["prompt"].strip()}
        for row in rows
        if isinstance(row.get("prompt"), str) and row["prompt"].strip()
    ][:limit]


def load_cases(path: Path, limit: int) -> list[dict[str, Any]]:
    """Load a privacy-minimized frozen cohort from an earlier audit or JSONL."""
    if path.suffix == ".jsonl":
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    else:
        payload = json.loads(path.read_text())
        rows = payload.get("results", payload) if isinstance(payload, dict) else payload
    cases = [
        {
            "response_id": row.get("response_id", index),
            "created_at": row.get("created_at", ""),
            "question": str(row.get("question") or row.get("prompt") or "").strip(),
        }
        for index, row in enumerate(rows, 1)
        if isinstance(row, dict) and str(row.get("question") or row.get("prompt") or "").strip()
    ]
    return cases[:limit]


def parse_sse(raw: str) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    for frame in re.split(r"\r?\n\r?\n", raw):
        name = "message"
        data_lines: list[str] = []
        for line in frame.splitlines():
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        if not data_lines:
            continue
        try:
            data = json.loads("\n".join(data_lines))
        except json.JSONDecodeError:
            data = {"_decode_error": True}
        events.append((name, data))
    return events


def replay(case: dict[str, Any], endpoint: str, timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({
            "prompt": case["question"],
            "training_level": "pgy2",
            "entry_surface": "quality_audit",
        }).encode(),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    base = dict(case)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
        events = parse_sse(raw)
    except Exception as exc:  # Preserve the failed case for denominator accounting.
        return {
            **base,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "fatal": f"{type(exc).__name__}: {exc}",
        }

    meta = next((data for name, data in events if name == "meta"), {})
    resolution = next((data for name, data in events if name == "resolution"), {})
    header = next((data for name, data in events if name == "header"), {})
    clarification = next((data for name, data in events if name == "clarification"), None)
    done = next((data for name, data in reversed(events) if name == "done"), {})
    sections = {
        str(data.get("section_id") or "unknown"): data
        for name, data in events
        if name == "section"
    }
    section_errors = {
        str(data.get("section_id") or "unknown"): data.get("reason") or data.get("message")
        for name, data in events
        if name == "section_error"
    }
    items = [
        {**item, "section_id": section_id}
        for section_id, section in sections.items()
        for item in (section.get("items") or [])
        if isinstance(item, dict)
    ]
    pimp_items = [item for item in items if item["section_id"] == "pimp_questions"]
    grounded = [item for item in items if not item.get("generated")]
    direct = [item for item in items if item.get("procedure_relevance") == "direct"]
    supported = [item for item in items if item.get("claim_support") == "direct"]
    source_ids = {source_id for item in items for source_id in (item.get("source_ids") or []) if source_id}
    empty_items = [
        item.get("id") for item in items
        if not normalized(item.get("question")) and not normalized(item.get("answer"))
    ]
    malformed_items = [
        item.get("id") for item in items
        if any(token in f"{item.get('question', '')} {item.get('answer', '')}" for token in ("�", "\x00", "_Ð"))
    ]
    exact_pimp_questions = [normalized(item.get("question")) for item in pimp_items if normalized(item.get("question"))]
    duplicate_pimp_count = len(exact_pimp_questions) - len(set(exact_pimp_questions))
    present_clinical = EXPECTED_SECTIONS.intersection(sections)
    canonical_slug = (header.get("case") or resolution.get("case") or {}).get("canonical_slug")
    definition = SLUG_TO_DEF.get(canonical_slug)
    prompt_profile = extract_prompt_profile(case["question"])
    prompt_regions = prompt_profile.get("regions") or []
    canonical_region = definition.body_region if definition else None
    region_consistent = (
        canonical_region in prompt_regions if canonical_region and prompt_regions else None
    )

    # Utility score is intentionally transparent and never substitutes for clinical review.
    resolution_points = (
        20
        if resolution.get("compatibility_status") == "valid" and region_consistent is not False
        else 0
    )
    reliability_points = 10 if events and not any(name == "error" for name, _ in events) else 0
    pimp_points = min(20, round(len(pimp_items) / 8 * 20))
    relevance_points = round(15 * len(direct) / len(items)) if items else 0
    support_points = round(15 * len(supported) / len(items)) if items else 0
    breadth_points = round(10 * len(present_clinical) / len(EXPECTED_SECTIONS))
    gate_points = 10 if done.get("quality_gate") == "passed" else 5 if done.get("quality_gate") == "limited" else 0

    return {
        **base,
        "elapsed_ms": round((time.monotonic() - started) * 1000),
        "caseprep_version": meta.get("caseprep_version"),
        "engine": meta.get("engine"),
        "event_names": [name for name, _ in events],
        "canonical_slug": canonical_slug,
        "canonical_name": (header.get("case") or resolution.get("case") or {}).get("canonical_name"),
        "canonical_region": canonical_region,
        "prompt_regions": prompt_regions,
        "region_consistent": region_consistent,
        "operative_intent_detected": "operative" in (prompt_profile.get("modifiers") or []),
        "compatibility_status": resolution.get("compatibility_status"),
        "clarification": clarification,
        "coverage_status": done.get("coverage_status"),
        "quality_gate": done.get("quality_gate"),
        "grounded_percentage": done.get("grounded_percentage"),
        "omitted_sections": done.get("omitted_sections") or [],
        "warnings": done.get("warnings") or [],
        "section_errors": section_errors,
        "section_counts": {section_id: len(section.get("items") or []) for section_id, section in sections.items()},
        "item_count": len(items),
        "pimp_count": len(pimp_items),
        "grounded_count": len(grounded),
        "generated_count": len(items) - len(grounded),
        "direct_relevance_count": len(direct),
        "direct_support_count": len(supported),
        "citation_count": len(source_ids),
        "empty_item_ids": empty_items,
        "malformed_item_ids": malformed_items,
        "duplicate_pimp_count": duplicate_pimp_count,
        "utility_score": resolution_points + reliability_points + pimp_points + relevance_points + support_points + breadth_points + gate_points,
        "pimp_questions": [
            {
                "question": item.get("question"),
                "answer": item.get("answer"),
                "provenance": item.get("provenance"),
                "procedure_relevance": item.get("procedure_relevance"),
                "claim_support": item.get("claim_support"),
                "confidence": item.get("confidence"),
                "source_ids": item.get("source_ids") or [],
            }
            for item in pimp_items
        ],
    }


def summarize(
    results: list[dict[str, Any]], endpoint: str, expected_version: str, cohort_source: str
) -> dict[str, Any]:
    completed = [row for row in results if not row.get("fatal")]
    latencies = [int(row["elapsed_ms"]) for row in completed]
    pimp_counts = [int(row.get("pimp_count") or 0) for row in completed]
    scores = [int(row.get("utility_score") or 0) for row in completed]
    return {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint,
        "expected_version": expected_version,
        "cohort_source": cohort_source,
        "requested": len(results),
        "completed": len(completed),
        "fatal_failures": len(results) - len(completed),
        "version_confirmed": sum(
            row.get("caseprep_version") == expected_version for row in completed
        ),
        "version_counts": dict(Counter(row.get("caseprep_version") or "missing" for row in completed)),
        "valid_resolution": sum(row.get("compatibility_status") == "valid" for row in completed),
        "region_mismatches": sum(row.get("region_consistent") is False for row in completed),
        "clarifications": sum(bool(row.get("clarification")) for row in completed),
        "unresolved_slugs": sum(not row.get("canonical_slug") for row in completed),
        "quality_gate_counts": dict(Counter(row.get("quality_gate") or "missing" for row in completed)),
        "coverage_status_counts": dict(Counter(row.get("coverage_status") or "missing" for row in completed)),
        "zero_pimp_cases": sum((row.get("pimp_count") or 0) == 0 for row in completed),
        "eight_plus_pimp_cases": sum((row.get("pimp_count") or 0) >= 8 for row in completed),
        "pimp_count_mean": round(statistics.mean(pimp_counts), 2) if pimp_counts else None,
        "pimp_count_median": statistics.median(pimp_counts) if pimp_counts else None,
        "cases_with_citations": sum((row.get("citation_count") or 0) > 0 for row in completed),
        "cases_with_empty_items": sum(bool(row.get("empty_item_ids")) for row in completed),
        "cases_with_malformed_items": sum(bool(row.get("malformed_item_ids")) for row in completed),
        "cases_with_section_errors": sum(bool(row.get("section_errors")) for row in completed),
        "latency_ms": {
            "median": round(statistics.median(latencies)) if latencies else None,
            "p90": percentile(latencies, 0.9),
            "p95": percentile(latencies, 0.95),
            "max": max(latencies) if latencies else None,
        },
        "utility_score": {
            "mean": round(statistics.mean(scores), 1) if scores else None,
            "median": statistics.median(scores) if scores else None,
            "p10": percentile(scores, 0.1),
        },
        "score_bands": {
            "excellent_85_plus": sum(score >= 85 for score in scores),
            "acceptable_70_to_84": sum(70 <= score < 85 for score in scores),
            "review_50_to_69": sum(50 <= score < 70 for score in scores),
            "failing_below_50": sum(score < 50 for score in scores),
        },
        "top_canonical_slugs": Counter(row.get("canonical_slug") or "unresolved" for row in completed).most_common(15),
        "top_omitted_sections": Counter(section for row in completed for section in row.get("omitted_sections", [])).most_common(),
        "top_warnings": Counter(str(warning) for row in completed for warning in row.get("warnings", [])).most_common(10),
        "worst_cases": [
            {
                "response_id": row["response_id"],
                "question": row["question"],
                "canonical_slug": row.get("canonical_slug"),
                "utility_score": row.get("utility_score"),
                "pimp_count": row.get("pimp_count"),
                "quality_gate": row.get("quality_gate"),
                "coverage_status": row.get("coverage_status"),
                "fatal": row.get("fatal"),
            }
            for row in sorted(results, key=lambda item: (item.get("utility_score", -1), item.get("response_id", 0)))[:15]
        ],
    }


def markdown_report(summary: dict[str, Any], results: list[dict[str, Any]]) -> str:
    completed = summary["completed"]
    pct = lambda count: f"{count}/{completed} ({count / completed:.0%})" if completed else "0/0"
    worst_rows = "\n".join(
        f"| {row['response_id']} | {row['utility_score'] if row['utility_score'] is not None else 'fatal'} | "
        f"{row['pimp_count'] if row['pimp_count'] is not None else '—'} | {row['quality_gate'] or '—'} | "
        f"{row['question'].replace('|', '/').replace(chr(10), ' ')} |"
        for row in summary["worst_cases"]
    )
    omissions = ", ".join(f"{name}: {count}" for name, count in summary["top_omitted_sections"]) or "none"
    warnings = "\n".join(f"- {count}× {warning}" for warning, count in summary["top_warnings"]) or "- None"
    return f"""# CasePrep {summary['expected_version']} — real-case quality audit

Evaluated: {summary['evaluated_at']}  
Endpoint: `{summary['endpoint']}`  
Cohort source: `{summary['cohort_source']}`. User IDs and historical answers are excluded.

## Executive metrics

- Completed: {summary['completed']}/{summary['requested']}; fatal failures: {summary['fatal_failures']}
- Confirmed expected-version responses: {pct(summary['version_confirmed'])}; observed: `{json.dumps(summary['version_counts'], sort_keys=True)}`
- Valid procedure resolution: {pct(summary['valid_resolution'])}; clarifications: {summary['clarifications']}; unresolved slugs: {summary['unresolved_slugs']}
- Prompt/slug region mismatches: {summary['region_mismatches']}
- Zero pimp-question packets: {pct(summary['zero_pimp_cases'])}; packets with 8+: {pct(summary['eight_plus_pimp_cases'])}
- Pimp questions: mean {summary['pimp_count_mean']}, median {summary['pimp_count_median']}
- Packets with citations: {pct(summary['cases_with_citations'])}
- Empty/malformed content: {summary['cases_with_empty_items']}/{summary['cases_with_malformed_items']} packets
- Section errors: {pct(summary['cases_with_section_errors'])}
- Latency: median {summary['latency_ms']['median']} ms, p90 {summary['latency_ms']['p90']} ms, p95 {summary['latency_ms']['p95']} ms, max {summary['latency_ms']['max']} ms
- Transparent utility score: mean {summary['utility_score']['mean']}/100, median {summary['utility_score']['median']}/100, p10 {summary['utility_score']['p10']}/100

Quality gates: `{json.dumps(summary['quality_gate_counts'], sort_keys=True)}`  
Coverage: `{json.dumps(summary['coverage_status_counts'], sort_keys=True)}`  
Omitted sections: {omissions}

The utility score weights valid, region-consistent resolution (20), reliable transport (10), eight pimp questions (20), direct procedure relevance (15), direct claim support (15), eleven-section breadth (10), and the stream quality gate (10). It is a triage measure, not a clinical-validity score.

## Lowest-scoring cases for clinical review

| Response | Score | Pimp | Gate | Prompt |
|---:|---:|---:|---|---|
{worst_rows}

## Most frequent warnings

{warnings}

## Interpretation boundary

This automated audit measures resolution, output completeness, provenance metadata, citations, and operational reliability. It does not prove factual clinical correctness. The JSON artifact preserves the generated pimp questions and answers for targeted expert review, without user identifiers.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--cohort-file", type=Path, help="Replay a frozen JSON/JSONL cohort instead of fetching Supabase.")
    parser.add_argument("--expected-version", default=LATEST_CASEPREP_VERSION)
    parser.add_argument("--check", action="store_true", help="Exit nonzero when release-quality thresholds fail.")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/caseprep-v1.2"))
    parser.add_argument("--label", default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()

    cases = (
        load_cases(args.cohort_file, args.limit)
        if args.cohort_file
        else fetch_cases(args.limit, args.env_file)
    )
    if len(cases) != args.limit:
        raise RuntimeError(f"Expected {args.limit} non-empty cases, fetched {len(cases)}")
    source = str(args.cohort_file) if args.cohort_file else "caseprep_runs"
    print(f"Loaded {len(cases)} privacy-minimized cases from {source}", flush=True)

    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(replay, case, args.endpoint, args.timeout): case for case in cases}
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            results.append(future.result())
            if index % 10 == 0 or index == len(cases):
                print(f"Completed {index}/{len(cases)}", flush=True)
    results.sort(key=lambda row: (row["created_at"], row["response_id"]), reverse=True)
    summary = summarize(results, args.endpoint, args.expected_version, source)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"real-cases-{args.limit}-{args.label}"
    json_path = args.output_dir / f"{stem}.json"
    md_path = args.output_dir / f"{stem}.md"
    json_path.write_text(json.dumps({"summary": summary, "results": results}, indent=2, default=list) + "\n")
    md_path.write_text(markdown_report(summary, results))
    print(json.dumps(summary, indent=2))
    print(f"Wrote {json_path} and {md_path}", flush=True)
    if args.check:
        completed = summary["completed"]
        failures = []
        if completed != summary["requested"]:
            failures.append("not every prompt completed")
        if summary["version_confirmed"] != completed:
            failures.append("one or more responses used an unexpected version")
        if summary["region_mismatches"]:
            failures.append("one or more confident resolutions conflict with prompt anatomy")
        if summary["cases_with_empty_items"] or summary["cases_with_malformed_items"]:
            failures.append("empty or malformed content was emitted")
        if completed and summary["valid_resolution"] / completed < 0.90:
            failures.append("valid resolution fell below 90%")
        if (summary["utility_score"]["mean"] or 0) < 70:
            failures.append("mean utility score fell below 70")
        if failures:
            raise RuntimeError("Quality checks failed: " + "; ".join(failures))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
