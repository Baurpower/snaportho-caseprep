# BroBot Anatomy Router v1 Audit Report
Generated: 2026-06-06T16:40:16.072497Z
Source: data/approach_playbook/orthobullets_procedure_playbook_v2_1.jsonl
Procedures converted: 60

## Distribution
- case_anatomy_type: {'mixed': 12, 'open_approach': 28, 'soft_tissue_repair': 6, 'decompression_or_release': 6, 'reduction_or_implant_anatomy': 3, 'uncertain': 1, 'arthroscopy_or_endoscopy': 4}
- confidence: {'low': 33, 'high': 3, 'medium': 24}
- manual_review: 33

## Top 20 Highest-Priority Missing Modules (from backlog, high priority procs first)
- approach_hip_lateral_hardinge (priority=high, needed_by=7): Referenced by router for 7 procedure(s)
- approach_lower_ext_knee_anterior_medial_parapatellar (priority=high, needed_by=6): Referenced by router for 6 procedure(s)
- anatomy_hip_short_external_rotators (priority=high, needed_by=5): Referenced by router for 5 procedure(s)
- risks_hip_sciatic_superior_gluteal (priority=high, needed_by=5): Referenced by router for 5 procedure(s)
- approach_knee_lateral (priority=high, needed_by=4): Referenced by router for 4 procedure(s)
- approach_cervical_anterior (or posterior cervical) (priority=high, needed_by=3): Required for Anterior Cervical Discectomy and Fusion (ACDF) (manual_review or gap in current catalog
- approach_lower_ext_hip_posterior_moore_southern (priority=high, needed_by=3): Referenced by router for 3 procedure(s)
- approach_lumbar_posterior (priority=high, needed_by=3): Required for Anterior Cervical Discectomy and Fusion (ACDF) (manual_review or gap in current catalog
- approach_wrist_dorsal (priority=high, needed_by=3): Referenced by router for 3 procedure(s)
- anatomy_knee_extensor_mechanism (priority=high, needed_by=2): Referenced by router for 2 procedure(s)
- approach_wrist_volar_distal_henry (priority=high, needed_by=2): Referenced by router for 2 procedure(s)
- reduction_pinning_modified_dunn (priority=high, needed_by=2): Referenced by router for 2 procedure(s)
- risks_knee_infrapatellar_saphenous_genicular (priority=high, needed_by=2): Referenced by router for 2 procedure(s)
- anatomy_acdf (priority=high, needed_by=1): Referenced by router for 1 procedure(s)
- anatomy_distal_radius_columns_watershed_listers (priority=high, needed_by=1): Referenced by router for 1 procedure(s)
- anatomy_nerve_course_carpal_tunnel_release (priority=high, needed_by=1): Referenced by router for 1 procedure(s)
- anatomy_nerve_course_cubital_tunnel_release (priority=high, needed_by=1): Referenced by router for 1 procedure(s)
- anatomy_nerve_course_posterior_lumbar_decompression_fusion (priority=high, needed_by=1): Referenced by router for 1 procedure(s)
- anatomy_proximal_humerus_neer_segments_circumflex (priority=high, needed_by=1): Referenced by router for 1 procedure(s)
- approach_acl_reconstruction (priority=high, needed_by=1): Referenced by router for 1 procedure(s)

## Entries Too Thin for Production (low facts + low confidence or high manual)
- bimalleolar_ankle_orif (type=mixed, conf=low, manual=True)
- trimalleolar_ankle_orif (type=mixed, conf=low, manual=True)
- pilon_ankle_fracture_orif (type=mixed, conf=low, manual=True)
- calcaneus_fracture_orif (type=mixed, conf=low, manual=True)
- olecranon_fracture_orif (type=mixed, conf=low, manual=True)
- pelvis_ring_fracture_orif (type=mixed, conf=low, manual=True)
- tha_anterior (type=open_approach, conf=low, manual=True)
- cubital_tunnel_release (type=decompression_or_release, conf=low, manual=True)
- clavicle_fracture_orif (type=mixed, conf=low, manual=True)
- monteggia_fracture_orif (type=open_approach, conf=low, manual=True)
- total_ankle_arthroplasty (type=open_approach, conf=low, manual=True)
- high_tibial_osteotomy (type=open_approach, conf=low, manual=True)
- supracondylar_humerus_fracture_pediatric (type=mixed, conf=low, manual=True)
- intertrochanteric_hip_fracture_orif (type=reduction_or_implant_anatomy, conf=low, manual=True)
- femoral_neck_fracture_orif_young (type=reduction_or_implant_anatomy, conf=low, manual=True)
... and 18 more

## Recommendations for Next Pass
1. Create high-priority modules from the backlog (start with those needed by distal_radius, tka, tha, acl, carpal, scfe, acdf, etc.).
2. Revisit 'uncertain' and 'mixed' entries after new modules/catalog approaches are added.
3. For manual_review procedures that are very common (ankle fractures, Lisfranc, SCFE, spine decomp), prioritize adding the missing approach IDs to the catalog so they can move out of manual_review.
4. Expand core_anatomy_questions and must_know with more procedure-specific detail once the modular files exist.
5. Add more conditional_module_ids for common branch points (e.g. dorsal vs volar radius, lateral vs medial plateau, anterior vs posterior column acetabulum).

## Validation Results
- Every input procedure_id appears exactly once in router: True
- No empty procedure_id: True
- No empty case_anatomy_type: True
- No empty anatomy_priority: True
- manual_review set appropriately for uncertain/low-data entries: 33 flagged
- All referenced modules collected into backlog (or noted as existing approach IDs).