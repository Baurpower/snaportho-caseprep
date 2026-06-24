# Procedure-to-Approach Router Integration Plan (Plan Only)

**Purpose**: Define how the Orthobullets-sourced, catalog-ID-strict `procedure_to_approach_map_v1.jsonl` (and its YAML sibling) will replace free-form GPT approach selection for the majority of common orthopaedic cases.

**Scope**: This document is planning only. No code changes, no BroBot modifications, no new router implementation in this phase. The map + reports complete the current task.

## Core Principle (carried from prior safety work)

Approach selection for well-described procedures must be deterministic and constrained before any generative model sees the catalog:
- First: recognize the procedure/case family via reliable triggers.
- Second: restrict the universe of legal approach IDs to only those supported by the map (recommended + fired conditionals).
- Third: block obviously incorrect IDs for that family.
- Fourth: pass the narrowed allowed/blocked sets downstream so that quiz generation and any selector operate inside a safe subset.
- Only when no map entry matches (or confidence=manual_review with no usable IDs): fall back to legacy full-catalog GPT path (still protected by post-selection validation).

This directly addresses the historical failure mode where GPT, given the full catalog, would select clinically incorrect approaches for classic cases (e.g., anterior ankle for bimalleolar ORIF when lateral + medial malleolar exposures are required).

## High-Level Flow (Future Router)

1. **Input normalization**
   - Case description, procedure text, or user "case type" string.
   - Optional structured fields (fracture pattern, additional pathology like "posterior malleolus", "dorsal comminution", etc.).

2. **Trigger matching (deterministic, first pass)**
   - Load the map (jsonl preferred for machine; yaml for human audit).
   - For each procedure entry, test case-insensitive substring / simple phrase match of any trigger against the input text (and any structured keywords).
   - Collect all matching procedure entries (usually 0 or 1; allow tie-breaking by specificity or explicit priority if needed later).
   - If zero matches → "unknown" → legacy GPT fallback (with full catalog, subject to existing safety validation).
   - If one or more matches → proceed with the highest-confidence or first hit (v1 can be single-match).

3. **Constraint assembly**
   - Start with `recommended_approach_ids` as the base allowed set.
   - For each `conditional_approach_ids` entry: if any of its `triggers` match the input, union its `approach_ids` into the allowed set.
   - Collect `blocked_approach_ids` for the matched procedure(s).
   - Result: `allowed_approach_ids` (intersection with actual catalog IDs at load time for safety) and `blocked_approach_ids`.
   - Attach `evidence_note`, `orthobullets_url`, and `confidence` into a `router_info` or `approachLogic` object for downstream transparency and logging.

4. **Downstream use of constraints**
   - Pass `allowed_approach_ids` and `blocked_approach_ids` (plus router metadata) to the approach selector (whether legacy GPT path in anatomy_gpt.py / select_approaches, a future deterministic picker, or hybrid).
   - The selector must only return IDs that are in allowed (or not in blocked) and that actually exist in the loaded catalog.
   - Post-selection validation (existing `validate_selected_approaches` logic or equivalent) prunes anything that violates the router constraints and records the removal + rationale.
   - The final approved approach ID list is then used to scope quiz generation: only approach cards whose IDs are in the final safe list are eligible for the anatomy quiz / source-backed facts for that case.

5. **Quiz / payload scoping**
   - The selected (and validated) approach IDs determine which approach cards are fetched for "approachSelection".
   - This keeps quizzes focused, clinically correct, and avoids presenting irrelevant or wrong approaches.
   - Source-backed anatomy (Miller or future) can still be retrieved in parallel for the same anatomic region, but approach choice itself is now map-driven for covered procedures.

6. **Fallback & monitoring**
   - "unknown" or manual_review entries with empty usable allowed sets → full legacy GPT path (current behavior) + strong post-validation + logging that a map miss occurred.
   - Metrics / logs should capture: map hit rate, which procedure_id fired, final allowed count, any prunes by validation, fallback rate.
   - Human review queue for manual_review cases (or new procedures) to promote them in v2+.

## Data Loading & Maintenance

- Map lives in `data/approach_playbook/`.
- Load at startup or on demand (small file; jsonl easy to stream).
- On catalog change (new approach JSONL entries added), re-validate the map: any recommended/conditional ID not present in catalog → treat as invalid at load, downgrade confidence or skip.
- Human edits prefer the .yaml for readability; a simple sync step can keep jsonl in sync (or treat yaml as source).
- Versioning: v1 today; future v2 after catalog gaps (especially ankle lateral/medial) are filled.

## Integration Points (Existing Code, for Reference Only)

- `approach_router.py` (or successor) would own `load_mappings` (adapted to new playbook schema) and `route_approaches` (trigger match + constraint assembly).
- `anatomy_gpt.py` / `select_approaches` (or the call site in main/hybrid) would accept the new `allowed_approach_ids` / `blocked_approach_ids` / `router_info` and inject hard constraints into prompts + validation.
- Existing safety net (`validate_selected_approaches`) continues to run after any selection (GPT or otherwise) and records `validation.removed` + reason.
- Hybrid payload (`anatomySystem.approachLogic`) can surface `"deterministic_map_v1"` or `"legacy_catalog_gpt"` so consumers know the source of the approach list.
- No change to Miller RAG / sourceBackedAnatomy path; the map only governs the approachSelection scoping.

## Benefits

- Eliminates the anterior-ankle-for-bimalleolar class of error for all mapped procedures.
- Makes behavior auditable: every mapped case has an Orthobullets URL + evidence_note explaining why those IDs (and why others blocked).
- Human-editable (YAML) so surgeons/educators can review and extend without code.
- Graceful degradation: unknown cases still work via legacy path.
- Sets the stage for quiz quality: questions are generated only from approaches that are actually indicated per the map.

## Risks & Mitigations (for Implementation Phase)

- Overly narrow allowed sets → insufficient options for selector → mitigation: always include at least one reasonable ID when possible, or explicitly return "manual_review" signal so fallback occurs.
- Trigger false positives/negatives → start conservative (exact-ish phrases), add logging of match rationale, allow override in UI or structured input.
- Catalog drift → load-time validation + QC report (already produced) run in CI or on catalog rebuild.
- Manual_review backlog → prioritize catalog additions for the 11 flagged procedures (ankle family first).

## Next Steps (After This Task)

- (Future) Implement a thin `procedure_approach_router.py` (or extend the existing one) that loads the playbook and exposes `route_approaches(case_text, extra_keywords=None) -> {allowed, blocked, matched_procedure_id, evidence_note, confidence}`.
- Wire the router output into the existing approach selection call sites behind a flag or by default for covered procedures.
- Expand catalog with the priority ankle (and olecranon/cubital/clavicle) IDs, then promote the corresponding manual_review entries to high-confidence in map v2.
- Add E2E tests that feed classic case strings ("bimalleolar ankle fracture", "distal radius ORIF with dorsal comminution", "posterior THA", etc.) and assert the returned allowed set + that anterior ankle is blocked for ankle malleolar cases.
- Update QC + inventory reports on each map/catalog revision.

This plan ensures the OB-grounded playbook becomes the single source of truth for deterministic approach restriction while preserving the useful legacy path for everything else.
