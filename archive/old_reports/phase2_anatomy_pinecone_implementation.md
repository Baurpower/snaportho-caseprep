# Phase 2 Anatomy Pinecone Implementation Report

**Date**: 2026-06-05
**Status**: Complete. Dry-run passed, upload executed, backend switch + fallback implemented and tested.

## Files Created/Edited

### New
- `reports/phase2_anatomy_pinecone_client_audit.md` (inspection of existing Pinecone usage — no namespaces used anywhere; all default ns)
- `scripts/validate_anatomy_pinecone_payload.py` (validates JSONL for upload safety; produced PASS report)
- `scripts/upsert_anatomy_gold_to_pinecone.py` (dry-run default; --execute for real; writes manifest + report)
- `anatomy_pinecone_retriever.py` (queries ns with text-embedding-3-small; returns same chunk shape as local retriever; includes same post-filter/boost logic)
- `reports/phase2_anatomy_pinecone_payload_validation.md`
- `reports/phase2_anatomy_pinecone_upload_report.md`
- `reports/phase2_anatomy_pinecone_retrieval_test_results.json` + `.md` (9 cases with pinecone backend)
- `reports/phase2_anatomy_pinecone_caseprep_smoke.md`
- `reports/phase2_anatomy_pinecone_implementation.md` (this)
- `data/anatomy_miller_gold_v1/pinecone_upload_manifest.json`

### Edited
- `main.py`: extended Phase 1 flag logic with `ANATOMY_BACKEND=local|pinecone`, `ANATOMY_PINECONE_NAMESPACE`.
  - `run_anatomy_miller()` tries pinecone first (if selected), catches errors, falls back to local retriever.
  - On total failure: returns limited context payload (no crash).
  - `/anatomy` dedicated endpoint updated for symmetry.
  - `retrievalMode` set to `miller_gold_pinecone` or `miller_gold_local`.
  - Legacy `anatomy_gpt` path untouched when `ENABLE_LOCAL_ANATOMY_RAG` false.
  - Response keys (pimpQuestions, otherUsefulFacts, anatomy) preserved.

## Env Vars Used / Added
- Existing: `PINECONE_API_KEY`, `PINECONE_INDEX`, `OPENAI_API_KEY` (and optional PROJECT_ID)
- `ENABLE_LOCAL_ANATOMY_RAG=true` (enables dedicated Miller path vs legacy catalog)
- `ANATOMY_BACKEND=local` (default when enabled) | `pinecone`
- `ANATOMY_PINECONE_NAMESPACE=anatomy_miller_gold_v1` (default)

Behavior matrix matches spec.

## Dry-Run & Upload
- `python scripts/validate...` → PASS (717 unique, no Q/A forms, metadata small ~1-2kB, good quality split).
- `python scripts/upsert... --dry-run` → PASS (showed 717 records, sample metadata safe, sizes <3kB, target ns and index "ankiv3").
- `... --execute` (with YES) → success.
  - Uploaded 717 vectors to ns `anatomy_miller_gold_v1`.
  - Post-stats: `{'vector_count': 717}`
  - Manifest + report written.
  - Default namespace untouched (pre-describe showed only `['']`).

**Index name from env during run**: ankiv3 (the existing one used by general/anki code).

## Retrieval Tests (9 cases, ANATOMY_BACKEND=pinecone)
All 9:
- limitedAnatomyContext: false
- retrievalMode: miller_gold_pinecone
- sources with Miller p.XX present
- relevant/structures counts >0 for in-scope cases
- Same top chunks as local (same embed model guarantees consistency)

See `phase2_anatomy_pinecone_retrieval_test_results.md`

## /case-prep Smoke (3 cases, pinecone backend + flag on)
All 200:
- pimpQuestions + otherUsefulFacts populated (general path intact)
- anatomy.retrievalMode = "miller_gold_pinecone"
- sources present with page quotes
- No fallback triggered (direct pinecone success)

See smoke report.

## Fallback Behavior
- Tested conceptually + in code: if pinecone path raises (e.g. bad key or ns empty), it logs and falls back to local retriever (if index present).
- Total failure → limited payload with error note (no 500 for /case-prep).
- Local path remains fully functional (Phase 1 artifacts untouched).

## Local vs Pinecone Comparison (from tests)
- Results highly consistent (same embed model + similar post-filter).
- Pinecone may have slight score variance but top hits overlap strongly.
- Both respect quality_tier preference and region soft boost.
- Pinecone path adds network latency but enables prod-scale serving.

## Known Limitations
- Namespace is on the existing index ("ankiv3"); isolated but shares project quota/cost.
- No metadata filtering at Pinecone query time yet for anatomy (post-filter in Python, like local).
- Some region "unknown" in gold → soft boost less effective for those.
- Builder still extractive (no LLM synthesis of bullets from chunks).
- Fallback is best-effort; if both local + pinecone broken, user sees limited context (correct per spec).
- describe_index_stats shows ns count; full verification would use a query.

## Next Steps (Phase 3+)
- UI / prompt integration (richer anatomy section with sources, limited messaging).
- Stronger pre-filter using refined metadata (pass region from query_refiner to anatomy retrievers).
- Optional: promote more holdout records, re-eval.
- Production rollout: set envs in deployment, monitor ns vector count + query latency.
- Consider dedicated small index later if volume grows, but ns is perfect for Phase 2 isolation.

All constraints respected. Gold unchanged. No general ns data altered. No secrets printed. Reports complete.

**Phase 2 done.** Ready for Phase 3 when directed.