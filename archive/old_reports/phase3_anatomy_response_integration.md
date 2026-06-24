# Phase 3 Anatomy Response Integration Report

**Date**: 2026-06-05
**Status**: Complete. Improved payload (AnatomyPayload v2), source-backed organization, strict mode, better low-confidence handling, updated integration, tests, and examples. All constraints honored.

## Files Created / Edited

### New Reports & Tests
- `reports/phase3_anatomy_response_shape_audit.md` (detailed legacy vs Miller comparison + recommended v2 schema)
- `reports/phase3_anatomy_response_examples.md` (real formatted payloads for 3 key cases)
- `reports/phase3_anatomy_payload_test_results.json` + `.md` (12 automated tests: 6 cases × local + pinecone)
- `scripts/test_phase3_anatomy_payload.py` (new harness validating v2 shape, strict mode, no-invention, etc.)

### Code Changes
- `anatomy_context_builder.py` (major refactor):
  - Produces full AnatomyPayload v2 with structured `sources` (list of objects), `retrievalSummary`, all required sections.
  - Improved categorization + deduping from chunks + metadata.
  - `ANATOMY_STRICT_SOURCE_MODE` support (default true): favors verbatim-ish excerpts from source_quote/text.
  - Better low-confidence path (limited=true + warning in summary; sources still returned).
  - No invention: sections only populated from supporting chunks.
  - Legacy compat fields remain (null in Miller path).
- `main.py` (minor):
  - `_limited_payload` updated to full v2 shape (including retrievalSummary).
  - Callers continue to set correct `retrievalMode` after build (local vs pinecone).
  - /anatomy and /case-prep paths unchanged in behavior.
- No changes to retrievers (chunk shape was already compatible).
- No changes to legacy `anatomy_gpt.py` or when flag is off.

## New / Updated Schema (AnatomyPayload v2)

See audit report for full rationale. Core stable shape (superset for compat):

```json
{
  // Legacy (only populated in legacy path; null otherwise)
  "approachSelection": {...}|null,
  "anatomyQuiz": {...}|null,
  "highYieldAnatomy": {...}|null,

  // Miller gold v2 (always in Miller path)
  "retrievalMode": "miller_gold_local" | "miller_gold_pinecone",
  "limitedAnatomyContext": boolean,
  "relevantAnatomy": string[],
  "structuresAtRisk": string[],
  "approachLandmarks": string[],
  "highYieldFacts": string[],
  "sources": [ { "id": "...", "page": 33, "heading": "...", "text": "...", "source_quote": "...", "score": 0.67 } ],
  "retrievalSummary": {
    "chunksUsed": 8,
    "mode": "...",
    "limited": false,
    "regions": ["wrist"],
    "warning": "..." | null
  }
}
```

**Sources** upgraded from plain strings to objects — enables future UI to link back to specific Miller pages/quotes.

## Env Vars

- `ENABLE_LOCAL_ANATOMY_RAG=true` (existing) — turns on Miller path vs legacy anatomy_gpt.
- `ANATOMY_BACKEND=local|pinecone` (existing) — chooses which Miller retriever.
- **New**: `ANATOMY_STRICT_SOURCE_MODE=true` (default) — when true, builder stays very close to source text (minimal synthesis). Set false only for experimentation.
- `ANATOMY_PINECONE_NAMESPACE` (existing, for pinecone backend).

When `ENABLE_LOCAL_ANATOMY_RAG=false` (or missing): completely unchanged legacy behavior (approach catalog + GPT quiz).

## Strict Mode Behavior (default on)

- Bullets are near-verbatim from `source_quote` or `text` of retrieved chunks.
- Categorization still happens (risk/landmark language detection), but content is not rephrased.
- If a fact is only weakly supported, it is omitted rather than generalized.
- Combined with `limitedAnatomyContext`, this gives conservative, citable output suitable for exam prep / OR reference.

## Low-Confidence / Weak Retrieval Handling

- Threshold: < 2 "useful" chunks (score + keyword overlap on anatomy terms) → `limitedAnatomyContext = true`.
- Lists are short/empty.
- `retrievalSummary.warning` explains (e.g., "Limited high-quality Miller gold...").
- `sources` list is still populated (transparency > hiding the attempt).
- Only technical failures in retriever (missing index, Pinecone error after fallback) use the error limited payload.
- Miller path never silently falls back to legacy anatomy_gpt (that only happens at the ENABLE flag level).

## /case-prep + /anatomy Integration

- Miller path (flag on): returns v2 shape with Miller fields populated + legacy fields null.
- Legacy path (flag off): returns original approachSelection + anatomyQuiz shape (highYieldAnatomy may be present).
- Top-level keys always: `pimpQuestions`, `otherUsefulFacts`, `anatomy`.
- `retrievalMode` and `sources` (with real Miller pages) present when Miller active.
- No breakage to general RAG output.
- Both backends (local/pinecone) produce identical payload shape (only `retrievalMode` and internal scores differ).

## Test Results

`scripts/test_phase3_anatomy_payload.py` ran 12 cases (6 seeds × 2 backends) with strict mode on:

- All "OK" (no validation errors).
- pimpQuestions + otherUsefulFacts always present.
- `retrievalMode` correct per backend.
- Structured sources present when not limited.
- `retrievalSummary` always present with `chunksUsed`, `warning` etc.
- No sections filled without source support.
- Pinecone and local produced equivalent useful content for these cases.

See `phase3_anatomy_payload_test_results.md` + JSON for details.

## Known Limitations (Phase 3)

- Builder is still deterministic/extractive (no LLM call for synthesis). This is intentional for strict/source-backed guarantee.
- Some cases still surface a few "noisy" chunks (e.g. approach language from other regions) because the 717-record gold has lexical overlap and we use soft boosts. `retrievalSummary.warning` and `limited` flag surface this.
- Legacy fields are null in Miller responses (old clients see empty quiz/approach sections when Miller is enabled — same as Phase 2).
- No change to how general (non-anatomy) pimp/facts are generated.
- Page numbers in sources can be float in raw meta (normalized in builder).

## Frontend / iOS Implications (for later phases)

- Current web types (AnatomyPayload) and iOS Codables will continue to work (they can ignore extra fields or see nulls for legacy sub-objects).
- To fully utilize Phase 3:
  - Render new sections under the Anatomy card: Relevant Anatomy, Structures at Risk, Landmarks, High-Yield Facts.
  - Show expandable/clickable `sources` list with page + quote (huge value for trust + pimp prep).
  - Display `retrievalSummary` (especially the warning) when `limitedAnatomyContext=true`.
  - Consider a small "Miller Gold" badge or "source-backed" indicator next to the anatomy block.
- `pimpQuestions` / `otherUsefulFacts` remain the primary "management" output; Miller anatomy is deliberately separated.
- When flag is off, behavior is identical to pre-Phase 1 (no regression).

## Next Steps (Phase 4+)

- UI rendering of the rich v2 anatomy payload (web + iOS).
- Optional: light LLM synthesis pass *only on the retrieved chunks* (still grounded) if strict mode is relaxed.
- Stronger region pre-filter passed from query_refiner into the anatomy retrievers.
- Expand gold corpus (promote holdouts) and re-evaluate noise on more real cases.
- Consider surfacing Miller sources inline in the pimp/other facts as well (future).
- Production: ensure `ANATOMY_STRICT_SOURCE_MODE` stays true for clinical safety.

All tasks completed. Validation:
- No Pinecone writes.
- Gold corpus untouched.
- Legacy path (flag off) works exactly as before.
- Local + Pinecone Miller backends work and produce v2.
- Strict mode active and tested.
- Reports + tests created.
- Backward compatibility preserved at the HTTP response level.

**Phase 3 done.** Ready for UI work in a subsequent phase when directed.