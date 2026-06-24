# Hybrid Approach + Miller Gold Anatomy Audit

**Date**: 2026-06-05
**Purpose**: Understand the current separation of legacy approach catalog system and Miller Gold RAG system so they can be safely combined into a hybrid payload without losing useful functionality or violating source-backed rules.

## 1. Legacy Approach Catalog System (anatomy_gpt.py)

**Location of logic**:
- `main.py` (when `ENABLE_LOCAL_ANATOMY_RAG=false` or in hybrid): calls `run_anatomy_legacy()` → `run_pipeline_fast(case_prompt, catalog=CATALOG, client=OPENAI_CLIENT)`
- `anatomy_gpt.py`:
  - `load_catalog_from_jsonl_file` (loads ~30 approach JSONL files from `data/upper_extremity/approaches` and `data/lower_extremity/approaches`)
  - `select_approaches` (GPT-4.1-mini structured output using compact catalog)
  - `build_quiz` (GPT generates approach-specific anatomy quiz questions)
  - `run_pipeline_fast` orchestrates selection + quiz (Stage 3/high-yield removed in current version)

**Output shape** (from current `run_pipeline_fast`):
```json
{
  "approachSelection": {
    "selected": [{"id": "...", "confidence": 0.XX, "rationale": "..."}],
    "notes": "..."
  },
  "anatomyQuiz": {
    "questions": [
      {"approach_id": "...", "q": "...", "answer": "...", "tag": "...", "difficulty": 1}
    ]
  }
}
```

**Strengths**:
- Identifies relevant surgical approaches for the case prompt.
- Generates approach-specific quiz (very useful for pimp / teaching).
- Uses curated approach catalog with intervals, key structures, etc.
- Fast and deterministic catalog selection.

**Weaknesses**:
- Not source-backed to Miller (or any specific textbook page).
- Can hallucinate details not strictly in the small catalog.
- No page citations or direct Miller quotes.

**HighYieldAnatomy**:
- Present in older UI types and some historical paths, but current `run_pipeline_fast` does **not** return it (Stage 3 was removed).
- In main.py limited payloads and builder, it is explicitly set to null.

## 2. Miller Gold RAG System (Phase 1/2/3)

**Locations**:
- `anatomy_retriever.py` (local numpy index from `data/anatomy_miller_gold_v1/local_index/`)
- `anatomy_pinecone_retriever.py` (queries namespace `anatomy_miller_gold_v1` in the existing Pinecone index)
- `anatomy_context_builder.py` (extractive builder that turns chunks into source-backed sections)
- Called from `run_anatomy_miller()` in main.py when `ENABLE_LOCAL_ANATOMY_RAG=true`

**Chunk shape** (returned by both retrievers):
```json
{
  "id": "miller-canonical-...",
  "score": 0.XX,
  "text": "...",
  "source_quote": "...",
  "page": 33,
  "heading": "...",
  "region": "...",
  "subregion": "...",
  "quality_tier": "high|medium",
  "metadata_trust": "..."
}
```

**Current Miller payload** (from `build_anatomy_context`):
```json
{
  "approachSelection": null,   // ← Problem
  "anatomyQuiz": null,         // ← Problem
  "highYieldAnatomy": null,
  "retrievalMode": "miller_gold_pinecone" | "miller_gold_local",
  "limitedAnatomyContext": bool,
  "relevantAnatomy": [...],
  "structuresAtRisk": [...],
  "approachLandmarks": [...],
  "highYieldFacts": [...],
  "sources": [ {id, page, heading, text, source_quote, score}, ... ],
  "retrievalSummary": { chunksUsed, mode, limited, regions, warning }
}
```

**Strengths**:
- Strictly source-backed to Miller gold corpus (717 records).
- Real page citations + source_quote.
- `retrievalSummary` for transparency.
- Strict mode (`ANATOMY_STRICT_SOURCE_MODE`) keeps output close to source text.

**Weaknesses** (current state):
- Completely drops approach selection and approach-specific quiz.
- `approachSelection` / `anatomyQuiz` were genuinely useful for case prep.
- No separation of "approach logic" vs "source-backed facts" — current Miller path overwrites the entire anatomy object.

## 3. Why Fields Are Currently Nullled

In `main.py`:
- The `if ENABLE_LOCAL_ANATOMY_RAG:` branch **only** calls `run_anatomy_miller()` (which only does retriever + builder).
- It never calls `run_anatomy_legacy()` when the flag is true.
- The builder hardcodes legacy fields to `None` for "compat".
- Result: when Miller is enabled, the response anatomy object loses the approach catalog value entirely.

This was introduced during the "Miller-only" phases and is the core bug the user wants fixed.

## 4. Safest Place to Merge

**Recommended architecture** (hybrid, not replacement):

In `main.py` (inside `case_prep` and `anatomy_only`):

```python
if ENABLE_LOCAL_ANATOMY_RAG:
    # Always run legacy approach logic (catalog + GPT selection + quiz)
    legacy_anatomy = await run_anatomy_legacy()

    # Also run Miller source-backed retrieval
    miller_anatomy = await run_anatomy_miller()   # or the retriever+builder directly

    # Merge in a dedicated helper
    anatomy_result = merge_hybrid_anatomy(legacy_anatomy, miller_anatomy)
else:
    anatomy_result = await run_anatomy_legacy()
```

**Best implementation location for merge logic**:
- New file: `hybrid_anatomy_builder.py` (or add clean functions to `anatomy_context_builder.py`).
- Keep `anatomy_gpt.py` and the retrievers untouched.
- The merge function should:
  - Take the full legacy dict and the full Miller dict.
  - Copy `approachSelection`, `anatomyQuiz` (and `highYieldAnatomy` if present) from legacy.
  - Copy all Miller source-backed fields (`relevantAnatomy`, `sources`, `retrievalSummary`, etc.).
  - Add `anatomySystem` transparency object.
  - Handle partial failures gracefully (e.g., legacy succeeds but Miller limited → still return good approach data + note in Miller section).

**Why this is safest**:
- No changes to the two source-of-truth systems.
- Clear provenance (`anatomySystem` explains what came from where).
- Legacy clients that only read `approachSelection`/`anatomyQuiz` continue to get value even when Miller facts are enabled.
- Miller strict source-backed rules are never violated by GPT approach content (they live in separate top-level keys or under `sourceBackedAnatomy`).

## 5. Additional Observations

- CATALOG is already loaded at startup in `_startup()` regardless of flag — no extra cost to always call legacy approach logic when the flag is on.
- The two systems are complementary, not mutually exclusive:
  - Approach system = "which approach(es) and what quiz/questions are relevant?"
  - Miller system = "what are the actual source-backed anatomic facts, risks, and landmarks with citations?"
- Current limited payload in main.py already tries to include both legacy nulls + Miller fields — this is the right direction but needs the actual legacy call + proper merge.
- For `/anatomy` dedicated endpoint the same hybrid logic should apply when flag is true.

**Conclusion for implementation**:
Do **not** replace. Run both in parallel when flag is true, then merge into a documented hybrid schema that keeps top-level legacy fields populated and adds clearly labeled Miller source-backed sections + provenance metadata.

This audit directly informs the hybrid schema and merge logic in the subsequent tasks.