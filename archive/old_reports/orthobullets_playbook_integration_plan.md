# Orthobullets Playbook Integration Plan (Plan Only)

**Purpose**: Define how the OB-only `orthobullets_procedure_playbook_v1.jsonl` (and YAML) becomes the primary curated product layer for BroBot anatomy/approach answers. Builds directly on the v1 procedure-to-approach map + existing catalog IDs. Miller Gold is support/enrichment only (citations, additional facts), not the driver.

**Scope**: Planning only. No code, no BroBot mods, no Pinecone/Miller corpus changes, no new fetches beyond this task's OB work. Use existing map as foundation (38 procedures, 30 catalog IDs).

## High-Level Flow (Future Use)
1. **Case query / prompt normalization**
   - User case (e.g. "bimalleolar ankle fracture ORIF", "distal radius ORIF with dorsal comminution", "posterior THA").
   - Optional: structured (fracture pattern, "posterior malleolus mentioned", etc.).
   - Refine (existing query_refiner or simple) for key terms.

2. **Deterministic procedure match (playbook gate)**
   - Load playbook (jsonl for prod; yaml for audit).
   - Match via triggers (case-insensitive substring/phrase, similar to prior router) or procedure_id.
   - If multiple, prefer highest confidence or most specific (high > medium; exact procedure_id over general).
   - Result: matched entry or "unknown"/manual_review.
   - If no confident match or manual_review/empty recommended (catalog gap): supported=false → limited response (see below). No guessing.

3. **Approach ID selection (from map/playbook)**
   - Use `recommended_approach_ids` as base (must be non-empty for full support).
   - Fire `conditional_approach_ids` if their triggers match (e.g., "posterior malleolus" → add posteromedial for ankle).
   - Apply `blocked_approach_ids` (e.g., never anterior ankle for bimalleolar).
   - Intersect with loaded catalog (30 IDs from upper/lower JSONL) for safety (existing validate logic).
   - Attach playbook fields: orthobullets_urls, evidence_notes, confidence.
   - Output: constrained list of approach IDs + playbook context.

4. **Playbook-driven anatomy / risks / landmarks / notes**
   - Pull directly from matched entry:
     - important_anatomy (with source_url/section/conf).
     - structures_at_risk (structure + why_it_matters + sources).
     - landmarks (landmark + why + sources).
     - approach_notes (text + sources).
   - These are resident-useful, concise, OB-only (paraphrased or short exact where needed).
   - pimp_topics: high-yield questions/answers derivable from the entry (or linked OB pages).
   - Every item traceable to OB URL (no invention; blanks where unsupported).

5. **Miller Gold support / enrichment (secondary, not driver)**
   - If supported and Miller backend enabled: run retrieval (local/Pinecone per ANATOMY_BACKEND) on the anatomic region + case family/approach names (e.g., append "volar Henry distal radius" or "posterior Moore hip").
   - Use results to:
     - Cite/add supporting facts or sources (sourceBackedAnatomy).
     - Fill gaps or provide depth (e.g., more on intervals if OB light but Miller has).
     - But **never override** playbook primary fields; Miller supports/cites.
   - If unsupported: skip Miller (or debug override only); return limited "not_run_unsupported_case" per prior gate.
   - retrievalMode: miller_gold_* (enriching) or not_run_...
   - anatomySystem: approachLogic from playbook/router ("deterministic_playbook" or "unsupported..."), sourceBackedFacts="miller_gold_enrichment" or similar, warning if limited.

6. **Final anatomy section assembly (product layer)**
   - Structure response around playbook:
     - "Approach": list selected IDs (with conditional/blocked rationale) + approach_notes from playbook + catalog card summaries.
     - "Important Anatomy": playbook list + any Miller citations.
     - "Structures at Risk": playbook + Miller.
     - "Landmarks": playbook.
     - "High-Yield / Pimp": playbook pimp_topics + Miller high-yield.
   - If unsupported: 
     - approachSelection: null or {"selected": [], "notes": "unsupported... per playbook; no guessing performed", "router": {...}}.
     - anatomyQuiz: null/empty.
     - sourceBackedAnatomy / Miller: limited (empty or "not_run"), limitedAnatomyContext=true, retrievalMode="not_run_unsupported_case".
     - anatomySystem: {"approachLogic": "unsupported_case_no_approach_guessing", "sourceBackedFacts": "not_run_unsupported_case", "warning": "This procedure is not yet mapped... Better limited response than wrong anatomy."}
   - Always preserve general /case-prep (pimpQuestions, otherUsefulFacts from vector/refine) — anatomy is additive/ gated layer.
   - Backward compat: flat mirrors + legacy fields for existing clients.

7. **Fallback & monitoring**
   - No playbook match or low-conf: limited unsupported payload (as above) + legacy general output only (no anatomy guess).
   - Manual_review in playbook: treat as unsupported until catalog/playbook updated.
   - Log: matched procedure_id, supported flag, #playbook facts used, Miller enrichment count, any blanks.
   - Human review queue for manual_review or new procedures (expand playbook iteratively).
   - Metrics: % supported cases, accuracy vs. resident feedback, reduction in "wrong approach" incidents.

## Benefits & Why Playbook is Primary
- OB-grounded, auditable (every field has URL + section).
- Deterministic for mapped (quality > volume; 38 starting, enriched core first).
- Prevents historical bugs (e.g., anterior ankle for bimalleolar while gaps exist; tibial shaft irrelevant Miller).
- Miller enriches (citations, depth) but doesn't drive (avoids irrelevant retrieval for unsupported).
- Resident-focused: concise, pimp-ready, landmarks/risks/why_it_matters.
- Integrates with prior router/supported gate (this playbook extends it with anatomy layer).
- /case-prep and /anatomy compat preserved (anatomy object gated; general fields untouched).

## Implementation Notes (Future)
- Load playbook at startup or on-demand (small).
- Match before/parallel to legacy run_pipeline_fast and run_anatomy_miller_only (gate calls as in supported_case work).
- In hybrid_anatomy_builder or new assembler: prioritize playbook fields, append Miller sources under "citations" or in sourceBackedAnatomy.
- Update anatomySystem per flow.
- When catalog expands (add lateral malleolus ID etc.), re-process affected manual_review entries to supported=true + full fields.
- Debug: env var to force Miller on unsupported or dump raw playbook match.
- No changes to Miller corpus, Pinecone, or non-anatomy paths.

This makes the OB playbook the "product layer" for clinically useful, safe answers while leveraging Miller as a supporting RAG tool.

(Plan only; aligns with prior procedure_approach_router_integration_plan.md and supported gate work.)
