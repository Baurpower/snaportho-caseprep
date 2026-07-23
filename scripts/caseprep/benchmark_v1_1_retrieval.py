#!/usr/bin/env python3
"""Run or score the CasePrep v1.1 Pocket Pimp retrieval benchmark."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from caseprep.evaluation.retrieval_benchmark import evaluate_case, summarize

DEFAULT_GOLD = ROOT / "data" / "caseprep" / "evaluation" / "pocket_pimp_retrieval_gold_v1.jsonl"


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def run_live(cases: List[Dict[str, Any]]) -> tuple[Dict[str, List[Dict[str, Any]]], Dict[str, int]]:
    from caseprep.services.ai_fallback import refine_prompt
    from caseprep.services.rag_retrieval_v1_1 import retrieve_case_qas

    results: Dict[str, List[Dict[str, Any]]] = {}
    latencies: Dict[str, int] = {}
    for case in cases:
        started = time.monotonic()
        refined = refine_prompt(case["prompt"])
        results[case["case_id"]] = retrieve_case_qas(refined)
        latencies[case["case_id"]] = int((time.monotonic() - started) * 1000)
    return results, latencies


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--results", type=Path, help="Previously captured JSON result map")
    parser.add_argument("--live", action="store_true", help="Query configured OpenAI/Pinecone services")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()
    if args.live == bool(args.results):
        parser.error("choose exactly one of --live or --results")

    cases = read_jsonl(args.gold)
    if args.live:
        candidates, latencies = run_live(cases)
    else:
        candidates = json.loads(args.results.read_text(encoding="utf-8"))
        latencies = {}
    per_case = [
        {
            **evaluate_case(case, candidates.get(case["case_id"], []), top_k=args.top_k),
            "latency_ms": latencies.get(case["case_id"]),
        }
        for case in cases
    ]
    report = {"summary": summarize(per_case), "cases": per_case}
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
