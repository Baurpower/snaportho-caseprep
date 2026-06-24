# Orthobullets Procedure Playbook v2 QC Report

**Date**: 2026 (post v2 expansion)
**Base**: v1.1 (38 procedures, data/approach_playbook/orthobullets_procedure_playbook_v1_1.jsonl)
**Derived**: v2 (data/approach_playbook/orthobullets_procedure_playbook_v2.jsonl + .yaml) — v1.1 files untouched/preserved.
**Method**: Audit of v1.1 (thin supported + catalog gaps) + OB-only candidate inventory (Task 2) + selected batch enrichment (query priorities: ACL, rotator cuff, prox humerus, both-bone, scaphoid, Achilles, Lisfranc, SCFE, DDH, spine decomp/fusion + high-yield missing like humeral/tibial shaft, total/reverse shoulder, meniscus, lateral ankle, metacarpal, distal femur, tennis elbow, etc.). All new facts from explicit Orthobullets page content (search snippets + pages: 1015/12061 for prox humerus, 3043 for cuff, 3008 for ACL, 7030 for Lisfranc, 4040 for SCFE, 4118 for DDH, 12001/12003 for spine approaches, 1043/1016 for shafts, etc.). Catalog discipline: only 30 real IDs used for recs; gaps → manual_review + [] recs. v1.1 entries copied unchanged except targeted clear improvements on thin supported with recs (e.g. prox humerus, rotator cuff, ACL, both-bone, scaphoid, Achilles).

## Total Procedures
- **60** (38 preserved from v1.1 + 22 net new/enriched in this pass).
- Acceptable per guidance (quality over exact 100; stopped at 60 as evidence for additional fields on more candidates was thin or catalog-blocked; can expand further in v2.1 with same rules).

## New Procedures Added (22)
humeral_shaft_fracture_orif, lisfranc_orif, scfe_pinning, acdf, posterior_lumbar_decompression_fusion, total_shoulder_arthroplasty, tibial_shaft_fracture_orif, meniscus_repair, ddh_surgery, reverse_shoulder_arthroplasty, perthes_disease_surgery, lateral_ankle_ligament_repair, metacarpal_fracture_orif, distal_femur_fracture_orif, lateral_epicondylitis_release, cervical_laminectomy_fusion, plantar_fasciitis_release, periprosthetic_hip_fracture_orif, elbow_arthroscopy, wrist_arthroscopy_tfcc, quadriceps_tendon_repair, boxers_fracture_orif (plus in-place enrichments to ACL, rotator cuff, proximal humerus, etc.).

## Procedures Preserved from v1.1
All 38 v1.1 entries carried forward as base (including 11 manual_review for catalog gaps like bimalleolar/trimalleolar/pilon/calcaneus/olecranon/cubital/clavicle/supracondylar/hallux/trigger/pelvis_ring). Minor targeted adds only to thin supported with existing recs and new OB support (prox humerus, rotator cuff, ACL, both bone, scaphoid, Achilles).

## High / Medium / Low / Manual Review Counts
- manual_review: **22** (11 original + ~11 new from spine/Lisfranc/gaps + some thin).
- With nonempty recommended_approach_ids: 38 (many from v1.1 strong mappings + new like humeral shaft, tibial shaft, total shoulder, meniscus, lateral ankle, distal femur, tennis elbow).
- High-confidence entries (≥1 high-conf fact): ~29.
- Entries with ia>0: 28; sar>0: 20; lm>0: 10; an>0: 40; pimp>0: most.

## Specialty Distribution (improved breadth)
- trauma: 23 (up from 19)
- recon: 10 (up)
- sports: 8 (up)
- hand: 7 (up)
- foot_ankle: 5
- pediatrics: 4 (up)
- spine: 3 (new)

## Procedures with Content Fields
- important_anatomy populated: 28 (big increase from v1.1's ~9)
- structures_at_risk: 20 (from ~6)
- landmarks: 10 (from ~5)
- approach_notes: 40 (strong)
- pimp_topics: nearly all (as before)

## Catalog Gap Count
- ~22 manual_review (original 11 ankle/foot/elbow/hand/peds gaps + new spine 3 + Lisfranc + some hand/foot/peds additions). 
- Confirmed gaps (no IDs): all spine (cervical anterior/posterior, lumbar posterior, transthoracic), Lisfranc/midfoot, dedicated lateral calcaneus/fibula/medial malleolus (ankle catalog limited), posterior elbow/olecranon/cubital (only Kocher + humerus posterior triceps), clavicle specific.
- New mappings succeeded where catalog strong: knee sports (parapatellar), shoulder recon (deltopectoral + lateral split), forearm (Henry), leg shafts (lateral/medial leg), etc.

## Weakest Entries
- Original manual 11 (bimalleolar etc.) + new spine (acdf, posterior_lumbar, cervical_laminectomy), Lisfranc, SCFE (manual due to pinning/dislocation approach not in catalog), some thin supported that were not enriched this pass (radial_head still low, olecranon manual, etc.).
- Many new added as manual or sparse per rules (no fake facts or IDs).

## Strongest Entries (post v2)
- distal_radius_fracture_orif (still leader)
- tka (rich post v1.1 + preserved)
- tha_posterior / hip variants
- proximal_humerus_fracture_orif (now enriched with Neer, deforming forces, blood supply (ant/post circumflex/arcuate), axillary/musculocutaneous/cephalic dangers, deltopectoral + lateral split notes)
- rotator_cuff_repair (now mini-open lateral deltoid split, arthroscopic margin convergence/footprint/double-row, subscapularis comma sign)
- acl_reconstruction (now has footprint stability, parapatellar notes)
- femoral_shaft (preserved strong)
- new strong-ish: humeral_shaft (radial n./Holstein-Lewis, approaches), total/reverse shoulder (deltopectoral), lateral ankle ligament (Brostrom), distal femur (Hoffa, parapatellar/lateral), tennis elbow (Kocher/PIN/LCL), metacarpal (dorsal, angulation)
- spine entries have excellent explicit approach facts (ACDF transverse/SCM/carotid/longus colli/sympathetic; lumbar midline/subperiosteal/flavum/dura) but gated manual due to no catalog IDs.

## Entries Needing Manual Review
- 22 listed above. Router/gate should treat as supported=false or limited (no guess). Catalog expansion needed for full deterministic (spine, Lisfranc, more ankle/foot, posterior elbow, etc.).

## Unsupported Fields Intentionally Blank
- All manual_review have empty anatomy/risk/landmark/note arrays (or minimal) + [] recs.
- No MCL/posterior neurovasc invented for TKA variants; no full spine anatomy beyond approach (focus per schema).
- New spine/Lisfranc/SCFE etc. have approach_notes or anatomy only where OB pages explicitly support; risks/landmarks blank if not detailed on the fetched pages.
- Every populated item has source_url + source_section + confidence (high/medium).

## Validation
- Orthobullets only (all new/added facts from site: searches + page content on 1015/12061, 3043, 3008, 7030, 4040, 4118, 12001, 12003, 1016, 1043, 3002, 6002, 1041, 3083, 4119, etc.; no Miller/MedGemma/GPT knowledge/AO/other).
- v1.1 preserved exactly as starting point.
- v2 created separately.
- No BroBot/Pinecone/Miller corpus changes.
- Catalog IDs only (30 real); no invention.
- Quality prioritized: stopped expansion at 60 when additional candidates would require padding or unsupported facts.

v2 significantly broadens coverage (trauma/sports/peds/spine/recon) while keeping the primary layer OB-curated and deterministic where catalog supports. Router can now classify more common cases to richer playbook content.
