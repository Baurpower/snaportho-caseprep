# Orthobullets Procedure Playbook v1.1 QC Report

**Date**: 2026-06 (post v1.1 enrichment)
**Base**: v1 (data/approach_playbook/orthobullets_procedure_playbook_v1.jsonl, 38 entries)
**Derived**: v1.1 (data/approach_playbook/orthobullets_procedure_playbook_v1_1.jsonl + .yaml) — v1 files untouched.
**Method**: Thin supported entries (manual_review=false, low counts in ia/sar/lm/an + prior weak test output) identified in orthobullets_playbook_thin_entries_audit.md. TKA deepened first using fresh Orthobullets page fetches only (https://www.orthobullets.com/approaches/12028/knee-medial-parapatellar-approach, https://www.orthobullets.com/recon/5031/tka-approaches, recon/12289 references). Then carpal_tunnel_release, femoral_shaft_fracture_orif, plus minimal supported additions for patella_fracture_orif + tibial_plateau_fracture_orif (total 5 improved). All new facts have explicit source_url + source_section from OB pages; unsupported (e.g. detailed MCL release specifics or posterior neurovascular for standard primary medial parapatellar TKA) left blank per constraints.

## Entries Improved (5 total)
- tka (primary target)
- carpal_tunnel_release
- femoral_shaft_fracture_orif
- patella_fracture_orif
- tibial_plateau_fracture_orif

(tha_posterior and distal_radius were reviewed per priority list; tha_posterior already had some prior enrichment and no large new gaps filled from quick checks; distal_radius was one of the "strongest" in v1 so only if obvious missing — none critical added this round.)

## Before/After Counts (key fields)
**tka** (biggest delta, correct approach was already mapped but output weak):
- v1: important_anatomy=1, structures_at_risk=1, landmarks=0, approach_notes=1, pimp_topics=2
- v1.1: important_anatomy=4, structures_at_risk=3, landmarks=4, approach_notes=3, pimp_topics=5
- Delta: +3 ia, +2 sar, +4 lm, +2 an, +3 pimp. Now covers intermuscular plane (rectus/VM), quad tendon + medial patella/patellar tendon borders + fat pad, patella eversion/lateral flip + tibial tubercle protection + 90° flexion, medial-based blood supply/skin perforators, exact incision landmarks (midline patella-tibial tubercle line, 5cm above sup pole to tubercle), infrapatellar saphenous + sup lat genicular + skin necrosis dangers, full steps + midvastus/subvastus variations (VMO sparing, patellar vascularity preservation).

**carpal_tunnel_release**:
- v1: ia=0, sar=0, lm=0, an=0
- v1.1: ia=3, sar=3, lm=2, an=2 (transverse carpal ligament, median n. position + motor branch anterolateral variation, palmar cutaneous branch course/protection, PL/FCR landmarks, ulnar-curved incision, full retinaculum release under vision, superficial palmar arch danger).

**femoral_shaft_fracture_orif**:
- v1 (partial): ia=2, sar=1, lm=0, an=1
- v1.1: ia=4, sar=3, lm=2, an=3 (linea aspera + 3 compartments + deforming forces from 1040, blood loss 1-1.5L closed/double open, profunda perforators/femoral vessels, GT/lateral thigh + linea aspera landmarks, lateral/posterolateral approach notes + early stabilization rationale).

**patella_fracture_orif** (minimal to reach threshold):
- v1: 0s
- v1.1: ia=1, sar=1, lm=1, an=1 (extensor mechanism protection, patella/tibial tubercle/medial-lateral borders landmarks, anterior/parapatellar approach note).

**tibial_plateau_fracture_orif** (minimal):
- v1: 0s
- v1.1: ia=1, sar=1, lm=1, an=1 (anterolateral + medial variants per map/OB 1042, joint line/tubercle/fibular head landmarks, menisci/ligament considerations, approach_notes cross-ref to knee cards).

## New High-Confidence Facts Added (examples, all OB-sourced)
- TKA: "Intermuscular plane is between rectus femoris and vastus medialis (both femoral nerve)." (12028)
- TKA: "Superior lateral genicular artery at risk during lateral retinacular release; may be the last remaining blood supply to the patella after medial parapatellar approach and fat pad excision." (12028 Dangers)
- TKA: "Subvastus (Southern) ... preserves patellar vascularity and extensor mechanism anatomy (quadriceps tendon remains intact); least extensile, minimal need for lateral retinacular release." (5031)
- TKA: Exact incision: "begin 5 cm above superior pole of the patella ... to the level of the tibial tubercle"; "develop medial skin flap to expose the quadriceps tendon, medial border of the patella, and medial border of the patellar tendon." (12028)
- Carpal: "Motor branch of median nerve (significant anatomic variation); risk minimized if incision through retinaculum made ulnar to median nerve." + "Superficial palmar arch crosses palm at level of distal end of outstretched thumb; avoid by direct observation for entire length." (12014)
- Femoral: "Blood loss in closed femoral shaft fractures is 1000-1500ml ... may be double ... in open"; deforming forces + linea aspera as "compressive strut"; 3 thigh compartments detailed. (1040)
- All items carry source_url + source_section + confidence (high/medium only where text directly supports).

## Weak Fields Still Blank (or low) After v1.1
- Many other supported entries remain thin (e.g. proximal_humerus, radial_head, both_bone_forearm, acl, rotator_cuff, scaphoid, monteggia, achilles, total_ankle, high_tibial_osteotomy, revision_* , intertrochanteric, femoral_neck_young, acetabulum variants had 0s or low). These were lower priority; stopped at TKA + 4 others per "at least 5" rule.
- tha_posterior etc. have partial (ia=1 sar=2 lm=1 an=1) but not re-enriched this round (already better than baseline thin).
- distal_radius remains one of the strongest (ia~4+ from prior Henry/FCR/dorsal work); no obvious missing OB-supported facts added.

## Fields Left Blank Due to No OB Support on Fetched Pages
- TKA: No detailed "MCL / medial release" steps or considerations in the standard medial parapatellar primary TKA pages fetched (12028/5031); posterior neurovascular (popliteal/tibial n., vessels) not described for this anterior approach (those appear in dedicated posterior knee approach pages). Per rules: left blank. (User spec: "only if Orthobullets supports it".)
- No invented intervals beyond explicit (rectus/VM plane), no AO/Wikipedia/general knowledge.
- Carpal/femoral similarly strict to page text (e.g. no Guyon's canal deep dive for CTR unless directly on the volar wrist page).

## Manual Review Count
- Unchanged: 11 (bimalleolar_*, trimalleolar_*, pilon_*, calcaneus_*, olecranon_*, pelvis_ring_*, cubital_*, clavicle_*, supracondylar_pediatric/hallux_valgus_*/trigger_finger_*). These remain manual_review=true due to catalog gaps (no matching lateral fibula/medial malleolus etc. IDs); supported=false in router. v1.1 did not touch them.

## Strongest Entries After v1.1
- distal_radius_fracture_orif (still leader: columns, watershed, Lister's, PIN/radial a./palmar cutaneous, Henry + conditional dorsal, multiple high-conf facts from 1027/12071/12013).
- tha_posterior / hip_hemi / tha_lateral (sciatic, inf gluteal, sup gluteal n. 3-5cm limit, short ERs, GT/ER landmarks, intervals from 12023/12022/12116).
- tka (now substantially improved; should eliminate "mostly quiz" weakness).
- femoral_shaft_fracture_orif (deforming forces, compartments, blood loss, linea aspera now solid).
- carpal_tunnel_release (now has real OB-supported CTR content vs 0s).

## Remaining Thin Entries (non-manual)
- ~20+ still low (proximal humerus, radial head, forearm both-bone, ACL, rotator cuff, scaphoid, Monteggia, Achilles, total ankle, HTO, revisions, acetabulum detailed, intertroch/femoral neck young, ankle arthrodesis, etc.). Catalog good for many (parapatellar, Henry, hip approaches, etc.); future enrichment possible if resident priority or new test weakness surfaces. No more added here per stop rule ("TKA clearly improved + at least 5 total OR insufficient evidence").

## Validation Notes (per task)
- Orthobullets only for all new facts (fetched via web_search site: + open_page on 12028/5031/12014/1040 + supporting searches; no Miller/MedGemma/GPT knowledge/AO/Wiki/textbooks).
- Every new item: text + source_url + source_section + confidence.
- v1 preserved (separate v1_1 files; jsonl + yaml dual).
- No BroBot / Pinecone / Miller corpus / MedGemma changes.
- manual_review and supported-gate behavior unchanged for the 11.
- TKA now supplies resident-level content matching the requested list (medial parapatellar steps, quad/VMO exposure via plane + borders, patella/patellar tendon/tibial tubercle + eversion, extensor, infrapatellar saphenous, skin/genicular risks, landmarks like medial patellar border/joint line implied via tubercle/patella/90deg, fat pad, variations).

## Summary
v1.1 successfully addresses the primary problem (thin supported entries causing weak outputs despite correct approach selection). TKA is the standout improvement. 5 total improved. Ready for BroBot switch testing (see integration plan). Further thin entries can be tackled in v1.2 with same OB-only discipline.

Next deliverables per user query: playbook_primary_v1_1_test_results.md (v1 vs v1.1 comparison on 5 cases), orthobullets_playbook_v1_1_integration_plan.md.
