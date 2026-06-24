# Approach Selection Safety Audit

**Date**: 2026-06-05
**Context**: Recent reports of clinically incorrect approach selection (e.g., anterior ankle approach chosen for standard bimalleolar ankle ORIF).

## Current Architecture

### 1. Approach Catalog
- Loaded in `main.py:_startup()` from two JSONL files:
  - `data/upper_extremity/approaches/upper_extremity_approaches.jsonl`
  - `data/lower_extremity/approaches/lower_extremity_approaches.jsonl`
- Total ~30 entries.
- Each entry has:
  - `id` (e.g., "approach_lower_ext_ankle_anterior")
  - `name`
  - `text` (description, often includes "Structures at risk")
  - `meta`: region, anatomic_area, bones, joint, category="approaches"
- **Ankle coverage is extremely limited**:
  - Only two ankle-specific entries:
    - `approach_lower_ext_ankle_anterior` (EHL / tibialis anterior interval; risks: peroneal nerves, anterior tibial artery)
    - `approach_lower_ext_ankle_posteromedial`
  - No dedicated `lateral fibula / lateral malleolus` or `medial malleolus` approach IDs in the catalog.
  - "Leg — Lateral approach" exists but is for leg (tibia/fibula shaft level), not ankle-specific malleolar ORIF.

### 2. Selection Logic (`anatomy_gpt.py`)
- `select_approaches()`:
  - Compacts the full catalog (id, name, aliases, region, anatomic_area, joint, summary=text[:280]).
  - Sends to GPT-4.1-mini with structured output schema (1-3 approaches, each with id/confidence/rationale).
  - Prompt instructions:
    - "Only output IDs that exist in the provided catalog."
    - "Prefer the most anatomically appropriate approach(es) given the case."
    - No procedure-specific rules, no "if this fracture type then these exposures".
  - Post-filter: keeps only IDs that actually exist in catalog.
- Then `build_quiz()` generates questions from the *selected* IDs only (good).
- `run_pipeline_fast()` orchestrates selection then quiz.
- No "indications", "contraindications", or "preferred for fracture X" metadata on catalog entries.
- GPT is the *sole* decider for which IDs to pick from the (small, incomplete) list.

### 3. Integration Points
- `main.py`:
  - When `ENABLE_LOCAL_ANATOMY_RAG=false`: calls legacy `run_anatomy_legacy()` → full GPT selector.
  - When `ENABLE_LOCAL_ANATOMY_RAG=true`: runs hybrid (legacy + Miller) via `run_anatomy_legacy()` + Miller path, then `hybrid_anatomy_builder.build_hybrid_anatomy()`.
  - The approachSelection/anatomyQuiz come exclusively from the legacy GPT selector.
- `hybrid_anatomy_builder.py`: preserves whatever the legacy selector returned; does not constrain or validate it.
- Miller path (retrievers + context builder) is independent and does **not** participate in approach selection (correctly — it provides source-backed facts/landmarks/risks after approaches are chosen).

### 4. Why Anterior Ankle Was Selected for Bimalleolar ORIF
- Prompt contains "ankle" + "ORIF" / "fracture".
- The only catalog entry whose `name` or `anatomic_area` contains "ankle" that could plausibly be associated with "ORIF" is `approach_lower_ext_ankle_anterior`.
- GPT, lacking any "standard bimalleolar exposures are lateral + medial malleolus" knowledge or catalog signals, picks the "ankle" match.
- No blocking rules, no case-family detection (bimalleolar ORIF vs. pilon vs. talus), no preference ordering.
- The catalog itself lacks the correct approaches (lateral fibula, medial malleolus), so even a perfect GPT would have been forced to pick the wrong one or fail.

### 5. Other Catalogs & Gaps
- Many common cases have decent coverage (hip approaches, knee parapatellar, carpal tunnel, etc.).
- Ankle fracture ORIF, distal radius (volar Henry is present), some acetabular, etc., have partial or missing dedicated entries.
- No "procedure → preferred approaches" mapping anywhere.
- No "fracture pattern → exposure" logic (e.g., posterior malleolus → add posterolateral).

### 6. Failure Modes
- **Over-reliance on GPT lexical matching**: "ankle" + "fracture" → anterior ankle.
- **Incomplete catalog**: Correct approaches often don't exist as IDs.
- **No safety net**: Selector can return any catalog ID; post-filter only checks existence, not appropriateness.
- **No separation of concerns**: GPT does both "which approach is indicated" (should be deterministic) and "generate quiz from the chosen approach" (acceptable for GPT).
- **Hybrid path inherits the bug**: Because it still calls the legacy selector for `approachSelection`/`anatomyQuiz`.
- **No confidence degradation or fallback for obvious mismatches**.

### 7. Current Strengths to Preserve
- Quiz generation is already scoped to selected IDs only (good).
- Miller facts are independent and source-backed (do not touch).
- Legacy fallback exists when router is uncertain.
- Structured output + safety filter on IDs.

## Recommendations (for implementation)
- Add a pre-GPT deterministic `approach_router.py` + `approach_mappings.yaml`.
- Router returns allowed/blocked lists for known case families.
- Feed allowed list (or force selection) into the legacy selector, or bypass GPT selector entirely for high-confidence families.
- After selection, run explicit safety validation (no blocked IDs, IDs exist, etc.).
- Store router metadata (`selectionMode`, `caseFamily`, `blockedApproachIds`, `routerRationale`) in the returned `approachSelection`.
- Treat GPT selector as fallback only when router returns "unknown".
- Start with high-confidence common ORIF cases (ankle bimalleolar, distal radius, hip, knee, carpal/cubital tunnel, etc.).
- Document missing catalog coverage explicitly.

This audit confirms the root cause is lack of deterministic, procedure-aware routing + incomplete catalog for ankle malleolar exposures. The fix must constrain selection before GPT sees the full catalog.