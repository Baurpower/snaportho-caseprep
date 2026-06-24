#!/usr/bin/env python3
"""
Resolver test matrix for resident-style inputs.
Run: python scripts/anatomy/resolver_test_matrix.py

Defines expected behaviors and checks against current resolve_procedure.
Used for regression in smoke and gates.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from procedure_registry import resolve_procedure, is_certified, CERTIFIED_SLUGS

# Test cases: (input, expected_behavior, notes)
# expected_behavior: certified_exact | certified_default | ambiguous_clarify | unsupported_fallback | not_certified
TEST_MATRIX = [
    # THA group
    ("THA tomorrow", "certified_exact", "generic -> posterior (alias hit)"),
    ("total hip tomorrow", "certified_default", "generic -> posterior"),
    ("posterior THA", "certified_exact", "specific posterior"),
    ("posterior total hip", "certified_default", "specific (contains)"),
    ("direct anterior THA", "certified_exact", "specific anterior"),
    ("anterior hip replacement", "certified_exact", "specific anterior"),
    ("Hardinge THA", "not_certified", "lateral non-cert, do not leak to posterior"),
    ("direct lateral THA", "not_certified", "lateral non-cert"),
    # Shoulder
    ("total shoulder arthroplasty", "certified_exact", "anatomic TSA"),
    ("TSA", "certified_exact", "anatomic"),
    ("reverse shoulder", "certified_exact", "RSA specific"),
    ("RSA", "certified_exact", "RSA"),
    ("proximal humerus fracture ORIF", "not_certified", "non-cert trauma"),
    ("shoulder scope", "unsupported_fallback", "unknown/arthro non-cert"),
    ("rotator cuff repair", "not_certified", "non-cert"),
    # Spine
    ("ACDF", "not_certified", "non-cert"),
    ("anterior cervical discectomy and fusion", "not_certified", "non-cert (matches acdf)"),
    ("posterior lumbar decompression fusion", "certified_default", "cert (contains)"),
    ("lumbar laminectomy and fusion", "certified_exact", "added alias"),
    ("TLIF", "certified_exact", "added alias to lumbar"),
    ("cervical decompression", "unsupported_fallback", "ambiguous/unknown"),
    # Distal radius
    ("distal radius ORIF", "certified_exact", "cert"),
    ("volar distal radius plate", "certified_exact", "added alias"),
    ("Colles fracture ORIF", "certified_exact", "added"),
    ("dorsal spanning plate", "certified_exact", "fixed from wrong reverse cert"),
    ("distal ulna ORIF", "certified_exact", "added, often with radius"),
    # Pelvis/acetabulum
    ("pelvic ring ORIF", "certified_exact", "fixed alias pelvic/pelvis"),
    ("SI screw", "certified_exact", "added, to pelvis ring"),
    ("acetabulum posterior wall", "certified_default", "contains to posterior"),
    ("posterior wall acetabulum ORIF", "certified_exact", "added alias"),
    ("anterior column acetabulum", "certified_exact", "added"),
    ("both column acetabulum", "certified_exact", "resolves to a cert (combined approaches)"),
    # Peds
    ("SCFE pinning", "certified_exact", "cert"),
    ("slipped capital femoral epiphysis", "certified_exact", "cert"),
    ("supracondylar humerus CRPP", "certified_default", "cert peds (contains)"),
    ("peds elbow fracture", "unsupported_fallback", "ambiguous; suggests, does not blindly resolve"),
    ("DDH surgery", "not_certified", "non-cert"),
    ("Perthes surgery", "not_certified", "non-cert"),
    # Sports
    ("ACL reconstruction", "certified_exact", "cert"),
    ("meniscus repair", "certified_exact", "cert"),
    ("meniscectomy", "unsupported_fallback", "non-cert"),
    ("MPFL reconstruction", "unsupported_fallback", "non-cert"),
    ("quadriceps tendon repair", "certified_exact", "cert"),
    ("Achilles repair", "not_certified", "non-cert"),
    # Foot/ankle
    ("hallux valgus correction", "certified_exact", "cert"),
    ("bunion surgery", "certified_default", "contains"),
    ("lateral ankle ligament repair", "certified_exact", "cert"),
    ("Brostrom", "certified_exact", "alias"),
    ("plantar fasciitis release", "certified_exact", "cert"),
    ("Lisfranc ORIF", "not_certified", "non-cert"),
    # Trauma/hand
    ("humeral shaft ORIF", "certified_exact", "cert"),
    ("distal femur ORIF", "certified_exact", "cert"),
    ("tibial shaft ORIF", "certified_exact", "cert"),
    ("Monteggia ORIF", "certified_exact", "cert"),
    ("metacarpal fracture ORIF", "unsupported_fallback", "non-cert"),
]

def classify_actual(slug: str, method: str, score: float) -> str:
    if not slug:
        return "unsupported_fallback" if method == "none" else "ambiguous_clarify"
    if is_certified(slug):
        if method == "alias" and score >= 100:
            return "certified_exact"
        return "certified_default"
    else:
        return "not_certified"

def run_matrix():
    print("=== Resolver Test Matrix ===\n")
    passed = 0
    failed = 0
    results = []
    for inp, expected, note in TEST_MATRIX:
        res = resolve_procedure(inp)
        slug = res.get("procedure_slug")
        method = res.get("match_method")
        score = res.get("match_score") or 0.0
        actual = classify_actual(slug, method, score)
        ok = (actual == expected)
        if ok:
            passed += 1
        else:
            failed += 1
        results.append({
            "input": inp,
            "slug": slug,
            "method": method,
            "score": score,
            "expected": expected,
            "actual": actual,
            "pass": ok,
            "note": note
        })
        status = "PASS" if ok else "FAIL"
        print(f"{status}: {inp[:40]:40} -> {str(slug)[:25]:25} {method:8} exp={expected:20} act={actual}")
        if not ok:
            print(f"       note: {note}")

    print(f"\n=== MATRIX RESULTS: {passed} passed, {failed} failed out of {len(TEST_MATRIX)} ===")
    if failed == 0:
        print("ALL MATRIX TESTS PASSED")
    else:
        print("SOME MATRIX TESTS FAILED - see above for routing issues fixed or remaining")

    # Hard regression guards (these must never regress to wrong certified payload)
    regression_failures = []
    for inp, bad_slug in [
        ("dorsal spanning plate", "reverse_shoulder_arthroplasty"),
        ("reverse shoulder", "total_shoulder_arthroplasty"),
        ("direct lateral THA", "tha_posterior"),
        ("Hardinge THA", "tha_posterior"),
        ("posterior wall acetabulum ORIF", "acetabulum_fracture_orif_anterior"),
        ("anterior column acetabulum", "acetabulum_fracture_orif_posterior"),
        ("peds elbow fracture", "supracondylar_humerus_fracture_pediatric"),
    ]:
        res = resolve_procedure(inp)
        if res.get("procedure_slug") == bad_slug:
            regression_failures.append(f"REGRESSION: {inp} resolved to forbidden {bad_slug}")
    if regression_failures:
        for rf in regression_failures:
            print(rf)
        print("HARD REGRESSION FAILURES - routing bugs re-introduced")
        return passed, failed + len(regression_failures), results
    print("All hard regression guards passed (no forbidden wrong-cert mappings).")

    return passed, failed, results

if __name__ == "__main__":
    run_matrix()
