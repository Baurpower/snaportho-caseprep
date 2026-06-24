# Anatomy Runtime Wiring Bug Audit

**Date**: 2026-06 (current workspace state)
**Goal of audit**: Identify why with ENABLE_LOCAL_ANATOMY_RAG=true + ANATOMY_BACKEND=pinecone (ANATOMY_STRICT_SOURCE_MODE=true) the /anatomy endpoint (and /case-prep hybrid) returns unavailable/null payload instead of hybrid legacy + Miller source-backed anatomy. Focus only on runtime wiring (imports, call sites, scoping, guards, duplication) per constraints.

**Reproduction (Task 1)**: Confirmed via direct harness (venv python + FastAPI TestClient + mocks for side-effect imports like pinecone/vector_search; forced conditions to hit both paths without real API keys or writes):
- POST /anatomy { "prompt": "bimalleolar ankle fracture ORIF" }
- Logs:
  - ✅ Loaded approach catalog: 30 items
  - ✅ OpenAI client initialized
  - 🦴 Miller gold via PINECONE (ns=anatomy_miller_gold_v1) with local fallback
  - ⚠️ /anatomy legacy approach failed: 'NoneType' object is not callable
  - ⚠️ /anatomy miller failed: name 'run_anatomy_miller_only' is not defined
- Result payload (via fallback paths): approachSelection=null, anatomyQuiz=null, retrievalMode=unavailable, anatomySystem.*=unavailable (or partial hybrid with nulls).

(The 401 in some runs is test-dummy-key artifact; the NoneType surfaces when legacy path reaches the validate call with validator=None. NameError is unconditional.)

## Files Inspected
- main.py (full, 245 lines)
- anatomy_gpt.py (run_pipeline_fast, select_approaches, top-level imports/guards, OpenAIJson)
- hybrid_anatomy_builder.py (build_hybrid_anatomy, _extract_miller_core, build_limited_hybrid if present)
- anatomy_context_builder.py (build_anatomy_context / AnatomyPayload v2, get_miller_anatomy_context helper, strict mode)
- anatomy_retriever.py (get_anatomy_chunks local, _load_index, embedding/query logic)
- anatomy_pinecone_retriever.py (get_anatomy_chunks pinecone, _get_pinecone_index, namespace query)
- (cross: scripts/test_hybrid_anatomy_payload.py for existing test awareness of missing helper; approach_router.py for the optional router/validate symbols; no changes to these or Pinecone/miller corpus/OB)

## Key Findings: Legacy Branch ('NoneType' object is not callable)
1. **/anatomy call site (main.py:182-190)**:
   ```python
   try:
       legacy = await run_in_threadpool( run_pipeline_fast, case_prompt=prompt, catalog=CATALOG, client=OPENAI_CLIENT )
   except Exception as leg_e:
       print(f"⚠️ /anatomy legacy approach failed: {leg_e}")
       legacy = None
   ```
   - Direct call (good for legacy), but error bubbles from inside run_pipeline_fast.

2. **Inside anatomy_gpt.run_pipeline_fast (called for both /anatomy and case-prep legacy)**:
   - Top of module (anatomy_gpt.py:8-12):
     ```python
     try:
         from approach_router import get_allowed_and_blocked, validate_selected_approaches
     except Exception:
         get_allowed_and_blocked = None
         validate_selected_approaches = None
     ```
     (Defensive for optional router; prior work made router non-fatal.)
   - Later (around line 348):
     ```python
     sel = select_approaches(...)  # may succeed or fail first (e.g. 401 on bad key)
     ...
     validation = validate_selected_approaches(selected_ids, valid_catalog_ids, router_info)  # <--- unconditional
     ```
   - If the import except fired (or symbols forced to None for any reason: bad install, circular import at runtime, test mocks, future breakage in approach_router.py, etc.), this is `None(...)` → exact "'NoneType' object is not callable".
   - In normal runs with real key + successful import, it may not surface here (error happens earlier in llm.run inside select_approaches). But the guard is missing, and observed in the failing env/run.
   - Also: select_approaches itself guards the *router* (if get_allowed... ), but post-select validate is not guarded.
   - In /anatomy flag-on path, even if legacy "partially" works, the hybrid may still be affected downstream.

3. **Other contributing**:
   - OPENAI_CLIENT is global, passed in; with dummy key in repro it fails early (auth inside OpenAI responses.create in llm.run / select).
   - No try inside run_pipeline_fast around the validate step.
   - approach_catalog load in startup succeeds (uses load_catalog_from_jsonl_file from same module).

## Key Findings: Miller Branch (name 'run_anatomy_miller_only' is not defined)
1. **References (undefined at runtime)**:
   - main.py:149 (inside async def case_prep, ENABLE_LOCAL... block):
     `miller_coro = _run_miller_anatomy_only(prompt, ANATOMY_BACKEND)`
   - main.py:193 (inside async def anatomy_only, flag-on block):
     `miller = await run_in_threadpool(run_anatomy_miller_only)  # reuse the pure miller helper defined above? Wait, scope`
     - Followed by comment acknowledging problem, then `miller = None`, then ad-hoc inline duplication:
       ```python
       be = ANATOMY_BACKEND
       if be == "pinecone":
           ... from anatomy_pinecone_retriever import ... ; ch = gpc(prompt...); miller = bac(ch...); miller["retrievalMode"]=...
       if miller is None:
           from anatomy_retriever ... ; ...
       ```
     - This inline is **not** run in threadpool properly for the pinecone/local, not wrapped for fallback on technical error, and the initial run_... line always raises NameError first (so except catches as "miller failed", sets None).
   - Grep across workspace: only these + one test that does `if hasattr(main, "_run_miller_anatomy_only") else None` (the existing test_hybrid... was written aware of the missing symbol).

2. **No definition exists**:
   - No `def _run_miller...` or `def run_anatomy_miller_only` at module scope in main.py (file ends ~line 245 after the anki endpoint).
   - No such func exported from anatomy_* modules.
   - context_builder.py *does* have a close convenience: `get_miller_anatomy_context(case_prompt, retriever_top_k=..., backend="local")` which does:
     ```python
     if backend == "pinecone":
         from anatomy_pinecone_retriever import get_anatomy_chunks
     else:
         from anatomy_retriever import get_anatomy_chunks
     chunks = get_anatomy_chunks(...)
     ctx = build_anatomy_context(chunks, case_prompt=case_prompt)
     return ctx
     ```
     - But: (a) not named/used as the required helper, (b) no Pinecone→local fallback on error inside, (c) build sets "miller_gold_local" hard (caller must override "retrievalMode"), (d) main never calls it.
   - retrievers themselves are solid (get_anatomy_chunks for local/pinecone return consistent chunk list; pinecone uses namespace, embeddings via OpenAI).

3. **/case-prep vs /anatomy divergence (wiring rot)**:
   - case-prep (flag on): parallel gather( legacy_coro=run_anatomy_legacy(), miller_coro=_run... (undefined) ); then if build_hybrid: build_hybrid_anatomy(legacy, miller) else fallback.
   - /anatomy (flag on): separate try for legacy (direct run_pipeline_fast), separate try with broken run_... + inline duplicate retriever+builder code + manual merge/fallback logic that is different (and buggy: miller=None before logic, no full error fallback to other backend, different shape handling).
   - Result: when flag on, /anatomy often hits NameError path → miller=None → ends in "both failed" or partial with unavailable.
   - build_hybrid_anatomy (hybrid_anatomy_builder.py) is designed for this (handles None legacy or miller, preserves approachSelection/anatomyQuiz from legacy only, Miller source fields from miller, sets anatomySystem, retrievalMode etc.); but never reliably fed good miller data from /anatomy.
   - case-prep also broken (undefined name) but may have been less exercised for the pure /anatomy endpoint.
   - No shared pure helper → duplication + scope bugs + missing fallback + mode not always set to pinecone when backend=pinecone.

4. **Hybrid merge (partial)**:
   - hybrid_anatomy_builder.build_hybrid_anatomy(legacy, miller) does the right thing (see _extract_miller_core, sets approach* from legacy only, Miller fields + anatomySystem + retrievalMode from miller or "unavailable").
   - But if miller path throws before producing a dict, or legacy throws, the callers in main don't always reach the builder, or builder gets bad inputs → unavailable.
   - In /anatomy post-error fallback there is manual `{**legacy, **miller}` + force approach/anatomyQuiz which is inferior to the builder and can produce the observed null/unavailable.

5. **Other wiring notes (no secrets, no corpus/Pinecone/OB/UI changes)**:
   - Startup correctly loads 30-item CATALOG + OpenAI client (independent of Miller).
   - ENABLE_LOCAL... and ANATOMY_BACKEND read at import time; prints correct log.
   - build_hybrid and build_limited_hybrid imported defensively as None (if fail, /anatomy has manual fallback).
   - Local retriever requires local_index/ files (present in data/); pinecone requires keys+index+ns (assumed configured, no uploads here).
   - context_builder already supports strict mode + v2 payload shape expected.
   - No other call sites for the missing names.
   - Legacy flag=off path (main:228+) is simple direct run_pipeline_fast and is untouched/should stay working.

## Summary Root Causes
- **Legacy NoneType**: Unconditional call to `validate_selected_approaches(...)` (which is set to None on import failure of the optional approach_router) inside run_pipeline_fast, with no `if validate_selected_approaches is not None:` guard. /anatomy catches but logs the error and nulls legacy.
- **Miller not defined + divergence**: References to nonexistent `_run_miller_anatomy_only` / `run_anatomy_miller_only` (copy-paste comments even note the scope problem); /anatomy falls back to fragile inline code instead of shared logic; case-prep assumes a helper that was never implemented at module scope. No error-fallback between pinecone/local inside the Miller path. Duplicated retriever+build code between endpoints.

This explains the "both branches throw → unavailable fallback" and why catalog loads but /anatomy is broken while flag-off legacy may appear to work in isolation.

**Recommendations implemented in subsequent fixes (see implementation report)**: Add guard for validate; implement the exact shared `run_anatomy_miller_only(prompt)` (using existing get_miller_anatomy_context + try pinecone then local + mode setting + error fallback); refactor both endpoints to call the shared helper + always use build_hybrid when available; keep flag-off and /case-prep compat; add tests.

All per constraints (no Pinecone mods, no uploads, no Miller corpus, no OB, no UI, only wiring + tests).
