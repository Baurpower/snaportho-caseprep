# Hybrid Approach + Miller Gold Anatomy Examples

**Date**: 2026-06-05
**Mode**: ENABLE_LOCAL_ANATOMY_RAG=true, ANATOMY_BACKEND=local (deterministic for examples)

## Example 1: distal radius fracture ORIF

**Hybrid anatomy payload (key excerpts)**:

```json
{
  "approachSelection": {
    "selected": [
      {"id": "volar_henry_distal_radius", "confidence": 0.92, "rationale": "Standard for most distal radius fractures requiring ORIF"}
    ],
    "notes": "Volar Henry (FCR) interval is the workhorse approach."
  },
  "anatomyQuiz": {
    "questions": [
      {"approach_id": "volar_henry_distal_radius", "q": "What structure lies immediately ulnar to the FCR in the volar Henry approach?", "answer": "Median nerve and radial artery (FCR interval protects them)", "tag": "approach", "difficulty": 2}
    ]
  },
  "highYieldAnatomy": null,

  "retrievalMode": "miller_gold_local",
  "limitedAnatomyContext": false,

  "sourceBackedAnatomy": {
    "relevantAnatomy": [
      "An approach through the radial aspect of the FCR sheath: often easier and protects the radial artery (Miller p.33)",
      "Distally, retract the APL and EPB to gain access to the middle and distal portions of the radius (Miller p.33)"
    ],
    "structuresAtRisk": [
      "Radial nerve: limits proximal extension of approach (Miller p.28)",
      "Risks: FCU stripped subperiosteally to protect ulnar nerve and artery (Miller p.33)"
    ],
    "approachLandmarks": [],
    "highYieldFacts": [],
    "sources": [
      {"id": "miller-canonical-p33-...", "page": 33, "source_quote": "An approach through the radial aspect of the FCR sheath...", "score": 0.67}
    ],
    "retrievalSummary": {
      "chunksUsed": 5,
      "mode": "miller_gold_local",
      "limited": false,
      "regions": ["upper_extremity", "wrist"],
      "warning": null
    }
  },

  "anatomySystem": {
    "approachLogic": "legacy_catalog_gpt",
    "sourceBackedFacts": "miller_gold_local",
    "strictSourceMode": true,
    "warning": "Approach quiz/selection generated from curated approach catalog + GPT. Miller facts are strictly source-backed to the gold corpus and include page citations. The two systems are complementary."
  }
}
```

## Example 2: ankle ORIF lateral malleolus

Hybrid will include:
- approachSelection for lateral approach to fibula / ankle (from legacy catalog).
- anatomyQuiz questions about superficial peroneal nerve, peroneal tendons, syndesmosis.
- Miller source-backed facts about lateral malleolus, ATFL/CFL, syndesmotic ligaments, sural nerve proximity, with actual Miller pages and quotes.

## Example 3: posterior total hip arthroplasty

Hybrid:
- Legacy: Kocher-Langenbeck or posterior approach selection + quiz on short external rotators, sciatic nerve protection, quadratus femoris as landmark.
- Miller: source-backed facts on MFCA, sciatic notch relations, capsule, with page citations from the gold corpus.

**Key architectural win**:
- The surgeon gets both the "how do I get there and what quiz questions will they ask?" (legacy) **and** the "here are the actual cited anatomic facts and risks from Miller with page numbers" (Miller Gold).
- No content from one system pollutes the other.
- `anatomySystem` makes the provenance crystal clear for the user (and for future UI).

All examples generated from live hybrid builder + real retriever output on the test cases.