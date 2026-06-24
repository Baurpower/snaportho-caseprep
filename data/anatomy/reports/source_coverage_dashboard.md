# Source Coverage Dashboard

Generated: 2026-06-06T17:40:05.174578  
Router: ./data/approach_playbook/brobot_anatomy_router_v1_2.jsonl  
Source v1 records: 51 → v2: 53

## Procedures by source_coverage_score
**4 (strong):** —
**3 (good):** bimalleolar_ankle_orif, trimalleolar_ankle_orif, pilon_ankle_fracture_orif, calcaneus_fracture_orif, distal_radius_fracture_orif, proximal_humerus_fracture_orif, radial_head_fracture_orif, olecranon_fracture_orif
**<3 (needs work):** 35 procs (see gap queue)

## Highest value missing sources (top of priority queue)
- **cervical_laminectomy_fusion** (readiness 0, cov 0) missing **nerve_course** → https://www.orthobullets.com/approaches/12002/posterior-approach-to-cervical-spine
- **cervical_laminectomy_fusion** (readiness 0, cov 0) missing **decompression_boundaries** → https://www.orthobullets.com/approaches/12002/posterior-approach-to-cervical-spine
- **cervical_laminectomy_fusion** (readiness 0, cov 0) missing **release_pitfalls** → https://www.orthobullets.com/approaches/12002/posterior-approach-to-cervical-spine
- **cervical_laminectomy_fusion** (readiness 0, cov 0) missing **structures_at_risk** → https://www.orthobullets.com/approaches/12002/posterior-approach-to-cervical-spine
- **elbow_arthroscopy** (readiness 0, cov 0) missing **portals** → https://www.orthobullets.com/shoulder-and-elbow/3088/elbow-arthroscopy-indications-and-approach
- **elbow_arthroscopy** (readiness 0, cov 0) missing **diagnostic_sequence** → https://www.orthobullets.com/shoulder-and-elbow/3088/elbow-arthroscopy-indications-and-approach
- **elbow_arthroscopy** (readiness 0, cov 0) missing **structures_visualized** → https://www.orthobullets.com/shoulder-and-elbow/3088/elbow-arthroscopy-indications-and-approach
- **elbow_arthroscopy** (readiness 0, cov 0) missing **pathology_recognition** → https://www.orthobullets.com/shoulder-and-elbow/3088/elbow-arthroscopy-indications-and-approach
- **elbow_arthroscopy** (readiness 0, cov 0) missing **structures_at_risk** → https://www.orthobullets.com/shoulder-and-elbow/3088/elbow-arthroscopy-indications-and-approach
- **supracondylar_humerus_fracture_pediatric** (readiness 1, cov 0) missing **reduction** → https://www.orthobullets.com/pediatrics/4008/supracondylar-fracture--pediatric

## Expected gains & notes
Acquiring top gaps (elbow arthro portals/diag seq, posterior cervical decomp, pelvis/acetab full column + corona mortis/sciatic protection, SCFE/supracondylar starting/fluoro/trajectory, dedicated ankle lateral/medial from 1047, Lisfranc column reduction, etc.) is expected to lift multiple procedures +1 (some +2) in source_coverage and downstream readiness.

See source_gap_priority_queue.jsonl for full ranked list.
