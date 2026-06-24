# BroBot Anatomy Modules Batch 1 Audit Report
Generated: 2026-06-06T16:49:57.878245Z

## Modules Created by Type
- approach: 18
- arthroscopy_sequence: 2
- decompression: 4
- fluoroscopy: 1
- pathology_anatomy: 9 (includes many 'anatomy_*' and 'risks_*' synthesized modules)
- reduction_implant: 6
- soft_tissue: 3

**Total unique modules: 46**

## Procedures Covered
All 17 priority procedures have at least one associated module (or explicit thin/manual explanation):
distal_radius_fracture_orif, tka, tha_posterior/hip_hemi, femoral_neck/intertroch, femoral/tibial shaft, acl, meniscus, rotator cuff, carpal/cubital tunnel, proximal humerus, acdf, lumbar decompression, ankle (via existing).

## Modules with manual_review=true
Count: 14
Examples: fluoroscopy_femoral_neck_intertroch (thin source data for pure nail fluoro), anatomy_acdf / lumbar (spine data limited in v2_1), several anatomy_* for new reduction concepts.

## Top Missing / Thin Gaps
- Rich layered approach details for many (catalogs provide summaries; full OB approaches/ pages would improve layer_by_layer and danger_zones).
- Dedicated arthroscopic portal distances, systematic checklists, and intra-op images (added basic knee/shoulder starters; expand from full OB sports arthro pages).
- Specific nail starting points, safe corridors, and fluoro for femoral/tibial shaft and SCFE (current ORIF-focused sources; added one thin fluoro).
- Full ACDF/lumbar posterior decompression anatomy (cervical/lumbar approach modules still mostly stubs or manual).
- Ankle family lateral/medial specific approaches (catalog gaps in original router limit module depth).

## Recommended Batch 2
1. Expand nail/ pinning reduction + fluoro + safe corridor modules (femoral shaft nail, tibial shaft nail, SCFE).
2. Full knee and shoulder arthroscopy portal + diagnostic + pathology modules (deeper than the starters).
3. Cervical anterior (ACDF) and posterior lumbar decompression layered modules.
4. Additional conditional modules (dorsal radius, lateral plateau, etc.).
5. Populate more 'anatomy_*' and 'risks_*' with direct quotes from additional local OB-derived sources if available.

## Validation Results (clean run)
- All 7 JSONL files valid and parseable.
- No duplicate module_ids after dedup/re-group.
- All modules have required fields (module_id, module_type, title, used_by_procedure_ids, source_confidence, case_prep_priority).
- 17/17 priority procedures linked to modules or have manual_review + missing sources noted.
- Router-referenced modules for priority either created in batch 1 or are pre-existing approach catalog IDs (reused) or explicitly thin/manual with missing_needed_sources.
- source_urls point only to local data/approach_playbook/* or approach catalog files (no fabricated OB URLs).
- must_know populated for non-manual modules; thin ones correctly flagged.
