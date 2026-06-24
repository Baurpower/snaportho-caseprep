# Orthobullets Playbook Thin Entries Audit

**Source**: data/approach_playbook/orthobullets_procedure_playbook_v1.jsonl (38 entries total)
**Prior reports cross-referenced**: orthobullets_procedure_playbook_qc.md, playbook_primary_test_results.md, procedure_to_approach_map_qc.md, existing_approach_catalog_inventory.md

## Methodology for "thin supported"
- Excluded manual_review=true entries (11: bimalleolar_*, trimalleolar_*, pilon_*, calcaneus_*, olecranon_*, pelvis_ring_*, cubital_*, clavicle_*, supracondylar_pediatric, hallux_valgus_*, trigger_finger_*). These are intentionally limited due to catalog gaps.
- For non-manual_review (supported or partially supported by map with recommended_approach_ids):
  - Counted: important_anatomy, structures_at_risk, landmarks, approach_notes.
  - Flagged if any <2 (or overall low total <4-5 for "thin").
  - Also considered prior test results showing weak outputs (mostly quiz instead of anatomy) and low prior enrichment counts from QC.

## Identified Thin Supported Entries
Many entries have 0 or very low counts because v1 focused enrichment on a few core ones (distal radius, some THA/hip, femoral shaft partial, TKA basic). 26+ flagged in analysis with low counts.

Prioritized list based on task (high volume, good catalog match, prior test weakness, resident importance for case-prep):

1. **tka** (Total Knee Arthroplasty):
   - ia=1, sar=1, lm=0, an=1
   - recs=1 (approach_lower_ext_knee_anterior_medial_parapatellar)
   - Current content (from v1): basic medial parapatellar description, infrapatellar saphenous branch risk (from approach page), exposure note.
   - Weak per prior tests: output relies on quiz or limited Miller; needs more OB-supported anatomy for extensor mechanism, landmarks (patella, tubercle, joint line), risks (geniculars, skin), pearls.
   - Priority: #1 as specified. High volume recon case.

2. **carpal_tunnel_release**:
   - ia=0, sar=0, lm=0, an=0
   - recs=1 (approach_wrist_carpal_tunnel)
   - recs good match, but no anatomy/landmarks/risks populated despite OB having CTR page with transverse carpal ligament, median nerve (motor branch at risk), etc.
   - Priority high: common hand procedure, prior tests weak.

3. **femoral_shaft_fracture_orif**:
   - ia=2, sar=1, lm=0, an=1 (partial from prior, e.g. deforming forces, compartments)
   - recs=2 (thigh lateral + posterolateral)
   - Some content (linea aspera, blood loss, deforming forces from OB 1040), but missing landmarks (e.g. greater trochanter? ), more risks (profunda perforators), specific approach notes for lateral ORIF.
   - Good catalog match, common trauma.

4. **tha_posterior** (and variants like tha_anterior, tha_lateral, hip_hemiarthroplasty):
   - tha_posterior: ia=1, sar=2, lm=1, an=1 (some enrichment: intervals, sciatic, inferior gluteal, GT/ERs landmarks)
   - tha_anterior: ia=1, sar=0, lm=0, an=1
   - tha_lateral: ia=1, sar=1, lm=0, an=1
   - hip_hemi: ia=1, sar=1, lm=0, an=1
   - Some data present, but gaps in landmarks, additional risks (e.g. more on femoral vessels for anterior), pearls specific to exposure.
   - Prior QC noted as "strongest" but still thin in some categories; improve if gaps.

5. **distal_radius_fracture_orif**:
   - Has more (ia~4+, from prior FCR/dorsal/Henry enrichment: columns, watershed, Lister's, PIN/radial a./median branches).
   - Check for missing obvious OB-supported: e.g. more on pronator quadratus, FPL protection, specific dorsal vs volar indications, additional landmarks (radial styloid details).
   - Only if missing; it was one of the "strongest" but task says "only if missing obvious".

Other thin supported (lower priority for this task but noted):
- proximal_humerus_fracture_orif (0s, recs=2: deltopectoral + lateral split)
- radial_head_fracture_orif (0s, recs=1: Kocher)
- both_bone_forearm_fracture_orif (0s, recs=1: Henry)
- acetabulum_fracture_orif_anterior/posterior (0s, good recs= ilioinguinal/KL)
- acl_reconstruction (0s, recs=1: parapatellar)
- rotator_cuff_repair (0s, recs=2: lateral split + deltopectoral)
- patella_fracture_orif (0s, recs=1: parapatellar)
- tibial_plateau_fracture_orif (0s, recs=2: parapatellar + lateral)
- scaphoid_fracture_orif (0s, recs=2: volar Henry + dorsal)
- monteggia_fracture_orif (0s, recs=1: Henry + conditional Kocher)
- achilles_tendon_repair (0s, recs=1: posteromedial ankle)
- total_ankle_arthroplasty (0s, recs=1: anterior ankle)
- high_tibial_osteotomy (0s, recs=2: medial + parapatellar)
- intertrochanteric_hip_fracture_orif (0s, recs=2: lateral Hardinge + thigh lateral)
- femoral_neck_fracture_orif_young (0s, recs=2: Smith-Peterson + Watson-Jones)
- revision_tha (0s, recs=2)
- revision_tka (0s, recs=1)
- ankle_arthrodesis (0s, recs=1: anterior ankle)

From prior QC/playbook tests: TKA, carpal, femoral shaft, some THA/hip showed weak anatomy output (relied on quiz or limited Miller).

## Summary of Thin Supported
- ~25+ non-manual supported entries are thin (mostly 0-1 in categories) because v1 enrichment was selective (distal radius, some hip/THA/femoral shaft/TKA basic).
- Catalog has good coverage for many (e.g. parapatellar for knee cases, Henry for forearm/wrist, hip approaches).
- Highest priority per task + volume/impact: TKA (recon staple, correct approach selected but thin content), carpal_tunnel_release (hand common, 0s), femoral_shaft_fracture_orif (trauma common, partial), THA variants (if gaps), distal_radius (check for missing).
- Goal for v1.1: Improve TKA first (target ia>=3-4, sar>=3, lm>=3, an>=3 with OB support), then at least 4-5 others (carpal, femoral shaft, perhaps patella, tibial plateau, one THA gap filler).
- Stop if OB pages lack explicit support (e.g. no dedicated "landmarks" section for some).

This audit confirms the problem: supported procedures have correct approach IDs from map, but thin OB-derived content leads to weak final outputs even with playbook primary + Miller support.

Next: Task 2, deep TKA using only OB pages (main TKA recon/12289, TKA approaches recon/5031, medial parapatellar approaches/12028, related dangers/anatomy snippets from searches).
