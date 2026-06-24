# Phase 3 Anatomy Response Shape Audit

**Date**: 2026-06-05 (continuing from Phase 1/2)
**Goal**: Document current legacy vs Miller anatomy payloads in /case-prep responses to design a stable, backward-compatible AnatomyPayload v2 for source-backed Miller gold integration.

## Current Legacy Anatomy Payload (from anatomy_gpt.py + main.py when ENABLE_LOCAL_ANATOMY_RAG=false)

From `anatomy_gpt.py:run_pipeline_fast` and `run_anatomy_legacy`:

```json
{
  "approachSelection": {
    "selected": [
      {"id": "...", "confidence": 0.9, "rationale": "..."}
    ],
    "notes": "..."
  },
  "anatomyQuiz": {
    "questions": [
      {"approach_id": "...", "q": "...", "answer": "...", "tag": "...", "difficulty": 1}
    ]
  },
  // Occasionally highYieldAnatomy in older paths / UI expectations
  "highYieldAnatomy": {
    "structures": [...],
    "must_not_miss": [...]
  }
}
```

This comes from the 30-item approach catalog JSONL + GPT selection + quiz generation. It is **not** Miller-gold backed. Sources are implicit in the catalog entries (not exposed as Miller pages/quotes).

Legacy path is still fully active and must be preserved when flag is off.

## Current Miller Anatomy Payload (Phase 1/2, from anatomy_context_builder + retrievers when ENABLE_LOCAL_ANATOMY_RAG=true)

From `anatomy_context_builder.py:build_anatomy_context` (used by both local and pinecone paths in main.py):

Current output shape (additive for compat):

```json
{
  "relevantAnatomy": ["string bullets..."],
  "structuresAtRisk": ["..."],
  "approachLandmarks": ["..."],
  "highYieldFacts": ["..."],
  "sources": ["Miller p.XX: excerpt..."],  // simple strings
  "limitedAnatomyContext": false,
  "retrievalMode": "miller_gold_local" | "miller_gold_pinecone",
  // legacy compat fields (set to null/None to avoid breaking old readers)
  "approachSelection": null,
  "anatomyQuiz": null,
  "highYieldAnatomy": null
}
```

**Chunk input shape** (from retrievers, used to build above):
- id, score, text, source_quote, page, heading, region, subregion, quality_tier, metadata_trust
- (plus raw_score in some)

**Sources** are currently flattened strings like "Miller p.33: An approach through the radial aspect of the FCR sheath...". No structured source objects with id/score/etc.

**retrievalSummary** does not exist yet.

**limitedAnatomyContext** and retrievalMode are already present from Phase 2.

The builder is mostly extractive (sentence splitting + keyword heuristics from text/source_quote). It categorizes bullets heuristically but does limited deduping and no deep clinical structuring.

## Fields Shared Between Legacy and Miller Paths

- None directly at the top level for the "anatomy facts" content.
- Both paths can produce an "anatomy" key under the top-level /case-prep response.
- Top-level response always has: pimpQuestions, otherUsefulFacts, anatomy (the value differs).
- Legacy compat fields (approachSelection etc.) are only meaningfully populated in legacy path.

## Fields Only in Legacy Path

- approachSelection (with selected items + rationale)
- anatomyQuiz (Q/A pairs tied to approaches)
- highYieldAnatomy (structures + must_not_miss) — present in UI types but often empty in current builder

These are generated from the small approach catalog + GPT (can hallucinate details not strictly in Miller).

## Fields Only in Miller Path (or Miller-specific)

- relevantAnatomy, structuresAtRisk, approachLandmarks, highYieldFacts (string lists)
- sources (list of strings with Miller p.XX)
- limitedAnatomyContext (bool)
- retrievalMode ("miller_gold_local" | "miller_gold_pinecone")
- (Internally: relies on retrieved chunks with source_quote + page for attribution)

## Potential Frontend/iOS Compatibility Concerns

From prior audit (web BroBot types in snaportho-web):
- BroBotPayload expects `anatomy?: AnatomyPayload | null`
- AnatomyPayload (current in web):
  ```ts
  {
    approachSelection?: { selected: [...], notes? };
    anatomyQuiz?: { questions: [...] };
    highYieldAnatomy?: { structures?: [...], must_not_miss? };
  }
  ```
- iOS (BroBotModel.swift etc.) has matching Codable structs for ApproachSelection, AnatomyQuizQuestion, HighYieldStructure, etc.
- UI cards render "Anatomy" section expecting quiz + high-yield structures + approach selection.
- If we return the Miller-only shape (with relevantAnatomy etc. and nulls for legacy), old clients may:
  - Show empty quiz/approach sections (acceptable for now, as per "no UI work yet").
  - Ignore unknown fields (good, since Miller fields are additive).
  - Break if they assume non-null or specific shapes without null checks.
- Backward compat is currently handled by setting legacy fields to null in Miller path, and Miller fields are extra.
- Risk: If a client does strict JSON schema or accesses .anatomyQuiz without ?., it may error on new responses when Miller path is active.
- pimpQuestions/otherUsefulFacts are always present from general path — safe.

## Recommended Stable Anatomy Schema (for Phase 3)

Introduce **AnatomyPayload v2** that is a superset:

```json
{
  // === Legacy / approach-catalog fields (populated only in legacy path, null otherwise for compat) ===
  "approachSelection": { ... } | null,
  "anatomyQuiz": { "questions": [...] } | null,
  "highYieldAnatomy": { "structures": [...], "must_not_miss": [...] } | null,

  // === Miller gold source-backed fields (always present in Miller path; may be present or empty in future merged) ===
  "retrievalMode": "legacy" | "miller_gold_local" | "miller_gold_pinecone",
  "limitedAnatomyContext": boolean,
  "relevantAnatomy": string[],           // source-backed key anatomy facts/relations
  "structuresAtRisk": string[],          // explicitly supported by chunks
  "approachLandmarks": string[],
  "highYieldFacts": string[],            // pimp-style from Miller (not quiz Q/A)
  "sources": [                           // structured, better than current strings
    {
      "id": "miller-...",
      "page": 33,
      "heading": "...",
      "text": "...",
      "source_quote": "...",
      "score": 0.67
    }
  ],
  "retrievalSummary": {
    "chunksUsed": 8,
    "mode": "...",
    "limited": false,
    "regions": ["wrist", "upper_extremity"],
    "warning": "..." | null
  }
}
```

**Rules for v2 (enforce in builder + main):**
- Legacy fields: only non-null when using anatomy_gpt path.
- Miller fields: populated from chunks only. Empty lists + limited=true if weak.
- "sources" become objects (with id/page/score/quote) for better attribution and future UI linking.
- retrievalSummary provides transparency (especially for limited cases).
- Never fill Miller sections from GPT hallucination or catalog alone.
- Strict mode (new env) further restricts to near-verbatim from source_quote/text.
- Always keep top-level /case-prep keys: pimpQuestions, otherUsefulFacts, anatomy (value follows v2 shape).
- This is additive — old clients that only read approachSelection/anatomyQuiz will see nulls (same as today) when Miller active, and full legacy when flag off.

This schema supports gradual UI migration later (Phase 4) while keeping current web/iOS from hard-breaking on Miller-enabled responses.

**Next steps in Phase 3**: Update builder to produce this v2, add strict mode, improve organization/dedup, update main wiring for clean integration, add tests + examples report + final impl doc.

Audit complete. Proceed to define/implement the schema in code.