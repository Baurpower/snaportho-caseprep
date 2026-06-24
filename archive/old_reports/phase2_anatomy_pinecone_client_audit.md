# Phase 2 Anatomy Pinecone Client Audit

**Date**: 2026-06-05
**Purpose**: Inspect current Pinecone integration in snaportho-caseprep to plan safe dedicated namespace usage for Miller gold anatomy (`anatomy_miller_gold_v1`).

## Current Pinecone Client Setup

### Env Vars (names only)
- `PINECONE_API_KEY`
- `PINECONE_INDEX` (used as `PINECONE_INDEX_NAME`)
- `PINECONE_ENVIRONMENT` (present in .env but **not used** in current code; legacy?)
- `OPENAI_API_KEY`, `OPENAI_PROJECT_ID`

Code always does:
```python
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX")
...
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)
```

No `PINECONE_HOST` or serverless specifics visible.

### Namespace Usage: **None**
- Every `index.query(...)`, `index.upsert(...)`, `index.delete(...)` in the codebase omits the `namespace=` kwarg.
- Therefore, **all operations target the default/empty namespace** (`""`).
- Confirmed in:
  - `vector_search.py`: `_pinecone_query` does `index.query(vector=..., top_k=..., include_metadata=..., filter=...)` — no namespace.
  - `anki_ortho_context.py`: similar `index.query` calls (with filters for curated pimp).
  - `data_embed_topinecone.py`, `embed_topinecone_facts.py`, `embed_topinecone_qa.py`: `index.upsert(vectors=batch)` or single — no namespace.
  - `deleteall_pinecone.py`: `index.delete(delete_all=True)` — wipes the **entire default namespace** of the index.
- No code ever calls `index.query(..., namespace=...)` or similar.

This means:
- Introducing `anatomy_miller_gold_v1` namespace will be **completely isolated** from existing data.
- Existing general retrieval, anki, etc. will be unaffected as long as we never omit namespace in new code or use default for anatomy.
- `delete_all=True` in delete script would **not** touch the new namespace (Pinecone delete_all is namespace-scoped if you pass namespace, but current code doesn't).

### Upsert Patterns
- Typical: `index.upsert(vectors=[(id, vector, metadata_dict), ...])` or batched.
- Metadata is flat dicts with:
  - strings, lists of strings, numbers, etc.
  - Common fields: `text`, `source`, `region`, `subregion`, `specialty`, `procedures`, `diagnoses`, `search_text`, etc.
- Embed model for general data: `text-embedding-3-small` (matches what we'll use for anatomy gold).
- No large nested objects seen in current metadata; lists are simple string lists.
- Batch size in scripts: often 100 or so.

### Query Patterns
- General RAG (`vector_search.py`): ladder of filtered queries (progressive relaxation of metadata filters from refined query), min_score=0.55, dedupe, fallback no-filter.
- Anki: filtered queries for specific sources + post-processing.
- No reranker beyond heuristics + GPT filter in gpt_refiner.
- Embed query text: same `embed_text` using OpenAI client.

### Index / Client Sharing
- Global `index` singleton in modules after load_dotenv.
- Multiple modules create their own `pc = Pinecone(...)` and `index = pc.Index(...)` (not shared singleton across modules).
- OpenAI client also instantiated per-module sometimes.
- For new anatomy retriever, we can follow similar pattern or centralize.

### Metadata Limits / Shape Concerns for Anatomy Gold
- Pinecone metadata: 40KB total per vector max recommended; values: str, int, float, bool, list[str], list[int], etc. No arbitrary nested dicts (they get stringified or rejected in strict mode?).
- From Phase 1 gold:
  - `anatomy_terms` is a dict of lists in JSONL.
  - `structures_at_risk`, `approach_terms`, `case_associations` are lists.
- Safe approach for Phase 2:
  - Promote top-level: `region`, `subregion`, `specialty`, `quality_tier`, `metadata_trust`, `page` (int), `source_quote` (str, truncated if needed), `text`.
  - For lists: keep as list[str] where possible.
  - For `anatomy_terms` dict: either omit (use for builder only), or flatten to e.g. `anatomy_neurovascular: [...]` or stringify `json.dumps(...)` as a single str field (for display only, not filter).
  - Avoid putting full long `source_quote` if it pushes size; but gold quotes are short.
- In payload validation (next task), check sizes.

### Best Place to Add Anatomy Namespace Retriever
- New module: `anatomy_pinecone_retriever.py` (parallel to `anatomy_retriever.py` from Phase 1).
- Share embedding logic? Current `embed_text` is private in vector_search. We can:
  - Duplicate small embed func (using same model), or
  - Extract a shared `embed.py` or use the OpenAI client from main.
- For consistency with Phase 1 local retriever, the Pinecone one should return identical chunk dict shape: `id, score, text, source_quote, page, heading, region, subregion, quality_tier, metadata_trust`.
- Wiring: in `main.py` (already partially done in Phase 1), extend the `ENABLE_LOCAL...` + introduce `ANATOMY_BACKEND` logic.
- Avoid modifying `vector_search.py` (that's for general RAG). Keep anatomy retrieval separate.
- Upsert script: standalone like `embed_topinecone_*.py`, using the gold JSONL.
- Validation script: before any upload.
- Use `index.query(..., namespace=ANATOMY_PINECONE_NAMESPACE)` and `index.upsert(..., namespace=...)`.
- Pinecone v2+ client (current is recent) supports namespace directly.

### Risks / Gotchas from Current Code
- Refiner sometimes produces "non-anatomic" region → may affect general, but for anatomy we can bypass refiner or use simple query embed + post-filter.
- No current code cleans up namespaces; new ns is append-only safe.
- `PINECONE_ENVIRONMENT` unused → we ignore it.
- Multiple clients: for anatomy, we'll init Pinecone inside the retriever module, similar to others.
- Error handling: current queries can return empty; we must handle and fallback.
- Stats: after upload, we can use `index.describe_index_stats()` which returns per-namespace counts (useful for verification).

### Recommendations for Phase 2
1. Namespace name: exactly `anatomy_miller_gold_v1` (as specified).
2. Env: `ANATOMY_PINECONE_NAMESPACE` (default to the name), `ANATOMY_BACKEND=local|pinecone`.
3. Dry-run validation first (payload + sample metadata).
4. Upload script must default to dry-run; require `--execute`.
5. In retriever: support fallback local -> pinecone error path.
6. When using pinecone backend, set `retrievalMode = "miller_gold_pinecone"` in anatomy payload (additive, safe).
7. Do **not** call delete on the anatomy ns in any existing delete scripts.
8. Update main.py startup/conditionals to support the switch without breaking legacy or local.
9. Test with same 9 cases as Phase 1.
10. Reports for audit, validation, upload, tests, smoke, implementation summary.

This audit confirms we can safely add the namespace without impacting existing default-ns data or code paths.

Next: implement validation script, then upload script (dry-run first).