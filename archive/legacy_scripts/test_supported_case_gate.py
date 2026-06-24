#!/usr/bin/env python3
"""
Tests for the supported-case gate (approach_router + main gating + limited payloads).

Covers:
- Unsupported (tibial shaft, random, forearm) -> supported=false, no GPT guess, no Miller (unless debug), limited payload.
- Supported (distal radius, carpal tunnel, posterior THA) -> supported=true, approach/quiz present, Miller runs.
- Manual_review / catalog gap (bimalleolar) -> supported=false (until catalog has lateral/medial).
- Debug override ANATOMY_ALLOW_UNSUPPORTED_RETRIEVAL=true bypasses Miller gate.
- Preserves general case-prep output.
- Flag-off legacy unchanged for unknowns (still gets GPT guess, but we test under true).

Uses TestClient + patches (no real OpenAI/Pinecone calls, no writes).
Saves reports/supported_case_gate_test_results.md + .json
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
import main
from approach_router import get_supported_case

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

CASES = {
    "unsupported_tibial": "tibial shaft fracture ORIF",
    "unsupported_random": "random ankle pain after soccer",
    "unsupported_forearm": "forearm pain no fracture",
    "supported_distal": "distal radius fracture ORIF",
    "supported_carpal": "carpal tunnel release",
    "supported_tha": "posterior THA",
    "gap_bimalleolar": "bimalleolar ankle fracture ORIF",  # manual_review in playbook, empty recs
}

RESULTS: List[Dict[str, Any]] = []

def _record(case: str, scenario: str, ok: bool, details: Dict[str, Any]):
    RESULTS.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "case": case,
        "scenario": scenario,
        "ok": ok,
        "details": details,
    })
    return ok

def _fake_legacy_supported() -> Dict[str, Any]:
    return {
        "approachSelection": {"selected": [{"id": "approach_wrist_volar_distal_henry", "confidence": 0.95, "rationale": "volar for DRF"}], "notes": ""},
        "anatomyQuiz": {"questions": [{"approach_id": "approach_wrist_volar_distal_henry", "q": "Nerve at risk?", "answer": "median (palmar cutaneous)", "tag": "nerve", "difficulty": 2}]},
        "router": {"case_family": "distal_radius_fracture_orif", "selectionMode": "deterministic_router", "supported": True},
    }

def _fake_miller(mode: str = "miller_gold_local") -> Dict[str, Any]:
    return {
        "approachSelection": None,
        "anatomyQuiz": None,
        "retrievalMode": mode,
        "limitedAnatomyContext": False,
        "relevantAnatomy": ["Volar Henry interval details from Miller gold."],
        "structuresAtRisk": ["Median nerve, radial artery."],
        "approachLandmarks": ["FCR tendon"],
        "highYieldFacts": ["Standard for most DRF ORIF."],
        "sources": [{"id": "miller-dr-1", "page": 120, "text": "volar approach..."}],
        "retrievalSummary": {"chunksUsed": 2, "mode": mode, "limited": False, "regions": ["wrist"], "warning": None},
    }

def _fake_legacy_unsupported() -> Dict[str, Any]:
    return {"approachSelection": None, "anatomyQuiz": {"questions": []}, "router": {"case_family": "unknown", "selectionMode": "unsupported_case_no_approach_guessing"}}

def run_tests():
    # Ensure startup
    if hasattr(main, "_startup"):
        main._startup()

    client = TestClient(main.app)

    # Force the new router (playbook) by env
    os.environ["ENABLE_LOCAL_ANATOMY_RAG"] = "true"

    # A. Unsupported cases (no guess, no Miller)
    for name, prompt in [("tibial", CASES["unsupported_tibial"]), ("random", CASES["unsupported_random"]), ("forearm", CASES["unsupported_forearm"])]:
        sc = get_supported_case(prompt)
        with patch("main.run_pipeline_fast", return_value=_fake_legacy_unsupported()), \
             patch("main.run_anatomy_miller_only", return_value={"retrievalMode": "miller_gold_local"}):
            resp = client.post("/anatomy", json={"prompt": prompt})
        data = resp.json() if resp.status_code == 200 else {}
        ok = (not sc.get("supported", True) and
              data.get("approachSelection") is None and
              data.get("retrievalMode") == "not_run_unsupported_case" and
              data.get("limitedAnatomyContext") is True)
        _record(prompt, f"A_unsupported_{name}", ok, {"supported_from_gate": sc.get("supported"), "mode": data.get("retrievalMode"), "approach_null": data.get("approachSelection") is None})

    # B. Supported cases (approach + quiz + Miller)
    for name, prompt in [("distal", CASES["supported_distal"]), ("carpal", CASES["supported_carpal"]), ("tha", CASES["supported_tha"])]:
        sc = get_supported_case(prompt)
        with patch("main.run_pipeline_fast", return_value=_fake_legacy_supported()), \
             patch("main.run_anatomy_miller_only", return_value=_fake_miller("miller_gold_local")):
            resp = client.post("/anatomy", json={"prompt": prompt})
        data = resp.json() if resp.status_code == 200 else {}
        ok = (sc.get("supported") and
              bool(data.get("approachSelection")) and
              bool(data.get("anatomyQuiz")) and
              data.get("retrievalMode") in ("miller_gold_local", "miller_gold_pinecone"))
        _record(prompt, f"B_supported_{name}", ok, {"supported_from_gate": sc.get("supported"), "mode": data.get("retrievalMode"), "has_approach": bool(data.get("approachSelection"))})

    # C. Manual review / catalog gap (bimalleolar) -> supported=false
    prompt = CASES["gap_bimalleolar"]
    sc = get_supported_case(prompt)
    with patch("main.run_pipeline_fast", return_value=_fake_legacy_unsupported()), \
         patch("main.run_anatomy_miller_only", return_value={"retrievalMode": "miller_gold_local"}):
        resp = client.post("/anatomy", json={"prompt": prompt})
    data = resp.json() if resp.status_code == 200 else {}
    ok = (not sc.get("supported") and
          data.get("retrievalMode") == "not_run_unsupported_case" and
          "manual_review" in (sc.get("reason") or "").lower() or "gap" in (sc.get("reason") or "").lower())
    _record(prompt, "C_gap_bimalleolar", ok, {"supported": sc.get("supported"), "reason": sc.get("reason"), "mode": data.get("retrievalMode")})

    # D. Debug override allows Miller for unsupported
    os.environ["ANATOMY_ALLOW_UNSUPPORTED_RETRIEVAL"] = "true"
    main.ANATOMY_ALLOW_UNSUPPORTED_RETRIEVAL = True  # if read at runtime
    prompt = CASES["unsupported_tibial"]
    sc = get_supported_case(prompt)
    with patch("main.run_pipeline_fast", return_value=_fake_legacy_unsupported()), \
         patch("main.run_anatomy_miller_only", return_value=_fake_miller("miller_gold_local")):
        resp = client.post("/anatomy", json={"prompt": prompt})
    data = resp.json() if resp.status_code == 200 else {}
    ok = (not sc.get("supported") and data.get("retrievalMode") == "miller_gold_local")
    _record(prompt, "D_debug_override_miller", ok, {"mode": data.get("retrievalMode")})
    del os.environ["ANATOMY_ALLOW_UNSUPPORTED_RETRIEVAL"]

    # E. Quick /case-prep compat (general fields still work, anatomy gated for unsupported)
    prompt = CASES["unsupported_tibial"]
    with patch("main.refine_query", lambda x: x), \
         patch("main.get_case_snippets", lambda x: [{"text": "generic", "score": 0.8}]), \
         patch("main.refine_case_snippets", return_value={"pimpQuestions": ["Q1"], "otherUsefulFacts": ["F1"]}), \
         patch("main.run_pipeline_fast", return_value=_fake_legacy_unsupported()), \
         patch("main.run_anatomy_miller_only", return_value={"retrievalMode": "not_run_unsupported_case", "limitedAnatomyContext": True}):
        resp = client.post("/case-prep", json={"prompt": prompt})
    data = resp.json() if resp.status_code == 200 else {}
    anatomy = data.get("anatomy") or {}
    ok = (len(data.get("pimpQuestions", [])) > 0 and
          len(data.get("otherUsefulFacts", [])) > 0 and
          anatomy.get("retrievalMode") == "not_run_unsupported_case")
    _record(prompt, "E_caseprep_unsupported", ok, {"has_pimp": len(data.get("pimpQuestions",[]))>0, "anatomy_mode": anatomy.get("retrievalMode")})

    # Write reports
    md_path = REPORTS_DIR / "supported_case_gate_test_results.md"
    json_path = REPORTS_DIR / "supported_case_gate_test_results.json"

    passed = sum(1 for r in RESULTS if r.get("ok"))
    total = len(RESULTS)

    with open(json_path, "w") as f:
        json.dump({"summary": {"total": total, "passed": passed, "failed": total-passed}, "results": RESULTS}, f, indent=2)

    md = ["# Supported Case Gate Test Results\n",
          f"Generated: {datetime.now(timezone.utc).isoformat()}\n",
          f"Total: {total} | Passed: {passed} | Failed: {total-passed}\n\n",
          "## Key assertions\n",
          "- Unsupported: supported=false, approachSelection null, retrievalMode=not_run_unsupported_case, limited=true\n",
          "- Supported: approach/quiz present, Miller runs with gold mode\n",
          "- Gap cases (manual_review/empty rec): supported=false\n",
          "- Debug var bypasses Miller gate\n",
          "- /case-prep pimp/other still present\n\n"]
    for r in RESULTS:
        st = "PASS" if r.get("ok") else "FAIL"
        md.append(f"- {st} | {r['scenario']} | {r['case'][:40]}... | {json.dumps(r['details'], ensure_ascii=False)[:200]}\n")
    md.append("\nSee JSON for full details.\n")

    with open(md_path, "w") as f:
        f.write("".join(md))

    print(f"Wrote {md_path} and {json_path}. Summary: {passed}/{total} passed")
    return passed == total

if __name__ == "__main__":
    ok = run_tests()
    sys.exit(0 if ok else 1)
