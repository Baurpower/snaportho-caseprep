# Orthobullets Playbook v2 Quality Rubric

**Purpose**: Provide a consistent, resident-focused scoring framework to audit and prioritize improvements to the procedure playbook. The playbook is the primary source for "what approach, what anatomy matters, what is at risk, what landmarks, what are the key steps/pearls for this case?"

**Scoring Scale (0-5) for each dimension** (applied per procedure):
- **0 = Unusable / Wrong**: Misleading, incorrect, or completely absent when it should be present (e.g. wrong approach or fabricated facts).
- **1 = Sparse or Mostly Unhelpful**: Minimal or generic content; does not meaningfully help a resident prepare anatomy for the case (e.g. 0-1 vague items, no sources, no "why it matters").
- **2 = Partially Useful**: Some relevant items present but incomplete, shallow, or missing key categories; resident would still need to consult primary sources heavily.
- **3 = Usable**: Covers the main points with source-backed facts; resident can use it for basic preparation but gaps remain in one or more areas.
- **4 = Strong**: Comprehensive coverage of approach, key anatomy, risks, landmarks, and notes with clear "why" and high-confidence OB citations; minor gaps only.
- **5 = Excellent for Resident Case Prep**: Ready-to-use, concise, high-yield, perfectly scoped to the procedure and mapped approach(s). Every major category is populated with actionable, source-backed detail that directly supports scrubbing/prep. No noise, no unsupported invention.

**Dimensions to Score**:
1. **approach_accuracy**: Correctness and specificity of recommended_approach_ids / conditional / blocked relative to Orthobullets-described standard approaches for the procedure. Penalize if recs are present but wrong per OB or if catalog gap forces empty when OB clearly supports a specific approach that exists in catalog.
2. **anatomy_usefulness**: Quality, specificity, and actionability of important_anatomy[] items (structures, intervals, planes, exposure details, blood supply, deforming forces, etc.). Must be procedure-specific and tied to the approach.
3. **structures_at_risk_usefulness**: Quality of structures_at_risk[] (named structure + clear "why_it_matters" clinical consequence + protection strategy if given in OB). Focus on those relevant to the chosen approach.
4. **landmark_usefulness**: Quality of landmarks[] (palpable/surgical landmarks + why they matter for incision, exposure, reduction, or protection).
5. **approach_notes_usefulness**: Quality of approach_notes[] (step-by-step or key pearls specific to the procedure + approach, variations, pearls/pitfalls directly from OB pages).
6. **pimp_topic_usefulness**: Quality and relevance of pimp_topics[] (high-yield questions a resident might be asked; directly derivable from the anatomy/risks/landmarks/notes in the entry; not generic).
7. **overall_resident_utility**: Holistic 0-5: "If I am a resident prepping for this case tomorrow and the router selects this playbook entry + its approaches, how much does this entry actually help me know the anatomy, risks, landmarks, and key steps without having to go back to raw OB or guess?"

**Additional Fields in Audit Output**:
- missing_fields: list of key arrays that are empty or near-empty when recs exist (e.g. ["important_anatomy", "landmarks"]).
- priority_tier:
  - **must_fix**: Supported (recs > 0, manual_review=false) but low overall utility (overall <=2). Common resident case.
  - **should_fix**: Supported with recs but incomplete (overall=2-3); high-volume or high educational value.
  - **okay**: Usable (overall=3) but room to reach 4-5.
  - **excellent**: overall=4-5 with strong coverage across dimensions.
  - **unsupported_gap**: manual_review=true due to catalog gap (content improvement secondary; fix requires new approach catalog IDs).
- reasons: bullet list of specific deficiencies (e.g. "no landmarks despite clear OB incision landmarks on 12028 for TKA parapatellar").
- suggested_improvements: specific, actionable suggestions tied to known OB pages (e.g. "Pull landmarks and superficial/deep dissection details from https://www.orthobullets.com/approaches/12028/knee-medial-parapatellar-approach for carpal_tunnel_release wait no - for relevant procedure").
- source_coverage_status: "strong" (multiple high-conf facts with distinct OB approach/topic pages), "partial", "weak", or "none".

**Usage for v2_1**:
- Run the audit script on v2.
- Sort by priority_tier (must_fix first), then by overall_resident_utility ascending, then by case volume (inferred from common procedures: ACL, rotator cuff, proximal humerus, both bone, scaphoid, carpal/cubital, achilles, ankle family supported ones, hip/knee recon variants, etc.).
- Improve only with fresh OB fetches (site:orthobullets.com + specific /approaches/ and /trauma/ /sports/ etc. pages).
- Goal: Move as many "must_fix" / "should_fix" supported entries as possible to 4-5 overall by adding 2-4 high-quality items per weak dimension, always with url + section.
- Do not touch unsupported_gap entries beyond minor pimp or notes if OB directly supports without requiring new catalog IDs.
- Preserve all v2 content unless a clear, sourced improvement is available.

This rubric ensures improvements are objective, resident-centric, and strictly evidence-based from Orthobullets.
