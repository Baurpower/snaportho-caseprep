# Anatomy Supported Case Gate Audit

**Date**: current state after prior wiring fixes
**Purpose**: Document why unsupported/unknown procedures (e.g. "tibial shaft fracture ORIF") currently produce unsafe guessed approaches + irrelevant Miller anatomy, and identify signals for a supported-case gate.

## Current Flow for Unknown/Unsupported Cases (ENABLE_LOCAL_ANATOMY_RAG=true)

1. **In main.py (case_prep / anatomy_only)**:
   - Always runs `legacy_coro = run_anatomy_legacy()` which does `run_pipeline_fast(...)` (from anatomy_gpt).
   - Always runs `miller_coro = run_in_threadpool(run_anatomy_miller_only, prompt)`.
   - Then `build_hybrid_anatomy(legacy, miller)` (or fallback merge).
   - No pre-check for whether the prompt is a "supported" procedure.

2. **Legacy path (anatomy_gpt.py: run_pipeline_fast + select_approaches)**:
   - Calls `get_allowed_and_blocked(case_prompt)` (from approach_router).
   - Current approach_router.py loads **old** `data/approach_router/approach_mappings.yaml` (not the v1 playbook).
   - If no keyword match (e.g. "tibial shaft" doesn't hit "ankle_fracture_orif", "distal_radius_orif", "tka_...", femoral_shaft etc. in the limited old families), returns:
     ```json
     {"case_family": "unknown", "allowed_approach_ids": [], "blocked_approach_ids": [], "confidence": "unknown", ...}
     ```
   - In anatomy_gpt (lines ~314-319):
     ```python
     if router_info.get("confidence") in ("high", "medium"):
         allowed = ...
     ```
     For "unknown" → allowed=None, blocked=None.
   - Then `select_approaches(..., allowed_approach_ids=None, ...)` runs full unconstrained GPT selection over the entire 30-item CATALOG.
   - GPT can (and does) pick any approaches that seem vaguely related, e.g. "lateral leg" + "medial leg" for tibial shaft ORIF because they exist in catalog under lower_extremity/leg.
   - Post `validate_selected_approaches` only does catalog-existence + router-allowed (but router allowed was empty) + blocked checks; no "is this a supported procedure?" test.
   - Result: `approachSelection` with guessed IDs + `selectionMode: "legacy_gpt_selector"`, `router: {case_family: "unknown", ...}`.
   - Quiz is then generated from whatever was (wrongly) selected.

3. **Miller path (run_anatomy_miller_only in main.py + retrievers + context_builder)**:
   - `get_miller_anatomy_context(prompt, backend=...)` → `get_anatomy_chunks(prompt)` (local or pinecone).
   - Retrievers (anatomy_retriever.py, anatomy_pinecone_retriever.py) do embedding similarity + region boost + score filter on the *prompt text* only. No concept of "supported procedure".
   - For "tibial shaft fracture ORIF", embedding can match chunks from tibial plateau (knee), femoral shaft (thigh), or even loose matches from ankle/hip/hand if keywords overlap or vector similarity pulls them.
   - `build_anatomy_context` produces sourceBackedAnatomy from those chunks, sets `limitedAnatomyContext=false` if >= MIN_USEFUL_CHUNKS useful chunks found (even if the chunks are from anatomically adjacent but clinically wrong regions for a "shaft ORIF" case).
   - `retrievalMode` set to miller_gold_* (never "not_run").
   - No check against playbook or router "supported".

4. **Hybrid merge (hybrid_anatomy_builder.py)**:
   - `build_hybrid_anatomy` unconditionally takes whatever legacy and miller produce.
   - `approachLogic` becomes "legacy_catalog_gpt" (even for unknown), `sourceBackedFacts` = the miller mode.
   - `limitedAnatomyContext` reflects only Miller weakness, not "this whole anatomy is inappropriate because case unsupported".
   - For tibial shaft example: wrong approaches in legacy + potentially off-topic Miller facts → `limitedAnatomyContext=false` (misleading) + full payload.

## Why "tibial shaft fracture ORIF" Produced Bad Output
- Not present as exact procedure_id in v1 playbook (playbook has `tibial_plateau_fracture_orif` (medium, knee approaches), `femoral_shaft_fracture_orif` (high, thigh lateral/posterolateral), `high_tibial_osteotomy` (high, knee medial/parapatellar) — no plain "tibial shaft ORIF").
- Old router YAML also lacks a "tibial_shaft_orif" family → unknown.
- GPT selector (full catalog) sees "tibial", "shaft", "orif", "fracture" → picks existing leg approaches (approach_lower_ext_leg_lateral, _medial) because they are the closest catalog entries for "leg".
- Miller retrieval: prompt embedding matches tibial-related Miller gold chunks (plateau, perhaps generic leg/lower extremity facts from other cards). If enough "useful" chunks (by keyword/score), limited=false and full sourceBackedAnatomy returned, even though the anatomy may describe knee/ankle exposures irrelevant to mid-shaft plating or nailing.
- No "supported" signal propagated to prevent the legacy GPT guess or to suppress Miller.
- Result observed in query: case_family=unknown, legacy_gpt_selector, guessed leg approaches, irrelevant Miller, limited=false.

## Existing Signals That Can Identify Unsupported Cases
- From playbook (v1.jsonl):
  - `confidence == "manual_review"` (11 entries: bimalleolar, trimalleolar, pilon, calcaneus, olecranon, pelvis_ring, cubital, clavicle, supracondylar_peds, hallux, trigger_finger, etc.).
  - `recommended_approach_ids == []` even for some medium (e.g. both_bone_forearm has conditional empty for ulna).
  - Absence of any matching `procedure_id` / trigger set for the prompt (→ would be treated as unknown).
- From current router output:
  - `confidence == "unknown"`
  - `allowed_approach_ids == []` + `case_family == "unknown"`
- From anatomy_gpt router attachment:
  - `selectionMode == "legacy_gpt_selector"` (meaning no router restriction was applied).
- Catalog gaps: many lower-ext procedures have no dedicated IDs (e.g. no true lateral malleolus despite OB describing it → playbook correctly marks manual_review).
- Playbook already encodes "supported" intent via confidence + non-empty recommended (27 high/med with recs vs 11 manual).

## Other Observations
- Old router (approach_router.py) and new playbook are out of sync: router hardcodes families from old YAML; playbook is the source of truth per prior task.
- `validate_selected_approaches` and select_approaches already respect allowed/blocked when provided, but for unknown they get nothing → full GPT.
- Miller retrievers and builder have no "case support" awareness (by design until now; they are pure retrieval).
- Flag-off (ENABLE_LOCAL_ANATOMY_RAG=false) path in main still does pure legacy run_pipeline_fast → we must preserve it unchanged.
- General case-prep output (pimpQuestions, otherUsefulFacts from vector_search + refine) must remain unaffected.
- Playbook has 38 procedures; ~27 can be "supported" (high/med + non-empty recs); the rest + anything not matching = unsupported.
- Prior wiring fixes already centralized Miller via run_anatomy_miller_only and hybrid builder — good place to add gate.

This audit confirms the need for a single supported-case gate (ideally in/around approach_router.py) that both legacy selector and Miller path consult when ENABLE=true. "supported" should be true only for high/medium confidence entries that provide actual recommended approach IDs (manual_review and empty-rec cases, plus true unknown, must be treated as unsupported to avoid guessing).

Next: implement the gate per Tasks 2-8.
