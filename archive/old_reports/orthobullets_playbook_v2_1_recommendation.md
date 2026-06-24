# Orthobullets Playbook v2_1 Recommendation

**Context**: v2 expanded coverage to 60 but left many supported (recs>0, manual=false) entries thin in anatomy/risks/landmarks/notes despite correct approaches (per line audit: 12 must_fix + 12 should_fix). v2_1 focused on deepening those high-ROI resident cases using only fresh OB evidence.

## Is v2_1 materially better than v2?
**Yes.** 
- 14 procedures received targeted, source-backed improvements (carpal_tunnel_release now has thenar/PL landmarks + palmar cutaneous + motor branch + full retinaculum release details from 12014; both_bone has Henry/PIN/superficial radial + interosseous from 12010/1025; radial_head has Kocher/Kaplan/PIN protection/LCL from 3068/1020; acetabula have columns/corona mortis/sciatic/MFCA from 1034; plus lifts for scaphoid, achilles, tibial_plateau, humeral/tibial shafts, meniscus, total_shoulder, monteggia, patella, etc.).
- Field counts and "why it matters" / actionable steps increased significantly in the priority batch.
- Audit showed many supported cases moved from overall 2 (sparse) toward 3-4.
- Product output test (34 cases) confirms higher "would help scrub tomorrow" potential on improved entries due to specific, OB-cited landmarks, risks, and approach notes.
- No regression on strong entries (distal_radius, tka, proximal_humerus, THA variants, femoral_shaft remain excellent).
- Gaps handled honestly (no fake facts or recs for manual_review cases).

## Which procedures are now excellent?
- Baseline leaders unchanged: distal_radius_fracture_orif, tka, proximal_humerus_fracture_orif (post v2), tha_posterior/hip variants, femoral_shaft_fracture_orif.
- Newly strengthened to strong/excellent: carpal_tunnel_release, both_bone_forearm_fracture_orif, radial_head_fracture_orif, acetabulum_fracture_orif (anterior + posterior), scaphoid_fracture_orif, achilles_tendon_repair, tibial_plateau_fracture_orif, humeral_shaft_fracture_orif, tibial_shaft_fracture_orif, meniscus_repair, total_shoulder_arthroplasty, lateral_ankle_ligament_repair, reverse_shoulder_arthroplasty, and several others in the batch (patella, monteggia, intertrochanteric now have more usable content).
- These now provide resident-level, approach-tied anatomy that directly supports case prep when the router selects them.

## Which remain unsafe/too thin?
- All 22 unsupported_gap / manual_review (bimalleolar/trimalleolar/pilon/calcaneus/olecranon/pelvis_ring/cubital/clavicle/supracondylar/hallux/trigger + lisfranc/scfe/acdf/posterior_lumbar/cervical/plantar/periprosthetic/elbow_arthroscopy/wrist_arthroscopy_tfcc/quadriceps/boxers etc.). These are correctly low because no matching catalog approach ID exists or OB does not support deterministic mapping for the procedure. Router/gate must keep them limited or blocked.
- Remaining thin supported not improved in this pass (some revisions, high_tibial_osteotomy, femoral_neck_young, ankle_arthrodesis, total_ankle — these were audited as must_fix/should_fix and are natural for a follow-up micro-pass).
- A few "new" v2 additions (cervical_laminectomy etc.) were added as minimal/manual and remain sparse (correct per rules).

## Which catalog IDs must be added next?
Highest ROI (to unlock the remaining manual + make more cases excellent):
- Spine: anterior cervical, posterior cervical laminectomy/fusion, posterior lumbar (multiple), transthoracic thoracic.
- Lisfranc / midfoot specific (or clear mapping rules for ankle anterior + additional).
- Lateral fibula / lateral malleolus (for bimalleolar/trimalleolar/pilon/ankle family).
- Extensile lateral calcaneus (or sinus tarsi variant).
- Posterior elbow / olecranon / triceps split dedicated (or confirm mapping to existing humerus posterior).
- Medial malleolus direct or dedicated posterolateral ankle.
- Clavicle / superior shoulder girdle.
- Additional peds specifics if volume justifies.

Adding even 4-6 of these would convert many unsupported_gap to supported and allow content deepening in a future pass.

## Is v2_1 ready to integrate into BroBot?
**Yes, with the same gates as v2.**
- Supported cases with recs now have materially richer, OB-sourced content (playbook primary will deliver better anatomy/risks/landmarks/pearls).
- Manual/gap cases remain gated (no change in router behavior needed).
- All facts have url + section; no invention.
- v2 map remains valid (content improvements only; no recs changed).

Recommend flipping the playbook load path to v2_1.jsonl (and keep map_v2). Re-run utility + supported-case smokes + real prompts for the improved batch (TKA/ACL/rotator/prox hum already strong; carpal/both_bone/radial_head/acetabulum/scaphoid/achilles/shafts now much better).

## Should v2_1 replace v2?
**Yes.** v2_1 is a strict quality superset for the same 60 procedures. v2 can be archived as the "expansion baseline."

## What are the next 10 highest ROI fixes?
1. Finish remaining must_fix/should_fix supported from the audit (high_tibial, intertroch, femoral_neck_young, revisions, ankle_arthrodesis, total_ankle — many have recs and are common).
2. Add the top catalog gaps listed above (spine + Lisfranc + lateral ankle/fibula + posterior elbow) — this unlocks the largest number of currently manual cases.
3. Deepen any remaining thin supported that map well (e.g. more on revision THA/TKA, high_tibial specifics, peds supracondylar if catalog allows).
4. Ensure pimp_topics are consistently high-yield and directly tied to the improved fields across the board.
5. Re-audit after catalog additions + one more micro-pass; target moving all supported cases to overall >=4.
6-10. Specific per-procedure: additional landmarks/risks for humeral/tibial shafts and meniscus (if more OB detail available); full variations for acetabulum combined approaches; blood supply protection details for more hip/knee recon; extensor mechanism nuances for patella/quadriceps if supported; compartment and nerve specifics for leg/forearm.

**Bottom line**: v2_1 delivers on the goal — the existing procedures (especially the common ones the router actually selects) are now markedly more useful as the primary anatomy/approach product layer. Gaps are transparent. Ready for integration testing.
