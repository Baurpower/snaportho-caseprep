# Phase 3 Anatomy Response Examples (Miller Gold v2)

**Date**: 2026-06-05
**Backend**: Both local and pinecone tested; examples below use pinecone (production path) with `ANATOMY_STRICT_SOURCE_MODE=true`.
**Note**: Content is 100% derived from retrieved chunks in `anatomy_miller_gold_v1` namespace. No GPT hallucination for Miller sections.

## Example 1: distal radius fracture volar approach

**Top-level /case-prep excerpt** (pimp/other truncated for brevity):

```json
{
  "pimpQuestions": [ "Q: ...", "..." ],
  "otherUsefulFacts": [ "..." ],
  "anatomy": {
    "approachSelection": null,
    "anatomyQuiz": null,
    "highYieldAnatomy": null,
    "retrievalMode": "miller_gold_pinecone",
    "limitedAnatomyContext": false,
    "relevantAnatomy": [
      "An approach through the radial aspect of the FCR sheath: often easier and protects the radial artery (Miller p.33)",
      "Distally, retract the APL and EPB to gain access to the middle and distal portions of the radius. (Miller p.33)"
    ],
    "structuresAtRisk": [
      "Radial nerve: limits proximal extension of approach (Miller p.28)",
      "Risks: FCU stripped subperiosteally to protect ulnar nerve and artery (Miller p.33)"
    ],
    "approachLandmarks": [],
    "highYieldFacts": [],
    "sources": [
      {
        "id": "miller-canonical-p33-d41b150ba1ec",
        "page": 33,
        "heading": "...",
        "text": "Distally, retract the APL and EPB...",
        "source_quote": "Distally, retract the APL and EPB to gain access to the middle and distal portions of the radius.",
        "score": 0.6688
      },
      { "id": "...", "page": 28, "source_quote": "...", "score": 0.65 }
    ],
    "retrievalSummary": {
      "chunksUsed": 5,
      "mode": "miller_gold_pinecone",
      "limited": false,
      "regions": ["upper_extremity", "wrist"],
      "warning": null
    }
  }
}
```

**Key observations**:
- Source-backed with Miller p.XX + quotes.
- Structures at risk pulled from risk language in chunks.
- No fake landmarks or high-yield invented.
- retrievalSummary provides transparency.

## Example 2: posterior total hip arthroplasty

```json
{
  "anatomy": {
    "retrievalMode": "miller_gold_pinecone",
    "limitedAnatomyContext": false,
    "relevantAnatomy": [
      "Distal extension of posterior acetabular approach (Kocher-Langenbeck) (Miller p.72)",
      "Can be injured by placement of acetabular screws in the anterosuperior quadrant during total hip arthroplasty (Miller p.63)"
    ],
    "structuresAtRisk": [
      "Particularly at risk for injury during psoas tenotomy through an anteromedial approach for developmental dysplasia of the hip (Miller p.64)"
    ],
    "approachLandmarks": [],
    "highYieldFacts": [],
    "sources": [ { "id": "...", "page": 64, "source_quote": "Particularly at risk...", "score": 0.646 }, ... ],
    "retrievalSummary": {
      "chunksUsed": 6,
      "mode": "miller_gold_pinecone",
      "limited": false,
      "regions": ["hip", "pelvis"],
      "warning": "Some results may be nonspecific (mixed regions in top chunks)."
    }
  }
}
```

Note the warning in summary for mixed-region hits — honest about corpus characteristics.

## Example 3: carpal tunnel release

```json
{
  "anatomy": {
    "retrievalMode": "miller_gold_pinecone",
    "limitedAnatomyContext": false,
    "relevantAnatomy": [
      "Space of Poirier: central weak area in floor of carpal tunnel; implicated in volar dislocation of lunate... (Miller p.7)",
      "Median nerve passes through the carpal tunnel between FDS and flexor carpi radialis (FCR) to supply the radial lumbricals... (Miller p.20)"
    ],
    "structuresAtRisk": [
      "Risks: FCU stripped subperiosteally to protect ulnar nerve and artery (Miller p.33)"
    ],
    "approachLandmarks": [],
    "highYieldFacts": [],
    "sources": [ ... structured objects with pages 7,20,33 ... ],
    "retrievalSummary": {
      "chunksUsed": 5,
      "mode": "miller_gold_pinecone",
      "limited": false,
      "regions": ["wrist", "hand"],
      "warning": null
    }
  }
}
```

All bullets traceable to specific Miller pages/quotes in the gold corpus.

## General Notes on Phase 3 Output
- When `ENABLE_LOCAL_ANATOMY_RAG=false`: returns legacy shape with real `approachSelection` + `anatomyQuiz` from catalog/GPT (highYieldAnatomy may be present or null).
- Miller path always sets legacy fields to null (to avoid confusion) and populates the source-backed sections.
- `sources` are now objects (id + page + quote + score) — much more useful for future citation UI than plain strings.
- `retrievalSummary.warning` surfaces when the retriever pulled from mixed/unknown regions.
- Strict mode (default true) keeps bullets close to source text; no over-generalization.
- If retrieval is weak: `limitedAnatomyContext=true`, most lists empty or very short, sources still returned for transparency.

These examples were generated from live runs of the Phase 3 builder + retrievers against the `anatomy_miller_gold_v1` namespace (and local index for parity).

See `phase3_anatomy_payload_test_results.md` for automated validation across cases/backends.