# Orthobullets Procedure Playbook Input Audit

**Date**: Current workspace state
**Source inputs audited**:
- `data/approach_playbook/procedure_to_approach_map_v1.jsonl` (38 procedures)
- `data/upper_extremity/approaches/upper_extremity_approaches.jsonl` (10 approaches)
- `data/lower_extremity/approaches/lower_extremity_approaches.jsonl` (20 approaches)
- `reports/existing_approach_catalog_inventory.md` (prior clean inventory)
- `reports/procedure_to_approach_map_qc.md` and `reports/orthobullets_procedure_inventory.md` (prior related reports)
- `reports/procedure_approach_router_integration_plan.md`

## Existing Procedure Mapping Count
- Total: **38** procedures in v1 map.
- Breakdown by confidence (from map):
  - high: 16
  - medium: 11
  - manual_review: 11
- Procedures with non-empty `recommended_approach_ids`: 27 (high/med only; manual_review have 0 or limited conditionals).
- Many have `orthobullets_url` pointing to main topic pages (e.g., trauma/1047/ankle-fractures, recon/12116/tha-approaches, etc.).
- Map includes triggers, recommended/conditional/blocked (empty for many manual_review), evidence_notes citing OB pages, but **no** detailed anatomy/risks/landmarks/approach_notes yet — that's the gap this playbook fills.
- Procedures span: trauma (many ORIFs), recon (THA/TKA/revisions), sports (ACL, rotator cuff, Achilles), hand (CTR, scaphoid), foot/ankle, pediatrics, etc.

List of all (with conf and rec count):
- bimalleolar_ankle_orif: manual_review (0)
- trimalleolar_ankle_orif: manual_review (0)
- pilon_ankle_fracture_orif: manual_review (0)
- calcaneus_fracture_orif: manual_review (0)
- distal_radius_fracture_orif: high (1)
- proximal_humerus_fracture_orif: high (2)
- radial_head_fracture_orif: high (1)
- olecranon_fracture_orif: manual_review (0)
- both_bone_forearm_fracture_orif: medium (1)
- acetabulum_fracture_orif_anterior: high (1)
- acetabulum_fracture_orif_posterior: high (1)
- pelvis_ring_fracture_orif: manual_review (0)
- hip_hemiarthroplasty: medium (1)
- tha_posterior: high (1)
- tha_anterior: high (1)
- tha_lateral: high (1)
- tka: high (1)
- acl_reconstruction: medium (1)
- rotator_cuff_repair: medium (2)
- carpal_tunnel_release: high (1)
- cubital_tunnel_release: manual_review (0)
- patella_fracture_orif: high (1)
- tibial_plateau_fracture_orif: medium (2)
- femoral_shaft_fracture_orif: high (2)
- clavicle_fracture_orif: manual_review (0)
- scaphoid_fracture_orif: medium (2)
- monteggia_fracture_orif: medium (1)
- achilles_tendon_repair: medium (1)
- total_ankle_arthroplasty: high (1)
- high_tibial_osteotomy: high (2)
- supracondylar_humerus_fracture_pediatric: manual_review (0)
- intertrochanteric_hip_fracture_orif: medium (2)
- femoral_neck_fracture_orif_young: high (2)
- revision_tha: medium (2)
- revision_tka: high (1)
- ankle_arthrodesis: medium (1)
- hallux_valgus_correction: manual_review (0)
- trigger_finger_release: manual_review (0)

## Existing Catalog Approach IDs (30 total)
**Upper extremity (10)** (source: data/upper_extremity/approaches/upper_extremity_approaches.jsonl):
- approach_shoulder_deltopectoral (indications: shoulder_arthroplasty, proximal_humerus_fracture)
- approach_shoulder_lateral_deltoid_split (proximal_humerus_orif)
- approach_shoulder_posterior (posterior_instability, reverse_shoulder_approach)
- approach_humerus_anterolateral_distal (humeral_shaft_fracture)
- approach_humerus_posterior_triceps_split (posterior_humerus_orif)
- approach_elbow_lateral_kocher (radial_head_fracture, elbow_instability)
- approach_forearm_anterior_henry (radius_orif, volar_forearm)
- approach_wrist_dorsal (dorsal_wrist_surgery)
- approach_wrist_volar_distal_henry (distal_radius_orif, carpal_tunnel_region)
- approach_wrist_carpal_tunnel (carpal_tunnel_release)

**Lower extremity (20)** (source: data/lower_extremity/approaches/lower_extremity_approaches.jsonl; most have empty indications):
- approach_lower_ext_iliac_crest_anterior
- approach_lower_ext_iliac_crest_posterior
- approach_lower_ext_pelvis_acetabulum_anterior_ilioinguinal
- approach_lower_ext_pelvis_acetabulum_posterior_kocher_langenbeck
- approach_lower_ext_hip_anterior_smith_peterson
- approach_lower_ext_hip_anterolateral_watson_jones
- approach_lower_ext_hip_lateral_hardinge
- approach_lower_ext_hip_posterior_moore_southern
- approach_lower_ext_hip_medial_ludloff
- approach_lower_ext_thigh_lateral
- approach_lower_ext_thigh_posterolateral
- approach_lower_ext_thigh_anteromedial
- approach_lower_ext_knee_anterior_medial_parapatellar
- approach_lower_ext_knee_medial
- approach_lower_ext_knee_lateral
- approach_lower_ext_knee_posterior
- approach_lower_ext_leg_lateral
- approach_lower_ext_leg_medial
- approach_lower_ext_ankle_anterior
- approach_lower_ext_ankle_posteromedial

## Missing Approach IDs (Critical Gaps)
From prior QC and catalog observations (confirmed in existing_approach_catalog_inventory.md and map evidence_notes):
- No dedicated **lateral malleolus / lateral fibula** approach (catalog has only ankle_anterior + ankle_posteromedial).
- No dedicated **direct medial malleolus** or anteromedial ankle.
- No **posterolateral ankle**.
- No **extensile lateral calcaneus** (L-shaped).
- No specific pilon variants or foot-specific.
- No dedicated **posterior elbow / olecranon** (only lateral Kocher).
- No dedicated **cubital / medial elbow**.
- No **clavicle / superior shoulder girdle**.
- Limited for pelvis ring (only ilioinguinal + KL; no dedicated anterior pelvic/Stoppa).
- Many lower extremity have no clinical_tags/indications populated.
- This directly causes manual_review for ankle/foot trauma cases and some others (bimalleolar etc. have empty recommended despite clear OB descriptions of lateral + medial).
- Catalog total 30 is strict; playbook must **only** reference these exact IDs (no invention).

## Procedures Most Important to Enrich First (Prioritization)
Prioritize high-confidence, high-volume, or high-impact cases where map already has solid recommended_approach_ids + OB URLs, and where anatomy/risks/landmarks are clinically critical for residents:
1. **High-confidence core ORIFs with good catalog match**:
   - distal_radius_fracture_orif (high; volar Henry + dorsal conditional; very common)
   - tha_posterior / tha_anterior / tha_lateral (high; direct matches to Moore/Southern, Smith-Peterson, Hardinge)
   - tka (high; medial parapatellar)
   - femoral_shaft_fracture_orif (high; thigh lateral/posterolateral)
   - proximal_humerus_fracture_orif (high; deltopectoral + lateral split)
   - radial_head_fracture_orif (high; Kocher)
   - patella_fracture_orif (high; anterior parapatellar)
   - total_ankle_arthroplasty (high; anterior ankle)
   - high_tibial_osteotomy (high; medial + parapatellar)
   - femoral_neck_fracture_orif_young (high; anterior/anterolateral hip)
   - revision_tka (high; parapatellar)
2. **Medium with good potential**:
   - tibial_plateau_fracture_orif (medium; parapatellar + lateral)
   - both_bone_forearm (medium; Henry)
   - acetabulum anterior/posterior (high actually; ilioinguinal + KL)
   - scaphoid, monteggia, achilles, ankle_arthrodesis, intertroch, revision_tha, acl, rotator_cuff
3. **Manual_review / gap cases (enrich with notes on gaps, but supported=false or limited)**:
   - All ankle/foot: bimalleolar, trimalleolar, pilon, calcaneus (critical for "what approach" questions; note missing lateral/medial IDs despite OB describing them explicitly).
   - olecranon, cubital, clavicle, supracondylar_peds, hallux, trigger, pelvis_ring.
- Why these first: High clinical volume (trauma recon, sports, hand), clear OB URLs in map, direct catalog ID matches for supported ones, and high risk of "guessing wrong" (e.g., anterior ankle for bimalleolar was historical bug fixed by prior router work).
- Avoid low-volume/minor (trigger finger, hallux) until core done.
- Total to start: All 38, but enrich the ~27 supported first for quality; manual_review get gap notes + "manual_review": true.

## Other Notes for Playbook Construction
- Map already has good "evidence_note" citing specific OB pages/sections (e.g., trauma/1047, dedicated /approaches/12xxx pages).
- Use those as starting points for fetch: e.g., https://www.orthobullets.com/trauma/1047/ankle-fractures , https://www.orthobullets.com/approaches/12037/approach-to-the-lateral-malleolus , THA approaches page, etc.
- Playbook must reference exact approach_ids (e.g., "approach_wrist_volar_distal_henry") where possible.
- For fields: important_anatomy, structures_at_risk, landmarks, approach_notes — only from OB "Approach", "Surgical Technique", "Anatomy", "Structures at Risk", "Positioning", "Pearls" sections.
- Confidence: high if direct from OB technique/approach page; medium if implied; low/manual if weak or gap.
- orthobullets_urls: include main + any specific approach subpages.
- pimp_topics: high-yield resident questions derivable from OB (e.g., "What nerve is at risk in Kocher?").
- No Miller, no other sources — every entry needs explicit source_url + source_section (e.g., "Surgical Technique > Approach" or "Approach to the Lateral Malleolus").
- Existing reports (procedure_approach_router_integration_plan.md, orthobullets_procedure_inventory.md, procedure_to_approach_map_qc.md) emphasize using map as foundation, strict catalog ID discipline, and deterministic use later.

This audit confirms we have a solid, already-curated set of 38 procedures (with 30 catalog IDs) ready for OB enrichment. Focus on fetching OB content for the listed high/medium ones first, noting gaps for manual_review. No need for new procedures per "start with the existing mapped procedures".

Next steps: Task 2 extraction using web tools on OB URLs from map.
