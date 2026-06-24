# Versioned Artifact Groups

Identified via filename patterns (v1/v2/v3, _v1_*, normalized_*, output_vector*, phase*, etc.) and content inspection.

## 1. Anatomy Modules
- data/anatomy_modules/approach_modules_v*.jsonl ... (v1 to v1_4 + variants)
- Similar for arthroscopy, decompression, fluoroscopy, pathology, reduction, soft_tissue
- **Newest:** *_v1_4.jsonl (copied to data/anatomy/modules/ in v1 migration)
- **Currently used:** data/anatomy/modules/*.jsonl (clean names, no version suffix)
- **Safe to archive:** entire data/anatomy_modules/ (superseded; 36 files)
- Moved to: archive/old_data/anatomy_modules/

## 2. Anatomy Sources / Library
- data/anatomy_sources/orthobullets_source_library_v*.jsonl + queues + logs (v1, v2, v3)
- **Newest:** source_library_v3.jsonl (source for data/anatomy/sources/orthobullets_sources.jsonl)
- **Currently used:** data/anatomy/sources/
- **Safe to archive:** data/anatomy_sources/ (and v1/v2 inside)
- Moved: archive/old_data/anatomy_sources/

## 3. Anatomy Integration / Certified (pre-clean v1)
- data/anatomy_integration/*_v1.jsonl / .json (certified_procedures, payloads, router, tests, non_cert)
- **Newest / source of truth copy:** data/anatomy/case_prep/ + registry/ (post v1 migration + hygiene)
- **Currently used:** data/anatomy/...
- **Safe to archive:** entire data/anatomy_integration/ (v1 artifacts)
- Moved: archive/old_data/anatomy_integration/

## 4. Approach Playbook Versions
- data/approach_playbook/orthobullets_procedure_playbook_v*.jsonl/.yaml (v1, v1_1, v2, v2_1)
- brobot_anatomy_router_v*.jsonl (v1 to v1_4)
- procedure_to_approach_map_v*.jsonl/.yaml
- **Newest relevant:** brobot_anatomy_router_v1_4.jsonl (was source for current data/anatomy/registry/procedures.jsonl)
- **Currently used in prod:** data/approach_playbook/ (for approach_router map + catalogs in main.py); data/anatomy/registry/procedures.jsonl
- **Safe to archive:** old v1/v2 playbooks and maps inside (keep dir for now because referenced; individual old versions could move later)
- Note: v1_4 not moved (historical reference value)

## 5. Miller Gold / Pinecone Versions
- data/anatomy_miller_gold_v1/...
- **Status:** HISTORICAL (used only in fallback RAG when not using clean certified path)
- Moved: archive/old_data/anatomy_miller_gold_v1/

## 6. Root Embedding / Normalization Generations (multiple experiments)
- embed_*.txt (anki_*, ob, pp, hipknee, millers, oite, orthoanatomy, pocketpimp)
- normalized_*.jsonl / .csv / .v1* (millers, ob_qa, pp, hipknee)
- output_vectorversion_* (hipknee, millers, ob, oite, orthoanatomy, pp)
- final_normalized_hipknee_facts.jsonl
- **Newest / current:** None in root (all superseded by data/anatomy/ + vector index)
- **Safe to archive:** all
- Moved to: archive/old_embeddings/ and archive/old_corpora/

## 7. Reports Versioned / Phased Audits
- Many in reports/: *v1_1*, *v1_2*, *v1_3*, *v1_4*, phase2_*, phase3_*, hybrid_approach_miller*, playbook_v2*, old audits, test_results.*
- **Current / keep in place or data/anatomy/reports/:** anatomy_v1_* (migration, hygiene, scan, clean), brobot_*_post_cleanup, integration_readiness_v1, source_coverage*, current_rag_pipeline_audit, etc.
- **Safe to archive:** phase*, v*_old, hybrid*, most playbook_v2 old, test_results json, old inventories
- Moved (bulk): archive/old_reports/ (kept ~15-20 recent ones in place)

## 8. Other Versioned / Temp
- metadata_dictionary.updated*.json
- normalized_millers_v1_021926 etc.
- **Safe:** archived as part of root moves.

**Summary recommendation:** The v1 clean migration (data/anatomy/) + resolver is the current source of truth. All pre-v1 versioned anatomy/approach data + embedding experiments + phase reports are historical. 120+ files moved in this pass (see archive_manifest.md). More can be reviewed/moved from manual_review/.

No current production code imports the old v* paths directly for certified BroBot case-prep (resolver + CERTIFIED_PAYLOADS gate ensures this).
