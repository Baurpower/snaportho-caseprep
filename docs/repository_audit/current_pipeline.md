# Current Production Pipeline Architecture (CasePrep)

**Based on code inspection of main.py, procedure_registry.py, approach_router.py, vector_search.py, and active data/anatomy/.**

## Entry Points (FastAPI in main.py)

1. **POST /case-prep** (primary BroBot case prep)
   - Input: `{"prompt": "..."}`
   - Always: `refine_query(prompt)` → `get_case_snippets(refined)` → `refine_case_snippets` (pimp / caseprep facts)
   - Anatomy decision (if `ENABLE_LOCAL_ANATOMY_RAG`):
     - `resolve_procedure(prompt)` (from procedure_registry) — dedicated layer **before** any playbook routing.
     - If `slug` in `CERTIFIED_PAYLOADS` (loaded at startup from `data/anatomy/case_prep/certified_case_prep_payloads.jsonl`): **short-circuit** return `brobot_case_prep` payload + anatomy section with resolver metadata. (No fall-through to old paths.)
     - Else: `get_supported_case(prompt)` (approach_router, which itself calls resolver for slug canonicalization) → hybrid legacy (`run_pipeline_fast` from anatomy_gpt) + `run_anatomy_miller_only` + optional `playbook_anatomy_builder` + `anatomy_curator`.
   - Returns combined caseprep + anatomy.

2. **POST /anatomy** (anatomy-only)
   - Similar resolver short-circuit for certified.
   - Falls back to hybrid + miller when not certified.

3. **POST /anki/ortho-context**
   - Separate anki export path.

4. **GET /** — health.

**Key env:** `ENABLE_LOCAL_ANATOMY_RAG` (enables resolver + miller + playbook paths; falls back to legacy catalog otherwise). `ANATOMY_BACKEND=local|pinecone`.

## Retrieval Pipeline (General RAG / Miller)

```
User prompt
  ↓ refine_query (query_refiner.py)
  ↓ get_case_snippets (vector_search.py)   ← Pinecone or local miller_gold index (data/anatomy_miller_gold_v1/ or pinecone)
  ↓ refine_case_snippets (gpt_refiner.py)
  ↓ (for anatomy) resolver or hybrid builder
  ↓ LLM generation (via OpenAI client in main / anatomy_gpt)
```

- Vector backend: `run_anatomy_miller_only` (local index or pinecone via env).
- Supports `miller_gold_pinecone` / `miller_gold_local`.
- Fallbacks documented in code.

## Anatomy / Case-Prep Specific Pipeline (Current v1)

**Resolver (procedure_registry.py)** — the key new layer post v1 migration:
- Loads aliases from `data/anatomy/registry/procedure_aliases.jsonl` (60 procedures, 24 certified marked).
- Multi-stage: exact alias (normalized), contains, fuzzy (rapidfuzz if avail), GPT classifier fallback (confidence >=0.8).
- Observability prints: ANATOMY INPUT / MATCH METHOD / MATCH SCORE / CANONICAL PROCEDURE.
- Returns canonical `procedure_slug` (e.g. "tha_posterior", "distal_radius_fracture_orif") or None + suggested_matches.

**Certified Path (data-driven, no raw text to router):**
- Startup: load all 24 payloads into `CERTIFIED_PAYLOADS` from `data/anatomy/case_prep/certified_case_prep_payloads.jsonl`.
- On match: direct return of full `brobot_case_prep_payload_v1` (must_know, SAR, pimp, checklist, sources, etc.).
- Fallback message for non-certified: "Anatomy case prep is still being improved for this procedure."
- Unknown: "Could not confidently identify..." + suggestedMatches.

**Supporting:**
- `data/anatomy/registry/procedures.jsonl` (60 procs from old v1_4 router, normalized schema).
- Modules (7 type files) + sources for enrichment (but certified payloads are pre-baked).
- `case_prep_router.json` (certified list + not_certified + fallback).
- `retrieval_tests.jsonl` (120 tests, 5 per certified).

**Legacy fallback (when not certified or flag off):**
- `anatomy_gpt.py` catalog + `hybrid_anatomy_builder` + `playbook_anatomy_builder` + `anatomy_curator`.
- Still loads old `APPROACH_CATALOG_PATHS` (data/lower+upper extremity + approach_router/ mappings) + `data/approach_playbook/` for approach_router.get_supported_case.

## Data Flow (Simplified Current)

```
User Query
  ↓
query_refiner.py (refine)
  ↓
vector_search.py (snippets / miller / pinecone)
  ↓
gpt_refiner.py (refine snippets)
  ↓
/case-prep or /anatomy handler in main.py
  ↓
procedure_registry.resolve_procedure (canonical slug)
  ↓
if certified slug in CERTIFIED_PAYLOADS (data/anatomy/case_prep/):
    return brobot_case_prep payload directly  ← preferred modern path
else:
    approach_router.get_supported_case (or legacy)
    + run_anatomy_miller_only + run_pipeline_fast (anatomy_gpt)
    + playbook_anatomy_builder + anatomy_curator (hybrid)
  ↓
LLM (OpenAI) + final assembly
```

## Anatomy Pipeline Specifics (v1 Clean)

- **Current source of truth:** `data/anatomy/` (see source_of_truth.md)
- **Corpus:** Orthobullets-derived (via previous source_library_v3 + modules v1_4 + cleanup). No Miller facts mixed into certified payloads.
- **Resolver makes it robust** to real surgeon wording (THA variants → tha_posterior etc.).
- **Certification:** 24 certified (post-cleanup + hygiene), payloads have source_urls, mins met, no (post-fix) legacy placeholders.
- **No more versioned v* leakage** into runtime for certified case-prep.

## Notes on Legacy Paths Still Present

- `data/approach_playbook/` (v1_4 used historically for procedures; still loaded for approach selection).
- Old anatomy_modules/sources (not used by current data/anatomy/ certified path).
- Miller gold v1 (used only in fallback RAG path).
- Many historical reports and test scripts.

See archive_manifest.md for what was moved, manual_review.md for uncertain items.
