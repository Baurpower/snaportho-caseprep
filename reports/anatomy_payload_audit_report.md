# Anatomy Payload Audit Report

Payloads audited: 24
Issues: 46
FAIL: 0, MAJOR: 1, MINOR: 45

## Issues by output category (source separated from clinical usability)

- **clinical_usability**: 7
- **source_quality**: 15
- **schema_quality**: 24

## Detailed issues

- **distal_radius_fracture_orif** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **hip_hemiarthroplasty** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **tha_posterior** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **tha_anterior** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **tha_anterior** | MINOR | source_quality
  Problem: Low source diversity (1 URL(s)); item-level source_refs provide support.
  Fix: Add additional primary sources if available; otherwise acceptable for clinically usable payload.

- **tka** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **acl_reconstruction** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **femoral_shaft_fracture_orif** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **femoral_shaft_fracture_orif** | MAJOR | clinical_usability
  Problem: Stringified dict corruption detected in educational fields (e.g. {'structure': '{...} or similar).
  Fix: Rebuild lists from clean source-backed strings or properly structured dicts. Remove any JSON-string artifacts from prior synthesis.

- **humeral_shaft_fracture_orif** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **humeral_shaft_fracture_orif** | MINOR | source_quality
  Problem: Low source diversity (1 URL(s)); item-level source_refs provide support.
  Fix: Add additional primary sources if available; otherwise acceptable for clinically usable payload.

- **scfe_pinning** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **scfe_pinning** | MINOR | source_quality
  Problem: Low source diversity (1 URL(s)); item-level source_refs provide support.
  Fix: Add additional primary sources if available; otherwise acceptable for clinically usable payload.

- **scfe_pinning** | MINOR | clinical_usability
  Problem: Contains generic filler pattern: \bkey anatomy\b
  Fix: Replace with specific, actionable fact for this case/approach.

- **posterior_lumbar_decompression_fusion** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **posterior_lumbar_decompression_fusion** | MINOR | source_quality
  Problem: Low source diversity (1 URL(s)); item-level source_refs provide support.
  Fix: Add additional primary sources if available; otherwise acceptable for clinically usable payload.

- **posterior_lumbar_decompression_fusion** | MINOR | clinical_usability
  Problem: Contains generic filler pattern: \bkey anatomy\b
  Fix: Replace with specific, actionable fact for this case/approach.

- **total_shoulder_arthroplasty** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **total_shoulder_arthroplasty** | MINOR | source_quality
  Problem: Low source diversity (1 URL(s)); item-level source_refs provide support.
  Fix: Add additional primary sources if available; otherwise acceptable for clinically usable payload.

- **total_shoulder_arthroplasty** | MINOR | clinical_usability
  Problem: Contains generic filler pattern: \bkey anatomy\b
  Fix: Replace with specific, actionable fact for this case/approach.

- **tibial_shaft_fracture_orif** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **tibial_shaft_fracture_orif** | MINOR | source_quality
  Problem: Low source diversity (1 URL(s)); item-level source_refs provide support.
  Fix: Add additional primary sources if available; otherwise acceptable for clinically usable payload.

- **meniscus_repair** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **meniscus_repair** | MINOR | source_quality
  Problem: Low source diversity (1 URL(s)); item-level source_refs provide support.
  Fix: Add additional primary sources if available; otherwise acceptable for clinically usable payload.

- **reverse_shoulder_arthroplasty** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **lateral_ankle_ligament_repair** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **lateral_ankle_ligament_repair** | MINOR | source_quality
  Problem: Low source diversity (1 URL(s)); item-level source_refs provide support.
  Fix: Add additional primary sources if available; otherwise acceptable for clinically usable payload.

- **lateral_ankle_ligament_repair** | MINOR | clinical_usability
  Problem: Contains generic filler pattern: \bkey anatomy\b
  Fix: Replace with specific, actionable fact for this case/approach.

- **distal_femur_fracture_orif** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **distal_femur_fracture_orif** | MINOR | source_quality
  Problem: Low source diversity (1 URL(s)); item-level source_refs provide support.
  Fix: Add additional primary sources if available; otherwise acceptable for clinically usable payload.

- **pelvis_ring_fracture_orif** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **supracondylar_humerus_fracture_pediatric** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **supracondylar_humerus_fracture_pediatric** | MINOR | source_quality
  Problem: Low source diversity (1 URL(s)); item-level source_refs provide support.
  Fix: Add additional primary sources if available; otherwise acceptable for clinically usable payload.

- **supracondylar_humerus_fracture_pediatric** | MINOR | clinical_usability
  Problem: Contains generic filler pattern: \bkey anatomy\b
  Fix: Replace with specific, actionable fact for this case/approach.

- **hallux_valgus_correction** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **hallux_valgus_correction** | MINOR | source_quality
  Problem: Low source diversity (1 URL(s)); item-level source_refs provide support.
  Fix: Add additional primary sources if available; otherwise acceptable for clinically usable payload.

- **plantar_fasciitis_release** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **plantar_fasciitis_release** | MINOR | source_quality
  Problem: Low source diversity (1 URL(s)); item-level source_refs provide support.
  Fix: Add additional primary sources if available; otherwise acceptable for clinically usable payload.

- **plantar_fasciitis_release** | MINOR | clinical_usability
  Problem: Contains generic filler pattern: \bkey anatomy\b
  Fix: Replace with specific, actionable fact for this case/approach.

- **quadriceps_tendon_repair** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **quadriceps_tendon_repair** | MINOR | source_quality
  Problem: Low source diversity (1 URL(s)); item-level source_refs provide support.
  Fix: Add additional primary sources if available; otherwise acceptable for clinically usable payload.

- **acetabulum_fracture_orif_anterior** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **acetabulum_fracture_orif_anterior** | MINOR | source_quality
  Problem: Low source diversity (1 URL(s)); item-level source_refs provide support.
  Fix: Add additional primary sources if available; otherwise acceptable for clinically usable payload.

- **acetabulum_fracture_orif_posterior** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

- **acetabulum_fracture_orif_posterior** | MINOR | source_quality
  Problem: Low source diversity (1 URL(s)); item-level source_refs provide support.
  Fix: Add additional primary sources if available; otherwise acceptable for clinically usable payload.

- **monteggia_fracture_orif** | MINOR | schema_quality
  Problem: Old or missing schema_version: brobot_case_prep_payload_v2
  Fix: Bump to brobot_case_prep_payload_v2 and migrate structure.

