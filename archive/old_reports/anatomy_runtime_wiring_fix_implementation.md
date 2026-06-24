# Anatomy Runtime Wiring Fix - Implementation

**Scope**: Fixed only runtime wiring errors for the /anatomy hybrid pipeline (and shared with /case-prep). No changes to Pinecone, no uploads, no Miller gold corpus, no Orthobullets, no frontend/iOS, legacy flag-off unchanged, /case-prep backward compat preserved.

## Root Causes (from audit)
1. **Legacy 'NoneType' object is not callable**:
   - anatomy_gpt.py module top: defensive `except: validate_selected_approaches = None` (when approach_router import fails for any reason).
   - run_pipeline_fast (used by legacy path in both endpoints): unconditionally `validation = validate_selected_approaches(...)` after select_approaches.
   - /anatomy (flag-on) catches the exception, logs it, nulls legacy → unavailable fallback.
   - (In repros with bad keys the 401 hit first; with import forced None + bypass of llm, exact error reproduced.)

2. **Miller 'name ... is not defined' + unavailable**:
   - main.py:149 (case-prep hybrid): `miller_coro = _run_miller_anatomy_only(...)` — symbol never defined at module scope.
   - main.py:193 (/anatomy): `run_in_threadpool(run_anatomy_miller_only)` — same undefined name (comment even says "defined above? Wait, scope").
   - /anatomy then does `miller = None` + fragile inline duplicate of retriever import + build_anatomy_context (not in threadpool for all paths, no pinecone→local fallback, mode may not be set for pinecone).
   - No shared helper; case-prep and /anatomy wiring diverged.
   - Result: NameError in try → except sets None → hybrid gets bad inputs → unavailable/nulls.
   - (Note: anatomy_context_builder.get_miller_anatomy_context existed and did the backend switch + build, but was never wired in main.)

3. **Hybrid merge problems**: Callers didn't reliably reach build_hybrid_anatomy(legacy, miller) with good values from both branches; manual fallbacks in /anatomy were inferior and could null everything.

4. **Why old fallback happened**: Both branches threw at runtime inside the ENABLE_LOCAL... paths → caught, set None, builder or manual produced unavailable.

## Files Changed
- anatomy_gpt.py (1 small guarded edit)
- main.py (added shared helper + refactored 2 call sites, removed dup inline code)
- scripts/test_anatomy_runtime_wiring.py (new)
- reports/*.md + *.json (new/updated per tasks; audit + impl + test results + caseprep smoke)

No other files touched.

## Exact Functions Fixed / Created
- **Guard added** (anatomy_gpt.py: ~348 block in run_pipeline_fast):
  ```python
  if validate_selected_approaches is not None:
      validation = validate_selected_approaches(...)
  else:
      validation = {"valid_selected": selected_ids, "removed": [], "reason": "validator unavailable (approach_router import skipped or None)"}
  ```
  Preserves approachSelection even if validator missing; quiz/approach path still works.

- **New shared helper** (main.py, top level after ANATOMY_ globals):
  ```python
  def run_anatomy_miller_only(prompt: str) -> dict:
      # tries configured backend first (pinecone or local)
      # on error for pinecone: falls back to local
      # on total fail: returns v2 payload with retrievalMode="unavailable" + empty Miller fields + legacy nulls
      # always sets retrievalMode to miller_gold_pinecone | miller_gold_local | unavailable
      # delegates to anatomy_context_builder.get_miller_anatomy_context (which does the chunk+build)
  ```
  Used by:
  - case-prep (via run_in_threadpool(run_anatomy_miller_only, prompt))
  - /anatomy (same)

- **Refactored call sites** (main.py):
  - case-prep hybrid block: now calls the shared (no more undefined _run...).
  - /anatomy flag-on block: now simple try legacy + try miller_shared + if build_hybrid_anatomy: build(...) else manual. Removed all the inline gpc/glc + bac dup + miller=None hack + comments.
  - Flag-off path and startup/CATALOG/OpenAI load untouched.

- **Hybrid merge**: Now both endpoints feed the (fixed) branches into build_hybrid_anatomy (or the builder's graceful None handling). Partial failure returns the working branch + anatomySystem warning (per builder design + our error payloads); only full unavailable if both truly fail.

## Why /anatomy and /case-prep Now Share Miller Logic
- Single `run_anatomy_miller_only(prompt)` at module scope in main.py.
- It uses the pre-existing (but previously unused for main wiring) `get_miller_anatomy_context(..., backend=...)` from anatomy_context_builder.
- Backend choice + pinecone→local fallback + mode override + error-to-unavailable payload all centralized.
- No duplication; both endpoints just call it (wrapped in threadpool where needed).
- Matches the "create single shared helper if needed" requirement exactly.

## Tests Run (Task 6 + 7)
- scripts/test_anatomy_runtime_wiring.py (new, 9/9 passed):
  - A (flag off): legacy approach/quiz present for 2 prompts.
  - B (flag+local): hybrid + approach not null + quiz not null + mode=miller_gold_local.
  - C (flag+pinecone): same + mode=miller_gold_pinecone (via patch).
  - D: miller fail → legacy ok; legacy fail → miller ok; plus /case-prep hybrid smoke.
  - Prompts used: all 4 specified.
  - Reports: anatomy_runtime_wiring_fix_test_results.md + .json (summary 9/9, per-case details).
- /case-prep smoke (2 required prompts):
  - bimalleolar ankle fracture ORIF + distal radius fracture ORIF.
  - pimpQuestions present, otherUsefulFacts present, anatomy present, retrievalMode=miller_gold_local, approachSelection not null, anatomyQuiz not null, hybrid fields true.
  - Report: anatomy_runtime_wiring_caseprep_smoke.md (no unavailable unless both branches simulated-fail).
- No errors for the previous two runtime strings in clean runs.

## Remaining Known Issues (esp. approach-selection correctness)
- The wiring fix makes the hybrid path execute without throwing, but does **not** change approach selection correctness itself (e.g., bimalleolar may still pick wrong ankle ID if the legacy GPT or router allows it; the separate procedure-to-approach playbook + router work addresses deterministic restriction).
- Real Pinecone/local retrieval quality depends on the Miller index (unchanged here).
- If no OPENAI_API_KEY for the local retriever embedding side, miller may fallback to unavailable (expected; legacy still works).
- approach_router may still be optional (the guard we added makes it non-fatal).
- /case-prep still does its own vector/pimp path (which may do Pinecone queries for non-anatomy content); anatomy Miller is independent.
- No change to strict source mode behavior or payload v2 shape (already correct in builders).

## Validation (per query)
- Server no longer logs the two runtime errors on /anatomy (repros now only hit when we intentionally force the old paths; clean runs succeed to hybrid).
- /anatomy no longer returns all-null unavailable when systems available (returns hybrid with approach/quiz + miller fields + correct mode).
- Approach catalog still loads (30 items) on startup.
- Miller Pinecone backend path exercised (via patch in C); local works.
- Local fallback in helper works.
- No Pinecone writes, no corpus changes, no UI/OB/BroBot changes.
- Legacy flag-off: unchanged (still calls run_pipeline_fast directly).
- /case-prep: backward compat + now gets working hybrid when flag on.

All tasks complete; stopped after wiring fixes + tests + reports.
