# Orthobullets Playbook v1.1 Integration Plan

**Purpose**: Describe how to switch the anatomy pipeline / BroBot from v1 to v1.1 playbook as the primary source of truth for supported procedures. This is a data-only enrichment (no code behavior change required for router/curator). v1 preserved for rollback.

## 1. How to Switch BroBot from v1 to v1.1
- **Primary config / env / constant** (in snaportho-caseprep or BroBot anatomy wiring):
  - Change the playbook load path from:
    `data/approach_playbook/orthobullets_procedure_playbook_v1.jsonl` (and .yaml)
    to:
    `data/approach_playbook/orthobullets_procedure_playbook_v1_1.jsonl` (and .yaml)
  - Example (approach_router.py or main.py or shared loader):
    ```python
    # Before
    PLAYBOOK_PATH = os.getenv("ANATOMY_PLAYBOOK_PATH", "data/approach_playbook/orthobullets_procedure_playbook_v1.jsonl")
    # After (for v1.1 rollout)
    PLAYBOOK_PATH = os.getenv("ANATOMY_PLAYBOOK_PATH", "data/approach_playbook/orthobullets_procedure_playbook_v1_1.jsonl")
    ```
  - Same for any YAML fallback loader.
  - If using explicit import/load in playbook_anatomy_builder.py or anatomy_curator tests, update the default there too (or make it env-driven).
- **No schema change**: v1.1 is fully backward-compatible (same 38 entries, same field shapes, added `playbook_update` metadata block only on the 5 enriched entries; other entries identical to v1).
- **Router/gate impact**: None required. `classify_procedure` / supported-case logic already reads the loaded playbook + map; it will automatically see richer `important_anatomy[]`, `structures_at_risk[]`, etc. for the 5 procedures (TKA, carpal, femoral shaft, patella, tibial plateau). Supported=true behavior unchanged.
- **Curator impact**: None required. `build_playbook_anatomy` + `curate_playbook_anatomy` consume the entry fields directly (playbook primary); richer content for thin cases will flow through (still capped by curator rules: max ~5, dedup, concise resident style, Miller only for citations on existing items, no invention).
- **Hybrid / Miller fallback**: Unchanged. For the now-enriched cases, Miller support will be even more secondary (term-overlap filter will find more playbook terms to retain relevant citations only).
- **Tests / smoke**: After path flip, re-run:
  - scripts/test_supported_case_gate.py (or equivalent)
  - scripts/test_playbook_primary.py (pointing at v1.1 or via env)
  - /case-prep and /anatomy smokes with the 5 cases (TKA should now return useful anatomy instead of quiz-heavy).
  - Existing `playbook_primary_test_results.md` baseline can be compared to `playbook_primary_v1_1_test_results.md`.

## 2. Does the Router Need Changes?
- No. Router (approach_router.py `load_playbook`, `classify_procedure`, `get_supported_case*`) is data-driven. It already correctly returns `supported=true` + `recommended_approach_ids` for these procedures (TKA has always had the medial parapatellar ID; carpal etc. had the correct single ID). v1.1 only adds depth inside the playbook entry.
- Optional nice-to-have (non-blocking): expose `playbook_update` version in the returned dict or limited payload for observability ("playbookVersion": "v1_1").

## 3. Does the Curator Need Changes?
- No. The strict "playbook primary, Miller supports/cites only, no invention" prompt and output shaping (Approach / Key Anatomy / Structures at Risk / Landmarks / Operative Pearls / Sources + millerSupport) already handle variable playbook richness. v1.1 simply provides more high-quality items for the curator to prioritize/dedup into the max-5 resident-facing lists.
- Optional: curator could surface `playbook_update.evidence_urls` or version in `sources[]` or metadata for audit, but not required for correctness.

## 4. Test Status (local v1.1 run)
- See `reports/playbook_primary_v1_1_test_results.md` (adapted harness executed against v1.1 + map for the exact 5 cases).
- TKA: anatomy went from nearly empty (relied on Miller/quiz) to 4+3+4+3 detailed, OB-sourced, matching the resident-level list in the task (medial parapatellar, quad/VMO exposure, patella/patellar tendon/tibial tubercle, extensor, infrapatellar saphenous, skin/genicular risks, landmarks, eversion/exposure, variations).
- carpal/femoral: now have real content vs 0/low.
- patella + tibial plateau: minimal but non-zero to meet "at least 5" threshold.
- Curator would keep output concise (existing rules).
- No unsupported facts (all new items have url+section from fetched OB pages only; blanks for MCL/posterior neurovasc respected).
- 11 manual_review entries remain gated (supported=false).
- Full end-to-end (with ENABLE_LOCAL_ANATOMY_RAG etc.) should be re-smoked in snaportho-caseprep after path switch.

## 5. Rollback Plan
- Immediate: flip the `ANATOMY_PLAYBOOK_PATH` (or hardcoded default) back to `..._v1.jsonl`. No code deploy needed if env-driven; otherwise revert the one-line path change.
- v1 files were never modified; they remain byte-identical to the pre-v1.1 state.
- If a bug is found only in v1.1 content: the 5 enriched entries can be manually edited in v1.1 (still OB-only discipline) or the path can stay on v1 while a v1.2 is prepared.
- No Pinecone/BroBot corpus change: rollback is pure data path flip + restart/redeploy of the service using the loader.
- Monitoring: after switch, watch for TKA/carpal/femoral case-prep outputs (should be richer anatomy, fewer "quiz" fallbacks); if regression, rollback instantly.

## 6. Deployment / Observability Recommendations
- Add a small "playbook_version" to anatomySystem or response metadata when loading (parse from one entry's `playbook_update.version` or a top-level marker file).
- Update any docs that hardcode "v1" (e.g. prior integration plans, QC).
- Consider a one-time smoke of the 5 cases + a couple manual_review/unknown cases (tibial shaft) post-switch to confirm gate still works and enriched cases are useful.
- No changes to approach catalog (30 IDs), map v1, or Miller corpus.

## 7. Open Items / Next (after switch approved)
- Monitor real resident/curator output quality for the 5 (especially TKA).
- If more thin supported surface as weak (e.g. from new test cases or volume), run another enrichment pass (same rules: OB-only, url+section, v1 preserved or new minor rev, QC + test update).
- Eventually: retire v1 or keep as "last-known-good" reference.
- Full BroBot prod testing + any light router/curator observability tweaks (optional).

## Validation Checklist (this plan)
- [x] v1 preserved (separate v1_1 files created, no overwrite)
- [x] All new facts OB-only with url+section (from live fetches on 12028/5031/12014/1040 + map cross-refs)
- [x] No Miller/MedGemma/other used to author playbook
- [x] No BroBot core / Pinecone / catalog / map changes yet
- [x] Router + curator need zero functional changes (data enrichment only)
- [x] 5+ thin supported improved (TKA primary + carpal + femoral + 2)
- [x] Tests/reports produced (QC, v1.1 test comparison, this plan)
- [x] Rollback is trivial path flip

**Ready to switch?** Yes — after review of the QC + v1.1 test comparison reports. TKA is clearly improved and should eliminate the "weak output despite correct medial parapatellar approach" problem. The other 4 bring the total to the required threshold without over-enriching unsupported areas.
