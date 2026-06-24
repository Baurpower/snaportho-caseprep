#!/usr/bin/env python3
"""
Approach Router Safety Tests + End-to-End checks against anatomy_gpt.

Covers the critical bimalleolar case and several others.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from approach_router import route_approaches, validate_selected_approaches
from anatomy_gpt import run_pipeline_fast, load_catalog_from_jsonl_file

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Load the real catalog once (same as main does)
CATALOG = []
try:
    CATALOG.extend(load_catalog_from_jsonl_file(
        str(Path(__file__).parent.parent / "data" / "upper_extremity" / "approaches" / "upper_extremity_approaches.jsonl")
    ))
    CATALOG.extend(load_catalog_from_jsonl_file(
        str(Path(__file__).parent.parent / "data" / "lower_extremity" / "approaches" / "lower_extremity_approaches.jsonl")
    ))
except Exception as e:
    print(f"WARNING: could not load full catalog for E2E tests: {e}")

TEST_CASES = [
    {
        "name": "bimalleolar ankle fracture ORIF",
        "prompt": "bimalleolar ankle fracture ORIF",
        "expected_blocked_contains": ["approach_lower_ext_ankle_anterior"],
        "expected_family": "ankle_fracture_orif",
    },
    {
        "name": "trimalleolar ankle fracture ORIF with posterior malleolus",
        "prompt": "trimalleolar ankle fracture ORIF posterior malleolus",
        "expected_family": "ankle_fracture_orif",
    },
    {
        "name": "distal radius fracture ORIF",
        "prompt": "distal radius fracture ORIF",
        "expected_allowed_contains": ["approach_wrist_volar_distal_henry"],
        "expected_family": "distal_radius_orif",
    },
    {
        "name": "carpal tunnel release",
        "prompt": "carpal tunnel release",
        "expected_allowed_contains": ["approach_wrist_carpal_tunnel"],
        "expected_family": "carpal_tunnel_release",
    },
    {
        "name": "posterior THA",
        "prompt": "posterior total hip arthroplasty",
        "expected_allowed_contains": ["approach_lower_ext_hip_posterior_moore_southern"],
        "expected_family": "posterior_tha",
    },
    {
        "name": "anterior THA",
        "prompt": "direct anterior total hip arthroplasty",
        "expected_allowed_contains": ["approach_lower_ext_hip_anterior_smith_peterson"],
        "expected_family": "anterior_tha",
    },
    {
        "name": "ambiguous ankle pain (no ORIF)",
        "prompt": "chronic ankle pain and instability",
        "expected_family": "unknown",
    },
]

def run_router_tests() -> List[Dict[str, Any]]:
    results = []
    for tc in TEST_CASES:
        r = route_approaches(tc["prompt"])
        blocked = r.get("blocked_approach_ids", [])
        allowed = r.get("allowed_approach_ids", [])
        family = r.get("case_family")

        blocked_ok = True
        if "expected_blocked_contains" in tc:
            for bad in tc["expected_blocked_contains"]:
                if bad not in blocked:
                    blocked_ok = False

        allowed_ok = True
        if "expected_allowed_contains" in tc:
            for good in tc["expected_allowed_contains"]:
                if good not in allowed:
                    allowed_ok = False

        family_ok = family == tc.get("expected_family")

        res = {
            "case": tc["name"],
            "prompt": tc["prompt"],
            "router": r,
            "checks": {
                "family_match": family_ok,
                "blocked_safety": blocked_ok,
                "allowed_present": allowed_ok,
            },
            "pass": family_ok and blocked_ok and allowed_ok,
        }
        results.append(res)
        print(f"{tc['name']}: family={family} pass={res['pass']}")
    return results

def run_e2e_with_gpt() -> List[Dict[str, Any]]:
    """End-to-end through the (now router-aware) legacy selector."""
    if not CATALOG:
        return [{"error": "catalog not loaded"}]

    e2e = []
    for tc in TEST_CASES[:4]:  # a few representative ones
        try:
            sel = run_pipeline_fast(
                case_prompt=tc["prompt"],
                catalog=CATALOG,
                n_min=1,
                n_max=2,
            )
            approach_sel = sel.get("approachSelection", {})
            selected = [x.get("id") for x in approach_sel.get("selected", [])]
            router_meta = approach_sel.get("router", {})
            validation = approach_sel.get("validation", {})

            bad_selected = []
            if "expected_blocked_contains" in tc:
                for bad in tc["expected_blocked_contains"]:
                    if bad in selected:
                        bad_selected.append(bad)

            res = {
                "case": tc["name"],
                "selected_ids": selected,
                "router_family": router_meta.get("case_family"),
                "selectionMode": router_meta.get("selectionMode"),
                "blocked_by_router": router_meta.get("blockedApproachIds", []),
                "validation_removed": [r["id"] for r in validation.get("removed", [])],
                "bad_approaches_still_selected": bad_selected,
                "pass": len(bad_selected) == 0,
            }
            e2e.append(res)
            print(f"E2E {tc['name']}: selected={selected} bad={bad_selected} pass={res['pass']}")
        except Exception as e:
            e2e.append({"case": tc["name"], "error": str(e)})
    return e2e

def main():
    router_results = run_router_tests()
    e2e_results = run_e2e_with_gpt()

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "router_tests": router_results,
        "e2e_gpt_tests": e2e_results,
    }

    json_path = REPORTS_DIR / "approach_router_test_results.json"
    json_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    md_lines = [
        "# Approach Router + Safety Validation Test Results",
        "",
        f"Generated: {data['generated_at']}",
        "",
        "## Router-only tests",
    ]
    for r in router_results:
        status = "PASS" if r.get("pass") else "FAIL"
        md_lines.append(f"- {r['case']}: {status} family={r['router'].get('case_family')}")

    md_lines.append("")
    md_lines.append("## End-to-end (router-aware GPT selector)")
    for r in e2e_results:
        if "error" in r:
            md_lines.append(f"- {r['case']}: ERROR {r['error']}")
            continue
        status = "PASS" if r.get("pass") else "FAIL"
        md_lines.append(f"- {r['case']}: {status} selected={r.get('selected_ids')} bad={r.get('bad_approaches_still_selected')}")

    (REPORTS_DIR / "approach_router_test_results.md").write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\nReports written to {REPORTS_DIR}")

if __name__ == "__main__":
    main()
