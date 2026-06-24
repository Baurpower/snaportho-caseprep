#!/usr/bin/env python3
"""
Phase 2: Validate the Miller gold anatomy corpus for safe Pinecone upsert.

- Loads the local copy of gold JSONL.
- Checks all required properties for pinecone-ready upload to namespace.
- Outputs detailed report (no secrets).

Usage:
  python scripts/validate_anatomy_pinecone_payload.py

Env (optional, for report):
  ANATOMY_PINECONE_NAMESPACE (defaults to anatomy_miller_gold_v1)
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
GOLD_PATH = BASE_DIR / "data" / "anatomy_miller_gold_v1" / "anatomy_gold_v1_pinecone_ready.jsonl"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_NAMESPACE = "anatomy_miller_gold_v1"

def load_records(path: Path) -> List[Dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                records.append(rec)
            except Exception as e:
                raise ValueError(f"Invalid JSON on line {i}: {e}")
    return records

def validate(records: List[Dict[str, Any]], namespace: str) -> Dict[str, Any]:
    issues: List[str] = []
    warnings: List[str] = []
    stats = {
        "total_records": len(records),
        "unique_ids": 0,
        "ids_with_text": 0,
        "ids_with_source_quote": 0,
        "ids_with_page": 0,
        "quality_tiers": {},
        "regions": {},
        "has_question_form": 0,
        "has_qc_fields": 0,
        "max_metadata_size_est": 0,
    }

    ids_seen = set()
    for i, rec in enumerate(records):
        rid = rec.get("id")
        if not rid:
            issues.append(f"Record {i}: missing id")
            continue
        if rid in ids_seen:
            issues.append(f"Duplicate id: {rid}")
        ids_seen.add(rid)

        text = rec.get("text") or ""
        if not text or len(text) < 5:
            issues.append(f"{rid}: missing or too-short 'text' field")
        else:
            stats["ids_with_text"] += 1

        if rec.get("source_quote"):
            stats["ids_with_source_quote"] += 1
        if rec.get("page") is not None:
            stats["ids_with_page"] += 1

        if "question_form" in rec or "answer_form" in rec:
            stats["has_question_form"] += 1
            issues.append(f"{rid}: contains question_form/answer_form (should be statement-only)")

        # Check for leftover QC/debug
        qc_like = [k for k in rec if any(x in k.lower() for x in ["qc", "gold_qc", "donor", "review", "holdout"])]
        if qc_like:
            stats["has_qc_fields"] += 1
            warnings.append(f"{rid}: has QC/debug fields {qc_like} (should be stripped in pinecone_ready)")

        meta = rec.get("metadata") or {}
        qt = meta.get("quality_tier") or "unknown"
        stats["quality_tiers"][qt] = stats["quality_tiers"].get(qt, 0) + 1

        region = meta.get("region") or "unknown"
        stats["regions"][region] = stats["regions"].get(region, 0) + 1

        # Rough metadata size (for Pinecone 40KB limit warning)
        try:
            meta_str = json.dumps(meta, ensure_ascii=False)
            size = len(meta_str.encode("utf-8"))
            if size > stats["max_metadata_size_est"]:
                stats["max_metadata_size_est"] = size
            if size > 30000:  # rough
                warnings.append(f"{rid}: metadata ~{size} bytes (close to Pinecone limits)")
        except Exception:
            warnings.append(f"{rid}: metadata not JSON serializable")

    stats["unique_ids"] = len(ids_seen)

    # Required display / retrieval fields at top level (per pinecone_ready)
    required_top = ["id", "text", "source_quote", "page", "section_path", "heading", "source", "corpus_version"]
    for rec in records[:5]:  # sample
        for k in required_top:
            if k not in rec:
                issues.append(f"Sample record missing top-level required field for display: {k}")
                break

    # Namespace
    effective_ns = os.getenv("ANATOMY_PINECONE_NAMESPACE", namespace)
    if effective_ns != namespace:
        warnings.append(f"ANATOMY_PINECONE_NAMESPACE={effective_ns} (expected {namespace})")

    # Final verdict
    if stats["has_question_form"] > 0:
        issues.append("Corpus contains question/answer forms — not suitable for pure fact retrieval")
    if stats["has_qc_fields"] > 0:
        warnings.append("Some records still carry QC fields (pinecone_ready should have stripped them)")

    passed = len(issues) == 0

    return {
        "passed": passed,
        "issues": issues,
        "warnings": warnings,
        "stats": stats,
        "namespace": effective_ns,
        "gold_path": str(GOLD_PATH),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

def main():
    namespace = os.getenv("ANATOMY_PINECONE_NAMESPACE", DEFAULT_NAMESPACE)
    print(f"Validating gold corpus for Pinecone namespace: {namespace}")
    print(f"Source: {GOLD_PATH}")

    if not GOLD_PATH.exists():
        print(f"❌ Gold file not found: {GOLD_PATH}")
        sys.exit(1)

    records = load_records(GOLD_PATH)
    print(f"Loaded {len(records)} records")

    result = validate(records, namespace)

    # Write report
    report_path = REPORTS_DIR / "phase2_anatomy_pinecone_payload_validation.md"
    lines = [
        "# Phase 2 Anatomy Pinecone Payload Validation",
        "",
        f"**Checked**: {result['checked_at']}",
        f"**Gold source**: {result['gold_path']}",
        f"**Target namespace**: {result['namespace']}",
        f"**Verdict**: {'✅ PASS' if result['passed'] else '❌ FAIL'}",
        "",
        "## Stats",
        f"- Total records: {result['stats']['total_records']}",
        f"- Unique IDs: {result['stats']['unique_ids']}",
        f"- With 'text': {result['stats']['ids_with_text']}",
        f"- With source_quote: {result['stats']['ids_with_source_quote']}",
        f"- With page: {result['stats']['ids_with_page']}",
        f"- Max metadata size est (bytes): {result['stats']['max_metadata_size_est']}",
        "",
        "### Quality Tiers",
    ]
    for k, v in sorted(result['stats']['quality_tiers'].items()):
        lines.append(f"- {k}: {v}")

    lines.append("")
    lines.append("### Regions (top)")
    sorted_regions = sorted(result['stats']['regions'].items(), key=lambda x: -x[1])[:10]
    for k, v in sorted_regions:
        lines.append(f"- {k}: {v}")

    if result['issues']:
        lines.append("")
        lines.append("## Issues (must fix)")
        for iss in result['issues']:
            lines.append(f"- {iss}")

    if result['warnings']:
        lines.append("")
        lines.append("## Warnings")
        for w in result['warnings']:
            lines.append(f"- {w}")

    lines.append("")
    if result['passed']:
        lines.append("✅ Payload is ready for dry-run upload to the anatomy namespace.")
        lines.append("Run the upsert script in --dry-run mode next.")
    else:
        lines.append("❌ Payload validation failed. Fix issues before any upload.")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written: {report_path}")

    # Also print summary to stdout
    print(f"\nVerdict: {'PASS' if result['passed'] else 'FAIL'}")
    print(f"Issues: {len(result['issues'])}, Warnings: {len(result['warnings'])}")

    if not result['passed']:
        sys.exit(2)

if __name__ == "__main__":
    main()
