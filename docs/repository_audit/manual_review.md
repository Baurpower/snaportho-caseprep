# Manual Review Queue

Files / items that could not be confidently classified as ACTIVE or HISTORICAL by automated + code-reference scan. **Nothing from this list was archived.**

Review these manually before any further moves or deletes. When in doubt during this pass, they stayed in place.

## High Uncertainty Items

1. **data/approach_playbook/** (entire dir + sub v* files)
   - Referenced by approach_router.py (hardcoded paths to procedure_to_approach_map_v1 + orthobullets_procedure_playbook_v1) and main.py APPROACH_CATALOG_PATHS (indirect).
   - v1_4 was source for current procedures.jsonl but old v1/v2 playbooks inside are historical.
   - **Suspected:** Still needed for legacy approach selection / supported case gate fallback.
   - **Recommendation:** Keep for now. Consider extracting only the v1 map if possible, or deprecate approach_router usage for pure certified BroBot path. Do not archive without confirming no prod traffic uses the old maps.

2. **data/lower_extremity/, data/upper_extremity/, data/spine/, data/approach_router/approach_mappings.yaml**
   - Explicitly loaded in main.py for APPROACH_CATALOG_PATHS (used in legacy catalog path + anatomy_gpt).
   - **Recommendation:** Keep as supporting (even if approach logic is secondary to new resolver + certified payloads). May be safe to archive only if ENABLE_LOCAL... + certified path becomes 100% of prod.

3. **Some root anatomy_*.py not directly imported in current main path but possibly transitive**
   - anatomy_context_builder.py, anatomy_curator.py (curator is imported in hybrid/playbook paths), playbook_anatomy_builder.py (imported).
   - anatomy_gpt.py (imported in main for run_pipeline_fast).
   - Others like anatomy_metadata_insertion.py, anatomy_extraction.py etc. moved to legacy (not referenced in active import chains).
   - **Recommendation:** Grep for imports of each remaining; keep if any dynamic load or test still uses.

4. **cpt_api.py, cpt_suggester.py, cpt_codes.db/.sql, setup_db.py, ortho_concepts.py**
   - Not referenced in main RAG/anatomy flows from scans.
   - **Suspected purpose:** CPT code support, DB setup, ortho concepts (side features or old).
   - **Recommendation:** Review usage in any BroBot client or other entrypoints. Likely safe to archive or move to a "tools/" but confirm.

5. **reports/source_gap_priority_queue.jsonl + some source_coverage* and current_rag_pipeline_audit**
   - Referenced in run_source_coverage_loop.py (active script).
   - Some reports kept in place.
   - **Recommendation:** Verify if the loop script is still run in prod CI or manually. If yes, keep; else move the jsonl to archive after confirming.

6. **anatomy_checkpoint.json, reference.txt, metadata_dictionary.json (the non-updated one)**
   - Low references.
   - **Recommendation:** Inspect content; if checkpoint for old embedding run or reference for docs, archive. The updated dicts were moved.

7. **Most individual old .py in root that were not moved (e.g. if any missed reformat or gpt5)**
   - **Recommendation:** Full `grep -r "import .*reformat|from .*gpt5" --include="*.py"` to confirm zero references, then archive.

8. **data/anatomy_legacy_archive/ (the previous one)**
   - Already quarantined.
   - **Recommendation:** Merge contents or leave; its README explains prior pass.

9. **__pycache__/, venv/ (obvious, but listed for completeness)**
   - Build artifacts. Should be .gitignore'd and never committed, but present.
   - **Recommendation:** Clean locally, ensure .gitignore covers; do not archive (or rm -rf if safe).

10. **Any remaining reports/ that were borderline (e.g. some "current_rag" or "existing_approach_catalog")**
    - Kept if they appeared in recent v1 docs or validate references.
    - **Recommendation:** Read the md; if purely historical audit, move.

## Process Note
During the pass, any file with even one reference in an ACTIVE .py (main, procedure_registry, approach_router, scripts/anatomy/validate+smoke+coverage_loop, or direct load in data/anatomy startup) or that is the current data/anatomy/ tree was left untouched.

If after manual review you decide something here is safe, add to a future archive_manifest and mv.

**Next step after this audit:** Have a human (or additional static analysis) go through this list + the archive/ contents before any `rm -rf archive/` or further cleanup.
