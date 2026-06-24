# Orthobullets Playbook v2 Line-by-Line Quality Audit Summary
Total procedures audited: 60
must_fix: 12 | should_fix: 12 | excellent: 10 | unsupported_gap: 22

## Top must_fix / should_fix (common supported cases with low utility)
- high_tibial_osteotomy (overall=2, facts=0, recs=2, manual=False)
  missing: ['important_anatomy', 'structures_at_risk', 'landmarks', 'approach_notes']
  reasons: supported with recs but very low anatomy/risk/landmark/note coverage; no important_anatomy despite mapped approach
- intertrochanteric_hip_fracture_orif (overall=2, facts=0, recs=2, manual=False)
  missing: ['important_anatomy', 'structures_at_risk', 'landmarks', 'approach_notes']
  reasons: supported with recs but very low anatomy/risk/landmark/note coverage; no important_anatomy despite mapped approach
- femoral_neck_fracture_orif_young (overall=2, facts=0, recs=2, manual=False)
  missing: ['important_anatomy', 'structures_at_risk', 'landmarks', 'approach_notes']
  reasons: supported with recs but very low anatomy/risk/landmark/note coverage; no important_anatomy despite mapped approach
- revision_tha (overall=2, facts=0, recs=2, manual=False)
  missing: ['important_anatomy', 'structures_at_risk', 'landmarks', 'approach_notes']
  reasons: supported with recs but very low anatomy/risk/landmark/note coverage; no important_anatomy despite mapped approach
- radial_head_fracture_orif (overall=2, facts=0, recs=1, manual=False)
  missing: ['important_anatomy', 'structures_at_risk', 'landmarks', 'approach_notes']
  reasons: supported with recs but very low anatomy/risk/landmark/note coverage; no important_anatomy despite mapped approach
- acetabulum_fracture_orif_anterior (overall=2, facts=0, recs=1, manual=False)
  missing: ['important_anatomy', 'structures_at_risk', 'landmarks', 'approach_notes']
  reasons: supported with recs but very low anatomy/risk/landmark/note coverage; no important_anatomy despite mapped approach
- acetabulum_fracture_orif_posterior (overall=2, facts=0, recs=1, manual=False)
  missing: ['important_anatomy', 'structures_at_risk', 'landmarks', 'approach_notes']
  reasons: supported with recs but very low anatomy/risk/landmark/note coverage; no important_anatomy despite mapped approach
- patella_fracture_orif (overall=2, facts=2, recs=1, manual=False)
  missing: ['structures_at_risk', 'approach_notes']
  reasons: supported with recs but very low anatomy/risk/landmark/note coverage
- monteggia_fracture_orif (overall=2, facts=0, recs=1, manual=False)
  missing: ['important_anatomy', 'structures_at_risk', 'landmarks', 'approach_notes']
  reasons: supported with recs but very low anatomy/risk/landmark/note coverage; no important_anatomy despite mapped approach
- total_ankle_arthroplasty (overall=2, facts=0, recs=1, manual=False)
  missing: ['important_anatomy', 'structures_at_risk', 'landmarks', 'approach_notes']
  reasons: supported with recs but very low anatomy/risk/landmark/note coverage; no important_anatomy despite mapped approach
- revision_tka (overall=2, facts=0, recs=1, manual=False)
  missing: ['important_anatomy', 'structures_at_risk', 'landmarks', 'approach_notes']
  reasons: supported with recs but very low anatomy/risk/landmark/note coverage; no important_anatomy despite mapped approach
- ankle_arthrodesis (overall=2, facts=0, recs=1, manual=False)
  missing: ['important_anatomy', 'structures_at_risk', 'landmarks', 'approach_notes']
  reasons: supported with recs but very low anatomy/risk/landmark/note coverage; no important_anatomy despite mapped approach
- perthes_disease_surgery (overall=2, facts=2, recs=1, manual=False)
  missing: ['structures_at_risk', 'landmarks']
  reasons: supported with recs but very low anatomy/risk/landmark/note coverage; no landmarks despite clear incision/exposure landmarks on OB approach pages for similar cases
- tibial_plateau_fracture_orif (overall=3, facts=1, recs=2, manual=False)
  missing: ['important_anatomy', 'structures_at_risk', 'landmarks']
  reasons: supported with recs but very low anatomy/risk/landmark/note coverage; no important_anatomy despite mapped approach
- scaphoid_fracture_orif (overall=3, facts=2, recs=2, manual=False)
  missing: ['structures_at_risk', 'landmarks']
  reasons: supported with recs but very low anatomy/risk/landmark/note coverage; no landmarks despite clear incision/exposure landmarks on OB approach pages for similar cases

## Excellent (overall 4-5)
- distal_radius_fracture_orif (facts=16, sources=4)
- proximal_humerus_fracture_orif (facts=10, sources=2)
- hip_hemiarthroplasty (facts=3, sources=2)
- tha_posterior (facts=5, sources=2)
- tha_anterior (facts=2, sources=1)
- tha_lateral (facts=3, sources=2)
- tka (facts=14, sources=2)
- rotator_cuff_repair (facts=5, sources=1)
- femoral_shaft_fracture_orif (facts=6, sources=1)
- reverse_shoulder_arthroplasty (facts=3, sources=2)

## Unsupported gaps (catalog-limited; content secondary)
- bimalleolar_ankle_orif
- trimalleolar_ankle_orif
- pilon_ankle_fracture_orif
- calcaneus_fracture_orif
- olecranon_fracture_orif
- pelvis_ring_fracture_orif
- cubital_tunnel_release
- clavicle_fracture_orif
- supracondylar_humerus_fracture_pediatric
- hallux_valgus_correction

See full line_quality_audit.jsonl / .csv for per-procedure scores, suggested OB pages, and improvement targets.
Use this to drive v2_1 quality deepening pass (focus must_fix + should_fix supported entries first).