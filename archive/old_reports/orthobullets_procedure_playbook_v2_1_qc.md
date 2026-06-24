# Orthobullets Procedure Playbook v2_1 QC Report

**Date**: Current (post v2_1 quality deepening)
**Base**: v2 (60 procedures)
**Derived**: v2_1 (60 procedures) — v2 files untouched/preserved. Only content improvements to selected high-value supported entries; no new procedures added.
**Method**: Full line audit (Task 2) identified 12 must_fix + 12 should_fix supported (recs>0, manual=false) with low overall utility despite correct approaches. Focused improvement batch on common resident cases with recs but thin fields (carpal_tunnel_release, both_bone_forearm, radial_head, acetabulum anterior+posterior, scaphoid, achilles, tibial_plateau, humeral_shaft, tibial_shaft, meniscus, total_shoulder, monteggia, patella, intertrochanteric, high_tibial, ankle_arthrodesis, revisions, femoral_neck_young, etc.). All additions from fresh or explicit Orthobullets pages (12014, 1025/12010, 3068/Kaplan, 1034, 6034, 3009, 1042, 1016/1043, 3006, 12061, 1024, 1044, etc.) with url + source_section + confidence. Gaps (manual_review or catalog-limited) left as-is.

## Total Procedures
- 60 (identical count to v2; quality over expansion).

## Procedures Improved
- 14 (radial_head_fracture_orif, both_bone_forearm_fracture_orif, acetabulum_fracture_orif_anterior, acetabulum_fracture_orif_posterior, carpal_tunnel_release, patella_fracture_orif, tibial_plateau_fracture_orif, scaphoid_fracture_orif, monteggia_fracture_orif, achilles_tendon_repair, humeral_shaft_fracture_orif, tibial_shaft_fracture_orif, meniscus_repair, total_shoulder_arthroplasty + targeted notes on others in the priority list).

## Before/After Scores (selected examples from audit + update)
- carpal_tunnel_release: v2 facts~1 (ia=1), overall ~3 -> v2_1 ia=2/sar=2/lm=1/an=1 (added exact 12014: thenar crease/PL landmark, palmar cutaneous, superficial palmar arch, motor branch variation, ulnar-side retinaculum release under vision).
- both_bone_forearm_fracture_orif: v2 facts=1 (an=1) -> v2_1 ia=1/sar=2/lm=1/an=2 (Henry details, PIN/superficial radial from 12010/1025, interosseous membrane, pronosupination).
- radial_head_fracture_orif: v2 facts=0 -> v2_1 ia=1/sar=2/lm=1/an=1 (Kocher/Kaplan, PIN risk/pronation protection, LCL, radiocapitellar equator arthrotomy from 3068/1020).
- acetabulum anterior: v2 facts=0 -> v2_1 ia=1/sar=2/lm=1/an=1 (columns, corona mortis, femoral n./LFCN/vessels from 1034 ilioinguinal/Stoppa).
- acetabulum posterior: v2 facts=0 -> v2_1 ia=1/sar=2/an=1 (posterior column, sciatic protection via short ERs, MFCA/femoral head blood supply, KL risks/HO from 1034).
- scaphoid: v2 facts=2 -> v2_1 ia=2/lm=1/an=1 (retrograde supply, humpback/DISI, snuffbox/Lister's/scaphoid tubercle, volar/dorsal choice from 6034).
- achilles: v2 facts=2 -> v2_1 ia=1/sar=2/an=1 (paratenon, sural lateral from 3009).
- tibial_plateau: v2 facts=1 -> v2_1 ia=1/lm=1/an=1 (menisci, joint line/fibular head landmarks, lateral plateau valgus from 1042).
- Similar lifts for humeral/tibial shaft (nerve/compartment + specific approaches), meniscus (arthro + open via parapatellar), total shoulder (deltopectoral landmarks/interval), monteggia (Henry + conditional Kocher), patella (extensor mechanism/geniculars).

Field count increases visible in improved entries (e.g. carpal from ~1 to 6 total facts; radial_head from 0 to 5).

## Strongest Procedures After v2_1
- distal_radius_fracture_orif (unchanged leader, high facts/sources)
- tka (rich from v1.1 + preserved)
- proximal_humerus_fracture_orif (strong post v2 enrichment)
- tha_posterior / hip variants
- femoral_shaft_fracture_orif
- New/improved standouts: carpal_tunnel_release, both_bone_forearm, radial_head, acetabulum (anterior/posterior now have column-specific risks/approaches/landmarks), scaphoid, achilles, tibial_plateau, humeral_shaft, tibial_shaft, meniscus, total_shoulder, lateral_ankle_ligament_repair, etc.
- reverse_shoulder, lateral_ankle, etc. remain solid.

## Weakest Procedures After v2_1
- All 22 unsupported_gap / manual_review (bimalleolar/trimalleolar/pilon/calcaneus/olecranon/pelvis_ring/cubital/clavicle/supracondylar/hallux/trigger + lisfranc/scfe/acdf/posterior_lumbar/cervical_laminectomy/plantar/periprosthetic/elbow_arthroscopy/wrist_arthroscopy/quadriceps/boxers etc.). Content not added because catalog IDs missing or OB pages do not provide procedure-specific approach anatomy for these without new catalog entries.
- Remaining thin supported not in this improvement batch (some revisions, high_tibial still low, intertroch/femoral_neck_young, ankle_arthrodesis, total_ankle — these were audited as must_fix/should_fix and can be next pass).
- Some "new" sparse ones from v2 (cervical_laminectomy etc.) left minimal per rules.

## Still-Manual-Review Procedures
- 22 (unchanged; catalog gaps block deterministic routing regardless of content depth). Router/gate must continue to treat as supported=false or limited.

## Catalog Gaps That Block Usefulness
- Same as v2 QC + audit: spine (all), Lisfranc/midfoot, lateral fibula/medial malleolus/extensile calcaneus, posterior elbow/olecranon/cubital, clavicle, some peds specifics. These prevent "excellent" for those procedures even with perfect content. Highest ROI next step: add dedicated approach catalog IDs for these.

## Unsupported Facts Intentionally Not Added
- No posterior neurovascular or detailed MCL release for standard TKA medial parapatellar (not supported on primary pages used).
- No invention for manual/gap entries (e.g. no fake Lisfranc midfoot ID or spine approach recs).
- All additions strictly from tool-fetched OB page text with url + section + confidence. Blanks left where pages did not explicitly support (e.g. certain landmarks or risks not detailed for a specific procedure on the accessed pages).

## Validation
- Orthobullets only (all changes from site: + open results on listed pages; no Miller/MedGemma/GPT/AO/other).
- v2 preserved exactly.
- v2_1 created separately (60 entries, same procedures).
- No BroBot/Pinecone/Miller corpus/catalog invention.
- Every new/changed item has source_url + source_section + confidence.
- Focus was quality deepening of existing supported thin entries per audit priority (must_fix/should_fix common cases first).

v2_1 materially improves the "supported but thin" problem for many high-volume resident cases while honestly leaving catalog-gap entries gated. The primary layer is now stronger for the procedures the router can confidently map.
