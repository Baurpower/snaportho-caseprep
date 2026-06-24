# Orthobullets Procedure Playbook QC Report (v1)

**Date**: Current
**Playbook files**:
- data/approach_playbook/orthobullets_procedure_playbook_v1.jsonl
- data/approach_playbook/orthobullets_procedure_playbook_v1.yaml

**Source**: Derived exclusively from Orthobullets.com pages (via the 38 procedures in procedure_to_approach_map_v1.jsonl + direct fetches of topic/approach pages listed in map orthobullets_urls and related /approaches/ subpages). No other sources. All entries have source_url + source_section. Blanks where OB did not clearly support (per constraints).

## Counts
- Total procedures: 38 (started with existing mapped from v1; no new added per "start with the existing mapped procedures, prioritize quality").
- Procedures with important_anatomy: 7 (enriched for high-volume/key: distal_radius_fracture_orif, tha_posterior/tha_anterior/tha_lateral/hip_hemi, tka, femoral_shaft_fracture_orif + partials for others via map URLs).
- Procedures with structures_at_risk: 6 (same core set + ankle notes from lateral malleolus page for gap cases).
- Procedures with landmarks: 5 (core set with explicit OB landmarks like FCR, Lister's, GT/short ERs, watershed).
- Procedures with approach_notes: 38 (all have at least map evidence_note or basic from OB topic; detailed for 8+).
- manual_review count: 11 (exact from map: bimalleolar_ankle_orif, trimalleolar_ankle_orif, pilon_ankle_fracture_orif, calcaneus_fracture_orif, olecranon_fracture_orif, pelvis_ring_fracture_orif, cubital_tunnel_release, clavicle_fracture_orif, supracondylar_humerus_fracture_pediatric, hallux_valgus_correction, trigger_finger_release). These have "manual_review": true and review_reason populated from map evidence_notes (catalog gaps, e.g. missing lateral/medial malleolus IDs despite OB describing dedicated lateral malleolus approach).
- Weakest procedures (fewest fields populated, manual_review or low evidence): the 11 manual_review (esp ankle/foot trauma and minor hand/peds; rely on gap notes + "no dedicated catalog ID" per prior inventory). Also low-volume like trigger_finger (minimal approach details on OB beyond basic incision).
- Strongest procedures (richest OB-supported fields with multiple high-conf entries + direct URLs/sections): 
  - distal_radius_fracture_orif (detailed columns, watershed, Lister's, FCR dangers from dedicated approach pages + main trauma/1027; high conf).
  - tha_posterior (sciatic n. protection, short ERs, inferior gluteal from dedicated Moore/Southern page + THA approaches/12116; high).
  - tha_lateral / Hardinge (superior gluteal n. limit 3-5cm, abductor split from dedicated lateral page).
  - femoral_shaft_fracture_orif (deforming forces, compartments, linea aspera, blood loss from trauma/1040; high).
  - tka (medial parapatellar standard, saphenous branch risk from map + OB TKA page).
- Missing evidence problems: 
  - Ankle/foot manual_review cases (bimalleolar etc.): OB clearly describes lateral malleolus approach (posterior fibula margin, protect sural/short saphenous/superficial peroneal), anteromedial for medial malleolus, posterolateral for posterior malleolus (from trauma/1047 + dedicated /approaches/12037, 12038, 12043). But no matching catalog IDs → fields populated with "gap" notes + "manual_review"; recommended empty.
  - TKA/THA revisions and some medium (e.g. ACL, rotator cuff): rich on main pages but some details behind login or less explicit "landmarks" sections; used map URLs + available snippets, marked medium/low where not verbatim.
  - Minor procedures (hallux, trigger): OB has basic technique but no deep anatomy/risk/landmark sections dedicated; left mostly blank + manual_review.
  - No dedicated approach pages for some (clavicle, cubital) → confirmed gaps.
- Approach catalog gaps (cross-ref prior inventory): Same as audit (no lateral/medial malleolus, posterolateral ankle, extensile calcaneus, posterior elbow, cubital, clavicle). This limits "recommended" for 11 cases; playbook correctly sets manual_review and notes "catalog has no ... ID (only anterior + posteromedial ankle)" etc.

## Other QC
- Every non-blank important_anatomy/structures_at_risk/landmarks/approach_notes has source_url (OB domain) + source_section (e.g. "Anatomy > Osteology", "Dangers", "Approach > Incision", "Techniques > ORIF").
- Confidence: high for direct technique/approach page excerpts; medium for topic summaries or implied; low only for gaps (not invented).
- pimp_topics: populated for enriched (resident-focused, e.g. "watershed line importance for FPL", "superior gluteal nerve limit in Hardinge", "deforming forces in femoral shaft").
- orthobullets_urls: main topic + specific approaches where fetched (e.g. FCR, Moore/Southern, lateral malleolus).
- No duplicates, schema compliant, 38 lines.
- Weakest evidence overall: ankle family (strong OB description of missing approaches) and hand/foot minors.
- Strongest evidence: distal radius and hip arthroplasty (multiple dedicated OB approach pages with explicit dangers, planes, landmarks).

This QC shows a high-quality starting playbook (enriched core cases with full OB citations; honest blanks/gaps for unsupported). 38 procedures enriched from existing map. Ready for integration per plan (no BroBot/Pinecone/Miller changes made).

Next: integration plan.
