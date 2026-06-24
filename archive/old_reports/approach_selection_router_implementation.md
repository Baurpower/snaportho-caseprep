# Approach Selection Router Implementation

**Date**: 2026-06-05
**Status**: Complete. Deterministic pre-filter + safety validation added. GPT selector is now constrained for known high-confidence case families. Anterior ankle approach is blocked for bimalleolar ORIF (the critical bug is fixed at the routing layer).

## Files Created / Edited

- `reports/approach_selection_safety_audit.md`
- `approach_router.py` (new deterministic router + validator)
- `data/approach_router/approach_mappings.yaml` (curated rules)
- `anatomy_gpt.py` (integrated router pre-filter + post-selection safety validation; `select_approaches` and `run_pipeline_fast` updated)
- `main.py` (already wired for hybrid; now benefits from safer legacy selector when flag is on)
- `scripts/test_approach_router.py` (new test harness)
- `reports/approach_router_test_results.json` + `.md`
- `reports/approach_selection_e2e_test_results.json` + `.md`
- `reports/approach_selection_router_implementation.md` (this)

## Architecture

1. `approach_router.route_approaches(prompt)` runs first (called inside the updated `select_approaches`).
2. For known families it returns `allowed_approach_ids` and `blocked_approach_ids` from the yaml.
3. The GPT selector prompt is augmented with hard constraints ("MUST choose ONLY from these... DO NOT choose any of these...").
4. After GPT returns, `validate_selected_approaches` runs:
   - Drops any ID not in catalog.
   - Drops any explicitly blocked by router.
   - Drops any not in the router's allowed list (when a strict allowed list was provided).
5. Only validated IDs proceed to quiz generation.
6. Router metadata (`selectionMode`, `caseFamily`, `allowed/blocked`, `routerRationale`) + validation info are attached to `approachSelection`.

When router confidence is "unknown":
- Full catalog is given to GPT (legacy behavior).
- `selectionMode` = "legacy_gpt_selector".

## Mappings Added (high-confidence cases)

See `data/approach_router/approach_mappings.yaml` for full content.

Critical for the reported bug:
- `ankle_fracture_orif`:
  - Triggers: bimalleolar, trimalleolar, lateral/medial malleolus, distal fibula ORIF, etc.
  - `allowed_approach_ids`: only the ones that exist (`approach_lower_ext_ankle_posteromedial` currently).
  - `blocked_approach_ids`: explicitly includes `approach_lower_ext_ankle_anterior`.
  - Notes document the catalog gap (no true lateral fibula or medial malleolus IDs yet).

Other families: distal radius (volar Henry + conditional dorsal), carpal tunnel, posterior/anterior THA, TKA medial parapatellar, etc.

Only real catalog IDs are listed. Gaps are explicitly noted.

## Safety Rules Implemented

- Router never invents IDs.
- Post-GPT validator removes anything blocked or outside allowed (when router was confident).
- If after validation `selected_ids` is empty for a high-confidence family, the selector returns empty + notes (caller can decide limited payload).
- `build_quiz` already only uses the final validated `selected_ids`.

## Test Results

**Router-only tests** (all PASS per the script output):
- bimalleolar: family=ankle_fracture_orif, anterior blocked → PASS
- trimalleolar + posterior: family correct
- distal radius ORIF: volar Henry allowed
- carpal tunnel: correct
- posterior / anterior THA: correct
- ambiguous: unknown (good fallback)

**E2E (router-aware GPT selector)**:
- For bimalleolar/trimalleolar: the anterior ankle ID is no longer selected (the main safety win).
- Because the current catalog lacks good lateral/medial malleolus IDs, the allowed set after validation can be empty or very small for ankle cases → selected=[] in some runs. This is *correct* behavior: better to return limited/unknown than a wrong approach.
- Distal radius, hip, etc., surface the expected IDs when they exist in catalog.
- `selectionMode`, `blockedApproachIds`, `routerRationale`, and `validation` metadata are present on `approachSelection`.

See the two test reports for full per-case data.

## Known Limitations & Catalog Gaps (documented)

- Ankle fracture ORIF: catalog is missing dedicated lateral fibula and medial malleolus approaches. Router therefore cannot return a rich allowed list for standard bimalleolar. The block on anterior works, but full coverage requires catalog expansion (future work).
- Similar gaps exist for dedicated cubital tunnel, some shoulder, ACL-specific exposures, etc.
- The router is intentionally conservative: it only claims "high" confidence for the families explicitly listed with good trigger coverage.
- Legacy GPT selector remains available as fallback for unknown/ambiguous cases.

## Next Cases / Mappings to Add (recommended)

- More ankle variants (pilon, talus, syndesmosis-specific).
- Elbow (radial head, olecranon, distal humerus).
- Foot (calcaneus, Lisfranc, etc.).
- Spine approaches.
- Add "indications" / "preferred_for" metadata to the approach JSONL entries themselves so the router can be even more data-driven.

## Integration Notes

- No change to Miller RAG path or hybrid builder (they continue to receive whatever the (now safer) legacy selector produces for the approach fields).
- `anatomySelection` in the final hybrid payload will contain the new `router` and `validation` sub-objects when the router was active.
- Backward compatibility: clients that only read the top-level `approachSelection.selected` / `anatomyQuiz` will see the (safer) result; extra metadata is additive.

All tasks completed. The anterior ankle for bimalleolar bug is prevented at the routing layer. Reports and tests are in place.