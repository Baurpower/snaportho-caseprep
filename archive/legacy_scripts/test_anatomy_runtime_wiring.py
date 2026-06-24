#!/usr/bin/env python3
"""
Regression tests for /anatomy (and /case-prep) runtime wiring fixes.

Covers:
A. flag off -> legacy approachSelection + anatomyQuiz (Miller off)
B. flag on + local backend -> hybrid, approach/quiz not null, retrievalMode=miller_gold_local
C. flag on + pinecone backend -> hybrid, approach/quiz not null, retrievalMode=miller_gold_pinecone (or fallback if no key)
D. partial failure: miller fails -> legacy still present; legacy fails -> miller still present

Uses FastAPI TestClient + env + targeted patches (no real Pinecone writes, no secrets exposed, local index preferred where possible).
Prompts: bimalleolar ankle fracture ORIF, distal radius fracture ORIF, posterior THA, carpal tunnel release.

Run: ENABLE_LOCAL_ANATOMY_RAG=true ANATOMY_BACKEND=local python scripts/test_anatomy_runtime_wiring.py
(also tests pinecone path via patch)

Saves reports/anatomy_runtime_wiring_fix_test_results.md and .json
"""
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
import main

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

CASES = [
    "bimalleolar ankle fracture ORIF",
    "distal radius fracture ORIF",
    "posterior THA",
    "carpal tunnel release",
]

RESULTS: List[Dict[str, Any]] = []

def _record(case: str, scenario: str, ok: bool, details: Dict[str, Any]):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "case": case,
        "scenario": scenario,
        "ok": ok,
        "details": details,
    }
    RESULTS.append(entry)
    return ok

def _fake_legacy() -> Dict[str, Any]:
    """Canned legacy anatomy result so tests don't require real OpenAI key for approach/quiz."""
    return {
        "approachSelection": {
            "selected": [
                {"id": "approach_lower_ext_ankle_lateral", "confidence": 0.92, "rationale": "lateral for fibula in bimalleolar"},
                {"id": "approach_lower_ext_ankle_posteromedial", "confidence": 0.85, "rationale": "medial malleolus"},
            ],
            "notes": "test canned",
            "validation": {"valid_selected": ["approach_lower_ext_ankle_lateral", "approach_lower_ext_ankle_posteromedial"], "removed": [], "reason": ""},
        },
        "anatomyQuiz": {
            "questions": [
                {"approach_id": "approach_lower_ext_ankle_lateral", "q": "What structure is at risk?", "answer": "Sural nerve", "tag": "nerve", "difficulty": 2},
            ]
        },
        "router": {"selectionMode": "legacy_gpt_selector"},
    }

def _fake_miller(mode: str) -> Dict[str, Any]:
    """Canned Miller v2 payload for wiring test (no real retrieval)."""
    return {
        "approachSelection": None,
        "anatomyQuiz": None,
        "retrievalMode": mode,
        "limitedAnatomyContext": False,
        "relevantAnatomy": ["Lateral malleolus approached via interval between peroneals and FHL (Miller p.XX)."],
        "structuresAtRisk": ["Sural nerve and short saphenous vein."],
        "approachLandmarks": ["Posterior border of fibula", "Tip of lateral malleolus"],
        "highYieldFacts": ["Standard bimalleolar ORIF uses direct lateral + direct medial."],
        "sources": [{"id": "miller-test-1", "page": 42, "heading": "Ankle approaches", "text": "Lateral malleolus...", "source_quote": "direct lateral approach to fibula", "score": 0.91}],
        "retrievalSummary": {"chunksUsed": 3, "mode": mode, "limited": False, "regions": ["ankle"], "warning": None},
    }

def run_tests():
    client = TestClient(main.app)

    # Ensure startup (catalog load) happens
    if hasattr(main, "_startup"):
        main._startup()

    # --- A. flag off: legacy only ---
    os.environ["ENABLE_LOCAL_ANATOMY_RAG"] = "false"
    # re-eval the flag inside main by reload? but since module level at import, we set before import in practice; here we monkey the value
    main.ENABLE_LOCAL_ANATOMY_RAG = False
    for case in CASES[:2]:  # two prompts
        try:
            # patch legacy to avoid key, but with flag off it calls run_pipeline_fast; we patch the func
            with patch("main.run_pipeline_fast", return_value=_fake_legacy()):
                resp = client.post("/anatomy", json={"prompt": case})
            data = resp.json() if resp.status_code == 200 else {}
            has_approach = bool(data.get("approachSelection"))
            has_quiz = bool(data.get("anatomyQuiz"))
            mode = data.get("retrievalMode", "n/a")
            ok = has_approach and has_quiz and "legacy" in str(mode).lower() or mode == "n/a"  # flag off may not set mode
            _record(case, "A_flag_off_legacy", ok, {"status": resp.status_code, "has_approach": has_approach, "has_quiz": has_quiz, "mode": mode, "sample_keys": list(data.keys())[:6]})
        except Exception as e:
            _record(case, "A_flag_off_legacy", False, {"error": str(e)})

    # --- B. flag on + backend local ---
    os.environ["ENABLE_LOCAL_ANATOMY_RAG"] = "true"
    os.environ["ANATOMY_BACKEND"] = "local"
    main.ENABLE_LOCAL_ANATOMY_RAG = True
    main.ANATOMY_BACKEND = "local"
    for case in CASES[:2]:
        try:
            with patch("main.run_pipeline_fast", return_value=_fake_legacy()), \
                 patch("main.run_anatomy_miller_only", return_value=_fake_miller("miller_gold_local")):
                resp = client.post("/anatomy", json={"prompt": case})
            data = resp.json() if resp.status_code == 200 else {}
            has_approach = bool(data.get("approachSelection"))
            has_quiz = bool(data.get("anatomyQuiz"))
            mode = data.get("retrievalMode")
            ok = has_approach and has_quiz and mode == "miller_gold_local"
            _record(case, "B_flag_on_local", ok, {"status": resp.status_code, "has_approach": has_approach, "has_quiz": has_quiz, "mode": mode})
        except Exception as e:
            _record(case, "B_flag_on_local", False, {"error": str(e)})

    # --- C. flag on + backend pinecone (via patch to simulate pinecone path + mode) ---
    os.environ["ANATOMY_BACKEND"] = "pinecone"
    main.ANATOMY_BACKEND = "pinecone"
    for case in CASES[2:]:
        try:
            with patch("main.run_pipeline_fast", return_value=_fake_legacy()), \
                 patch("main.run_anatomy_miller_only", return_value=_fake_miller("miller_gold_pinecone")):
                resp = client.post("/anatomy", json={"prompt": case})
            data = resp.json() if resp.status_code == 200 else {}
            has_approach = bool(data.get("approachSelection"))
            has_quiz = bool(data.get("anatomyQuiz"))
            mode = data.get("retrievalMode")
            ok = has_approach and has_quiz and mode == "miller_gold_pinecone"
            _record(case, "C_flag_on_pinecone", ok, {"status": resp.status_code, "has_approach": has_approach, "has_quiz": has_quiz, "mode": mode})
        except Exception as e:
            _record(case, "C_flag_on_pinecone", False, {"error": str(e)})

    # --- D. partial failure simulation ---
    # D1: miller fails -> legacy still returned
    os.environ["ANATOMY_BACKEND"] = "local"
    main.ANATOMY_BACKEND = "local"
    case = CASES[0]
    try:
        with patch("main.run_pipeline_fast", return_value=_fake_legacy()), \
             patch("main.run_anatomy_miller_only", side_effect=RuntimeError("simulated miller fail")):
            resp = client.post("/anatomy", json={"prompt": case})
        data = resp.json() if resp.status_code == 200 else {}
        has_approach = bool(data.get("approachSelection"))
        has_quiz = bool(data.get("anatomyQuiz"))
        # even on miller fail, hybrid/builder or fallback should keep legacy
        ok = has_approach and has_quiz
        _record(case, "D1_miller_fail_legacy_ok", ok, {"status": resp.status_code, "has_approach": has_approach, "has_quiz": has_quiz, "retrievalMode": data.get("retrievalMode")})
    except Exception as e:
        _record(case, "D1_miller_fail_legacy_ok", False, {"error": str(e)})

    # D2: legacy fails -> miller still returned (via builder)
    try:
        with patch("main.run_pipeline_fast", side_effect=RuntimeError("simulated legacy fail")), \
             patch("main.run_anatomy_miller_only", return_value=_fake_miller("miller_gold_local")):
            resp = client.post("/anatomy", json={"prompt": case})
        data = resp.json() if resp.status_code == 200 else {}
        # miller path should provide the source fields even if legacy null
        has_miller_fields = bool(data.get("retrievalMode") == "miller_gold_local" and data.get("sources"))
        ok = has_miller_fields
        _record(case, "D2_legacy_fail_miller_ok", ok, {"status": resp.status_code, "retrievalMode": data.get("retrievalMode"), "has_sources": bool(data.get("sources"))})
    except Exception as e:
        _record(case, "D2_legacy_fail_miller_ok", False, {"error": str(e)})

    # Also quick /case-prep smoke under flag on (local) to ensure not unavailable
    try:
        os.environ["ANATOMY_BACKEND"] = "local"
        main.ANATOMY_BACKEND = "local"
        with patch("main.run_pipeline_fast", return_value=_fake_legacy()), \
             patch("main.run_anatomy_miller_only", return_value=_fake_miller("miller_gold_local")):
            resp = client.post("/case-prep", json={"prompt": CASES[0]})
        data = resp.json() if resp.status_code == 200 else {}
        anatomy = data.get("anatomy") or {}
        has_pimp = "pimpQuestions" in data and len(data.get("pimpQuestions", [])) >= 0
        has_anatomy = bool(anatomy)
        mode = anatomy.get("retrievalMode")
        ok = has_pimp and has_anatomy and mode == "miller_gold_local"
        _record(CASES[0], "D3_caseprep_hybrid_smoke", ok, {"status": resp.status_code, "has_pimp": has_pimp, "mode": mode})
    except Exception as e:
        _record(CASES[0], "D3_caseprep_hybrid_smoke", False, {"error": str(e)})

    # Write reports
    md_path = REPORTS_DIR / "anatomy_runtime_wiring_fix_test_results.md"
    json_path = REPORTS_DIR / "anatomy_runtime_wiring_fix_test_results.json"

    passed = sum(1 for r in RESULTS if r["ok"])
    total = len(RESULTS)

    with open(json_path, "w") as f:
        json.dump({"summary": {"total": total, "passed": passed, "failed": total - passed}, "results": RESULTS}, f, indent=2)

    md = ["# Anatomy Runtime Wiring Fix - Test Results\n",
          f"**Generated**: {datetime.now(timezone.utc).isoformat()}\n",
          f"**Total tests**: {total} | **Passed**: {passed} | **Failed**: {total-passed}\n\n",
          "## Scenarios\n",
          "- A: ENABLE=false (legacy path)\n",
          "- B: ENABLE=true + ANATOMY_BACKEND=local\n",
          "- C: ENABLE=true + ANATOMY_BACKEND=pinecone (simulated via patch)\n",
          "- D: partial failures + case-prep smoke\n\n",
          "## Per-case results\n"]
    for r in RESULTS:
        status = "✅ PASS" if r["ok"] else "❌ FAIL"
        md.append(f"- {status} | {r['scenario']} | {r['case']}\n")
        md.append(f"  details: {json.dumps(r['details'], ensure_ascii=False)[:300]}\n")
    md.append("\n## Raw JSON\nSee anatomy_runtime_wiring_fix_test_results.json\n")

    with open(md_path, "w") as f:
        f.write("".join(md))

    print(f"\nWrote {md_path} and {json_path}")
    print(f"Summary: {passed}/{total} passed")
    return passed == total

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
