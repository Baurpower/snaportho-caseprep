# Supported Case Gate Implementation

**Files edited**:
- approach_router.py (primary: new get_supported_case + playbook loader + compat wrappers)
- anatomy_gpt.py (import get_supported_case; enhanced router pre-filter + short-circuit for !supported when ENABLE=true)
- main.py (import; gate logic in case_prep + anatomy_only ENABLE blocks; _unsupported_miller_payload helper; conditional calls to legacy/Miller)
- hybrid_anatomy_builder.py (updated build_hybrid to preserve special unsupported anatomySystem + mode)
- scripts/test_supported_case_gate.py (new)
- reports/anatomy_supported_case_gate_audit.md, supported_case_gate_test_results.{md,json}, supported_case_gate_caseprep_smoke.md, supported_case_gate_implementation.md (new/updated)

**Supported-case rule** (in approach_router.get_supported_case):
- Load v1 playbook (jsonl primary, yaml fallback; legacy yaml as last resort).
- Keyword trigger match (normalize + substring, score by hits).
- Pick best (prefer high conf, then more hits).
- supported = (confidence in ("high", "medium")) AND len(recommended_approach_ids) > 0
- manual_review or empty recs (catalog gaps) or no match → supported=false, case_family=proc_id or "unknown", reason populated.
- Returns the exact schema in the query (plus matched_triggers).

**Unsupported behavior (ENABLE_LOCAL_ANATOMY_RAG=true)**:
- Gate runs first (get_supported_case).
- Legacy: short-circuit in run_pipeline_fast (if enforce) or in main: approachSelection=null (or limited with selectionMode=unsupported...), anatomyQuiz=null/empty. No GPT call for guessing.
- Miller: skip run_anatomy_miller_only / retriever by default; return limited v2 payload with retrievalMode="not_run_unsupported_case", limitedAnatomyContext=true, empty arrays, anatomySystem with approachLogic="unsupported_case_no_approach_guessing" + warning.
- Hybrid builder receives the limited objects and preserves the special mode/anatomySystem.
- General pimp/otherUsefulFacts from case-prep vector path still returned.
- Debug: ANATOMY_ALLOW_UNSUPPORTED_RETRIEVAL=true forces Miller run even for !supported (dev only; logged).

**When ENABLE=false**:
- Full legacy run_pipeline_fast (GPT on full catalog for unknowns) unchanged. Gate code in gpt checks the env and does not short-circuit.

**Known supported cases** (high/med + non-empty recs from playbook, ~27):
- distal_radius_fracture_orif (high, volar + conditional dorsal)
- carpal_tunnel_release (high)
- tha_posterior / tha_anterior / tha_lateral (high)
- tka, femoral_shaft_fracture_orif, high_tibial_osteotomy, acetabulum_* (high/medium), proximal_humerus, radial_head, etc.
- (Full list in playbook; router now uses it.)

**Known unsupported / catalog-gap / manual_review** (11+):
- bimalleolar/trimalleolar/pilon/calcaneus (manual_review, empty recs; anterior explicitly blocked in playbook but no positive lateral/medial IDs yet)
- olecranon, pelvis_ring, cubital_tunnel, clavicle, supracondylar_peds, hallux_valgus, trigger_finger
- Anything not matching a procedure_id (e.g. "tibial shaft fracture ORIF" — no exact entry, even though similar like tibial_plateau/femoral_shaft exist)
- "random ankle pain", "forearm pain no fracture", etc.

**Next priority mappings / catalog additions** (from audit + playbook):
1. Add dedicated lower-ext leg/ankle catalog entries (lateral malleolus/fibula, direct medial malleolus, posterolateral ankle, extensile lateral calcaneus) → promote bimalleolar etc. from manual_review to high.
2. Add tibial shaft ORIF (or generalize "tibial_shaft_fracture_orif" using leg_lateral + perhaps others).
3. Olecranon / posterior elbow, cubital/medial elbow, clavicle approaches.
4. Expand for more trauma (monteggia, scaphoid, achilles, etc. if they have solid recs).

**Validation performed**:
- tibial shaft ORIF: gate engaged, approach null, mode=not_run_unsupported_case (no lateral/medial leg guess).
- bimalleolar: supported=false (gap), no anterior guess.
- Supported cases (distal radius, carpal, posterior THA): supported=true, approach/quiz present, Miller runs.
- 9/9 tests passed (including debug, gap, case-prep compat).
- Smokes: pimp/other always present; anatomy gated correctly for unsupported, hybrid for supported.
- No Pinecone writes, no corpus/OB/UI changes, flag-off legacy preserved (unknowns still get GPT guess when flag=false).
- approach catalog still loads 30.

The gate makes the pipeline "fail safe" for unknown procedures while keeping the curated experience for the 27+ mapped cases.
