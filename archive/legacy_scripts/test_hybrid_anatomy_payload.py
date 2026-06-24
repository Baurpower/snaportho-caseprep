#!/usr/bin/env python3
"""
Hybrid Anatomy Payload Tests (legacy approach + Miller Gold).

Tests the combined behavior when ENABLE_LOCAL_ANATOMY_RAG=true.
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
import main

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

CASES = [
    "distal radius fracture ORIF",
    "ankle ORIF lateral malleolus",
    "posterior total hip arthroplasty",
    "carpal tunnel release",
    "cubital tunnel release",
    "rotator cuff repair",
]

def _check_hybrid(anatomy: Dict[str, Any], case: str) -> List[str]:
    errs = []
    if not isinstance(anatomy, dict):
        errs.append("anatomy not dict")
        return errs

    # Legacy approach fields should be present (even if partial)
    if "approachSelection" not in anatomy:
        errs.append("missing approachSelection (hybrid should preserve legacy)")
    if "anatomyQuiz" not in anatomy:
        errs.append("missing anatomyQuiz (hybrid should preserve legacy)")

    # Miller source-backed fields
    if "retrievalMode" not in anatomy:
        errs.append("missing retrievalMode")
    if "limitedAnatomyContext" not in anatomy:
        errs.append("missing limitedAnatomyContext")
    if "sources" not in anatomy:
        errs.append("missing sources")

    # anatomySystem for provenance
    if "anatomySystem" not in anatomy:
        errs.append("missing anatomySystem (provenance)")

    # sourceBackedAnatomy grouping (new recommended)
    if "sourceBackedAnatomy" in anatomy:
        sba = anatomy["sourceBackedAnatomy"]
        if not isinstance(sba, dict):
            errs.append("sourceBackedAnatomy not dict")
        elif "retrievalSummary" not in sba:
            errs.append("sourceBackedAnatomy missing retrievalSummary")

    return errs

def test_case(case: str, flag_on: bool = True) -> Dict[str, Any]:
    os.environ["ENABLE_LOCAL_ANATOMY_RAG"] = "true" if flag_on else "false"
    os.environ.setdefault("ANATOMY_BACKEND", "local")

    # Direct calls to avoid TestClient side-effects in this environment
    try:
        if flag_on:
            # Simulate hybrid path
            legacy = main.run_pipeline_fast(
                case_prompt=case,
                catalog=main.CATALOG,
                client=main.OPENAI_CLIENT,
            ) if hasattr(main, "CATALOG") else None
            miller = asyncio.get_event_loop().run_until_complete(
                main._run_miller_anatomy_only(case, os.environ.get("ANATOMY_BACKEND", "local"))
            ) if hasattr(main, "_run_miller_anatomy_only") else None
            anat = main.build_hybrid_anatomy(legacy, miller) if hasattr(main, "build_hybrid_anatomy") and main.build_hybrid_anatomy else (miller or legacy or {})
        else:
            anat = asyncio.get_event_loop().run_until_complete(
                main.run_in_threadpool(
                    main.run_pipeline_fast,
                    case_prompt=case,
                    catalog=getattr(main, "CATALOG", []),
                    client=getattr(main, "OPENAI_CLIENT", None),
                )
            )
    except Exception as e:
        anat = {"error": str(e)}

    # For case-prep simulation, just check that pimp path would still be there
    result = {
        "case": case,
        "flag_on": flag_on,
        "backend": os.environ.get("ANATOMY_BACKEND"),
        "anatomy": {
            "has_approachSelection": bool(anat.get("approachSelection")) if isinstance(anat, dict) else False,
            "has_anatomyQuiz": bool(anat.get("anatomyQuiz")) if isinstance(anat, dict) else False,
            "has_sources": bool(anat.get("sources")) if isinstance(anat, dict) else False,
            "retrievalMode": anat.get("retrievalMode") if isinstance(anat, dict) else None,
            "has_anatomySystem": bool(anat.get("anatomySystem")) if isinstance(anat, dict) else False,
        },
        "note": "Direct hybrid builder test (full /case-prep would also include pimp/other)",
    }
    print(f"{case}: approach={result['anatomy']['has_approachSelection']} quiz={result['anatomy']['has_anatomyQuiz']} sources={result['anatomy']['has_sources']} mode={result['anatomy']['retrievalMode']}")
    return result

def main():
    results = []
    for case in CASES:
        res = test_case(case, flag_on=True)
        results.append(res)

    # Also spot-check legacy-off
    legacy_res = test_case(CASES[0], flag_on=False)
    results.append(legacy_res)

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }

    json_path = REPORTS_DIR / "hybrid_approach_miller_anatomy_test_results.json"
    json_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    md_lines = ["# Hybrid Approach + Miller Gold Anatomy Test Results", "", f"Generated: {data['generated_at']}", ""]
    for r in results:
        md_lines.append(f"### {r['case']} (flag_on={r['flag_on']})")
        a = r["/anatomy"]
        cp = r["/case-prep"]
        md_lines.append(f"- /anatomy: approachSelection={a['has_approachSelection']}, anatomyQuiz={a['has_anatomyQuiz']}, sources={a['has_sources']}, mode={a['retrievalMode']}, errors={len(a.get('errors',[]))}")
        if cp.get("anatomy"):
            cpa = cp["anatomy"]
            md_lines.append(f"- /case-prep: pimp={cp['pimp_count']}, other={cp['other_count']}, approach={cpa['has_approachSelection']}, sources={cpa['has_sources']}")
        md_lines.append("")

    (REPORTS_DIR / "hybrid_approach_miller_anatomy_test_results.md").write_text("\n".join(md_lines), encoding="utf-8")
    print("Reports written.")

if __name__ == "__main__":
    main()
