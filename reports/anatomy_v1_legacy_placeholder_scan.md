# Anatomy v1 Legacy Placeholder Scan Report

**Scope:** All files under data/anatomy/ (canonical v1 only).

**Total instances found:** 175
**Certified payloads affected:** ['hip_hemiarthroplasty', 'monteggia_fracture_orif', 'scfe_pinning', 'tha_anterior', 'tha_posterior']
**Linked modules (used_by certified) affected:** ['approach_hip_lateral_hardinge']

## Full Instance List

### data/anatomy/case_prep/certified_case_prep_payloads.jsonl
- Line 2: proc=hip_hemiarthroplasty, mod=N/A, string=`Primary structure at risk?`, field=`attending_pimp_questions`, impact=`certified_payload`
  Context: {"schema_version": "brobot_case_prep_payload_v1", "procedure_id": "hip_hemiarthroplasty", "procedure_name": "Hip Hemiarthroplasty", "case_prep_status": "certified", "procedure_overview": "Hip Hemiarthroplasty (open_approach). Certified. Score 4. Sour
- Line 2: proc=hip_hemiarthroplasty, mod=N/A, string=`Key approach for this case`, field=`must_know_anatomy`, impact=`certified_payload`
  Context: {"schema_version": "brobot_case_prep_payload_v1", "procedure_id": "hip_hemiarthroplasty", "procedure_name": "Hip Hemiarthroplasty", "case_prep_status": "certified", "procedure_overview": "Hip Hemiarthroplasty (open_approach). Certified. Score 4. Sour
- Line 3: proc=tha_posterior, mod=N/A, string=`Primary structure at risk?`, field=`attending_pimp_questions`, impact=`certified_payload`
  Context: {"schema_version": "brobot_case_prep_payload_v1", "procedure_id": "tha_posterior", "procedure_name": "Total Hip Arthroplasty (Posterior Approach)", "case_prep_status": "certified", "procedure_overview": "Total Hip Arthroplasty (Posterior Approach) (o
- Line 3: proc=tha_posterior, mod=N/A, string=`Key approach for this case`, field=`must_know_anatomy`, impact=`certified_payload`
  Context: {"schema_version": "brobot_case_prep_payload_v1", "procedure_id": "tha_posterior", "procedure_name": "Total Hip Arthroplasty (Posterior Approach)", "case_prep_status": "certified", "procedure_overview": "Total Hip Arthroplasty (Posterior Approach) (o
- Line 4: proc=tha_anterior, mod=N/A, string=`Primary structure at risk?`, field=`attending_pimp_questions`, impact=`certified_payload`
  Context: {"schema_version": "brobot_case_prep_payload_v1", "procedure_id": "tha_anterior", "procedure_name": "Total Hip Arthroplasty (Direct Anterior Approach)", "case_prep_status": "certified", "procedure_overview": "Total Hip Arthroplasty (Direct Anterior A
- Line 4: proc=tha_anterior, mod=N/A, string=`Key approach for this case`, field=`must_know_anatomy`, impact=`certified_payload`
  Context: {"schema_version": "brobot_case_prep_payload_v1", "procedure_id": "tha_anterior", "procedure_name": "Total Hip Arthroplasty (Direct Anterior Approach)", "case_prep_status": "certified", "procedure_overview": "Total Hip Arthroplasty (Direct Anterior A
- Line 9: proc=scfe_pinning, mod=N/A, string=`Primary structure at risk?`, field=`attending_pimp_questions`, impact=`certified_payload`
  Context: {"schema_version": "brobot_case_prep_payload_v1", "procedure_id": "scfe_pinning", "procedure_name": "SCFE Percutaneous Pinning / Modified Dunn", "case_prep_status": "certified", "procedure_overview": "SCFE Percutaneous Pinning / Modified Dunn (reduct
- Line 9: proc=scfe_pinning, mod=N/A, string=`Key approach for this case`, field=`must_know_anatomy`, impact=`certified_payload`
  Context: {"schema_version": "brobot_case_prep_payload_v1", "procedure_id": "scfe_pinning", "procedure_name": "SCFE Percutaneous Pinning / Modified Dunn", "case_prep_status": "certified", "procedure_overview": "SCFE Percutaneous Pinning / Modified Dunn (reduct
- Line 24: proc=monteggia_fracture_orif, mod=N/A, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`certified_payload`
  Context: {"schema_version": "brobot_case_prep_payload_v1", "procedure_id": "monteggia_fracture_orif", "procedure_name": "Monteggia Fracture ORIF", "case_prep_status": "certified", "procedure_overview": "Monteggia Fracture ORIF (open_approach). Certified. Scor
- Line 24: proc=monteggia_fracture_orif, mod=N/A, string=`Key approach for this case`, field=`must_know_anatomy`, impact=`certified_payload`
  Context: {"schema_version": "brobot_case_prep_payload_v1", "procedure_id": "monteggia_fracture_orif", "procedure_name": "Monteggia Fracture ORIF", "case_prep_status": "certified", "procedure_overview": "Monteggia Fracture ORIF (open_approach). Certified. Scor

### data/anatomy/modules/approach_modules.jsonl
- Line 3: proc=N/A, mod=approach_hip_lateral_hardinge, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`linked_module`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "approach_hip_lateral_hardinge", "module_type": "approach", "title": "Approach Hip Lateral Hardinge", "used_by_procedure_ids": ["hip_hemiarthroplasty", "intertrochanteric_hip_fracture_orif",
- Line 3: proc=N/A, mod=approach_hip_lateral_hardinge, string=`Key approach for this case`, field=`must_know`, impact=`linked_module`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "approach_hip_lateral_hardinge", "module_type": "approach", "title": "Approach Hip Lateral Hardinge", "used_by_procedure_ids": ["hip_hemiarthroplasty", "intertrochanteric_hip_fracture_orif",
- Line 5: proc=N/A, mod=approach_lower_ext_ankle_anterior, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "approach_lower_ext_ankle_anterior", "module_type": "approach", "title": "Approach Lower Ext Ankle Anterior", "used_by_procedure_ids": ["ankle_arthrodesis"], "source_urls": ["data/upper_extr
- Line 5: proc=N/A, mod=approach_lower_ext_ankle_anterior, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "approach_lower_ext_ankle_anterior", "module_type": "approach", "title": "Approach Lower Ext Ankle Anterior", "used_by_procedure_ids": ["ankle_arthrodesis"], "source_urls": ["data/upper_extr
- Line 14: proc=N/A, mod=approach_rotator_cuff_repair, string=`Primary structure at risk?`, field=`common_pimp_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "approach_rotator_cuff_repair", "module_type": "approach", "title": "Approach Rotator Cuff Repair", "used_by_procedure_ids": ["rotator_cuff_repair"], "source_urls": ["data/approach_playbook/
- Line 14: proc=N/A, mod=approach_rotator_cuff_repair, string=`Key approach for this case`, field=`common_pimp_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "approach_rotator_cuff_repair", "module_type": "approach", "title": "Approach Rotator Cuff Repair", "used_by_procedure_ids": ["rotator_cuff_repair"], "source_urls": ["data/approach_playbook/
- Line 15: proc=N/A, mod=approach_shoulder_deltopectoral, string=`Primary structure at risk?`, field=`common_pimp_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "approach_shoulder_deltopectoral", "module_type": "approach", "title": "Approach Shoulder Deltopectoral", "used_by_procedure_ids": ["proximal_humerus_fracture_orif"], "source_urls": ["data/u
- Line 15: proc=N/A, mod=approach_shoulder_deltopectoral, string=`Key approach for this case`, field=`common_pimp_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "approach_shoulder_deltopectoral", "module_type": "approach", "title": "Approach Shoulder Deltopectoral", "used_by_procedure_ids": ["proximal_humerus_fracture_orif"], "source_urls": ["data/u
- Line 16: proc=N/A, mod=approach_shoulder_lateral_deltoid_split, string=`Primary structure at risk?`, field=`common_pimp_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "approach_shoulder_lateral_deltoid_split", "module_type": "approach", "title": "Approach Shoulder Lateral Deltoid Split", "used_by_procedure_ids": ["proximal_humerus_fracture_orif"], "source
- Line 16: proc=N/A, mod=approach_shoulder_lateral_deltoid_split, string=`Key approach for this case`, field=`common_pimp_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "approach_shoulder_lateral_deltoid_split", "module_type": "approach", "title": "Approach Shoulder Lateral Deltoid Split", "used_by_procedure_ids": ["proximal_humerus_fracture_orif"], "source
- Line 21: proc=N/A, mod=approach_achilles_tendon_repair, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "approach_achilles_tendon_repair", "module_type": "approach", "title": "Approach Achilles Tendon Repair", "used_by_procedure_ids": ["achilles_tendon_repair"], "source_urls": ["https://www.or
- Line 22: proc=N/A, mod=approach_forearm_anterior_henry, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "approach_forearm_anterior_henry", "module_type": "approach", "title": "Approach Forearm Anterior Henry", "used_by_procedure_ids": ["both_bone_forearm_fracture_orif"], "source_urls": ["https
- Line 22: proc=N/A, mod=approach_forearm_anterior_henry, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "approach_forearm_anterior_henry", "module_type": "approach", "title": "Approach Forearm Anterior Henry", "used_by_procedure_ids": ["both_bone_forearm_fracture_orif"], "source_urls": ["https
- Line 25: proc=N/A, mod=approach_lower_ext_knee_medial, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "approach_lower_ext_knee_medial", "module_type": "approach", "title": "Approach Lower Ext Knee Medial", "used_by_procedure_ids": ["high_tibial_osteotomy"], "source_urls": [], "source_confide
- Line 25: proc=N/A, mod=approach_lower_ext_knee_medial, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "approach_lower_ext_knee_medial", "module_type": "approach", "title": "Approach Lower Ext Knee Medial", "used_by_procedure_ids": ["high_tibial_osteotomy"], "source_urls": [], "source_confide

### data/anatomy/modules/decompression_modules.jsonl
- Line 2: proc=N/A, mod=decompression_carpal_tunnel_release, string=`Primary structure at risk?`, field=`common_pimp_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "decompression_carpal_tunnel_release", "module_type": "decompression", "title": "Decompression Carpal Tunnel Release", "used_by_procedure_ids": ["carpal_tunnel_release"], "source_urls": ["ht
- Line 2: proc=N/A, mod=decompression_carpal_tunnel_release, string=`Key approach for this case`, field=`common_pimp_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "decompression_carpal_tunnel_release", "module_type": "decompression", "title": "Decompression Carpal Tunnel Release", "used_by_procedure_ids": ["carpal_tunnel_release"], "source_urls": ["ht
- Line 3: proc=N/A, mod=decompression_cubital_tunnel_release, string=`Per map evidence`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "decompression_cubital_tunnel_release", "module_type": "decompression", "title": "Decompression Cubital Tunnel Release", "used_by_procedure_ids": ["cubital_tunnel_release"], "source_urls": [
- Line 3: proc=N/A, mod=decompression_cubital_tunnel_release, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "decompression_cubital_tunnel_release", "module_type": "decompression", "title": "Decompression Cubital Tunnel Release", "used_by_procedure_ids": ["cubital_tunnel_release"], "source_urls": [
- Line 3: proc=N/A, mod=decompression_cubital_tunnel_release, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "decompression_cubital_tunnel_release", "module_type": "decompression", "title": "Decompression Cubital Tunnel Release", "used_by_procedure_ids": ["cubital_tunnel_release"], "source_urls": [
- Line 3: proc=N/A, mod=decompression_cubital_tunnel_release, string=`No free-form guessing`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "decompression_cubital_tunnel_release", "module_type": "decompression", "title": "Decompression Cubital Tunnel Release", "used_by_procedure_ids": ["cubital_tunnel_release"], "source_urls": [

### data/anatomy/modules/pathology_anatomy_modules.jsonl
- Line 7: proc=N/A, mod=anatomy_nerve_course_carpal_tunnel_release, string=`Primary structure at risk?`, field=`common_pimp_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_nerve_course_carpal_tunnel_release", "module_type": "other", "title": "Anatomy Nerve Course Carpal Tunnel Release", "used_by_procedure_ids": ["carpal_tunnel_release"], "source_urls"
- Line 7: proc=N/A, mod=anatomy_nerve_course_carpal_tunnel_release, string=`Key approach for this case`, field=`common_pimp_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_nerve_course_carpal_tunnel_release", "module_type": "other", "title": "Anatomy Nerve Course Carpal Tunnel Release", "used_by_procedure_ids": ["carpal_tunnel_release"], "source_urls"
- Line 8: proc=N/A, mod=anatomy_nerve_course_cubital_tunnel_release, string=`Per map evidence`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_nerve_course_cubital_tunnel_release", "module_type": "other", "title": "Anatomy Nerve Course Cubital Tunnel Release", "used_by_procedure_ids": ["cubital_tunnel_release"], "source_ur
- Line 8: proc=N/A, mod=anatomy_nerve_course_cubital_tunnel_release, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_nerve_course_cubital_tunnel_release", "module_type": "other", "title": "Anatomy Nerve Course Cubital Tunnel Release", "used_by_procedure_ids": ["cubital_tunnel_release"], "source_ur
- Line 8: proc=N/A, mod=anatomy_nerve_course_cubital_tunnel_release, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_nerve_course_cubital_tunnel_release", "module_type": "other", "title": "Anatomy Nerve Course Cubital Tunnel Release", "used_by_procedure_ids": ["cubital_tunnel_release"], "source_ur
- Line 8: proc=N/A, mod=anatomy_nerve_course_cubital_tunnel_release, string=`No free-form guessing`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_nerve_course_cubital_tunnel_release", "module_type": "other", "title": "Anatomy Nerve Course Cubital Tunnel Release", "used_by_procedure_ids": ["cubital_tunnel_release"], "source_ur
- Line 9: proc=N/A, mod=anatomy_proximal_humerus_neer_segments_circumflex, string=`Primary structure at risk?`, field=`common_pimp_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_proximal_humerus_neer_segments_circumflex", "module_type": "other", "title": "Anatomy Proximal Humerus Neer Segments Circumflex", "used_by_procedure_ids": ["proximal_humerus_fractur
- Line 9: proc=N/A, mod=anatomy_proximal_humerus_neer_segments_circumflex, string=`Key approach for this case`, field=`common_pimp_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_proximal_humerus_neer_segments_circumflex", "module_type": "other", "title": "Anatomy Proximal Humerus Neer Segments Circumflex", "used_by_procedure_ids": ["proximal_humerus_fractur
- Line 12: proc=N/A, mod=footprint_achilles_tendon_repair, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "footprint_achilles_tendon_repair", "module_type": "other", "title": "Footprint Achilles Tendon Repair", "used_by_procedure_ids": ["achilles_tendon_repair"], "source_urls": ["https://www.ort
- Line 13: proc=N/A, mod=anatomy_bimalleolar_ankle_orif, string=`Per map evidence`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_bimalleolar_ankle_orif", "module_type": "pathology_anatomy", "title": "Anatomy Bimalleolar Ankle Orif", "used_by_procedure_ids": ["bimalleolar_ankle_orif"], "source_urls": ["https:/
- Line 13: proc=N/A, mod=anatomy_bimalleolar_ankle_orif, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_bimalleolar_ankle_orif", "module_type": "pathology_anatomy", "title": "Anatomy Bimalleolar Ankle Orif", "used_by_procedure_ids": ["bimalleolar_ankle_orif"], "source_urls": ["https:/
- Line 13: proc=N/A, mod=anatomy_bimalleolar_ankle_orif, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_bimalleolar_ankle_orif", "module_type": "pathology_anatomy", "title": "Anatomy Bimalleolar Ankle Orif", "used_by_procedure_ids": ["bimalleolar_ankle_orif"], "source_urls": ["https:/
- Line 13: proc=N/A, mod=anatomy_bimalleolar_ankle_orif, string=`No free-form guessing`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_bimalleolar_ankle_orif", "module_type": "pathology_anatomy", "title": "Anatomy Bimalleolar Ankle Orif", "used_by_procedure_ids": ["bimalleolar_ankle_orif"], "source_urls": ["https:/
- Line 14: proc=N/A, mod=anatomy_calcaneus_fracture_orif, string=`Per map evidence`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_calcaneus_fracture_orif", "module_type": "pathology_anatomy", "title": "Anatomy Calcaneus Fracture Orif", "used_by_procedure_ids": ["calcaneus_fracture_orif"], "source_urls": ["http
- Line 14: proc=N/A, mod=anatomy_calcaneus_fracture_orif, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_calcaneus_fracture_orif", "module_type": "pathology_anatomy", "title": "Anatomy Calcaneus Fracture Orif", "used_by_procedure_ids": ["calcaneus_fracture_orif"], "source_urls": ["http
- Line 14: proc=N/A, mod=anatomy_calcaneus_fracture_orif, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_calcaneus_fracture_orif", "module_type": "pathology_anatomy", "title": "Anatomy Calcaneus Fracture Orif", "used_by_procedure_ids": ["calcaneus_fracture_orif"], "source_urls": ["http
- Line 14: proc=N/A, mod=anatomy_calcaneus_fracture_orif, string=`No free-form guessing`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_calcaneus_fracture_orif", "module_type": "pathology_anatomy", "title": "Anatomy Calcaneus Fracture Orif", "used_by_procedure_ids": ["calcaneus_fracture_orif"], "source_urls": ["http
- Line 15: proc=N/A, mod=anatomy_clavicle_fracture_orif, string=`Per map evidence`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_clavicle_fracture_orif", "module_type": "pathology_anatomy", "title": "Anatomy Clavicle Fracture Orif", "used_by_procedure_ids": ["clavicle_fracture_orif"], "source_urls": ["https:/
- Line 15: proc=N/A, mod=anatomy_clavicle_fracture_orif, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_clavicle_fracture_orif", "module_type": "pathology_anatomy", "title": "Anatomy Clavicle Fracture Orif", "used_by_procedure_ids": ["clavicle_fracture_orif"], "source_urls": ["https:/
- Line 15: proc=N/A, mod=anatomy_clavicle_fracture_orif, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_clavicle_fracture_orif", "module_type": "pathology_anatomy", "title": "Anatomy Clavicle Fracture Orif", "used_by_procedure_ids": ["clavicle_fracture_orif"], "source_urls": ["https:/
- Line 15: proc=N/A, mod=anatomy_clavicle_fracture_orif, string=`No free-form guessing`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_clavicle_fracture_orif", "module_type": "pathology_anatomy", "title": "Anatomy Clavicle Fracture Orif", "used_by_procedure_ids": ["clavicle_fracture_orif"], "source_urls": ["https:/
- Line 19: proc=N/A, mod=anatomy_olecranon_fracture_orif, string=`Per map evidence`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_olecranon_fracture_orif", "module_type": "pathology_anatomy", "title": "Anatomy Olecranon Fracture Orif", "used_by_procedure_ids": ["olecranon_fracture_orif"], "source_urls": ["http
- Line 19: proc=N/A, mod=anatomy_olecranon_fracture_orif, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_olecranon_fracture_orif", "module_type": "pathology_anatomy", "title": "Anatomy Olecranon Fracture Orif", "used_by_procedure_ids": ["olecranon_fracture_orif"], "source_urls": ["http
- Line 19: proc=N/A, mod=anatomy_olecranon_fracture_orif, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_olecranon_fracture_orif", "module_type": "pathology_anatomy", "title": "Anatomy Olecranon Fracture Orif", "used_by_procedure_ids": ["olecranon_fracture_orif"], "source_urls": ["http
- Line 19: proc=N/A, mod=anatomy_olecranon_fracture_orif, string=`No free-form guessing`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_olecranon_fracture_orif", "module_type": "pathology_anatomy", "title": "Anatomy Olecranon Fracture Orif", "used_by_procedure_ids": ["olecranon_fracture_orif"], "source_urls": ["http
- Line 21: proc=N/A, mod=anatomy_pilon_ankle_fracture_orif, string=`Per map evidence`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_pilon_ankle_fracture_orif", "module_type": "pathology_anatomy", "title": "Anatomy Pilon Ankle Fracture Orif", "used_by_procedure_ids": ["pilon_ankle_fracture_orif"], "source_urls": 
- Line 21: proc=N/A, mod=anatomy_pilon_ankle_fracture_orif, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_pilon_ankle_fracture_orif", "module_type": "pathology_anatomy", "title": "Anatomy Pilon Ankle Fracture Orif", "used_by_procedure_ids": ["pilon_ankle_fracture_orif"], "source_urls": 
- Line 21: proc=N/A, mod=anatomy_pilon_ankle_fracture_orif, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_pilon_ankle_fracture_orif", "module_type": "pathology_anatomy", "title": "Anatomy Pilon Ankle Fracture Orif", "used_by_procedure_ids": ["pilon_ankle_fracture_orif"], "source_urls": 
- Line 21: proc=N/A, mod=anatomy_pilon_ankle_fracture_orif, string=`No free-form guessing`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_pilon_ankle_fracture_orif", "module_type": "pathology_anatomy", "title": "Anatomy Pilon Ankle Fracture Orif", "used_by_procedure_ids": ["pilon_ankle_fracture_orif"], "source_urls": 
- Line 31: proc=N/A, mod=decompression_trigger_finger_release, string=`Per map evidence`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "decompression_trigger_finger_release", "module_type": "other", "title": "Decompression Trigger Finger Release", "used_by_procedure_ids": ["trigger_finger_release"], "source_urls": ["https:/
- Line 31: proc=N/A, mod=decompression_trigger_finger_release, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "decompression_trigger_finger_release", "module_type": "other", "title": "Decompression Trigger Finger Release", "used_by_procedure_ids": ["trigger_finger_release"], "source_urls": ["https:/
- Line 31: proc=N/A, mod=decompression_trigger_finger_release, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "decompression_trigger_finger_release", "module_type": "other", "title": "Decompression Trigger Finger Release", "used_by_procedure_ids": ["trigger_finger_release"], "source_urls": ["https:/
- Line 31: proc=N/A, mod=decompression_trigger_finger_release, string=`No free-form guessing`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "decompression_trigger_finger_release", "module_type": "other", "title": "Decompression Trigger Finger Release", "used_by_procedure_ids": ["trigger_finger_release"], "source_urls": ["https:/
- Line 32: proc=N/A, mod=anatomy_nerve_course_trigger_finger_release, string=`Per map evidence`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_nerve_course_trigger_finger_release", "module_type": "pathology_anatomy", "title": "Anatomy Nerve Course Trigger Finger Release", "used_by_procedure_ids": ["trigger_finger_release"]
- Line 32: proc=N/A, mod=anatomy_nerve_course_trigger_finger_release, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_nerve_course_trigger_finger_release", "module_type": "pathology_anatomy", "title": "Anatomy Nerve Course Trigger Finger Release", "used_by_procedure_ids": ["trigger_finger_release"]
- Line 32: proc=N/A, mod=anatomy_nerve_course_trigger_finger_release, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_nerve_course_trigger_finger_release", "module_type": "pathology_anatomy", "title": "Anatomy Nerve Course Trigger Finger Release", "used_by_procedure_ids": ["trigger_finger_release"]
- Line 32: proc=N/A, mod=anatomy_nerve_course_trigger_finger_release, string=`No free-form guessing`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_nerve_course_trigger_finger_release", "module_type": "pathology_anatomy", "title": "Anatomy Nerve Course Trigger Finger Release", "used_by_procedure_ids": ["trigger_finger_release"]
- Line 33: proc=N/A, mod=anatomy_trimalleolar_ankle_orif, string=`Per map evidence`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_trimalleolar_ankle_orif", "module_type": "pathology_anatomy", "title": "Anatomy Trimalleolar Ankle Orif", "used_by_procedure_ids": ["trimalleolar_ankle_orif"], "source_urls": ["http
- Line 33: proc=N/A, mod=anatomy_trimalleolar_ankle_orif, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_trimalleolar_ankle_orif", "module_type": "pathology_anatomy", "title": "Anatomy Trimalleolar Ankle Orif", "used_by_procedure_ids": ["trimalleolar_ankle_orif"], "source_urls": ["http
- Line 33: proc=N/A, mod=anatomy_trimalleolar_ankle_orif, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_trimalleolar_ankle_orif", "module_type": "pathology_anatomy", "title": "Anatomy Trimalleolar Ankle Orif", "used_by_procedure_ids": ["trimalleolar_ankle_orif"], "source_urls": ["http
- Line 33: proc=N/A, mod=anatomy_trimalleolar_ankle_orif, string=`No free-form guessing`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "anatomy_trimalleolar_ankle_orif", "module_type": "pathology_anatomy", "title": "Anatomy Trimalleolar Ankle Orif", "used_by_procedure_ids": ["trimalleolar_ankle_orif"], "source_urls": ["http

### data/anatomy/modules/reduction_implant_modules.jsonl
- Line 1: proc=N/A, mod=implant_trajectory_femoral_neck_fracture_orif_young, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "implant_trajectory_femoral_neck_fracture_orif_young", "module_type": "reduction_implant", "title": "Implant Trajectory Femoral Neck Fracture Orif Young", "used_by_procedure_ids": ["femoral_
- Line 1: proc=N/A, mod=implant_trajectory_femoral_neck_fracture_orif_young, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "implant_trajectory_femoral_neck_fracture_orif_young", "module_type": "reduction_implant", "title": "Implant Trajectory Femoral Neck Fracture Orif Young", "used_by_procedure_ids": ["femoral_
- Line 2: proc=N/A, mod=implant_trajectory_intertrochanteric_hip_fracture_orif, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "implant_trajectory_intertrochanteric_hip_fracture_orif", "module_type": "reduction_implant", "title": "Implant Trajectory Intertrochanteric Hip Fracture Orif", "used_by_procedure_ids": ["in
- Line 2: proc=N/A, mod=implant_trajectory_intertrochanteric_hip_fracture_orif, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "implant_trajectory_intertrochanteric_hip_fracture_orif", "module_type": "reduction_implant", "title": "Implant Trajectory Intertrochanteric Hip Fracture Orif", "used_by_procedure_ids": ["in
- Line 4: proc=N/A, mod=reduction_femoral_neck_fracture_orif_young, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "reduction_femoral_neck_fracture_orif_young", "module_type": "reduction_implant", "title": "Reduction Femoral Neck Fracture Orif Young", "used_by_procedure_ids": ["femoral_neck_fracture_orif
- Line 4: proc=N/A, mod=reduction_femoral_neck_fracture_orif_young, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "reduction_femoral_neck_fracture_orif_young", "module_type": "reduction_implant", "title": "Reduction Femoral Neck Fracture Orif Young", "used_by_procedure_ids": ["femoral_neck_fracture_orif
- Line 5: proc=N/A, mod=reduction_intertrochanteric_hip_fracture_orif, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "reduction_intertrochanteric_hip_fracture_orif", "module_type": "reduction_implant", "title": "Reduction Intertrochanteric Hip Fracture Orif", "used_by_procedure_ids": ["intertrochanteric_hi
- Line 5: proc=N/A, mod=reduction_intertrochanteric_hip_fracture_orif, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "reduction_intertrochanteric_hip_fracture_orif", "module_type": "reduction_implant", "title": "Reduction Intertrochanteric Hip Fracture Orif", "used_by_procedure_ids": ["intertrochanteric_hi
- Line 6: proc=N/A, mod=reduction_pinning_modified_dunn, string=`Primary structure at risk?`, field=`structures_at_risk`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "reduction_pinning_modified_dunn", "module_type": "reduction_implant", "title": "Reduction Pinning Modified Dunn", "used_by_procedure_ids": ["femoral_neck_fracture_orif_young"], "source_urls
- Line 6: proc=N/A, mod=reduction_pinning_modified_dunn, string=`Key approach for this case`, field=`must_know`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "reduction_pinning_modified_dunn", "module_type": "reduction_implant", "title": "Reduction Pinning Modified Dunn", "used_by_procedure_ids": ["femoral_neck_fracture_orif_young"], "source_urls

### data/anatomy/modules/soft_tissue_modules.jsonl
- Line 3: proc=N/A, mod=footprint_rotator_cuff_repair, string=`Primary structure at risk?`, field=`common_pimp_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "footprint_rotator_cuff_repair", "module_type": "soft_tissue", "title": "Footprint Rotator Cuff Repair", "used_by_procedure_ids": ["rotator_cuff_repair"], "source_urls": ["https://www.orthob
- Line 3: proc=N/A, mod=footprint_rotator_cuff_repair, string=`Key approach for this case`, field=`common_pimp_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_module_v1", "module_id": "footprint_rotator_cuff_repair", "module_type": "soft_tissue", "title": "Footprint Rotator Cuff Repair", "used_by_procedure_ids": ["rotator_cuff_repair"], "source_urls": ["https://www.orthob

### data/anatomy/registry/procedures.jsonl
- Line 1: proc=bimalleolar_ankle_orif, mod=N/A, string=`Per map evidence`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "bimalleolar_ankle_orif", "procedure_name": "Bimalleolar Ankle ORIF", "orthobullets_slug": "ankle-fractures", "source_url": "https://www.orthobullets.com/trauma/1047/ankle-fractures", 
- Line 1: proc=bimalleolar_ankle_orif, mod=N/A, string=`Primary structure at risk?`, field=`core_anatomy_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "bimalleolar_ankle_orif", "procedure_name": "Bimalleolar Ankle ORIF", "orthobullets_slug": "ankle-fractures", "source_url": "https://www.orthobullets.com/trauma/1047/ankle-fractures", 
- Line 1: proc=bimalleolar_ankle_orif, mod=N/A, string=`Key approach for this case`, field=`core_anatomy_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "bimalleolar_ankle_orif", "procedure_name": "Bimalleolar Ankle ORIF", "orthobullets_slug": "ankle-fractures", "source_url": "https://www.orthobullets.com/trauma/1047/ankle-fractures", 
- Line 1: proc=bimalleolar_ankle_orif, mod=N/A, string=`No free-form guessing`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "bimalleolar_ankle_orif", "procedure_name": "Bimalleolar Ankle ORIF", "orthobullets_slug": "ankle-fractures", "source_url": "https://www.orthobullets.com/trauma/1047/ankle-fractures", 
- Line 2: proc=trimalleolar_ankle_orif, mod=N/A, string=`Per map evidence`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "trimalleolar_ankle_orif", "procedure_name": "Trimalleolar Ankle ORIF", "orthobullets_slug": "ankle-fractures", "source_url": "https://www.orthobullets.com/trauma/1047/ankle-fractures"
- Line 2: proc=trimalleolar_ankle_orif, mod=N/A, string=`Primary structure at risk?`, field=`core_anatomy_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "trimalleolar_ankle_orif", "procedure_name": "Trimalleolar Ankle ORIF", "orthobullets_slug": "ankle-fractures", "source_url": "https://www.orthobullets.com/trauma/1047/ankle-fractures"
- Line 2: proc=trimalleolar_ankle_orif, mod=N/A, string=`Key approach for this case`, field=`core_anatomy_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "trimalleolar_ankle_orif", "procedure_name": "Trimalleolar Ankle ORIF", "orthobullets_slug": "ankle-fractures", "source_url": "https://www.orthobullets.com/trauma/1047/ankle-fractures"
- Line 2: proc=trimalleolar_ankle_orif, mod=N/A, string=`No free-form guessing`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "trimalleolar_ankle_orif", "procedure_name": "Trimalleolar Ankle ORIF", "orthobullets_slug": "ankle-fractures", "source_url": "https://www.orthobullets.com/trauma/1047/ankle-fractures"
- Line 3: proc=pilon_ankle_fracture_orif, mod=N/A, string=`Per map evidence`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "pilon_ankle_fracture_orif", "procedure_name": "Pilon (Tibial Plafond) Fracture ORIF", "orthobullets_slug": "pilon-fractures", "source_url": "https://www.orthobullets.com/trauma/1048/p
- Line 3: proc=pilon_ankle_fracture_orif, mod=N/A, string=`Primary structure at risk?`, field=`core_anatomy_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "pilon_ankle_fracture_orif", "procedure_name": "Pilon (Tibial Plafond) Fracture ORIF", "orthobullets_slug": "pilon-fractures", "source_url": "https://www.orthobullets.com/trauma/1048/p
- Line 3: proc=pilon_ankle_fracture_orif, mod=N/A, string=`Key approach for this case`, field=`core_anatomy_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "pilon_ankle_fracture_orif", "procedure_name": "Pilon (Tibial Plafond) Fracture ORIF", "orthobullets_slug": "pilon-fractures", "source_url": "https://www.orthobullets.com/trauma/1048/p
- Line 3: proc=pilon_ankle_fracture_orif, mod=N/A, string=`No free-form guessing`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "pilon_ankle_fracture_orif", "procedure_name": "Pilon (Tibial Plafond) Fracture ORIF", "orthobullets_slug": "pilon-fractures", "source_url": "https://www.orthobullets.com/trauma/1048/p
- Line 4: proc=calcaneus_fracture_orif, mod=N/A, string=`Per map evidence`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "calcaneus_fracture_orif", "procedure_name": "Calcaneus Fracture ORIF", "orthobullets_slug": "calcaneus-fractures", "source_url": "https://www.orthobullets.com/trauma/1051/calcaneus-fr
- Line 4: proc=calcaneus_fracture_orif, mod=N/A, string=`Primary structure at risk?`, field=`core_anatomy_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "calcaneus_fracture_orif", "procedure_name": "Calcaneus Fracture ORIF", "orthobullets_slug": "calcaneus-fractures", "source_url": "https://www.orthobullets.com/trauma/1051/calcaneus-fr
- Line 4: proc=calcaneus_fracture_orif, mod=N/A, string=`Key approach for this case`, field=`core_anatomy_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "calcaneus_fracture_orif", "procedure_name": "Calcaneus Fracture ORIF", "orthobullets_slug": "calcaneus-fractures", "source_url": "https://www.orthobullets.com/trauma/1051/calcaneus-fr
- Line 4: proc=calcaneus_fracture_orif, mod=N/A, string=`No free-form guessing`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "calcaneus_fracture_orif", "procedure_name": "Calcaneus Fracture ORIF", "orthobullets_slug": "calcaneus-fractures", "source_url": "https://www.orthobullets.com/trauma/1051/calcaneus-fr
- Line 6: proc=proximal_humerus_fracture_orif, mod=N/A, string=`Primary structure at risk?`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "proximal_humerus_fracture_orif", "procedure_name": "Proximal Humerus Fracture ORIF", "orthobullets_slug": "proximal-humerus-fractures", "source_url": "https://www.orthobullets.com/tra
- Line 6: proc=proximal_humerus_fracture_orif, mod=N/A, string=`Key approach for this case`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "proximal_humerus_fracture_orif", "procedure_name": "Proximal Humerus Fracture ORIF", "orthobullets_slug": "proximal-humerus-fractures", "source_url": "https://www.orthobullets.com/tra
- Line 7: proc=radial_head_fracture_orif, mod=N/A, string=`Primary structure at risk?`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "radial_head_fracture_orif", "procedure_name": "Radial Head Fracture ORIF", "orthobullets_slug": "radial-head-fractures", "source_url": "https://www.orthobullets.com/trauma/1020/radial
- Line 7: proc=radial_head_fracture_orif, mod=N/A, string=`Key approach for this case`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "radial_head_fracture_orif", "procedure_name": "Radial Head Fracture ORIF", "orthobullets_slug": "radial-head-fractures", "source_url": "https://www.orthobullets.com/trauma/1020/radial
- Line 8: proc=olecranon_fracture_orif, mod=N/A, string=`Per map evidence`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "olecranon_fracture_orif", "procedure_name": "Olecranon Fracture ORIF", "orthobullets_slug": "olecranon-fractures", "source_url": "https://www.orthobullets.com/trauma/1021/olecranon-fr
- Line 8: proc=olecranon_fracture_orif, mod=N/A, string=`Primary structure at risk?`, field=`core_anatomy_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "olecranon_fracture_orif", "procedure_name": "Olecranon Fracture ORIF", "orthobullets_slug": "olecranon-fractures", "source_url": "https://www.orthobullets.com/trauma/1021/olecranon-fr
- Line 8: proc=olecranon_fracture_orif, mod=N/A, string=`Key approach for this case`, field=`core_anatomy_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "olecranon_fracture_orif", "procedure_name": "Olecranon Fracture ORIF", "orthobullets_slug": "olecranon-fractures", "source_url": "https://www.orthobullets.com/trauma/1021/olecranon-fr
- Line 8: proc=olecranon_fracture_orif, mod=N/A, string=`No free-form guessing`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "olecranon_fracture_orif", "procedure_name": "Olecranon Fracture ORIF", "orthobullets_slug": "olecranon-fractures", "source_url": "https://www.orthobullets.com/trauma/1021/olecranon-fr
- Line 9: proc=both_bone_forearm_fracture_orif, mod=N/A, string=`Primary structure at risk?`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "both_bone_forearm_fracture_orif", "procedure_name": "Both Bone Forearm Fracture ORIF", "orthobullets_slug": "forearm-fractures-both-bone", "source_url": "https://www.orthobullets.com/
- Line 9: proc=both_bone_forearm_fracture_orif, mod=N/A, string=`Key approach for this case`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "both_bone_forearm_fracture_orif", "procedure_name": "Both Bone Forearm Fracture ORIF", "orthobullets_slug": "forearm-fractures-both-bone", "source_url": "https://www.orthobullets.com/
- Line 11: proc=acetabulum_fracture_orif_posterior, mod=N/A, string=`Per map evidence`, field=`iteration_v1_4_notes`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "acetabulum_fracture_orif_posterior", "procedure_name": "Acetabulum Fracture ORIF (Posterior/Kocher-Langenbeck)", "orthobullets_slug": "acetabular-fractures", "source_url": "https://ww
- Line 11: proc=acetabulum_fracture_orif_posterior, mod=N/A, string=`Primary structure at risk?`, field=`iteration_v1_4_notes`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "acetabulum_fracture_orif_posterior", "procedure_name": "Acetabulum Fracture ORIF (Posterior/Kocher-Langenbeck)", "orthobullets_slug": "acetabular-fractures", "source_url": "https://ww
- Line 12: proc=pelvis_ring_fracture_orif, mod=N/A, string=`Per map evidence`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "pelvis_ring_fracture_orif", "procedure_name": "Pelvis Ring Fracture ORIF", "orthobullets_slug": "pelvis-fractures", "source_url": "https://www.orthobullets.com/trauma/1034/pelvis-frac
- Line 12: proc=pelvis_ring_fracture_orif, mod=N/A, string=`Primary structure at risk?`, field=`core_anatomy_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "pelvis_ring_fracture_orif", "procedure_name": "Pelvis Ring Fracture ORIF", "orthobullets_slug": "pelvis-fractures", "source_url": "https://www.orthobullets.com/trauma/1034/pelvis-frac
- Line 12: proc=pelvis_ring_fracture_orif, mod=N/A, string=`Key approach for this case`, field=`core_anatomy_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "pelvis_ring_fracture_orif", "procedure_name": "Pelvis Ring Fracture ORIF", "orthobullets_slug": "pelvis-fractures", "source_url": "https://www.orthobullets.com/trauma/1034/pelvis-frac
- Line 12: proc=pelvis_ring_fracture_orif, mod=N/A, string=`No free-form guessing`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "pelvis_ring_fracture_orif", "procedure_name": "Pelvis Ring Fracture ORIF", "orthobullets_slug": "pelvis-fractures", "source_url": "https://www.orthobullets.com/trauma/1034/pelvis-frac
- Line 12: proc=pelvis_ring_fracture_orif, mod=N/A, string=`unknown or uncertain type`, field=`case_readiness_gaps`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "pelvis_ring_fracture_orif", "procedure_name": "Pelvis Ring Fracture ORIF", "orthobullets_slug": "pelvis-fractures", "source_url": "https://www.orthobullets.com/trauma/1034/pelvis-frac
- Line 19: proc=rotator_cuff_repair, mod=N/A, string=`Primary structure at risk?`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "rotator_cuff_repair", "procedure_name": "Rotator Cuff Repair", "orthobullets_slug": "rotator-cuff-tears", "source_url": "https://www.orthobullets.com/shoulder-and-elbow/3043/rotator-c
- Line 19: proc=rotator_cuff_repair, mod=N/A, string=`Key approach for this case`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "rotator_cuff_repair", "procedure_name": "Rotator Cuff Repair", "orthobullets_slug": "rotator-cuff-tears", "source_url": "https://www.orthobullets.com/shoulder-and-elbow/3043/rotator-c
- Line 20: proc=carpal_tunnel_release, mod=N/A, string=`Primary structure at risk?`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "carpal_tunnel_release", "procedure_name": "Carpal Tunnel Release", "orthobullets_slug": "carpal-tunnel-syndrome", "source_url": "https://www.orthobullets.com/hand/6018/carpal-tunnel-s
- Line 20: proc=carpal_tunnel_release, mod=N/A, string=`Key approach for this case`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "carpal_tunnel_release", "procedure_name": "Carpal Tunnel Release", "orthobullets_slug": "carpal-tunnel-syndrome", "source_url": "https://www.orthobullets.com/hand/6018/carpal-tunnel-s
- Line 21: proc=cubital_tunnel_release, mod=N/A, string=`Per map evidence`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "cubital_tunnel_release", "procedure_name": "Cubital Tunnel Release", "orthobullets_slug": "cubital-tunnel-syndrome", "source_url": "https://www.orthobullets.com/hand/6021/cubital-tunn
- Line 21: proc=cubital_tunnel_release, mod=N/A, string=`Primary structure at risk?`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "cubital_tunnel_release", "procedure_name": "Cubital Tunnel Release", "orthobullets_slug": "cubital-tunnel-syndrome", "source_url": "https://www.orthobullets.com/hand/6021/cubital-tunn
- Line 21: proc=cubital_tunnel_release, mod=N/A, string=`Key approach for this case`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "cubital_tunnel_release", "procedure_name": "Cubital Tunnel Release", "orthobullets_slug": "cubital-tunnel-syndrome", "source_url": "https://www.orthobullets.com/hand/6021/cubital-tunn
- Line 21: proc=cubital_tunnel_release, mod=N/A, string=`No free-form guessing`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "cubital_tunnel_release", "procedure_name": "Cubital Tunnel Release", "orthobullets_slug": "cubital-tunnel-syndrome", "source_url": "https://www.orthobullets.com/hand/6021/cubital-tunn
- Line 22: proc=patella_fracture_orif, mod=N/A, string=`Per map evidence`, field=`iteration_v1_4_notes`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "patella_fracture_orif", "procedure_name": "Patella Fracture ORIF", "orthobullets_slug": "patella-fractures", "source_url": "https://www.orthobullets.com/trauma/1044/patella-fractures"
- Line 22: proc=patella_fracture_orif, mod=N/A, string=`Primary structure at risk?`, field=`iteration_v1_4_notes`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "patella_fracture_orif", "procedure_name": "Patella Fracture ORIF", "orthobullets_slug": "patella-fractures", "source_url": "https://www.orthobullets.com/trauma/1044/patella-fractures"
- Line 23: proc=tibial_plateau_fracture_orif, mod=N/A, string=`Primary structure at risk?`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "tibial_plateau_fracture_orif", "procedure_name": "Tibial Plateau Fracture ORIF", "orthobullets_slug": "tibial-plateau-fractures", "source_url": "https://www.orthobullets.com/trauma/10
- Line 23: proc=tibial_plateau_fracture_orif, mod=N/A, string=`Key approach for this case`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "tibial_plateau_fracture_orif", "procedure_name": "Tibial Plateau Fracture ORIF", "orthobullets_slug": "tibial-plateau-fractures", "source_url": "https://www.orthobullets.com/trauma/10
- Line 25: proc=clavicle_fracture_orif, mod=N/A, string=`Per map evidence`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "clavicle_fracture_orif", "procedure_name": "Clavicle Fracture ORIF", "orthobullets_slug": "clavicle-fractures", "source_url": "https://www.orthobullets.com/trauma/1016/clavicle-fractu
- Line 25: proc=clavicle_fracture_orif, mod=N/A, string=`Primary structure at risk?`, field=`core_anatomy_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "clavicle_fracture_orif", "procedure_name": "Clavicle Fracture ORIF", "orthobullets_slug": "clavicle-fractures", "source_url": "https://www.orthobullets.com/trauma/1016/clavicle-fractu
- Line 25: proc=clavicle_fracture_orif, mod=N/A, string=`Key approach for this case`, field=`core_anatomy_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "clavicle_fracture_orif", "procedure_name": "Clavicle Fracture ORIF", "orthobullets_slug": "clavicle-fractures", "source_url": "https://www.orthobullets.com/trauma/1016/clavicle-fractu
- Line 25: proc=clavicle_fracture_orif, mod=N/A, string=`No free-form guessing`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "clavicle_fracture_orif", "procedure_name": "Clavicle Fracture ORIF", "orthobullets_slug": "clavicle-fractures", "source_url": "https://www.orthobullets.com/trauma/1016/clavicle-fractu
- Line 26: proc=scaphoid_fracture_orif, mod=N/A, string=`Primary structure at risk?`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "scaphoid_fracture_orif", "procedure_name": "Scaphoid Fracture ORIF", "orthobullets_slug": "scaphoid-fracture", "source_url": "https://www.orthobullets.com/hand/6009/scaphoid-fracture"
- Line 26: proc=scaphoid_fracture_orif, mod=N/A, string=`Key approach for this case`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "scaphoid_fracture_orif", "procedure_name": "Scaphoid Fracture ORIF", "orthobullets_slug": "scaphoid-fracture", "source_url": "https://www.orthobullets.com/hand/6009/scaphoid-fracture"
- Line 27: proc=monteggia_fracture_orif, mod=N/A, string=`Per map evidence`, field=`iteration_v1_4_notes`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "monteggia_fracture_orif", "procedure_name": "Monteggia Fracture ORIF", "orthobullets_slug": "monteggia-fractures", "source_url": "https://www.orthobullets.com/trauma/1024/monteggia-fr
- Line 27: proc=monteggia_fracture_orif, mod=N/A, string=`Primary structure at risk?`, field=`iteration_v1_4_notes`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "monteggia_fracture_orif", "procedure_name": "Monteggia Fracture ORIF", "orthobullets_slug": "monteggia-fractures", "source_url": "https://www.orthobullets.com/trauma/1024/monteggia-fr
- Line 28: proc=achilles_tendon_repair, mod=N/A, string=`Primary structure at risk?`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "achilles_tendon_repair", "procedure_name": "Achilles Tendon Repair", "orthobullets_slug": "achilles-tendon-rupture", "source_url": "https://www.orthobullets.com/sports/3009/achilles-t
- Line 28: proc=achilles_tendon_repair, mod=N/A, string=`Key approach for this case`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "achilles_tendon_repair", "procedure_name": "Achilles Tendon Repair", "orthobullets_slug": "achilles-tendon-rupture", "source_url": "https://www.orthobullets.com/sports/3009/achilles-t
- Line 30: proc=high_tibial_osteotomy, mod=N/A, string=`Primary structure at risk?`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "high_tibial_osteotomy", "procedure_name": "High Tibial Osteotomy", "orthobullets_slug": "high-tibial-osteotomy", "source_url": "https://www.orthobullets.com/recon/3135/high-tibial-ost
- Line 30: proc=high_tibial_osteotomy, mod=N/A, string=`Key approach for this case`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "high_tibial_osteotomy", "procedure_name": "High Tibial Osteotomy", "orthobullets_slug": "high-tibial-osteotomy", "source_url": "https://www.orthobullets.com/recon/3135/high-tibial-ost
- Line 31: proc=supracondylar_humerus_fracture_pediatric, mod=N/A, string=`Per map evidence`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "supracondylar_humerus_fracture_pediatric", "procedure_name": "Supracondylar Humerus Fracture (Pediatric) ORIF/CRPP", "orthobullets_slug": "supracondylar-fracture--pediatric", "source_
- Line 31: proc=supracondylar_humerus_fracture_pediatric, mod=N/A, string=`Primary structure at risk?`, field=`core_anatomy_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "supracondylar_humerus_fracture_pediatric", "procedure_name": "Supracondylar Humerus Fracture (Pediatric) ORIF/CRPP", "orthobullets_slug": "supracondylar-fracture--pediatric", "source_
- Line 31: proc=supracondylar_humerus_fracture_pediatric, mod=N/A, string=`Key approach for this case`, field=`core_anatomy_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "supracondylar_humerus_fracture_pediatric", "procedure_name": "Supracondylar Humerus Fracture (Pediatric) ORIF/CRPP", "orthobullets_slug": "supracondylar-fracture--pediatric", "source_
- Line 31: proc=supracondylar_humerus_fracture_pediatric, mod=N/A, string=`No free-form guessing`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "supracondylar_humerus_fracture_pediatric", "procedure_name": "Supracondylar Humerus Fracture (Pediatric) ORIF/CRPP", "orthobullets_slug": "supracondylar-fracture--pediatric", "source_
- Line 31: proc=supracondylar_humerus_fracture_pediatric, mod=N/A, string=`unknown or uncertain type`, field=`case_readiness_gaps`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "supracondylar_humerus_fracture_pediatric", "procedure_name": "Supracondylar Humerus Fracture (Pediatric) ORIF/CRPP", "orthobullets_slug": "supracondylar-fracture--pediatric", "source_
- Line 32: proc=intertrochanteric_hip_fracture_orif, mod=N/A, string=`Primary structure at risk?`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "intertrochanteric_hip_fracture_orif", "procedure_name": "Intertrochanteric Hip Fracture ORIF", "orthobullets_slug": "intertrochanteric-fractures", "source_url": "https://www.orthobull
- Line 32: proc=intertrochanteric_hip_fracture_orif, mod=N/A, string=`Key approach for this case`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "intertrochanteric_hip_fracture_orif", "procedure_name": "Intertrochanteric Hip Fracture ORIF", "orthobullets_slug": "intertrochanteric-fractures", "source_url": "https://www.orthobull
- Line 33: proc=femoral_neck_fracture_orif_young, mod=N/A, string=`Primary structure at risk?`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "femoral_neck_fracture_orif_young", "procedure_name": "Femoral Neck Fracture ORIF (Young Patient)", "orthobullets_slug": "femoral-neck-fractures", "source_url": "https://www.orthobulle
- Line 33: proc=femoral_neck_fracture_orif_young, mod=N/A, string=`Key approach for this case`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "femoral_neck_fracture_orif_young", "procedure_name": "Femoral Neck Fracture ORIF (Young Patient)", "orthobullets_slug": "femoral-neck-fractures", "source_url": "https://www.orthobulle
- Line 34: proc=revision_tha, mod=N/A, string=`Primary structure at risk?`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "revision_tha", "procedure_name": "Revision Total Hip Arthroplasty", "orthobullets_slug": "tha-approaches", "source_url": "https://www.orthobullets.com/recon/12116/tha-approaches", "ca
- Line 34: proc=revision_tha, mod=N/A, string=`Key approach for this case`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "revision_tha", "procedure_name": "Revision Total Hip Arthroplasty", "orthobullets_slug": "tha-approaches", "source_url": "https://www.orthobullets.com/recon/12116/tha-approaches", "ca
- Line 35: proc=revision_tka, mod=N/A, string=`Primary structure at risk?`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "revision_tka", "procedure_name": "Revision Total Knee Arthroplasty", "orthobullets_slug": "total-knee-arthroplasty", "source_url": "https://www.orthobullets.com/recon/12289/total-knee
- Line 35: proc=revision_tka, mod=N/A, string=`Key approach for this case`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "revision_tka", "procedure_name": "Revision Total Knee Arthroplasty", "orthobullets_slug": "total-knee-arthroplasty", "source_url": "https://www.orthobullets.com/recon/12289/total-knee
- Line 37: proc=hallux_valgus_correction, mod=N/A, string=`Per map evidence`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "hallux_valgus_correction", "procedure_name": "Hallux Valgus (Bunion) Correction", "orthobullets_slug": "hallux-valgus", "source_url": "https://www.orthobullets.com/foot-and-ankle/1213
- Line 37: proc=hallux_valgus_correction, mod=N/A, string=`Primary structure at risk?`, field=`core_anatomy_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "hallux_valgus_correction", "procedure_name": "Hallux Valgus (Bunion) Correction", "orthobullets_slug": "hallux-valgus", "source_url": "https://www.orthobullets.com/foot-and-ankle/1213
- Line 37: proc=hallux_valgus_correction, mod=N/A, string=`Key approach for this case`, field=`core_anatomy_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "hallux_valgus_correction", "procedure_name": "Hallux Valgus (Bunion) Correction", "orthobullets_slug": "hallux-valgus", "source_url": "https://www.orthobullets.com/foot-and-ankle/1213
- Line 37: proc=hallux_valgus_correction, mod=N/A, string=`No free-form guessing`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "hallux_valgus_correction", "procedure_name": "Hallux Valgus (Bunion) Correction", "orthobullets_slug": "hallux-valgus", "source_url": "https://www.orthobullets.com/foot-and-ankle/1213
- Line 37: proc=hallux_valgus_correction, mod=N/A, string=`unknown or uncertain type`, field=`case_readiness_gaps`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "hallux_valgus_correction", "procedure_name": "Hallux Valgus (Bunion) Correction", "orthobullets_slug": "hallux-valgus", "source_url": "https://www.orthobullets.com/foot-and-ankle/1213
- Line 38: proc=trigger_finger_release, mod=N/A, string=`Per map evidence`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "trigger_finger_release", "procedure_name": "Trigger Finger Release", "orthobullets_slug": "trigger-finger", "source_url": "https://www.orthobullets.com/hand/6014/trigger-finger", "cas
- Line 38: proc=trigger_finger_release, mod=N/A, string=`Primary structure at risk?`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "trigger_finger_release", "procedure_name": "Trigger Finger Release", "orthobullets_slug": "trigger-finger", "source_url": "https://www.orthobullets.com/hand/6014/trigger-finger", "cas
- Line 38: proc=trigger_finger_release, mod=N/A, string=`Key approach for this case`, field=`brobot_case_prep_questions`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "trigger_finger_release", "procedure_name": "Trigger Finger Release", "orthobullets_slug": "trigger-finger", "source_url": "https://www.orthobullets.com/hand/6014/trigger-finger", "cas
- Line 38: proc=trigger_finger_release, mod=N/A, string=`No free-form guessing`, field=`must_know_before_case`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "trigger_finger_release", "procedure_name": "Trigger Finger Release", "orthobullets_slug": "trigger-finger", "source_url": "https://www.orthobullets.com/hand/6014/trigger-finger", "cas
- Line 51: proc=metacarpal_fracture_orif, mod=N/A, string=`Per map evidence`, field=`iteration_v1_4_notes`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "metacarpal_fracture_orif", "procedure_name": "Metacarpal Fracture ORIF (incl. Boxer's)", "orthobullets_slug": "metacarpal-fractures", "source_url": "https://www.orthobullets.com/hand/
- Line 51: proc=metacarpal_fracture_orif, mod=N/A, string=`Primary structure at risk?`, field=`iteration_v1_4_notes`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "metacarpal_fracture_orif", "procedure_name": "Metacarpal Fracture ORIF (incl. Boxer's)", "orthobullets_slug": "metacarpal-fractures", "source_url": "https://www.orthobullets.com/hand/
- Line 54: proc=cervical_laminectomy_fusion, mod=N/A, string=`Per map evidence`, field=`iteration_v1_4_notes`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "cervical_laminectomy_fusion", "procedure_name": "Posterior Cervical Laminectomy and Fusion", "orthobullets_slug": "cervical_laminectomy_fusion", "source_url": "", "case_anatomy_type":
- Line 54: proc=cervical_laminectomy_fusion, mod=N/A, string=`Primary structure at risk?`, field=`iteration_v1_4_notes`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "cervical_laminectomy_fusion", "procedure_name": "Posterior Cervical Laminectomy and Fusion", "orthobullets_slug": "cervical_laminectomy_fusion", "source_url": "", "case_anatomy_type":
- Line 55: proc=plantar_fasciitis_release, mod=N/A, string=`Per map evidence`, field=`iteration_v1_4_notes`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "plantar_fasciitis_release", "procedure_name": "Plantar Fasciitis Release", "orthobullets_slug": "plantar_fasciitis_release", "source_url": "", "case_anatomy_type": "decompression_or_r
- Line 55: proc=plantar_fasciitis_release, mod=N/A, string=`Primary structure at risk?`, field=`iteration_v1_4_notes`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "plantar_fasciitis_release", "procedure_name": "Plantar Fasciitis Release", "orthobullets_slug": "plantar_fasciitis_release", "source_url": "", "case_anatomy_type": "decompression_or_r
- Line 57: proc=elbow_arthroscopy, mod=N/A, string=`Per map evidence`, field=`iteration_v1_4_notes`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "elbow_arthroscopy", "procedure_name": "Elbow Arthroscopy", "orthobullets_slug": "elbow_arthroscopy", "source_url": "", "case_anatomy_type": "arthroscopy_or_endoscopy", "anatomy_priori
- Line 57: proc=elbow_arthroscopy, mod=N/A, string=`Primary structure at risk?`, field=`iteration_v1_4_notes`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "elbow_arthroscopy", "procedure_name": "Elbow Arthroscopy", "orthobullets_slug": "elbow_arthroscopy", "source_url": "", "case_anatomy_type": "arthroscopy_or_endoscopy", "anatomy_priori
- Line 59: proc=quadriceps_tendon_repair, mod=N/A, string=`Per map evidence`, field=`iteration_v1_4_notes`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "quadriceps_tendon_repair", "procedure_name": "Quadriceps Tendon Repair", "orthobullets_slug": "quadriceps_tendon_repair", "source_url": "", "case_anatomy_type": "soft_tissue_repair", 
- Line 59: proc=quadriceps_tendon_repair, mod=N/A, string=`Primary structure at risk?`, field=`iteration_v1_4_notes`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "quadriceps_tendon_repair", "procedure_name": "Quadriceps Tendon Repair", "orthobullets_slug": "quadriceps_tendon_repair", "source_url": "", "case_anatomy_type": "soft_tissue_repair", 
- Line 60: proc=boxers_fracture_orif, mod=N/A, string=`Per map evidence`, field=`iteration_v1_4_notes`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "boxers_fracture_orif", "procedure_name": "Boxer's (5th Metacarpal Neck) Fracture ORIF", "orthobullets_slug": "boxers_fracture_orif", "source_url": "", "case_anatomy_type": "mixed", "a
- Line 60: proc=boxers_fracture_orif, mod=N/A, string=`Primary structure at risk?`, field=`iteration_v1_4_notes`, impact=`non_cert_or_registry`
  Context: {"schema_version": "brobot_anatomy_procedure_v1", "procedure_id": "boxers_fracture_orif", "procedure_name": "Boxer's (5th Metacarpal Neck) Fracture ORIF", "orthobullets_slug": "boxers_fracture_orif", "source_url": "", "case_anatomy_type": "mixed", "a

