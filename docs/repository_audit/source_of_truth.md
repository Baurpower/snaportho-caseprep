# Source of Truth Report

Explicit identification of what actually powers production after the clean v1 migration + resolver + hygiene passes.

## Production APIs (serve real requests)
- **main.py** (FastAPI app)
  - `/case-prep` (primary)
  - `/anatomy`
  - `/anki/ortho-context`
  - Startup loads: APPROACH_CATALOG_PATHS + CERTIFIED_PAYLOADS from data/anatomy/
- Direct runtime dependencies (imported at top or in ENABLE path):
  - vector_search.py (snippets / miller / pinecone)
  - query_refiner.py
  - gpt_refiner.py
  - anatomy_gpt.py (legacy run_pipeline_fast)
  - hybrid_anatomy_builder.py + playbook_anatomy_builder.py + anatomy_curator.py (hybrid assembly)
  - procedure_registry.py (resolver — **the critical new layer**)
  - approach_router.py (supported case gate + approach selection; calls resolver)
  - anki_ortho_context*.py

## Current Anatomy Corpus (BroBot certified case-prep)
- **Single source of truth:** `data/anatomy/`
  - `registry/procedures.jsonl` (60 canonical procedure definitions, from old v1_4 router normalized)
  - `registry/procedure_aliases.jsonl` (60 entries with rich aliases + is_certified flag; loaded by procedure_registry)
  - `registry/certification_registry.jsonl` (24 certified)
  - `case_prep/certified_case_prep_payloads.jsonl` (24 full resident-facing payloads)
  - `case_prep/case_prep_router.json` (certified list, not_certified list, fallback_message)
  - `case_prep/retrieval_tests.jsonl` (120 tests)
  - `modules/*.jsonl` (7 type-specific, used_by certified procs)
  - `sources/orthobullets_sources.jsonl` + `source_gap_queue.jsonl`
  - `reports/` (v1 integration docs)

**Key property:** Certified payloads are pre-baked, source-backed, and returned **directly** via resolver slug match. No raw user text or old playbook paths reach the certified path.

## Current Embedding / Retrieval Pipeline
- `vector_search.py` + `run_anatomy_miller_only` (local index under data/anatomy_miller_gold_v1/ or pinecone namespace)
- Fallback RAG path only (when no certified match or flag off).
- **Note:** Miller gold v1 is *not* used for the 24 certified BroBot payloads (those are static in case_prep/).

## Current Prompt / Context Assembly
- query_refiner + gpt_refiner for general caseprep facts.
- For anatomy: resolver (procedure_registry) + (certified payload or hybrid/playbook builders + miller).
- OpenAI client in main + anatomy_gpt.

## Current QC / Validation
- `scripts/anatomy/validate_clean_anatomy_v1.py` (structure, counts=24/60, no legacy placeholders post-hygiene, min sections, runtime paths)
- `scripts/anatomy/smoke_test_anatomy_runtime.py` (certified resolve + payload + no_legacy + logs; non-cert fallback; unknown suggested; observability)
- `scripts/anatomy/run_source_coverage_loop.py` (for expanding beyond 24)

## Current Playbook / Approach Matching System
- `approach_router.py` (still active for non-certified + approach IDs).
- `data/approach_playbook/` (map + old playbooks; referenced for catalogs).
- Supporting: data/lower_extremity/, upper_extremity/, spine/, approach_router/approach_mappings.yaml (loaded in main).

## What Is NOT Source of Truth (Historical)
- Everything under `archive/` (by definition of this audit).
- data/anatomy_integration/, anatomy_modules/*v*, anatomy_sources/*v*, anatomy_miller_gold_v1/
- Root normalized_*, output_vector*, embed_*.txt, old reports (phase*, v1_1 etc.)
- Most scripts/ outside scripts/anatomy/
- Legacy anatomy_*.py not in the import chain of main + current hybrid.
- Old playbook v1/v2 full content (v1_4 router data was promoted to data/anatomy/registry/procedures.jsonl).

**Rule for future changes:** Any change to certified case-prep must touch only files under `data/anatomy/` (or the loader in procedure_registry.py / main.py startup). Old paths must not leak into the certified short-circuit.

See current_pipeline.md for the end-to-end flow diagram and entry points.
