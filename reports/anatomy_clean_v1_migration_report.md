# Anatomy Clean v1 Migration Report

**Date:** 2026 (post BroBot integration + resolver hardening)  
**Goal:** Consolidate latest working modular anatomy architecture into stable, obvious `data/anatomy/` v1. Remove transitional clutter while preserving all history in git. Make BroBot case-prep use a single canonical source. No new content acquisition or fact generation.

## 1. Canonical v1 File Map (Phase 2/3)

Latest good sources (verified via audit of counts, schemas, integration_readiness report, post-cleanup artifacts):

| Target (data/anatomy/...)                  | Source (latest canonical)                              | Notes / Normalization |
|--------------------------------------------|-------------------------------------------------------|-----------------------|
| `registry/procedures.jsonl`               | `data/approach_playbook/brobot_anatomy_router_v1_4.jsonl` (60 unique procedure_ids) | schema_version -> `brobot_anatomy_procedure_v1`; includes procedure_id, name, case_anatomy_type, default/conditional modules, readiness etc. |
| `registry/procedure_aliases.jsonl`        | Generated from `procedure_registry.py:REGISTRY` (60 entries) | New. `brobot_procedure_alias_v1`. Includes is_certified flag (24 true). Aliases cover all procs + real-world variants. |
| `registry/certification_registry.jsonl`   | `data/anatomy_integration/certified_procedures_v1.jsonl` (24) | schema -> `brobot_certification_registry_v1`. (Non-certified list lives in case_prep_router.) |
| `sources/orthobullets_sources.jsonl`      | `data/anatomy_sources/source_library_v3.jsonl` (58)   | schema -> `brobot_anatomy_source_v1`. Source-backed facts layer. |
| `sources/source_gap_queue.jsonl`          | `reports/source_gap_priority_queue.jsonl` (205)       | Latest gap queue for future iteration. |
| `modules/approach_modules.jsonl`          | `data/anatomy_modules/approach_modules_v1_4.jsonl`      | 34 modules |
| `modules/arthroscopy_modules.jsonl`       | `.../arthroscopy_modules_v1_4.jsonl`                  | 3 |
| `modules/reduction_implant_modules.jsonl` | `.../reduction_modules_v1_4.jsonl`                    | 7 (mapped to task-specified name) |
| `modules/decompression_modules.jsonl`     | `.../decompression_modules_v1_4.jsonl`                | 6 |
| `modules/soft_tissue_modules.jsonl`       | `.../soft_modules_v1_4.jsonl`                         | 4 (mapped) |
| `modules/fluoroscopy_modules.jsonl`       | `.../fluoroscopy_modules_v1_4.jsonl`                  | 2 |
| `modules/pathology_anatomy_modules.jsonl` | `.../pathology_modules_v1_4.jsonl`                    | 33 (mapped) |
| `case_prep/certified_case_prep_payloads.jsonl` | `data/anatomy_integration/certified_case_prep_payloads_v1.jsonl` (24) | Kept as `brobot_case_prep_payload_v1`. |
| `case_prep/case_prep_router.json`         | `data/anatomy_integration/case_prep_router_v1.json`   | Exact copy (certified + not_certified lists + fallback_message). |
| `case_prep/retrieval_tests.jsonl`         | `data/anatomy_integration/case_prep_retrieval_tests_v1.jsonl` (120) | 5 realistic prompts per certified. |
| `reports/integration_readiness.md`        | `reports/brobot_anatomy_integration_readiness_v1.md`  | Primary BroBot surface doc. |
| `reports/...` (selected)                  | freeze_list_v1_4, next_gap_queue_v1_4, iteration_v1_4, source_coverage_dashboard, certification_leaderboard (post-cleanup) | For reference; not all historical reports copied. |

**Total:** 60 procedures, 24 certified, 89 modules, 58 sources.

## 2. Files Created (this migration)

- `data/anatomy/` + full subdir tree (registry/, sources/, modules/, case_prep/, reports/, + legacy archive sibling).
- `data/anatomy/registry/procedure_aliases.jsonl` (generated).
- `data/anatomy_legacy_archive/README.md` (quarantine doc + runtime contract).
- `scripts/anatomy/validate_clean_anatomy_v1.py` (full 8+ checks).
- `scripts/anatomy/smoke_test_anatomy_runtime.py` (5 test scenarios + log/legacy checks).
- `reports/anatomy_clean_v1_migration_report.md` (this file).
- (Copies of canonical data + light schema_version normalization only; no content rewrite of facts.)

## 3. Runtime Code Paths Updated (Phase 5)

- **main.py**:
  - Added `ANATOMY_ROOT = BASE_DIR / "data" / "anatomy"` + derived paths (CERTIFIED_CASE_PREP_PATH now points to `case_prep/certified_case_prep_payloads.jsonl`, plus PROCEDURES_PATH, ALIASES_PATH, CASE_PREP_ROUTER_PATH, CERTIFICATION_PATH).
  - Startup load now reads from `data/anatomy/case_prep/...`.
  - Resolver call (`resolve_procedure`) is first action in both `/case-prep` and `/anatomy` handlers.
  - Certified short-circuit: if resolver slug in CERTIFIED_PAYLOADS → return full `brobot_case_prep` payload + mode (bypasses all old playbook/Miller/hybrid for these cases).
  - Non-certified → fallback message from router ("Anatomy case prep is still being improved for this procedure.").
  - Unknown/low-conf → warning "Could not confidently identify a supported procedure from the case description." + `suggestedMatches`.
  - Updated comments + error messages to reference new paths and "no old approach_playbook leak for certified case-prep".
  - Still supports hybrid/legacy paths for non-certified.

- **procedure_registry.py**:
  - Added `_load_procedure_aliases()` that reads `data/anatomy/registry/procedure_aliases.jsonl` (populates full 60 + is_certified).
  - `REGISTRY = _load...()` (replaces previous 300+ line hardcoded list).
  - Small embedded fallback (5 common certified) only if data file missing (dev safety).
  - All resolver stages (A-D), normalization, prints, and `resolve_procedure` unchanged.
  - `is_certified()`, lookups, etc. continue to work.

- **approach_router.py**:
  - Already integrated resolver first (from prior work). Now benefits from data-driven aliases.
  - Still loads `data/approach_playbook/procedure_to_approach_map_v1.jsonl` (and anatomy playbook) for approach selection logic. This is intentional (separate concern); certified case-prep short-circuit in main.py prevents fall-through for BroBot payloads.
  - Updated failure reason to new warning text.

**Result:** For any prompt that resolver maps to a certified procedure_id, BroBot receives the exact certified payload with zero dependency on old `approach_playbook/`, `anatomy_modules/*_v*`, `anatomy_sources/*_v*`, or `anatomy_integration/` at runtime.

## 4. Certified / Non-Certified Counts

- Procedures (registry): 60 (unique).
- Certified: 24 (certification_registry + payloads + router list).
- Non-certified: 36 (in case_prep_router; not in separate registry file).
- Aliases: 60 (24 flagged is_certified=true).
- Modules: 89 total across 7 type files.
- Sources: 58.

## 5. Validation Results (Phase 7)

Ran `python scripts/anatomy/validate_clean_anatomy_v1.py`:

**PASS (majority):**
- data/anatomy + all 15+ required files exist.
- procedures.jsonl: 60 entries, 60 unique IDs.
- aliases: 60, covers every procedure.
- certification + case_prep_router + payloads: 24, IDs match exactly.
- No duplicate module_ids (89 total).
- All certified payloads have required sections (source_urls, must_know_anatomy, structures_at_risk, attending_pimp_questions, night_before_review_checklist).
- Runtime code references `data/anatomy` paths.
- All JSONL/JSON parse.

**FAIL (known / reported):**
- Legacy placeholder strings found in certified payloads (examples: "Primary structure at risk?", "Key approach for this case" in hip/tha payloads' must_know arrays). (See audit note: present in source modules at time of payload synthesis; integration report claimed clean but actual v1 jsonl retains some. No rewrite performed per rules.)

Validation exits non-zero on the legacy flag but is otherwise clean. This is the primary remaining content hygiene item.

## 6. Smoke Test Results (Phase 8)

Ran `python scripts/anatomy/smoke_test_anatomy_runtime.py`:

**PASS (5):**
- Certified prompts resolve to correct slug + return real payload (distal_radius_fracture_orif, acl_reconstruction).
- Resolver observability prints emitted (ANATOMY INPUT, MATCH METHOD, MATCH SCORE, CANONICAL PROCEDURE) for all cases.
- Non-certified ("prep me for trigger finger release") → slug present but not certified → would hit fallback path + message.
- Unknown ("prep me for something weird...") → suggested_matches (5), method=none.
- Logs captured correctly in tests.

**FAIL (2) — attributable to same legacy content:**
- tha_posterior payload test: `no_legacy=False` (contains "Primary structure at risk?" / "Key approach..." strings).
- Global "no legacy in any certified payload on disk".

All structural + resolver + routing + fallback logic smoke tests pass. The legacy strings are data content, not routing bugs.

Example log output from smoke (tha_posterior case):
```
ANATOMY INPUT: 72 yo undergoing posterior THA tomorrow
MATCH METHOD: alias
MATCH SCORE: 100.0
CANONICAL PROCEDURE: tha_posterior
```

## 7. Legacy Files Archived or Ignored (Phase 6)

- Created `data/anatomy_legacy_archive/README.md` with full explanation, runtime contract, list of ignored paths, and recovery note ("git checkout").
- **No aggressive deletes or moves** of data files (safety). Old versioned files, reports, miller gold, old playbooks, v1/v2 sources, anatomy_integration originals, etc. remain in place for history.
- Runtime updated to ignore them for new BroBot anatomy flows (only `data/anatomy/` referenced in resolver + main certified path).
- Reports: only recent canonical ones (integration readiness, post-cleanup leaderboards, gaps, coverage) selectively promoted to `data/anatomy/reports/`. Historical bulk left in `reports/`.
- `source_gap_priority_queue.jsonl` promoted (as gap queue source).

## 8. Remaining Known Limitations / Risks

- **Legacy strings in certified payloads** (and some modules): "Key approach for this case per OB and map?", "Primary structure at risk?", etc. still appear in a subset of the 24 (mostly hip family). These were present at integration time. Validation and smoke flag them. Future content pass (outside this reset) should purge at source (modules) and re-emit payloads. Per rules, we did not rewrite.
- **Approach selection layer**: `approach_router.py` + `data/approach_playbook/procedure_to_approach_map_v1.jsonl` (and old playbook) remain for approach IDs / hybrid paths. Certified case-prep is protected by early return in main.py, but full "only data/anatomy" for every anatomy-related thing would require further refactoring of approach maps (not in scope of this consolidation).
- **Other legacy in tree**: miller gold v1, many old scripts/reports, embed files, etc. Unrelated to this anatomy db reset.
- **No runtime config file yet**: Paths are hardcoded in main/procedure_registry. Easy to externalize later.
- **Module naming**: Slight inconsistencies in original v1_4 filenames (soft vs soft_tissue, pathology vs pathology_anatomy, reduction vs reduction_implant) were mapped to the task-specified clean names.
- **Schema versions**: Lightly normalized only the version field; full content left untouched.
- **Future scaling**: The layout (registry + sources + modules + case_prep + reports) + data-driven aliases + resolver makes adding procedures straightforward. Next step per integration report: expand the 24 certified by targeting non-certified gaps.

## 9. Next Recommended Development Step

Per the integration readiness report (now at `data/anatomy/reports/integration_readiness.md`):

"Proceed with certified subset only" for BroBot testing.

1. Wire the new `data/anatomy/` paths into any remaining BroBot client code / tests.
2. Run the smoke + retrieval_tests as regression (assert no legacy text + correct payload per procedure_id).
3. Monitor resolver logs (the 4 ANATOMY INPUT lines) in production.
4. Iterate non-certified (use source_gap_queue + next_gap reports) to grow the certified set.
5. Optional: one-time content hygiene pass to purge remaining legacy strings from modules → re-emit the 24 payloads (no new sources needed).

This v1 gives a clean, reliable foundation. All prior history is safe in git.

**Canonical v1 is live. Old noise quarantined in docs + git.**
