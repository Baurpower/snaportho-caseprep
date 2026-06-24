# Playbook Primary Architecture Audit

**Date**: Current state (post supported gate, OB playbook v1, hybrid wiring fixes)
**Goal of this task**: Document the current anatomy data flow to identify where the Orthobullets playbook should become primary, Miller secondary/support, and GPT only curator (no invention).

## Current Data Flow (High Level)

1. **Entry points** (main.py):
   - /case-prep and /anatomy POST.
   - If ENABLE_LOCAL_ANATOMY_RAG=true (hybrid mode, default for new path):
     - Supported case gate: `get_supported_case(prompt)` (from approach_router) → determines "supported" based on map_v1 (triggers, confidence, non-empty recommended_approach_ids). Note: router currently loads procedure_to_approach_map_v1.jsonl (called "playbook" in code/comments), not the full anatomy-enriched orthobullets_procedure_playbook_v1.jsonl.
     - If supported (or debug override): 
       - Run legacy: `run_anatomy_legacy()` → `run_pipeline_fast` in anatomy_gpt.py (does router pre-filter for allowed/blocked approaches using get_allowed_and_blocked, then GPT select_approaches + build_quiz via OpenAI structured outputs on approach catalog).
       - Run Miller: `run_anatomy_miller_only(prompt)` → uses anatomy_context_builder + retriever (local or pinecone) to get chunks → build Miller v2 payload (relevantAnatomy, structuresAtRisk, etc. from Miller gold only).
       - Merge: `build_hybrid_anatomy(legacy, miller)` (hybrid_anatomy_builder.py).
     - If not supported: synthesize limited legacy (no approach/quiz) + _unsupported_miller_payload (mode="not_run_unsupported_case").
   - If flag=false: pure legacy anatomy_gpt path (no Miller, no gate).
   - Always run general case-prep (refine + vector search for pimp/otherUsefulFacts) and attach "anatomy" object.

2. **Legacy path (anatomy_gpt.py)**:
   - Uses approach_router (map-based) for pre-filter (allowed/blocked from supported case).
   - GPT (via OpenAI responses.create with JSON schema) for approach selection (constrained if allowed provided) and quiz generation from selected catalog cards.
   - Outputs: approachSelection (with router metadata, validation), anatomyQuiz.
   - GPT here is for *selection and quiz from catalog*, not raw anatomy facts.
   - No direct use of orthobullets_procedure_playbook_v1 yet for content.

3. **Miller path (run_anatomy_miller_only in main, anatomy_context_builder.py, retrievers)**:
   - anatomy_retriever.py or anatomy_pinecone_retriever.py: embed prompt, retrieve top chunks from Miller gold (with boosts, filtering).
   - anatomy_context_builder.py: `build_anatomy_context(chunks)` → strictly from Miller chunks only:
     - relevantAnatomy, structuresAtRisk, approachLandmarks, highYieldFacts (extracted/categorized from chunk text/quote, strict mode prefers verbatim).
     - sources with page/quote/score.
     - retrievalSummary (mode set to miller_gold_* by caller).
     - Always Miller-driven; no playbook input.
   - This dominates the "sourceBackedAnatomy" in current hybrid output.
   - retrievalMode, limitedAnatomyContext come from here.

4. **Merge / hybrid (hybrid_anatomy_builder.py)**:
   - Takes legacy (approach/quiz) + miller.
   - Extracts Miller core.
   - Builds hybrid payload with:
     - Legacy fields (approachSelection, anatomyQuiz) from legacy.
     - Miller fields (retrievalMode, limited..., sourceBackedAnatomy with relevantAnatomy etc., flat mirrors).
     - anatomySystem (approachLogic based on legacy presence or "unavailable"/"unsupported...", sourceBackedFacts from Miller mode).
   - Handles partial failures gracefully but is still legacy+ Miller hybrid, not playbook-centric.
   - No lookup or prioritization from orthobullets_procedure_playbook_v1.jsonl for anatomy/risks/landmarks/pearls.

5. **Where playbook (orthobullets_procedure_playbook_v1) is used today**:
   - Indirectly via supported gate (through map_v1 in router for "supported" + recommended IDs).
   - The full anatomy playbook (with important_anatomy, structures_at_risk, landmarks, approach_notes, pimp_topics, sources from OB) exists (populated for some like distal_radius, THA variants, femoral shaft from prior OB extraction task; skeletons/gaps for others).
   - But **not loaded or used in builders** for primary content. Router loads the map (procedure_to_approach_map_v1), not this one for anatomy fields.
   - Previous reports (orthobullets_procedure_playbook_qc.md, integration_plan.md, input_audit.md) document it as intended primary, with Miller support.
   - No current code path: load playbook entry by procedure_id → use its fields as base for output.

6. **Where Miller dominates**:
   - The entire sourceBackedAnatomy / relevantAnatomy / structuresAtRisk etc. in hybrid and /anatomy payloads.
   - retrieval from Miller gold index (embeddings, chunks with scores, pages from Miller corpus).
   - Even when "supported", Miller facts are pulled based on prompt similarity (may include cross-region or weak relevance), then blindly included (or limited by chunk count).
   - anatomy_context_builder is 100% Miller-chunk driven (no playbook filtering or prioritization).
   - This leads to "noisy Miller facts, duplicated concepts, weak relevance" as described in the query.

7. **Where GPT currently generates content**:
   - In legacy path: approach selection (GPT picks from catalog, constrained by router) and quiz (generates Q/A from selected approach cards).
   - No GPT for "anatomy facts" per se in Miller path (strict chunk-based).
   - In curator task (this one), we will add a new GPT layer *only for curation* of (playbook + filtered Miller).
   - Risk: current GPT in select/build_quiz could "guess" but is now gated by supported + allowed from map (prior fixes).

8. **Opportunities to simplify / make playbook primary**:
   - **Router update**: Make approach_router load *both* map (for supported/recommended IDs) *and* the anatomy playbook (for content). Or separate the anatomy lookup.
   - **New playbook_anatomy_builder.py** (per task): Primary builder. Lookup entry by procedure_id (matched via router). Use its important_anatomy/structures_at_risk/landmarks/approach_notes/pimp as base. Merge/ support only *relevant* Miller (filtered). Output clean schema focused on procedure/approach.
   - **anatomy_curator.py** (GPT layer): Post-builder, pre-user. Strict prompt: "You are a curator. Use ONLY the provided playbook fields as source of truth. Miller facts only if they directly support/overlap with playbook items. Dedup, prioritize (procedure-specific first), format resident-style (concise, bullets or short paras), max limits. Return ONLY JSON. Never invent new facts, terms, or anatomy."
   - **Filtering** (before curator): In builder or pre-step, filter Miller chunks for term overlap with the *playbook entry's* anatomy/risk/landmark/approach text + procedure/region/approach IDs. Discard unrelated (e.g., ankle facts for tibial shaft, or hand for hip). Remove low-score or cross-region. Document rules in playbook_miller_filtering_rules.md.
   - **Update hybrid/main**: For supported cases, prefer or replace Miller-heavy path with playbook_builder + curator. Legacy approach/quiz can stay (or be augmented by playbook approach_notes). For unsupported: keep limited as before.
   - **Schema evolution**: Move toward final output (Approach, Key Anatomy, Structures at Risk, Landmarks, Operative Pearls, Sources) with no raw Miller, no scores, no "retrievalMode" noise in user view (internal only?).
   - **Simplifications**: Reduce duplication in context_builder (Miller-only) vs new builder. Make Miller retriever "support only" callable from playbook builder. Remove or deprecate raw sourceBackedAnatomy dumps for supported cases. Use playbook pimp_topics as base for any quiz/pearls.
   - **Gaps observed**: Playbook v1 has good coverage on ~7-8 procedures (distal radius, THAs, femoral shaft, etc. with OB-sourced fields + sources); many manual_review or empty (ankle family limited by catalog gaps). Router still points to map not full playbook for anatomy. No current filtering of Miller by playbook terms. GPT not yet in curator role for anatomy facts.
   - **Benefits of change**: Playbook (OB-curated, procedure-specific, cited) as truth → less noise, better relevance, resident-useful format. Miller becomes "supporting evidence" like citations. GPT only polishes (dedup/format) within bounds → safe, no invention.

## Recommendations from Audit (for implementation)
- Primary new modules: playbook_anatomy_builder.py (deterministic lookup + Miller filter/merge), anatomy_curator.py (GPT post-process with strict prompt + OpenAI client from main).
- Wire in main.py hybrid path (after supported gate): if supported, use new builder+curator for the anatomy object instead of (or in addition to, prioritized over) pure Miller/hybrid.
- Update approach_router to expose full playbook entry or add `get_playbook_entry(procedure_id)` that loads the anatomy v1 jsonl.
- Filtering rules: explicit term overlap + procedure/approach keywords; discard if no overlap with playbook content.
- Test with provided cases (distal radius, posterior THA, etc.) to verify playbook facts surface, Miller is filtered/cited only, output is clean/structured/no invention.
- Preserve compat: keep legacy fields, general pimp/otherUsefulFacts, unsupported limited path.
- No changes to Miller corpus, retrievers (just consume), Pinecone, catalog, or UI.

This audit shows the architecture is ready for "playbook primary" shift with minimal new code + strict GPT guardrails. Current hybrid is a good base but Miller/legacy still dominate anatomy facts.

(References: main.py hybrid block + supported gate, anatomy_gpt.py router/GPT, hybrid_anatomy_builder.py merge, anatomy_context_builder.py Miller v2, approach_router.py get_supported_case + _load_playbook (map), orthobullets_procedure_playbook_v1.jsonl state from prior OB task, previous reports like orthobullets_playbook_* and supported_case_gate_*. )
