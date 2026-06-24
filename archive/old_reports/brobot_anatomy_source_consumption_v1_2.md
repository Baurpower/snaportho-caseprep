# BroBot Anatomy Source Consumption v1_2

**Date:** 2026-06-06T17:31:29.754440Z  
**Input source library:** orthobullets_source_library_v1.jsonl (51 records)  
**Base:** v1_1 router + 7 module files (no v1_1 files modified)  
**Output:** v1_2 router + 7 module files + this report + remaining gaps report

## 1. Number of source records consumed
51 (12 success/live or snippet-augmented including 1047 ankle, 1022 olecranon, 1011 clavicle, 12001 anterior cervical, 6009 wrist, 7030 lisfranc + 39 existing_local_derived from v1_1 module provenance with OB URLs/sections).

## 2. Number of procedures improved
16 (focused on low-score/manual + high-yield with usable concrete facts: ankle family, olecranon, clavicle, ACDF, Lisfranc, wrist TFCC, and several other score 0-2 with matching sources or new modules).

## 3. Score distribution before vs after
Before (v1_1): {0: 5, 1: 13, 2: 12, 3: 1, 4: 29}  
After (v1_2): {0: 4, 1: 5, 2: 10, 3: 12, 4: 29}

## 4. Procedures moved to ≥3
11: bimalleolar_ankle_orif, trimalleolar_ankle_orif, pilon_ankle_fracture_orif, calcaneus_fracture_orif, olecranon_fracture_orif, clavicle_fracture_orif, total_ankle_arthroplasty, ankle_arthrodesis, lisfranc_orif, acdf, wrist_arthroscopy_tfcc

## 5. New modules created
7: approach_ankle_lateral_fibula, approach_ankle_medial_malleolus, approach_elbow_posterior_olecranon, approach_clavicle_superior, reduction_lisfranc_tmt_columns, portal_wrist_arthroscopy_tfcc, arthroscopy_wrist_tfcc_diagnostic_sequence

## 6. Existing modules enriched
8 (examples: anatomy_bimalleolar_ankle_orif and siblings, anatomy_olecranon_fracture_orif, anatomy_clavicle_fracture_orif, anatomy_lisfranc_orif, approach_cervical_anterior (or posterior cervical), plus minor on strong ones where additional provenance added).

## 7. Manual_review modules resolved
Several (ankle family, olecranon, clavicle, lisfranc, acdf cervical approach, wrist TFCC portals/diag) set manual_review=false or reduced after concrete source facts + new modules populated. Some remain true where catalog gaps (dedicated ankle lateral/medial cards) or thin extraction persist.

## 8. Procedures still below 3
19 (see remaining_gaps_v1_2.md for full list with exact missing domains/facts needed).

## 9. Why each remaining weak procedure is still weak
See brobot_anatomy_remaining_gaps_v1_2.md (per-proc: missing domains, exact facts still needed from sources, suggested pages, gap type: source/extraction/catalog/manual/classification).

## 10. Validation results
(See separate validation run output below in this process.) All checks passed: 60 unique pids in v1_2 router, no dup module_ids, required exist or noted in missing, >=3 have >=5 questions, modules have source provenance or explicit manual, no fabricated URLs, v1_1 files untouched, facts traceable to source_lib or prior local OB provenance, gaps report covers all remaining <3.

**Key improvements examples:**
- Ankle family (bimalleolar etc.): now have approach_ankle_lateral_fibula + medial_malleolus + enriched path anatomy with 1047 concrete (deltoid layers, syndesm 4 components + strongest, 4 approaches, specific NV/tendons at risk, biomech). Score 1->3, questions 2->6, manual resolved for content.
- Olecranon: approach_elbow_posterior_olecranon with ulnar protection, V-osteotomy, triceps, full dangers from 1022+12005. Score 1->3.
- Similar for clavicle (new approach + deforming/SAR), ACDF (full fascia/landmarks/RLN/sympathetic from 12001), Lisfranc (columns + reduction seq from 7030), wrist TFCC (complete portals + midcarpal + TFCC + checklist + 8mm ulnar n risk from 6009).

**Process notes:** Selective enrichment only (no blind paste). Facts filtered to concrete case-prep (approaches, intervals, SAR, landmarks, reduction, portals, deforming, biomech, nerve course). Legacy map text excluded from modules. New modules only where router missing + source supported + no clean existing fit. All 60 router entries processed for v1_2 (light touch on already-strong 4s). Procedure remains unit of quality.
