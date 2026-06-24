# Archive Manifest

All moves performed with `mv` (no deletes; original git history preserved). Only files meeting strict criteria moved (not imported by main active paths, not current data/anatomy/ source of truth, clearly superseded versioned artifacts or one-off experiments).

## Moves Performed (batch 1+)

### archive/old_data/
- data/anatomy_integration/ → archive/old_data/anatomy_integration/ (v1 certified artifacts; superseded by data/anatomy/ copy + hygiene)
- data/anatomy_modules/ → archive/old_data/anatomy_modules/ (all 36 versioned v1-v1_4; copied to clean modules/)
- data/anatomy_sources/ → archive/old_data/anatomy_sources/ (v1/v2/v3; v3 copied to sources/)
- data/anatomy_miller_gold_v1/ → archive/old_data/anatomy_miller_gold_v1/ (old pinecone gold; fallback only)

### archive/legacy_scripts/
- scripts/test_playbook_*.py, test_phase3_*, test_hybrid_*, test_supported_case_gate.py, test_approach_router.py, test_anatomy_runtime_wiring.py, test_local_anatomy_rag.py, test_playbook_v2* etc.
- scripts/audit_playbook_v2_quality.py
- scripts/build_local_anatomy_gold_index.py
- (plus moved root legacy: anatomy_pinecone_retriever.py, anatomy_retriever.py, anatomy_extraction.py, anatomy_metadata_insertion.py, anatomy_term_*.py, reformat_anki_*.py, gpt5_refiner.py, embed_topinecone_*.py, data_embed_topinecone.py, deleteall_pinecone.py, upsert_*, checkvector.py, audit_vectordb.py, etc.)

### archive/old_reports/
- Bulk of reports/ (phase2_*, phase3_*, v1_1*, v1_2*, hybrid_approach_miller_*, playbook_v2_*, most *_test_results.json, old audits, orthobullets_playbook_*, source_gap* moved selectively; kept recent anatomy_v1_*, brobot post-cleanup, integration_readiness, source_coverage*, current_rag etc. in place or under data/anatomy/reports/)

### archive/old_embeddings/ + archive/old_corpora/
- All root embed_*.txt (anki, ob, pp, hipknee, millers, oite, orthoanatomy, pocketpimp)
- normalized_*.jsonl/.csv (multiple gens)
- output_vectorversion_*.jsonl
- final_normalized_*, pp_anatomy_terms.jsonl, rejected_*.log, stray "f", anatomy_checkpoint.json, metadata_dictionary.updated*.json, normalize_metadata.py, csv_to_jsonl.py, update_jsonl.py, inspect_metadata.py, db_dictionary_generator.py, cpt related loose if not core, etc.

**Total moved in pass:** ~120+ files (exact count in `find archive -type f | wc -l` after all batches).

## Reasons (per file group)
- Superseded by data/anatomy/ v1 canonical (modules, sources, integration, procedures router v*).
- Embedding experiment artifacts (no longer part of current vector or anatomy pipeline).
- One-off historical tests/audits for v2 playbooks, phase2/3 RAG, hybrid miller (replaced by current resolver + certified + smoke/validate).
- Old pinecone tooling (current uses miller local or direct certified load).
- Versioned reports from prior iterations (current docs are the v1 migration + hygiene reports).

Nothing moved was imported at top-level in main.py or the active scripts/anatomy/ validators or referenced as current source of truth in procedure_registry or the certified short-circuit logic.

See executive_summary.md for recommendations on further pruning of archive/ after review.
