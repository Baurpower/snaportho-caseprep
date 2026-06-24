# Anatomy Runtime Wiring Fix - Test Results
**Generated**: 2026-06-06T01:42:01.465735+00:00
**Total tests**: 9 | **Passed**: 9 | **Failed**: 0

## Scenarios
- A: ENABLE=false (legacy path)
- B: ENABLE=true + ANATOMY_BACKEND=local
- C: ENABLE=true + ANATOMY_BACKEND=pinecone (simulated via patch)
- D: partial failures + case-prep smoke

## Per-case results
- ✅ PASS | A_flag_off_legacy | bimalleolar ankle fracture ORIF
  details: {"status": 200, "has_approach": true, "has_quiz": true, "mode": "n/a", "sample_keys": ["approachSelection", "anatomyQuiz", "router"]}
- ✅ PASS | A_flag_off_legacy | distal radius fracture ORIF
  details: {"status": 200, "has_approach": true, "has_quiz": true, "mode": "n/a", "sample_keys": ["approachSelection", "anatomyQuiz", "router"]}
- ✅ PASS | B_flag_on_local | bimalleolar ankle fracture ORIF
  details: {"status": 200, "has_approach": true, "has_quiz": true, "mode": "miller_gold_local"}
- ✅ PASS | B_flag_on_local | distal radius fracture ORIF
  details: {"status": 200, "has_approach": true, "has_quiz": true, "mode": "miller_gold_local"}
- ✅ PASS | C_flag_on_pinecone | posterior THA
  details: {"status": 200, "has_approach": true, "has_quiz": true, "mode": "miller_gold_pinecone"}
- ✅ PASS | C_flag_on_pinecone | carpal tunnel release
  details: {"status": 200, "has_approach": true, "has_quiz": true, "mode": "miller_gold_pinecone"}
- ✅ PASS | D1_miller_fail_legacy_ok | bimalleolar ankle fracture ORIF
  details: {"status": 200, "has_approach": true, "has_quiz": true, "retrievalMode": "unavailable"}
- ✅ PASS | D2_legacy_fail_miller_ok | bimalleolar ankle fracture ORIF
  details: {"status": 200, "retrievalMode": "miller_gold_local", "has_sources": true}
- ✅ PASS | D3_caseprep_hybrid_smoke | bimalleolar ankle fracture ORIF
  details: {"status": 200, "has_pimp": true, "mode": "miller_gold_local"}

## Raw JSON
See anatomy_runtime_wiring_fix_test_results.json
