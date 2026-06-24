# Orthobullets Playbook v2 Current State Audit (v1.1 baseline)

**Source**: data/approach_playbook/orthobullets_procedure_playbook_v1_1.jsonl (and .yaml)
**Date of analysis**: Current session
**Cross-referenced**: reports/orthobullets_procedure_playbook_v1_1_qc.md, reports/orthobullets_playbook_thin_entries_audit.md, reports/existing_approach_catalog_inventory.md, procedure_to_approach_map_v1.jsonl, existing catalog (30 IDs)

## Current Procedure Count
- Total: **38** procedures.
- From v1 (38) → v1.1 (38, no net add; only enrichment of 5 thin supported + minor for 2 more).

## Specialty Distribution (v1.1)
- trauma: 19
- recon: 8
- hand: 4
- sports: 3
- foot_ankle: 3
- pediatrics: 1

## Region Distribution
- hip: 7
- ankle: 6
- knee: 6
- wrist: 3
- shoulder: 3
- elbow: 3
- pelvis: 3
- foot: 2
- forearm: 2
- thigh: 1
- humerus: 1
- hand: 1
- (many gaps in spine, more peds, more sports upper, etc.)

## High-Confidence Entries
- Entries with at least one "high" confidence fact: **9**
- Strongest (from prior QC + counts):
  - distal_radius_fracture_orif (ia=4, sar=5, lm=4, an=3; Henry + conditional dorsal; watershed, columns, Lister's, PIN, etc. from 1027/12071/12013)
  - tka (ia=4, sar=3, lm=4, an=3; medial parapatellar + variations from 12028/5031; post v1.1 enrichment)
  - tha_posterior / hip variants (partial: sciatic, ERs, sup gluteal n., GT landmarks from 12023/12022/12116)
  - femoral_shaft_fracture_orif (ia=2/4 post, deforming forces, compartments, linea aspera, blood loss from 1040)
  - carpal_tunnel_release (ia=1-3 post, transverse carpal lig, motor branch, palmar cutaneous from 12014)
- Many others have pimp_topics (often 2-4) but 0 or 1 real anatomy/risk/landmark/note facts.

## manual_review Entries
- **11** (unchanged from v1):
  - bimalleolar_ankle_orif, trimalleolar_ankle_orif, pilon_ankle_fracture_orif, calcaneus_fracture_orif (ankle/foot catalog gaps: no lateral fibula, no dedicated medial malleolus, no extensile lateral calcaneus)
  - olecranon_fracture_orif (no posterior elbow/olecranon catalog ID; only Kocher)
  - pelvis_ring_fracture_orif (limited catalog support)
  - cubital_tunnel_release (no medial/posterior elbow catalog ID)
  - clavicle_fracture_orif (no dedicated clavicle/superior shoulder girdle ID)
  - supracondylar_humerus_fracture_pediatric (peds specific gaps?)
  - hallux_valgus_correction, trigger_finger_release (foot/hand specific gaps in catalog)

These are intentionally limited; router should treat as supported=false or manual_review.

## Thin Entries Remaining (non-manual_review, low content)
- **19** thin supported (ia+sar+lm+an <2 total facts, or very low):
  - proximal_humerus_fracture_orif (0s in v1.1; has recs=2: deltopectoral + lateral split)
  - radial_head_fracture_orif (0s; recs=1: Kocher)
  - both_bone_forearm_fracture_orif (0s post v1; recs=1 Henry)
  - acetabulum_fracture_orif_anterior/posterior (0s; good recs but no anatomy populated)
  - acl_reconstruction (0s; recs=1 parapatellar)
  - rotator_cuff_repair (0s; recs=2 lateral split + deltopectoral)
  - carpal_tunnel_release (was 0s; v1.1 partial enrichment but still thin in audit snapshot)
  - tibial_plateau_fracture_orif (minimal post v1.1)
  - scaphoid_fracture_orif (0s; recs=2 volar/dorsal)
  - monteggia_fracture_orif (0s; recs=1 Henry + cond Kocher)
  - achilles_tendon_repair (0s; recs=1 posteromedial ankle)
  - total_ankle_arthroplasty (0s; recs=1 anterior ankle)
  - high_tibial_osteotomy (0s; recs=2 medial + parapatellar)
  - intertrochanteric_hip_fracture_orif (0s; recs=2)
  - femoral_neck_fracture_orif_young (0s)
  - revision_tha, revision_tka (0s)
  - ankle_arthrodesis (0s; recs=1 anterior)
- Note: v1.1 enrichment touched TKA (strong now), carpal (better), femoral shaft (better), patella, tibial plateau (minimal). But many "supported" entries that map to good catalog IDs are still thin (rely on Miller or produce weak output).

## Approach Catalog Gaps (from inventory + map QC)
- Total catalog: **30** (10 upper, 20 lower).
- Strong coverage: hip (all 5-6 THA variants), knee (medial parapatellar + medial + lateral + posterior), pelvis/acetabulum (ilioinguinal + KL), shoulder (deltopectoral, lateral split, posterior), wrist (volar distal Henry, dorsal, dedicated carpal tunnel), elbow (Kocher), forearm (Henry).
- Critical gaps causing manual_review or empty recs:
  - Ankle/foot: no lateral fibula/lateral malleolus, no dedicated medial malleolus (only posteromedial ankle), no posterolateral ankle, no extensile lateral calcaneus/sinus tarsi specific, limited for Lisfranc/pilon variants.
  - Elbow: no posterior/triceps split or medial for olecranon/cubital.
  - Clavicle/upper: no dedicated clavicle or superior shoulder girdle approach.
  - Humerus shaft/distal specifics limited.
  - Spine: none (no cervical/thoracic/lumbar approaches in catalog).
  - Peds specifics limited.
  - Many lower entries in catalog have empty indications (clinical_tags not populated).
- Map v1: ~16-20 with nonempty recommended (high/medium conf), ~11 manual_review, many with empty recs or only conditionals/blocked.
- Result: correct approach selected for many (e.g. TKA parapatellar, distal radius Henry), but thin playbook content → weak final product.

## Entries That Should Be Preserved Unchanged (or minimally touched)
- All 11 manual_review (catalog gaps; do not invent recs or anatomy).
- Strongest like distal_radius_fracture_orif (already high quality; only improve if clear new OB-supported facts from new pages).
- TKA (post v1.1 enrichment; already good for primary).
- Core hip recon (tha_posterior etc.; have some interval/risk/landmark from dedicated approach pages).
- Any with solid recs + some content where no new high-yield OB page adds value without padding.
- Rule for v2: Start from all v1.1 records **unchanged** unless a clear Orthobullets-supported improvement (new page facts with url/section) is found during enrichment of new or targeted thin ones. Prefer quality.

## Summary / Implications for v2 Expansion
- Base is solid but narrow (38, trauma/recon heavy, many thin even when mapping succeeds).
- Expansion target: add high-yield common resident case-prep procedures (ACL, rotator cuff, proximal humerus details, olecranon if possible, both-bone details, scaphoid, cubital if possible, Achilles, Lisfranc, hallux if possible, supracondylar, SCFE, DDH, spine decomp/fusion if OB pages yield usable anatomy/approach facts + map to existing catalog).
- For new: only populate recs/conditionals/blocked if real catalog ID matches (from the 30). Otherwise manual_review=true + empty recs.
- For anatomy fields: ONLY from explicit OB page text (approaches/xxxx or topic pages with "Approach", "Anatomy", "Dangers", "Techniques" sections). Leave blank if not supported on OB.
- Must create v2 separately; update map to v2 (include all, with proper triggers).
- Preserve v1.1 exactly (no overwrite).
- Prioritize ~30-60 new to reach ~70-100 total only if evidence quality high; stop earlier if OB pages lack explicit support for fields.
- Biggest value: fill thin supported that already have good catalog matches (prox humerus, rotator cuff, ACL, both bone, scaphoid, Achilles, etc.) + add common missing (Lisfranc, more peds, spine if feasible).

This audit confirms the need for v2 expansion focused on quality, catalog discipline, and OB-only facts to make the playbook the true primary layer.

(Next: Task 2 inventory via OB searches only.)
