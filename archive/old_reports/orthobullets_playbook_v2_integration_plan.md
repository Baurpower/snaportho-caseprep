# Orthobullets Playbook v2 Integration Plan

**Purpose**: Switch BroBot anatomy/approach layer from v1_1 (38, many thin) to v2 (60, broader high-yield coverage with enriched facts for common cases). Data-only change; minimal code impact. v1_1 + map_v1 preserved for rollback.

## 1. Switching BroBot from v1_1 to v2 Playbook
- Update loader path (approach_router.py, playbook_anatomy_builder.py, main.py anatomy paths, or shared config):
  ```python
  # v1.1
  PLAYBOOK_PATH = os.getenv("ANATOMY_PLAYBOOK_PATH", "data/approach_playbook/orthobullets_procedure_playbook_v1_1.jsonl")
  # v2
  PLAYBOOK_PATH = os.getenv("ANATOMY_PLAYBOOK_PATH", "data/approach_playbook/orthobullets_procedure_playbook_v2.jsonl")
  ```
- Same for YAML if used.
- No schema change: v2 is superset-compatible (same fields + optional `playbook_update` metadata on enriched/new entries).
- Richer content for TKA (already good), proximal humerus (now Neer/deforming/blood supply/approach dangers), rotator cuff (mini-open + arthro details), ACL (footprints/parapatellar), new cases (humeral/tibial shaft, total/reverse shoulder, meniscus, lateral ankle, distal femur, tennis elbow, etc.) will flow to curator automatically.
- Manual_review entries (22) remain gated (supported=false or limited payload) — no behavior change needed.

## 2. Switching procedure_to_approach_map from v1 to v2
- Update map path in router/gate:
  ```python
  MAP_PATH = os.getenv("PROCEDURE_MAP_PATH", "data/approach_playbook/procedure_to_approach_map_v2.jsonl")
  ```
- v2 map includes all 60 v2 procedures (preserved v1 mappings + 22 new with triggers/recs where catalog IDs match, or [] + manual_review + evidence_note for gaps).
- Triggers expanded for new (e.g. "acl reconstruction", "lisfranc", "scfe pinning", "acdf", "humeral shaft orif", "meniscus repair", "reverse shoulder").
- Router classify_procedure + get_restrictions will automatically use v2 for more procedures while enforcing catalog (only 30 IDs) and manual_review rules.
- No change to supported-case gate logic.

## 3. Catalog Gaps That Must Be Fixed First (for Full Deterministic)
- Spine (ACDF, posterior lumbar/cervical, transthoracic): 3 new manual_review entries. No catalog IDs → all spine gated.
- Lisfranc / midfoot ORIF/arthrodesis: manual (no midfoot/Lisfranc ID; ankle anterior insufficient for column-specific).
- Ankle/foot expansions (lateral fibula/malleolus, medial malleolus separate, extensile lateral calcaneus, sinus tarsi): keeps original 4 ankle manual + limits new foot cases.
- Posterior elbow / olecranon / cubital (no dedicated; only Kocher + humerus posterior triceps_split): keeps olecranon/cubital manual.
- Clavicle / dedicated upper girdle.
- Some peds specifics and periprosthetic nuances.
- Recommendation: Add 5-10 new catalog IDs (lateral ankle/fibula, posterior elbow, Lisfranc/midfoot variants, spine anterior/posterior cervical + posterior lumbar, clavicle) before full v2 prod rollout for those procedures. Until then, they correctly stay manual/gated.

## 4. Procedures Ready for Deterministic Routing (v2)
- High: TKA, distal radius (Henry + cond dorsal), femoral shaft (lateral/posterolat), ACL (parapatellar), rotator cuff (deltoid split + deltopectoral), proximal humerus (deltopectoral + lateral split, now enriched), both bone (Henry), scaphoid (Henry + dorsal), humeral shaft (anterolat distal + post triceps), tibial shaft (leg lateral/medial), total/reverse shoulder (deltopectoral + lateral), meniscus (parapatellar), lateral ankle ligament (anterior ankle), distal femur (knee parapatellar + lateral), tennis elbow (Kocher), metacarpal (dorsal wrist), DDH (Ludloff + cond Smith-Peterson), etc.
- These have nonempty recs + improved fact counts → readiness 3-4 in utility tests.
- Original strong (THA posterior/anterior/lateral, hip hemi, patella, tibial plateau, Achilles, high tibial, ankle arthrodesis/total ankle) preserved or lightly improved.

## 5. Procedures That Should Remain Gated / Manual Review (v2)
- 22 manual: original 11 (bimalleolar/trimalleolar/pilon/calcaneus/olecranon/pelvis_ring/cubital/clavicle/supracondylar/hallux/trigger) + new spine 3 (acdf, post lumbar, cervical laminectomy), Lisfranc, SCFE, perthes (limited), cervical_laminectomy, plantar, periprosthetic (partial), elbow_arthroscopy, wrist_arthroscopy_tfcc, quadriceps (some), boxers (overlaps metacarpal).
- In router: supported=false, limitedAnatomyContext=true, retrievalMode=not_run_unsupported_case (or similar), warning "manual_review or catalog gap".
- Do not guess approaches or run full Miller for these.

## 6. Rollback Plan
- Flip paths back to v1_1.jsonl + map_v1.jsonl (env or code change, one line).
- v1_1 and v1 map untouched.
- If content bug in specific v2 entry: edit only that entry in v2 (OB-only discipline) or stay on v1_1 while preparing v2.1.
- No corpus/Pinecone/BroBot core change; instant via restart/redeploy of loader.
- Monitor: after switch, re-run utility test + /case-prep smokes on 20 cases (TKA/prox hum/ACL/rotator now richer; spine/Lisfranc still gated).

## 7. Recommended Rollout Steps
1. Review QC + utility test results (strongest now include enriched proximal humerus, new shaft/shoulder/sports; gaps honest).
2. Add critical catalog IDs (spine + Lisfranc + lateral ankle/fibula + posterior elbow) if full coverage desired.
3. Flip paths in dev/staging, run full supported-case gate tests + 20+ utility cases + real prompts (TKA, ACL, rotator cuff, humeral shaft, Lisfranc, ACDF, SCFE).
4. Enable in prod with feature flag or gradual (e.g. A/B on recon/trauma prompts first).
5. Update any docs/hardcodes referencing "v1_1".
6. Optional: surface "playbookVersion": "v2" + evidence_urls in anatomySystem metadata for audit.

## 8. Validation Checklist
- [x] v1_1 preserved (separate v2 files)
- [x] All facts OB-only with url + source_section (from 2026 fetches on listed pages)
- [x] No Miller/MedGemma/other for facts
- [x] No BroBot/Pinecone/Miller corpus changes
- [x] Map v2 separate, uses only real 30 catalog IDs
- [x] 60 procedures (38 preserved + 22 added/enriched); quality > pad
- [x] Tests (utility harness on 24 cases) + QC + this plan produced
- [x] Rollback trivial path flip

**Ready to switch?** Yes for core recon/trauma/sports/shoulder/knee/forearm cases (many now 3-4 readiness). Spine/foot/gap cases correctly remain gated/manual until catalog expanded. Run utility test + smokes post-flip.
