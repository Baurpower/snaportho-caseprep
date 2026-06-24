# CasePrep Production Pipeline — Plain English Explanation

This document explains exactly what happens when a user submits a surgical case description, based on the current code in `main.py`, `procedure_registry.py`, `approach_router.py`, and the data under `data/anatomy/`.

## High-Level Answer

When a user enters a case (e.g. "72 yo undergoing posterior THA tomorrow"):

1. The system first tries to identify the exact procedure using a dedicated **Procedure Resolver** (`procedure_registry.resolve_procedure`).
2. If the resolver confidently maps the input to one of the 24 **certified** procedures, it **short-circuits** and returns a pre-built, high-quality "BroBot case prep payload" directly from `data/anatomy/case_prep/certified_case_prep_payloads.jsonl`. No GPT generation of anatomy happens for these cases.
3. If it is not a certified procedure (or the resolver is not confident), the system falls back to a complex hybrid path that does query refinement, vector retrieval (Miller/Pinecone), legacy approach selection, playbook matching, and GPT-based anatomy generation.
4. Pinecone (or local Miller index) retrieval always runs for the "pimp questions / case prep facts" part.
5. Many legacy code paths from earlier versions of the system are still reachable in the fallback branches.

The design intention after the v1 cleanup was "certified-first, resolver-driven, never raw user text to the old router for certified cases." However, the fallback paths are still large and complex.

## Detailed Numbered Flow (Current Code)

1. **User input arrives** at one of the FastAPI endpoints in `main.py`:
   - `POST /case-prep` (most common — returns both pimp/caseprep facts + anatomy)
   - `POST /anatomy` (anatomy-only, used for testing)
   - `POST /anki/ortho-context` (separate)

2. **Always executed (for /case-prep and /anatomy when ENABLE_LOCAL_ANATOMY_RAG is true)**:
   - `refined_prompt = await run_in_threadpool(refine_query, prompt)` — `query_refiner.py`
   - `snippets = await run_in_threadpool(get_case_snippets, refined_prompt)` — `vector_search.py` (this talks to Pinecone or the local Miller gold index)
   - `caseprep_result = await run_in_threadpool(refine_case_snippets, prompt, snippets)` — `gpt_refiner.py` (this produces the pimpQuestions / otherUsefulFacts part)

3. **Anatomy decision branch** (only when `ENABLE_LOCAL_ANATOMY_RAG`):
   - `resolved = resolve_procedure(prompt, OPENAI_CLIENT)` — **procedure_registry.py** (the dedicated resolver layer)
     - This is the key "new" component from the v1 cleanup.
     - It runs 4 stages internally:
       - A: Exact alias match (after normalization: lowercase, remove punctuation, collapse whitespace)
       - B: Contains match (alias appears inside the prompt)
       - C: Fuzzy match using rapidfuzz (score >= 85)
       - D: GPT fallback classifier (only if A/B/C fail; requires confidence >= 0.8)
     - It always prints the 4 observability lines:
       ```
       ANATOMY INPUT: ...
       MATCH METHOD: alias|contains|fuzzy|gpt|none
       MATCH SCORE: ...
       CANONICAL PROCEDURE: <slug or unknown>
       ```
     - Returns a dict with `procedure_slug`, `match_method`, `match_score`, `suggested_matches`, etc.
     - Source of truth for aliases: `data/anatomy/registry/procedure_aliases.jsonl` (loaded in `_load_procedure_aliases`).

4. **Certified payload short-circuit** (the modern happy path):
   - `if slug and slug in CERTIFIED_PAYLOADS:` (CERTIFIED_PAYLOADS is populated at startup in `_startup()` from `data/anatomy/case_prep/certified_case_prep_payloads.jsonl`)
   - Immediately return the pre-baked payload under `"brobot_case_prep"` + a thin anatomy wrapper.
   - This is the only path that is supposed to be used for the 24 certified procedures.
   - Old playbook/approach/miller code is completely bypassed.
   - This is what makes the system "robust to real-world surgeon input."

5. **Fallback path** (non-certified or low confidence):
   - `sc = get_supported_case(prompt)` — `approach_router.py`
     - Inside `get_supported_case`, it **again calls the resolver** (`resolve_procedure`) first to get a canonical slug.
     - Then it does an **exact** `procedure_id == canonical_slug` lookup in the old playbook loaded from `data/approach_playbook/procedure_to_approach_map_v1.jsonl` (or yaml).
     - If no exact match in that map, it falls back to the old legacy trigger scoring on raw normalized prompt text.
   - If `supported` or `ANATOMY_ALLOW_UNSUPPORTED_RETRIEVAL`:
     - Runs `run_anatomy_legacy()` → `run_pipeline_fast` from `anatomy_gpt.py` (legacy catalog + GPT approach/quiz generation).
     - Runs `run_anatomy_miller_only(prompt)` (defined in `main.py`):
       - Tries the configured `ANATOMY_BACKEND` (pinecone or local).
       - Calls `anatomy_context_builder.get_miller_anatomy_context(...)`.
       - Sets `retrievalMode` to `miller_gold_pinecone` or `miller_gold_local`.
     - Tries to use the new playbook path:
       - `from playbook_anatomy_builder import build_playbook_anatomy`
       - `from anatomy_curator import curate_playbook_anatomy`
       - Uses `get_supported_case_with_playbook`, `build_playbook_anatomy`, then `curate_playbook_anatomy`.
     - Falls back to `build_hybrid_anatomy(legacy_anatomy, miller_anatomy)` if the new builders fail or are unavailable.
   - If not supported: returns limited "unsupported_case" payload with the new warning text + `suggestedMatches` (populated from the resolver).

6. **Legacy flag off path** (`else` of `if ENABLE_LOCAL_ANATOMY_RAG`):
   - Completely bypasses resolver + miller + playbook.
   - Just calls the old `run_pipeline_fast` from `anatomy_gpt.py` using the old `CATALOG` (loaded from `data/upper_extremity/...` and `data/lower_extremity/...` + `data/approach_router/approach_mappings.yaml`).

7. **Final assembly**:
   - `return {**caseprep_result, "anatomy": anatomy_result}`

## Data Files That Are Current Source of Truth (for the v1 path)

- `data/anatomy/registry/procedure_aliases.jsonl` — used by the resolver.
- `data/anatomy/registry/procedures.jsonl` — the 60 canonical procedures (originally from `brobot_anatomy_router_v1_4.jsonl`).
- `data/anatomy/registry/certification_registry.jsonl` — the 24 certified ones.
- `data/anatomy/case_prep/certified_case_prep_payloads.jsonl` — the actual pre-built payloads returned in the short-circuit.
- `data/anatomy/case_prep/case_prep_router.json` — lists of certified vs not_certified + fallback message.
- `data/anatomy/case_prep/retrieval_tests.jsonl` — the 120 golden tests.
- `data/anatomy/modules/*.jsonl` (7 files) — the modular anatomy content.
- `data/anatomy/sources/orthobullets_sources.jsonl` + `source_gap_queue.jsonl`.

## Legacy Files/Paths That Are Still Reachable

- `data/approach_playbook/procedure_to_approach_map_v1.jsonl` (and v2, old playbooks) — still loaded by `approach_router.py` and `main.py` for fallback + approach selection.
- `anatomy_gpt.py` + `run_pipeline_fast` + the old `CATALOG` — still called in multiple fallback branches.
- `data/anatomy_miller_gold_v1/` (local index) + Pinecone logic — used by `run_anatomy_miller_only`.
- Old `hybrid_anatomy_builder.py`, `playbook_anatomy_builder.py`, `anatomy_curator.py` — still imported and called in the hybrid fallback.
- Many files under the old `data/anatomy_*` directories and root `normalized_*` / `output_vectorversion_*` artifacts (they are not loaded in the hot path for certified cases, but some scripts and old tests still reference them).
- The entire old approach selection logic inside `approach_router.py` (the legacy trigger scoring path) is still there as a last-resort fallback.

## Summary of Current Reality

- **Best path (certified)**: resolver (procedure_registry) → exact slug match in CERTIFIED_PAYLOADS (data/anatomy/case_prep) → direct trusted payload. This is what the v1 cleanup was trying to make the only path for important cases.
- **Everything else**: a large, multi-layered fallback that still contains most of the pre-cleanup code (legacy GPT, old playbooks, hybrid builders, miller retrieval, etc.).
- The resolver is called in two places (directly in main.py and again inside approach_router.get_supported_case).
- Old data and code paths were not fully removed during cleanup — they were quarantined in `archive/` and `data/anatomy_legacy_archive/`, but the runtime still has reachability to similar logic via the fallback branches.

This is why the system "still feels hard to understand" — there is a modern certified short-circuit sitting on top of a very large, still-executable legacy anatomy generation system.