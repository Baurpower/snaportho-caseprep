# Orthobullets Top-100 Candidate Inventory (for v2 Playbook Expansion)

**Generated**: Current session, using ONLY site:orthobullets.com searches and page content snippets (web_search site: + targeted).
**Goal**: Identify high-yield orthopaedic procedures/cases for resident case-prep across specialties. Quality > quantity. Do not enrich yet.
**Rules applied**: Prefer common volume procedures (ORIF, recon, sports soft tissue, peds pinning, spine decomp/fusion). Note explicit approach/anatomy support from OB pages. Flag catalog gaps. already_in_v1_1 based on exact procedure_id match from current v1.1 (38 total).

**Catalog constraint reminder** (30 real IDs only; from data/upper... + lower...):
Upper: approach_shoulder_deltopectoral, approach_shoulder_lateral_deltoid_split, approach_shoulder_posterior, approach_humerus_anterolateral_distal, approach_humerus_posterior_triceps_split, approach_elbow_lateral_kocher, approach_forearm_anterior_henry, approach_wrist_dorsal, approach_wrist_volar_distal_henry, approach_wrist_carpal_tunnel.
Lower: ...iliac_crest_*, pelvis_acetabulum_* (ilioinguinal + KL), hip_* (Smith-Peterson, Watson-Jones, Hardinge, Moore/Southern, Ludloff), thigh_* (lateral, posterolateral, anteromedial), knee_* (medial_parapatellar, medial, lateral, posterior), leg_* (lateral, medial), ankle_* (anterior, posteromedial).

No spine, no dedicated lateral fibula/calcaneus/Lisfranc/midfoot, no posterior elbow (olecranon/cubital), no medial malleolus separate, limited peds specifics.

## Inventory (selected high/medium priority candidates; ~70+ listed for breadth, not all will be added)
Prioritization: high = common recon/trauma/sports/peds case prep with OB procedure + approach sections; medium = useful but less universal or partial support; low = rare or weak OB approach/anatomy text. already_in_v1_1 noted. proposed_priority for selection.

### Trauma (high volume ORIF / fractures)
- proximal_humerus_fracture_orif (already_in_v1_1: true; specialty: trauma; region: shoulder; url: https://www.orthobullets.com/trauma/1015/proximal-humerus-fractures or /1018; reason_for_priority: very common elderly + young; deltopectoral/lateral split supported + Neer anatomy, blood supply (ant/post circumflex), deforming forces (pec major, deltoid, rotators); currently thin 0s in v1.1 despite recs; high)
- humeral_shaft_fracture_orif (already: false; trauma; humerus; https://www.orthobullets.com/trauma/1016/humeral-shaft-fractures; radial n. risk, Holstein-Lewis; approaches anterolateral distal or posterior triceps (catalog has both); high)
- both_bone_forearm_fracture_orif (already: true; trauma; forearm; https://www.orthobullets.com/trauma/1023/forearm-fractures-both-bone; Henry for radius, ulna subcutaneous; currently thin; high)
- olecranon_fracture_orif (already: true; trauma; elbow; https://www.orthobullets.com/trauma/1021/olecranon-fractures; posterior approach (12005 exists on OB: triceps split/olecranon osteotomy for intra-articular); but no posterior elbow catalog ID (only Kocher) → will be manual; medium)
- radial_head_fracture_orif (already: true; trauma; elbow; https://www.orthobullets.com/trauma/1020/radial-head-fractures; Kocher lateral; currently thin; medium-high)
- clavicle_fracture_orif (already: true; trauma; shoulder; https://www.orthobullets.com/trauma/1016/clavicle-fractures; superior/anterior direct; no dedicated catalog ID → manual; medium)
- distal_radius_fracture_orif (already: true; strong already; keep/enrich if new; high)
- scaphoid_fracture_orif (already: true; hand; https://www.orthobullets.com/hand/6034/scaphoid-fracture or 6009; volar Henry or dorsal; percutaneous vs ORIF; thin; high)
- tibial_plateau_fracture_orif (already: true; trauma; knee; https://www.orthobullets.com/trauma/1042/tibial-plateau-fractures; parapatellar + lateral knee; minimal now; high)
- patella_fracture_orif (already: true; trauma; knee; extensor mechanism; minimal; medium)
- femoral_shaft_fracture_orif (already: true; strong post v1.1; but note IMN more common than plate in many; medium for ORIF variant)
- intertrochanteric_hip_fracture_orif (already: true; trauma; hip; https://www.orthobullets.com/trauma/1037 or specific; lateral/Hardinge or trochanteric; thin; high)
- femoral_neck_fracture_orif_young (already: true; trauma/recon; hip; young patient ORIF vs hemi; thin; high)
- acetabulum_fracture_orif_* (already: true; pelvis; good recs ilioinguinal/KL but 0 anatomy; high)
- calcaneus_fracture_orif (already: true; foot; https://www.orthobullets.com/trauma/1051/calcaneus-fractures; extensile lateral L-shaped; no catalog ID for it → manual; high volume but gap)
- pilon_ankle_fracture_orif (already: true; ankle; manual due to gaps; medium)
- bimalleolar/trimalleolar (already: true; manual due to gaps; high volume but gap)
- Lisfranc ORIF / arthrodesis (already: false; foot_ankle; https://www.orthobullets.com/foot-and-ankle/7030/lisfranc-injury + approaches/12129; ORIF with dual longitudinal incisions (1-2 webspace), screws/plates for medial column; primary arthrodesis for ligamentous/chronic; no exact Lisfranc catalog ID (use ankle anterior? or manual); high priority for midfoot trauma)
- tibial_shaft_fracture_orif (already: false; trauma; leg; https://www.orthobullets.com/trauma/1043/tibial-shaft-fractures (inferred common); leg lateral/medial approaches catalog; IMN primary but plate ORIF supported; high)
- distal_femur_fracture_orif (already: false; trauma; thigh/knee; supracondylar, Hoffa; knee parapatellar + lateral or posterior; high)
- pelvis_ring_fracture_orif (already: true; manual; medium)

### Sports / Soft Tissue / Knee-Shoulder
- acl_reconstruction (already: true; sports; knee; https://www.orthobullets.com/knee-and-sports/3008/acl-tear (or 3007 prior); parapatellar approach (catalog has); bundles, footprints, landmarks (tibial tubercle, lateral femoral condyle, notch); risks (saphenous infrapatellar, peroneal, popliteal if described); currently 0s; high)
- rotator_cuff_repair (already: true; sports/shoulder; https://www.orthobullets.com/shoulder-and-elbow/3043/rotator-cuff-tears; mini-open (lateral deltoid split catalog), arthroscopic; margin convergence, footprint, subscap; currently 0s; high)
- achilles_tendon_repair (already: true; sports; ankle; https://www.orthobullets.com/sports/3009/achilles-tendon-rupture; posteromedial (catalog has); high)
- meniscus_repair / meniscectomy (already: false; sports; knee; common; parapatellar portals/approach; high)
- shoulder_anterior_instability_bankart_repair (already: false; sports; shoulder; deltopectoral or arthro; high)
- lateral_ankle_ligament_repair / brostrom (already: false; sports; ankle; anterior or posterolateral? ; medium)
- high_tibial_osteotomy (already: true; recon/sports; knee; thin; medium)
- total_ankle_arthroplasty (already: true; foot_ankle; anterior ankle; thin; medium)
- ankle_arthrodesis (already: true; foot_ankle; anterior; thin; medium)

### Hand / Wrist / Elbow
- carpal_tunnel_release (already: true; hand; improved in v1.1 but verify; high)
- cubital_tunnel_release (already: true; hand/elbow; manual due to no medial elbow catalog; high volume; medium)
- trigger_finger_release (already: true; hand; manual?; medium)
- scaphoid (see trauma)
- metacarpal_fracture_orif / boxer's (already: false; hand; perhaps dorsal or Henry variant; medium)
- distal_humerus_fracture_orif (already: false; trauma; elbow; posterior elbow approach on OB (12005: olecranon osteotomy for intra-artic); catalog has humerus_posterior_triceps_split; high if matches)

### Adult Reconstruction (beyond current hip/knee)
- total_shoulder_arthroplasty (already: false; recon; shoulder; deltopectoral (catalog); high)
- reverse_shoulder_arthroplasty (already: false; recon; shoulder; deltopectoral or lateral; high)
- revision_tha / revision_tka (already: true; thin; high volume cases)
- unicompartmental_knee (already: false; recon; knee; parapatellar or medial; medium)

### Pediatrics
- supracondylar_humerus_fracture_pediatric (already: true; pediatrics; manual or limited; https://www.orthobullets.com/pediatrics/4006 or similar; CRPP/pinning; high)
- scfe_pinning (already: false; pediatrics; hip; https://www.orthobullets.com/pediatrics/4040/slipped-capital-femoral-epiphysis-scfe; percutaneous in situ fixation (1-2 screws, central axis, 5 threads), modified Dunn open for unstable/severe; no specific peds hip pinning catalog ID (use hip approaches?); high priority peds case)
- ddh_pavlik_or_closed_reduction_or_osteotomy (already: false; pediatrics; hip; https://www.orthobullets.com/pediatrics/4118/developmental-dysplasia-of-the-hip-ddh; Pavlik harness, closed/open reduction, Salter/Dega osteotomy, femoral varus; approaches (medial Ludloff catalog or anterior Smith-Peterson); high)
- legg_calve_perthes (already: false; pediatrics; hip; containment osteotomies; medium)
- both_bone_forearm_pediatric (already: false; pediatrics; forearm; medium)
- distal_humerus_physeal_separation_pediatric (already: false; peds elbow; CRPP; medium)

### Spine (high yield but catalog gap = likely manual_review or limited)
- anterior_cervical_disectomy_and_fusion_acdf (already: false; spine; https://www.orthobullets.com/approaches/12001/anterior-approach-to-cervical-spine + spine/2031; transverse incision, platysma split, SCM lateral, carotid sheath lateral, longus colli, ALL, discectomy/corpectomy; excellent explicit approach anatomy/landmarks/dangers (sympathetic chain, recurrent laryngeal?); high for cervical but NO spine catalog ID → manual_review + empty recs)
- posterior_lumbar_decompression_fusion (already: false; spine; https://www.orthobullets.com/approaches/12003/posterior-approach-to-lumbar-spine; midline, spinous process, paraspinal subperiosteal, ligamentum flavum, dura; for discectomy/fusion/tumor; high volume but no catalog → manual)
- posterior_cervical_laminectomy_fusion (already: false; spine; limited page info but exists; medium)
- transthoracic_thoracic_spine (already: false; spine; https://www.orthobullets.com/approaches/2079/transthoracic-approach-to-thoracic-spine; for anterior thoracic; medium, less common)

### Foot & Ankle additional
- hallux_valgus_correction (already: true; foot_ankle; https://www.orthobullets.com/foot-and-ankle/7008/hallux-valgus; distal chevron, proximal, Lapidus, etc.; manual due to gaps; high volume)
- (Lisfranc, calcaneus, total ankle, arthrodesis already noted)

### Other / Filler (medium/low if evidence)
- More peds (Perthes, CP hip), elbow arthroscopy or lateral epicondylitis release, wrist arthroscopy/TFCC, plantar fasciitis release, quadriceps/patellar tendon repair, periprosthetic fx, etc. Only add if strong OB + feasible map.

**Summary stats from inventory**:
- ~38 already in v1.1 (many thin or manual).
- ~30-40 strong new/high-priority candidates with clear OB procedure pages + approach/anatomy text (ACL, rotator cuff, Lisfranc, SCFE, DDH, ACDF, lumbar post, humeral shaft, tibial shaft, total shoulder, meniscus, etc.).
- ~15-20 that will require manual_review due to catalog gaps (spine all, Lisfranc likely, more ankle/foot specifics, cubital/olecranon already flagged).
- Total potential high-quality: 70-90 if we add ~35-50 new (stop at 60-80 total if evidence for fields weak on some pages).
- Gaps that block full deterministic routing: spine (0 IDs), Lisfranc/midfoot/calcaneus lateral, posterior elbow, dedicated ankle lateral/medial malleolus, clavicle.

**Selection guidance for Task 3**: Prioritize the exact list in query (ACL, rotator cuff, prox humerus, clavicle, olecranon, both-bone, scaphoid, trigger/cubital, Achilles, Lisfranc, calcaneus, hallux, supracondylar, SCFE, DDH) + high-yield missing with OB support (humeral/tibial shaft, total shoulder, ACDF/post lumbar, meniscus). Enrich only those with explicit facts from pages; add with recs only on real catalog matches or []+manual_review. Preserve all v1.1 as base.

This inventory is OB-sourced only (no external lists). Ready for batch selection + enrichment pass.
