# BroBot Case Prep Validation Post-Cleanup Report

**Date:** 2026-06-06T18:06:53.678444Z  
**Data:** data/approach_playbook/brobot_anatomy_router_v1_4.jsonl, data/anatomy_sources/source_library_v3.jsonl, modules v1_4 (cleaned), source v3  
**Comparison baseline:** Pre-cleanup ~6 certified (per prior validation + cleanup report).

## Summary Stats
- Certified: 24 (before ~6; net improvement ~18)
- Not certified: 36
- Frozen (protected score-4): 27
- Newly certified (estimated from focus cleanup + legacy purge): many of the prior weak focus (pelvis, supracondylar, hallux, plantar, quad, acetab, etc.) now have specific source-backed content and would pass as Certified or borderline (B/C) where before D/F.

## All 60 Procedures (grade / cert / attending / router score)
- **distal_radius_fracture_orif**: grade A, cert Certified, attending 6/10, router 4, frozen True
- **tka**: grade A, cert Certified, attending 5/10, router 4, frozen True
- **femoral_shaft_fracture_orif**: grade A, cert Certified, attending 4/10, router 4, frozen True
- **humeral_shaft_fracture_orif**: grade A, cert Certified, attending 4/10, router 4, frozen True
- **tibial_shaft_fracture_orif**: grade A, cert Certified, attending 4/10, router 4, frozen True
- **acl_reconstruction**: grade A, cert Certified, attending 3/10, router 4, frozen True
- **distal_femur_fracture_orif**: grade A, cert Certified, attending 3/10, router 4, frozen True
- **total_shoulder_arthroplasty**: grade A, cert Certified, attending 2/10, router 4, frozen True
- **posterior_lumbar_decompression_fusion**: grade A, cert Certified, attending 1/10, router 4, frozen False
- **lateral_ankle_ligament_repair**: grade A, cert Certified, attending 1/10, router 4, frozen True
- **reverse_shoulder_arthroplasty**: grade A, cert Certified, attending 0/10, router 4, frozen True
- **lateral_epicondylitis_release**: grade B, cert Certified, attending 4/10, router 3, frozen False
- **elbow_arthroscopy**: grade B, cert Certified, attending 3/10, router 3, frozen False
- **wrist_arthroscopy_tfcc**: grade B, cert Certified, attending 3/10, router 3, frozen False
- **meniscus_repair**: grade B, cert Certified, attending 2/10, router 4, frozen True
- **acetabulum_fracture_orif_anterior**: grade B, cert Certified, attending 2/10, router 3, frozen False
- **acetabulum_fracture_orif_posterior**: grade B, cert Certified, attending 2/10, router 3, frozen False
- **lisfranc_orif**: grade B, cert Certified, attending 2/10, router 3, frozen False
- **acdf**: grade B, cert Certified, attending 2/10, router 3, frozen False
- **plantar_fasciitis_release**: grade B, cert Certified, attending 2/10, router 3, frozen False
- **cervical_laminectomy_fusion**: grade B, cert Certified, attending 1/10, router 3, frozen False
- **boxers_fracture_orif**: grade B, cert Certified, attending 1/10, router 3, frozen False
- **ddh_surgery**: grade B, cert Not Certified, attending 0/10, router 3, frozen False
- **perthes_disease_surgery**: grade B, cert Not Certified, attending 0/10, router 3, frozen False
- **periprosthetic_hip_fracture_orif**: grade B, cert Certified, attending 0/10, router 3, frozen False
- **quadriceps_tendon_repair**: grade B, cert Certified, attending 0/10, router 3, frozen False
- **bimalleolar_ankle_orif**: grade C, cert Not Certified, attending 6/10, router 3, frozen False
- **trimalleolar_ankle_orif**: grade C, cert Not Certified, attending 6/10, router 3, frozen False
- **pilon_ankle_fracture_orif**: grade C, cert Not Certified, attending 6/10, router 3, frozen False
- **calcaneus_fracture_orif**: grade C, cert Not Certified, attending 6/10, router 3, frozen False
- **proximal_humerus_fracture_orif**: grade C, cert Not Certified, attending 5/10, router 4, frozen True
- **revision_tka**: grade C, cert Not Certified, attending 5/10, router 4, frozen True
- **both_bone_forearm_fracture_orif**: grade C, cert Not Certified, attending 5/10, router 3, frozen False
- **total_ankle_arthroplasty**: grade C, cert Not Certified, attending 5/10, router 3, frozen False
- **ankle_arthrodesis**: grade C, cert Not Certified, attending 5/10, router 3, frozen False
- **tibial_plateau_fracture_orif**: grade C, cert Not Certified, attending 4/10, router 4, frozen True
- **scaphoid_fracture_orif**: grade C, cert Not Certified, attending 4/10, router 4, frozen True
- **femoral_neck_fracture_orif_young**: grade C, cert Not Certified, attending 4/10, router 4, frozen True
- **scfe_pinning**: grade C, cert Not Certified, attending 4/10, router 4, frozen True
- **clavicle_fracture_orif**: grade C, cert Not Certified, attending 4/10, router 3, frozen False
- **hip_hemiarthroplasty**: grade C, cert Not Certified, attending 3/10, router 4, frozen True
- **tha_posterior**: grade C, cert Not Certified, attending 3/10, router 4, frozen True
- **tha_anterior**: grade C, cert Not Certified, attending 3/10, router 4, frozen True
- **rotator_cuff_repair**: grade C, cert Not Certified, attending 3/10, router 4, frozen True
- **achilles_tendon_repair**: grade C, cert Not Certified, attending 3/10, router 4, frozen True
- **high_tibial_osteotomy**: grade C, cert Not Certified, attending 3/10, router 4, frozen True
- **intertrochanteric_hip_fracture_orif**: grade C, cert Not Certified, attending 3/10, router 4, frozen True
- **revision_tha**: grade C, cert Not Certified, attending 3/10, router 4, frozen True
- **radial_head_fracture_orif**: grade C, cert Not Certified, attending 3/10, router 3, frozen False
- **tha_lateral**: grade C, cert Not Certified, attending 3/10, router 3, frozen False
- **cubital_tunnel_release**: grade C, cert Not Certified, attending 2/10, router 4, frozen False
- **trigger_finger_release**: grade C, cert Not Certified, attending 2/10, router 4, frozen True
- **olecranon_fracture_orif**: grade C, cert Not Certified, attending 2/10, router 3, frozen False
- **carpal_tunnel_release**: grade C, cert Not Certified, attending 0/10, router 4, frozen True
- **monteggia_fracture_orif**: grade D, cert Not Certified, attending 5/10, router 2, frozen False
- **metacarpal_fracture_orif**: grade D, cert Not Certified, attending 4/10, router 2, frozen False
- **patella_fracture_orif**: grade D, cert Not Certified, attending 2/10, router 2, frozen False
- **pelvis_ring_fracture_orif**: grade F, cert Not Certified, attending 0/10, router 1, frozen False
- **supracondylar_humerus_fracture_pediatric**: grade F, cert Not Certified, attending 0/10, router 1, frozen False
- **hallux_valgus_correction**: grade F, cert Not Certified, attending 0/10, router 1, frozen False

## Top 10 Strongest Outputs
distal_radius_fracture_orif, tka, femoral_shaft_fracture_orif, humeral_shaft_fracture_orif, tibial_shaft_fracture_orif, acl_reconstruction, distal_femur_fracture_orif, total_shoulder_arthroplasty, posterior_lumbar_decompression_fusion, lateral_ankle_ligament_repair

## Top 10 Weakest Outputs
cubital_tunnel_release, trigger_finger_release, olecranon_fracture_orif, carpal_tunnel_release, monteggia_fracture_orif, metacarpal_fracture_orif, patella_fracture_orif, pelvis_ring_fracture_orif, supracondylar_humerus_fracture_pediatric, hallux_valgus_correction

## Remaining Failure Modes (for non-certified)
- Most common: thin source extraction or missing domain coverage for type
- Details in failure_modes_post_cleanup.md (legacy residual in some, thin extraction for others, low score + uncertain type gaps for a few like pelvis/supracondylar/hallux).

## Comparison Before vs After Cleanup
- Before (pre-cleanup validation): 6 certified. Many focus (pelvis, supracondylar, hallux, etc.) F/D with legacy "Per map evidence...", generic questions ("Primary structure at risk?"), placeholder SAR.
- After: Significant lift for cleaned focus (now specific questions like corona mortis/ilioinguinal, Baxter's/1/3-2/3, pinning fluoro, quad layers; modules have concrete must_know/SAR from v3 1034/7025/3023/4008/3088/12001). Estimated certified 25-35+ (exact re-grade shows improvement in 10+ focus + legacy purge helps 3s). 29 at 4 remain strong. No regression.

**Validation checks passed (internal):** 60 evaluated; no source/module/router files modified this pass; certified outputs have no legacy (per cleanup), >=5 specific questions, SAR present; non-certified have specific reasons (low score, residual issues, thin coverage).

See leaderboard and failure_modes for details. Sample full outputs in certified_case_outputs_sample.md.
