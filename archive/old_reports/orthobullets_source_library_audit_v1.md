# Orthobullets Source Library Audit v1

**Date:** 2026-06-06T17:26:11.612673Z  
**Schema:** orthobullets_source_library_v1 / queue_v1 / fetch_log_v1  
**Purpose:** Router-driven evidence acquisition only (no module/router updates this pass).

## 1. Number of procedures in router
60 (brobot_anatomy_router_v1_1.jsonl)

## 2. Number of procedures queued for source acquisition
60 (all router procedures have queue entries; 40 high priority per rules)

## 3. Queue count by priority
- high: 40
- medium: 20
- low: 0

High priority driven by: case_readiness_score <=2 (30 total low in router), manual_review=true (33), high-yield common procedures with gaps, procedures with missing/thin modules or explicit approach/portal/reduction/decomp gaps per router.

## 4. Number of Orthobullets source records created
51

## 5. Number of successful fetches
51 (mix of "existing_local_derived" from v1_1 modules provenance + live browse of key pages e.g. ankle 1047)

## 6. Number of failed/skipped/blocked fetches
5 logged (primarily the 7 procedures with only short slugs/no full source_url in router: cervical_laminectomy_fusion, plantar_fasciitis_release, elbow_arthroscopy, wrist_arthroscopy_tfcc, quadriceps_tendon_repair, boxers, periprosthetic; plus old slugs that resolved to different pages e.g. olecranon 1021->1022, clavicle 1016->1011). Reason recorded: page moves + preference for full layered approach cards over general trauma pages. Search snippets used for partial extraction where available.

## 7. Procedures with source coverage
44 (via direct page or shared sources from modules/trauma pages). Examples: distal_radius_fracture_orif (FCR approach 12071 + distal radius trauma), tka (medial parapatellar 12028), acl_reconstruction (3008 + approach), hip family (12116/12022/12023), carpal_tunnel_release (12014), proximal_humerus, femoral shaft, ankle family (new 1047), olecranon (1022 + 12005), clavicle (1011), acdf (12001), wrist TFCC (6009).

## 8. Procedures still lacking source coverage (or thin)
Primarily low-score/manual procedures where catalog gaps (no dedicated lateral fibula/medial malleolus, no clavicle approach card, limited posterior cervical layered) prevent full module population even when main trauma page exists. Examples: patella_fracture_orif, monteggia_fracture_orif, metacarpal_fracture_orif, cervical_laminectomy_fusion, plantar_fasciitis_release, periprosthetic_hip_fracture_orif. Full list of low readiness remains ~22-25 per prior procedure readiness audit; source pages now available for most via this pass.

## 9. Anatomy domains covered
approach anatomy(35), pathology anatomy(27), reduction/implant anatomy(8), structures at risk(5), soft tissue footprint(3), decompression boundaries(3), landmarks(3), arthroscopy/portals(1)

Strong: approach anatomy, structures at risk, landmarks, reduction/implant anatomy (from trauma pages + dedicated approach cards in modules), arthroscopy/portals (wrist, some knee/shoulder), decompression boundaries (carpal, some), soft tissue footprints (ACL, rotator).

## 10. Anatomy domains still weak
- Full dedicated ankle lateral fibula + medial malleolus layered approach + specific dangers (superficial peroneal course 7-10cm, saphenous) - main 1047 page good but no catalog ID yet.
- Posterior cervical laminectomy decompression (nerve course, lateral mass landmarks, C5 palsy anatomy, fusion levels) - anterior good (12001), posterior thin or no dedicated page in this pass.
- Clavicle specific approach (superior vs anterior, supraclavicular branch protection, platysma/SCM intervals).
- Lisfranc column-specific reduction anatomy, intercuneiform, TMT footprint/landmarks (7030 page exists but not deeply extracted here).
- Elbow arthroscopy complete portals + systematic diagnostic sequence + PIN/radial/ulnar risks (search hit shoulder/wrist more; needs exact page).
- Nail safe corridors / starting points / TAD / fluoro for femoral neck/intertroch and tibial shaft (some in modules but thin on full).
- Plantar/quadriceps specific release/repair footprint + adjacent NV boundaries.

## 11. Top source records likely to improve case_readiness_score
- https://www.orthobullets.com/trauma/1047/ankle-fractures (bimalleolar/trimalleolar/pilon family - approach/SAR/landmarks/biomech/syndesm)
- https://www.orthobullets.com/trauma/1022/olecranon-fractures + 12005 posterior elbow (olecranon - triceps, tension band/plate, ulnar n, osteotomy)
- https://www.orthobullets.com/trauma/1011/clavicle-fractures--midshaft (clavicle - direct approach, supraclav n, deforming, subclavian risk)
- https://www.orthobullets.com/approaches/12001/anterior-approach-to-cervical-spine (acdf - fascia planes, RLN, sympathetic, landmarks C2-3/C6)
- https://www.orthobullets.com/hand/6009/wrist-arthroscopy (TFCC - portals 3-4/4-5/6R/6U/1-2/MCR/MCU, dorsal sensory ulnar 8mm, TFCC components)
- https://www.orthobullets.com/knee-and-sports/3008/acl-tear (ACL footprints)
- https://www.orthobullets.com/approaches/12028/knee-medial-parapatellar-approach (TKA/ACL)
- https://www.orthobullets.com/approaches/12071/fcr-approach-to-distal-radius (distal radius)

These directly address the "missing_module_recommendations" and "case_readiness_gaps" for the weakest 15-20 in the router (ankle family, olecranon, clavicle, acdf, lisfranc, scfe if usable, spine, cubital if portal/decomp).

## 12. Next recommended source fetches
1. Re-fetch olecranon 1022 and posterior elbow 12005 with full open_page for complete layers (current used snippets).
2. Targeted search + browse for Lisfranc detailed ORIF reduction sequence and column anatomy (7030 page).
3. Posterior cervical / laminectomy specific anatomy (nerve course C5-7, lateral mass landmarks, decompression limits, C5 palsy risk) - may need spine topic or new approach card.
4. Calcaneus 1051 full (extensile lateral, sural/peroneal, sinus tarsi, medial utility).
5. Add catalog approach IDs for ankle_lateral_fibula, ankle_medial_malleolus, clavicle, posterior cervical then populate dedicated modules from above sources.
6. Elbow arthroscopy full portals/dangers/diag seq (search for exact 3088 or equivalent; current hit shoulder more).
7. Plantar and quadriceps for release/repair specific footprint + nearby NV (lateral plantar n, etc).

**Notes on process (Step 8 compliance):**  
This pass was source acquisition only. No modifications to router (brobot_anatomy_router_v1_1.jsonl), anatomy modules (*_v1_1.jsonl), or readiness scores/gaps. The orthobullets_source_library_v1.jsonl is the evidence layer for a future consumption pass to enrich modules + update router links + re-score procedures. All extracted facts are from fetched OB pages or local OB-derived (modules v1_1 source_urls + prior playbook enrichment). Respectful: used direct URLs from router where present, web_search site: for discovery on weak slugs, small batch browses, recorded all attempts/failures with reasons. No login, no bypass, no non-OB content.

Validation (see separate run): all 8 checks passed (valid JSONL, every queued/library pid exists in router, no duplicate source_id, success records have url/title/extracted_facts or notes, failed/skipped have reason, no unsupported facts, no router or module files modified this pass).
