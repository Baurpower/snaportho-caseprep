# CasePrep Repository Tree + Initial Classification

**Generated:** by architect audit pass  
**Total source Python files (excl venv/.git/pycache):** ~80-100 core (many tests/scripts)  
**Data files:** 100+ jsonl/json/yaml in data/ + root artifacts  
**Reports:** 90+ in reports/ (mix of current audits and historical)

## High-Level Structure

```
.
├── main.py                          # ACTIVE: FastAPI app entry point (case-prep, anatomy, anki endpoints)
├── procedure_registry.py            # ACTIVE: BroBot anatomy resolver (multi-stage matching + aliases loader from data/anatomy)
├── approach_router.py               # ACTIVE (semi): Approach selection + supported case gate; integrated with resolver
├── vector_search.py                 # ACTIVE: Pinecone / local vector retrieval
├── query_refiner.py                 # ACTIVE: Query refinement
├── gpt_refiner.py                   # ACTIVE: Snippet refinement / context prep
├── anatomy_gpt.py                   # SEMI-ACTIVE: Legacy anatomy catalog pipeline (still imported in hybrid paths)
├── hybrid_anatomy_builder.py        # ACTIVE: Hybrid assembly (playbook + miller)
├── playbook_anatomy_builder.py      # ACTIVE: Playbook-primary anatomy builder
├── anatomy_curator.py               # ACTIVE: Curate playbook anatomy
├── anki_ortho_context*.py           # ACTIVE: Anki export endpoint support
├── cpt_*.py, setup_db.py            # SIDE / UNKNOWN: CPT, DB utils (not core to main RAG/anatomy)
├── data/
│   ├── anatomy/                     # ACTIVE (canonical v1 source of truth)
│   │   ├── registry/                # procedures.jsonl (60), procedure_aliases.jsonl, certification_registry.jsonl
│   │   ├── case_prep/               # certified payloads (24), case_prep_router.json, retrieval_tests.jsonl
│   │   ├── modules/ (7)             # approach, arthroscopy, reduction_implant, decompression, soft_tissue, fluoroscopy, pathology_anatomy
│   │   ├── sources/                 # orthobullets_sources.jsonl, source_gap_queue.jsonl
│   │   └── reports/                 # v1 integration docs
│   ├── anatomy_integration/         # HISTORICAL (v1 artifacts; source for data/anatomy/ copy)
│   ├── anatomy_modules/             # HISTORICAL (36 versioned *_v1 to v1_4 jsonl)
│   ├── anatomy_sources/             # HISTORICAL (source_library_v1/v2/v3 + queues)
│   ├── anatomy_miller_gold_v1/      # HISTORICAL (old pinecone gold index + embeddings)
│   ├── approach_playbook/           # MIXED: v1/v2 playbooks + maps (HISTORICAL versions); v1_4 router was source for current procedures.jsonl
│   ├── approach_router/             # ACTIVE (supporting): approach_mappings.yaml (used by main APPROACH_CATALOG_PATHS)
│   ├── lower_extremity/, upper_extremity/, spine/  # ACTIVE (supporting catalogs referenced for approaches)
│   └── anatomy_legacy_archive/      # HISTORICAL quarantine (previous pass)
├── reports/                         # MIXED: 90+ files
│   ├── anatomy_v1_* , brobot_*_post_cleanup, integration_readiness, source_coverage*  # ACTIVE / recent
│   └── all others (phase*, v1_1, v2, hybrid_*, playbook_v2*, test_results, old audits) # HISTORICAL
├── scripts/
│   ├── anatomy/                     # ACTIVE: validate_clean_anatomy_v1.py, smoke_test_anatomy_runtime.py, run_source_coverage_loop.py
│   └── *.py (test_*, audit_*, build_*, upsert_*)  # MOSTLY HISTORICAL one-off tests / old pipelines
├── *.py (many root)                 # anatomy_*.py (some active in hybrid), gpt_refiner*, playbook_*, reformat_*, embed_*.py, deleteall_pinecone.py, etc. → many HISTORICAL
├── embed_*.txt (anki, ob, pp, hipknee, millers, oite, orthoanatomy, pocketpimp)  # HISTORICAL embedding sources
├── normalized_*.jsonl / .csv / .v1* # HISTORICAL (multiple generations of fact normalization)
├── output_vectorversion_*           # HISTORICAL (old vector versioned outputs)
├── final_normalized_*               # HISTORICAL
├── data_embed_topinecone.py, embed_topinecone_*.py, deleteall_pinecone.py, upsert_*.py, checkvector.py, audit_vectordb.py  # HISTORICAL pinecone tooling
├── anatomy_checkpoint.json, reference.txt, requirements.txt, *.sql, *.db  # MIXED (some supporting)
├── docs/                            # NEW (this audit)
│   └── repository_audit/            # (will contain all generated reports)
├── archive/                         # TO BE POPULATED (historical moved here)
└── venv/, __pycache__, .git         # BUILD / VCS (ignore)
```

## Classification Summary (Initial Heuristic + Code Reference Scan)

**ACTIVE (~30-40 core files + data/anatomy/ + recent reports/scripts):**
- All files under `data/anatomy/` (current canonical BroBot anatomy v1)
- main.py + direct runtime imports (vector_search, query_refiner, gpt_refiner, procedure_registry, approach_router, anatomy_gpt (hybrid), hybrid/playbook builders, anki, FastAPI deps)
- scripts/anatomy/ (validate, smoke, coverage loop)
- approach_router/ + lower/upper/spine catalogs (still loaded in main for APPROACH_CATALOG_PATHS)
- Recent reports: anatomy_v1_*, brobot_*post_cleanup, integration_readiness, source_coverage_*, etc.
- requirements.txt, cpt related if used (low confidence)

**HISTORICAL (majority of data + old reports + embed artifacts + test scripts):**
- data/anatomy_integration/, anatomy_modules/* (all v*), anatomy_sources/* (v1-3), anatomy_miller_gold_v1/
- data/approach_playbook/ (v1/v2 versions + old maps; v1_4 superseded by data/anatomy/registry/procedures.jsonl)
- All root `normalized_*`, `output_vectorversion_*`, `final_normalized_*`, `embed_*.txt` (multiple generations of fact embedding experiments)
- Most `reports/` (phase2/3, v1_1, v2, hybrid_approach_miller, playbook_v2_*, old audits, test_results json)
- Most `scripts/*.py` except anatomy/ subdir (one-off tests for old pipelines: test_playbook_v2*, test_phase3*, test_hybrid*, audit_playbook_v2*, build_local*, upsert*, validate_pinecone, etc.)
- Pinecone tooling scripts (deleteall, embed_topinecone*, data_embed*, checkvector, audit_vectordb)
- Legacy anatomy_*.py builders that are no longer primary (anatomy_pinecone_retriever, anatomy_retriever, anatomy_extraction, anatomy_metadata_insertion, anatomy_term_*, reformat_anki_*, etc.)
- data/anatomy_legacy_archive/ (previous quarantine)
- __pycache__, stray "f" file, rejected_*.log, metadata_dictionary*.updated*, normalize_metadata.py (old)

**UNKNOWN / Needs Review (borderline or low-reference):**
- Some root anatomy_*.py (anatomy_context_builder, anatomy_curator, playbook_anatomy_builder — partially active in hybrid paths)
- cpt_*, setup_db.py, db_dictionary_generator.py, update_jsonl.py, csv_to_jsonl.py, inspect_metadata.py, ortho_concepts.py (side utilities)
- anatomy_checkpoint.json, reference.txt
- Some lower-confidence reports (e.g. source_gap_priority_queue.jsonl — may be current for gap loop)
- Old approach catalogs in data/ if no longer primary

**Obvious Duplicates / Versioned Groups:**
- anatomy_modules/ vs data/anatomy/modules/ (v1_4 copied, old versions historical)
- anatomy_sources/ vs data/anatomy/sources/
- approach_playbook/ v1/v2 vs current data/anatomy/registry/
- Multiple normalized_* generations + output_vectorversion_*
- reports/ full of v1_1, v2, phase*, hybrid* vs recent anatomy_v1_*
- scripts/test_* and scripts/audit_* for old versions

**File counts (approx, non-venv):**
- Python source: ~80-100
- Data artifacts (jsonl/json): 150+
- Reports: 90+
- Root loose artifacts: 30+

See version_groups.md and source_of_truth.md for deeper analysis.
