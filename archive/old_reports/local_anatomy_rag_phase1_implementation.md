# Local Anatomy RAG Phase 1 Implementation Report

**Status**: Complete (local-only, flag-gated, no Pinecone).
**Date**: 2026-06-05
**Workspace**: snaportho-caseprep
**Gold corpus**: 717 records (`anatomy_gold_v1_pinecone_ready.jsonl` copied from anatomy_pipeline)

## Files Created / Edited

### New files
- `data/anatomy_miller_gold_v1/anatomy_gold_v1_pinecone_ready.jsonl` (safe copy of authoritative gold)
- `data/anatomy_miller_gold_v1/README.md` (provenance, count, usage, no-upload note)
- `data/anatomy_miller_gold_v1/local_index/` (generated)
  - `embeddings.npy` (717 × 1536 float32)
  - `ids.json`
  - `metas.json`
  - `manifest.json`
- `scripts/build_local_anatomy_gold_index.py` (OpenAI text-embedding-3-small + save artifacts + manifest)
- `anatomy_retriever.py` (load index, embed query, cosine, post-filter + boost, return chunks)
- `anatomy_context_builder.py` (extractive structured payload from chunks + limited flag)
- `scripts/test_local_anatomy_rag.py` (9 cases harness → JSON + MD reports)
- `reports/local_anatomy_rag_phase1_caseprep_smoke.md`
- `reports/local_anatomy_rag_phase1_test_results.json`
- `reports/local_anatomy_rag_phase1_test_results.md`
- `reports/local_anatomy_rag_phase1_implementation.md` (this file)

### Edited
- `main.py`:
  - Added `ENABLE_LOCAL_ANATOMY_RAG` env check at import time (prints status).
  - `case_prep`: general path always runs; anatomy path chosen by flag (legacy `anatomy_gpt` vs new miller local).
  - `/anatomy` endpoint also respects flag for easy testing.
  - Early returns and merge preserve `pimpQuestions` / `otherUsefulFacts`.
  - Miller path uses lazy imports inside the enabled branches (no breakage when flag=false).
  - Added fallback in miller path so a missing index never kills the request.

## Environment
- `ENABLE_LOCAL_ANATOMY_RAG=true` (or 1/yes/on) → new path
- `OPENAI_API_KEY` (and optional `OPENAI_PROJECT_ID`) required for query embeddings in retriever and for index build.
- No other new env vars. Existing Pinecone vars untouched.
- Report variable names only; values never logged in code or this report.

## Commands

### 1. (One-time) Build the local index
```bash
cd /Volumes/PS3000/snaportho-caseprep
ENABLE_LOCAL_ANATOMY_RAG=true ./venv/bin/python scripts/build_local_anatomy_gold_index.py
# or with explicit gold if needed
```

### 2. Run full 9-case harness (direct modules, no server)
```bash
./venv/bin/python scripts/test_local_anatomy_rag.py
# produces reports/local_anatomy_rag_phase1_test_results.{md,json}
```

### 3. Smoke /case-prep (with flag)
```bash
ENABLE_LOCAL_ANATOMY_RAG=true ./venv/bin/python -c '
import os, json
os.environ["ENABLE_LOCAL_ANATOMY_RAG"]="true"
import main
from fastapi.testclient import TestClient
client = TestClient(main.app)
for c in ["distal radius fracture volar approach", "posterior total hip arthroplasty", "carpal tunnel release"]:
    r = client.post("/case-prep", json={"prompt":c})
    d = r.json()
    print(c, "→ pimp=", len(d.get("pimpQuestions",[])), "anatomy_mode=", (d.get("anatomy") or {}).get("retrievalMode"))
'
```

### 4. Verify legacy still works
```bash
ENABLE_LOCAL_ANATOMY_RAG=false ./venv/bin/python -c '...'  # should show approachSelection/anatomyQuiz
```

### 5. Server (for real curls)
```bash
ENABLE_LOCAL_ANATOMY_RAG=true ./venv/bin/python -m uvicorn main:app --port 8000
curl -X POST http://localhost:8000/case-prep -H 'content-type: application/json' -d '{"prompt":"..."}'
```

## Response Shape (when flag on)
Top-level keys preserved:
- `pimpQuestions`
- `otherUsefulFacts`
- `anatomy` (now the Miller structured dict instead of legacy catalog object)

`anatomy` example (additive fields):
```json
{
  "relevantAnatomy": ["..."],
  "structuresAtRisk": ["..."],
  "approachLandmarks": ["..."],
  "highYieldFacts": ["..."],
  "sources": ["Miller p.33: ...", "..."],
  "limitedAnatomyContext": false,
  "retrievalMode": "miller_gold_local",
  "approachSelection": null,
  "anatomyQuiz": null,
  "highYieldAnatomy": null
}
```

When flag off: `anatomy` is the legacy shape from `anatomy_gpt.py` (`approachSelection`, `anatomyQuiz`, ...).

Early error cases still return `{"pimpQuestions": [], "otherUsefulFacts": [...], "anatomy": null}` (unchanged).

## Test Results Summary (from harness + smoke)
- 9/9 cases: limited=false, sources with Miller p.XX quotes present.
- pimp/other always produced (general path independent).
- Some retrieval noise (e.g. fibula/hindfoot pages appearing for wrist/hip queries) because:
  - Corpus contains many "approach" descriptions that lexically overlap.
  - Current soft boost + min_score + dedupe is conservative but not perfect on 717 small set.
  - Refiner sometimes emits "non-anatomic" for pure-procedure prompts, weakening general filter (unrelated to Miller path).
- Smoke confirmed: 3 cases, 200, pimp/other >0, miller mode + sources.

See `local_anatomy_rag_phase1_test_results.md` for per-case chunk previews and exact lists.

## Validation Checklist (per query)
- [x] No Pinecone upload / no production index touched (no pinecone code path executed for anatomy).
- [x] Gold corpus untouched (read-only copy + original path never written).
- [x] Orthobullets never referenced.
- [x] Secrets: only checked presence/len of OPENAI_API_KEY in build; never printed values.
- [x] Flag off → legacy anatomy_gpt path (approachSelection etc. present).
- [x] Flag on → miller local path (retrievalMode, sources with pages, limited flag, structured lists).
- [x] Reports created under `reports/`.
- [x] TestClient + direct module tests + uvicorn smoke all green.
- [x] Existing /case-prep contract (pimp + other + anatomy key) preserved for web/iOS.

## Known Limitations (Phase 1)
- Extractive builder (no LLM synthesis yet) → lists can be small or slightly noisy if top chunks are only partially relevant.
- No region pre-filter on the Miller index (soft boost only); some cross-region leakage possible.
- Catalog (30 approaches) still loaded at startup even for miller path (small cost).
- `/anatomy` dedicated endpoint now also supports miller when flag on (intentional for testing).
- Index is in-memory numpy (fine for 717); larger future corpus may need faiss/lancedb.
- No re-ranker model; simple cosine + heuristics.
- Some cases surface fewer "structuresAtRisk" or "approachLandmarks" than ideal because the gold metadata fields are sparse and we stayed strictly extractive.

## Next Steps (toward Phase 2)
- Phase 2: Pinecone staging namespace `anatomy_miller_gold_v1` (same index, text-embedding-3-small vectors).
  - Add `anatomy_retriever_pinecone.py` (or extend) that targets the ns.
  - Upload script (dry-run by default, explicit confirm).
  - Update flag or new `ANATOMY_BACKEND=local|pinecone`.
- Improve builder (optional small LLM pass on the retrieved chunks only, still "use only these").
- Stronger guards (query-refiner region passed to miller retriever for hard/soft filter).
- Wire richer anatomy shape into web/iOS UI (per earlier integration plan).
- Expand gold (promote holdout, more real cases) and re-eval.
- Consider hybrid: still run legacy approach quiz + new miller facts, merge in response.

## Appendix: Index Manifest (example)
```json
{
  "corpus_path": ".../anatomy_gold_v1_pinecone_ready.jsonl",
  "record_count": 717,
  "indexed_count": 717,
  "embedding_model": "text-embedding-3-small",
  "embedding_dim": 1536,
  ...
}
```

All artifacts generated with production embed model for future seamless ns migration.

**Phase 1 complete and validated.**
