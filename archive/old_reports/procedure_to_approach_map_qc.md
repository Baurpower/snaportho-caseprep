# Procedure-to-Approach Map QC Report (v1)

**Date**: current workspace state
**Map files**:
- data/approach_playbook/procedure_to_approach_map_v1.jsonl
- data/approach_playbook/procedure_to_approach_map_v1.yaml

**Source constraint**: All procedure support and approach recommendations derived exclusively from Orthobullets.com topic pages (trauma/xxxx, recon/xxxx, hand/xxxx, sports/xxxx, foot-and-ankle/xxxx, pediatrics/xxxx) and their linked /approaches/ subpages (surgical technique, approach, positioning sections only). No other sources. No anatomy facts, intervals, structures-at-risk, or quiz content present in the map.

## Counts

- Total procedures mapped: 38
- High confidence: 16
- Medium confidence: 11
- Low confidence: 0
- Manual review / low-catalog-support: 11

## Procedures with no matching catalog approach (recommended_approach_ids empty)

These were deliberately left blank rather than guessed. They flag clear catalog gaps or cases where OB recommends a specific named approach (e.g., dedicated lateral malleolus) that has no equivalent ID in the current upper/lower extremity approach JSONL catalogs.

- bimalleolar_ankle_orif
- trimalleolar_ankle_orif
- pilon_ankle_fracture_orif
- calcaneus_fracture_orif
- olecranon_fracture_orif
- pelvis_ring_fracture_orif
- cubital_tunnel_release
- clavicle_fracture_orif
- supracondylar_humerus_fracture_pediatric (open reduction subset)
- hallux_valgus_correction
- trigger_finger_release

(11 total; additional minor procedures in inventory also fall here.)

## Catalog approaches never used in this v1 map (10)

- approach_humerus_anterolateral_distal
- approach_humerus_posterior_triceps_split
- approach_lower_ext_hip_medial_ludloff
- approach_lower_ext_iliac_crest_anterior
- approach_lower_ext_iliac_crest_posterior
- approach_lower_ext_knee_posterior
- approach_lower_ext_leg_lateral
- approach_lower_ext_leg_medial
- approach_lower_ext_thigh_anteromedial
- approach_shoulder_posterior

These are valid catalog IDs but did not have a strong, common-procedure match in the first ~38-50 OB-grounded procedures selected (or were lower priority for v1). They remain available for future expansion.

## Conflicting mappings

None in v1. All recommended + conditional sets are disjoint per procedure and respect catalog ID existence. No procedure recommends an ID that is also blocked for that same procedure.

## Blocked approach rules (current)

- bimalleolar_ankle_orif: blocks approach_lower_ext_ankle_anterior (OB specifies lateral fibula + medial malleolus exposures; anterior is for joint/talus/pilon variants)
- trimalleolar_ankle_orif: blocks approach_lower_ext_ankle_anterior (same rationale)
- pilon_ankle_fracture_orif: blocks approach_lower_ext_ankle_anterior (pattern-dependent; anterior is one option but not default for all; blocked as safety default until more specific catalog entries)

These are the only explicit blocked rules in v1. Additional blocking can be added in future revisions when OB clearly contraindicates a catalog ID for a procedure family.

## Highest priority manual fixes / catalog gaps (for next iteration)

1. **Ankle malleolar / pilon / calcaneus coverage (highest)**: Add dedicated catalog entries for:
   - Lateral malleolus / lateral fibula approach (OB has dedicated page: approaches/12037 + trauma/1047 direct lateral)
   - Direct medial malleolus / anteromedial ankle approach (OB approaches/12038)
   - Posterolateral ankle approach (OB approaches/12043)
   - Extensile lateral calcaneus (L-shaped) approach
   Once added, bimalleolar/trimalleolar/pilon/calcaneus can move from manual_review to high with recommended lists + conditionals.

2. Olecranon / posterior elbow: Add posterior midline elbow / olecranon osteotomy approach ID (or triceps-reflecting variants). Would allow olecranon_fracture_orif and distal humerus complex cases.

3. Cubital / medial elbow: Add medial elbow approach (in situ ulnar nerve decompression / transposition). Would cover cubital_tunnel_release.

4. Clavicle / shoulder girdle: Add superior or direct anterior clavicle approach.

5. Foot / hallux specific and minor hand releases: Consider lightweight dedicated IDs or accept that many remain manual_review (low volume for router).

6. Expand pelvis/iliac: Add Stoppa / anterior pelvic ring or Pfannenstiel variant if open reduction cases are common.

7. Posterior knee and niche (Ludloff, iliac crest approaches): Lower priority unless specific procedures added to inventory.

## Other QC notes

- Total unique catalog IDs referenced across recommended + conditional: 20 out of 30.
- 3 procedures carry explicit blocked rules (all ankle safety for anterior).
- Evidence_notes are short, cite specific OB URLs/pages, and explicitly call out catalog gaps instead of forcing mappings.
- Triggers are practical keyword/phrase sets drawn from common case nomenclature + OB topic language (case-insensitive match intended for router).
- No duplicate procedure_ids.
- Map is intentionally conservative: blank/manual_review preferred when OB support exists but catalog ID does not.

This QC is based on parsing the v1 map + current catalog JSONL files. Re-run after catalog expansion or map v2 additions.
