# Current RAG Pipeline Audit — BroBot / SnapOrtho CasePrep

**Date**: 2026-06-05 (audit performed across workspace + /Users/alexbaur/anatomy_pipeline + snaportho-web)
**Scope**: BroBot web/API RAG, CasePrep service (the workspace), Pinecone retrieval, embedding, prompt/output, anatomy logic, consumers. Anatomy gold corpus inspected for integration readiness. **Audit + plan only** — no code changes, no uploads, no index creation, no .env edits, no secret values reported.

---

## 1. RAG Pipeline Location and Summary

### Primary Services / Repos
- **CasePrep service** (active RAG backend): `/Volumes/PS3000/snaportho-caseprep` (this workspace, main.py + supporting .py)
  - FastAPI app exposing the core endpoints.
  - Hosts vector retrieval, query refinement, GPT refinement, and current anatomy pipeline.
  - Deployed as the upstream for BroBot (api.snap-ortho.com).
- **BroBot web/API proxy** (Next.js frontend + secure proxy): `/Volumes/PS3000/snaportho_dev/snaportho-web`
  - Only allowed caller of the external `/case-prep` (see src/app/api/brobot/ask/route.ts:4 comment).
  - Handles auth, entitlements, quotas (guests + users via Supabase + Stripe), logging, then proxies prompt to CasePrep.
- Legacy / secondary:
  - `/Volumes/PS3000/snaportho-brobot` (old standalone FastAPI + vector_search/gpt_refiner; appears superseded).
  - Anki/study paths in CasePrep (`/anki/ortho-context`) and web (`/api/brobot-anki/*`).
  - iOS "Snap Ortho" app (BroBot feature) — consumes the same BroBot API surface (web proxy or direct to hosted CasePrep); Swift sources not in text workspace but reference BroBot* models/entitlements.

### Main API Routes / Endpoints (CasePrep)
- `GET /` — sanity "SnapOrtho CasePrep API is live."
- `POST /case-prep` — **primary BroBot entry**. Body: `{ "prompt": "..." }`. Returns BroBotPayload (see below).
- `POST /anatomy` — dedicated anatomy-only (uses current catalog pipeline; not vector).
- `POST /anki/ortho-context` — separate Anki/study RAG path (also Pinecone, custom rerank).
- `POST /cpt/suggest` — unrelated CPT helper.

**Web proxy**:
- `POST /api/brobot/ask` (src/app/api/brobot/ask/route.ts) — normalizes prompt variants (prompt/caseDescription/query/etc), checks quotas/entitlements (guests via signed cookie, users via Supabase), proxies exactly `{ "prompt": ... }` to `${CASEPREP_INTERNAL_BASE_URL}/case-prep`, validates response shape, returns augmented with `meta.remaining`.
- Other: `/api/brobot/guest-entitlements`, billing, etc. No direct browser CasePrep calls (deprecated in src/lib/types/api.ts; enforced).

**Where case queries enter**:
1. Web UI (brobotmember.tsx for members, basic/page.tsx for guests) → `fetch('/api/brobot/ask', { prompt })`.
2. Proxy validates/limits → upstream `POST /case-prep`.
3. (Internal/dev) direct curls to CasePrep `/case-prep` or `/anatomy`.

### Retrieval Functions
- `vector_search.py:get_case_snippets(refined_query: dict) -> List[dict]`
  - Uses query refiner output for metadata-driven filtering.
  - Ladder of Pinecone queries (strict → relaxed filters → region-only → no-filter fallback).
  - `embed_text` (OpenAI), `_pinecone_query`, `_score_matches` (MIN_SCORE=0.55), `_dedupe_keep_best`.
  - Returns ~40 deduped snippets with text + source + region/specialty/dx/proc/score.
- Anki path has `_query_curated_pimp_matches` + custom `_rerank_matches` (score + metadata boosts for dx/proc/region/subregion).
- No reranker model (cross-encoder etc.); GPT + heuristic rerank/filter.

### Embedding Model
- **Production queries + uploads**: `text-embedding-3-small` (1536-dim). Consistent in:
  - vector_search.py:27
  - anki_ortho_context.py:22
  - embed_topinecone_facts.py:23 (and peers)
- Local anatomy evals/indexes (anatomy_pipeline) historically used `all-MiniLM-L6-v2` (384-dim) via sentence-transformers for offline.
- Query embedding construction: `payload_to_embedding_text` (search_text + anchors for specialties/region/subregion/diagnoses/procedures).

### Vector DB / Index / Namespace
- **Single Pinecone index** (name from `PINECONE_INDEX` env; `PINECONE_API_KEY` + legacy `PINECONE_ENVIRONMENT`).
- **No namespace usage in project source** (all queries/upserts use default/empty namespace; confirmed by grep of non-venv .py + vector_search/anki code).
- Index contains mixed corpus: old Miller (normalized QA/facts), Orthobullets (facts + QA), PocketPimp, hip/knee facts, OITE, anki-derived, approach data, etc. (sampled from upload preps/normalized_* + output_vectorversion_*).
- Metadata filters are the primary isolation (region/subregion/specialty/diagnoses/procedures lists or scalars; see query_refiner controlled vocab).
- Current `get_case_snippets` does **not** target anatomy-only content; general retrieval mixes everything. Anatomy facts from Miller exist in index historically but not isolated or prioritized for "anatomy section".

**Env vars referenced (names only)**: `PINECONE_API_KEY`, `PINECONE_INDEX`, `OPENAI_API_KEY`, `OPENAI_PROJECT_ID`, `PINECONE_ENVIRONMENT` (legacy).

### Reranking Logic
- Pinecone native score + MIN_SCORE cutoff.
- Metadata filter ladder (AND clauses on region/subregion/dx/proc/specialty; progressive relaxation).
- Dedup by id or MD5 text sig.
- GPT-based: `gpt_refiner.py:_filter_irrelevant_snippets` (tool call for boolean keepMask per snippet, case-specific; conservative — prefers keep on doubt).
- Anki-specific: `_rerank_matches` adds bonuses for region/subregion/dx/proc matches + small bonuses (e.g. +0.04 for high clinical tags).
- No dedicated rerank model or Cohere/etc.

### Prompt Templates (Inline)
- `query_refiner.py`: system prompt for canonical metadata token extraction (specialties 1-2 from controlled list, region/subregion/dx/proc slugs from metadata_dictionary.json; strict JSON; false-negative bias).
- `gpt_refiner.py`:
  - Filter: "orthopaedic attending... decide keepMask for THIS case" (region/topic match; prefer keep).
  - Reformat: "orthopaedic attending... pimpQuestions (Q/A only if supported) + otherUsefulFacts (short, faithful to snippets)". Tool-enforced schema.
- `anatomy_gpt.py`: approach selector + quiz builder (structured outputs via Responses API + json_schema). Instructions emphasize "only IDs that exist in catalog", "anatomically appropriate".
- All prompts stress "Do NOT invent", "faithful to snippets", but current anatomy path has no retrieved fact chunks (only 30 approach summaries).

### Output Schema
**BroBotPayload** (src/types/caseprep.ts + main.py + web ask/route.ts):
```ts
{
  pimpQuestions: string[],           // "Q: ... A: ..." formatted
  otherUsefulFacts: string[],
  anatomy?: AnatomyPayload | null    // see below
}
```
**Current AnatomyPayload** (from anatomy_gpt + legacy):
- `approachSelection`: { selected: [{id, confidence, rationale}], notes? }
- `anatomyQuiz`: { questions: [{approach_id, q, answer, tag?, difficulty?}] }
- `highYieldAnatomy?`: { structures?: [{name, type, why_high_yield?, when_in_case?, approach_ids?}], must_not_miss? }

Returned merged in main.py:129: `{**caseprep_result, "anatomy": anatomy_result}` (parallel gather of refine_case_snippets + run_pipeline_fast).

**No per-fact citations/sources** surfaced in pimp/facts/anatomy today (snippets sometimes carry `[Source: ...]` into GPT, but reformatter outputs plain strings; UI Section just renders bullets; no "Miller p.XX" or quotes in prod output).

**UI consumers** (render):
- brobotmember.tsx (member) + basic/page.tsx (guest): "Prep Summary" card (pimp + other facts), separate "Anatomy" card (approach quiz + highYieldAnatomy structures if present). Collapsible sections, ToggleItem for Q/A.
- FeedbackSection present.
- No source/quote/page display.

### Frontend / Mobile Consumers
- **Web**: Next.js pages under /brobot (member + basic/guest), calls only the secure proxy. Also anki-decks flows (separate prep/generate).
- **Mobile (iOS "Snap Ortho")**: BroBot feature uses same surface (BroBotModel, entitlements, storekit). Calls expected to hit the hosted proxy or api.snap-ortho.com (same RAG). No separate mobile RAG path found in text sources.
- Other: internal dev curls, possibly future Anki mobile integration via /brobot-anki endpoints (still backed by CasePrep Pinecone).
- Config: CASEPREP_INTERNAL_BASE_URL (server-only, preferred), NEXT_PUBLIC_CASEPREP_API (deprecated direct use blocked).

**Flow trace (case query)**:
User prompt (case desc) → web proxy (quota/auth) → CasePrep /case-prep → refine_query (gpt-4o-mini + dict → metadata payload) → get_case_snippets (embed + filtered Pinecone ladder + dedupe) → parallel: refine_case_snippets (gpt filter + reformat → pimp/other) + run_pipeline_fast (catalog GPT → approach/quiz) → merge + return → web (add meta) → UI cards.

**No anatomy vector retrieval today**. General Pinecone can surface anatomy-ish content (mixed corpus), but it is not isolated, not prioritized for the Anatomy card, and not source-attributed from Miller gold.

---

## 2. Current Anatomy Behavior

- **Not retrieved separately via vector on gold corpus**: No.
- **Mixed into general retrieval?** Partially/accidentally (old Miller facts/QA live in the shared index + general query can return them among pimp/facts), but **not used for the "Anatomy" output section**.
- **Prompt-only hallucinated?** Current dedicated anatomy is **catalog + GPT**: 30 approach JSONL entries (upper/lower extremity approaches/*.jsonl, loaded at startup into CATALOG, ~10 upper + 20 lower) provide name/aliases/region/summary. GPT selects + generates quiz. High-yield structures generated (not strictly from catalog snippets in all paths). Risk of hallucination on details, landmarks, structures-at-risk, relations not present in the tiny catalog.
- **Existing "anatomy" output section?** Yes — parallel `anatomy` key in every /case-prep response, rendered in dedicated "Anatomy" card (separate from Prep Summary pimp/facts).
- **What sources currently feed anatomy answers?**
  - Primary: the 30 curated approach JSONL (text summaries of approaches).
  - Secondary/legacy: whatever general retrieval surfaces for pimp/other (mixed corpus, including historical Miller/OB/PP anatomy).
  - No Miller canonical/gold facts, no source_quote, no page-level attribution, no 717-fact corpus.
- **How anatomy citations/sources displayed?** Not displayed. No Miller/page/quote in Anatomy card or pimp/facts. UI renders plain strings or Q/A; "Crafted from the highest-yield orthopaedic student resources." footer note only.

**Dedicated /anatomy endpoint** exists for testing but uses same catalog pipeline (no vector).

**anatomy_gpt.py** (run_pipeline_fast): approach selector (structured) → quiz builder (structured). Stage 3 removed in current version. Fast, parallelized in main.

**Conclusion on anatomy**: Currently a **limited-scope, non-retrieval, approach-catalog GPT pipeline** + incidental mixed retrieval. Does not use the cleaned Miller gold corpus. Does not provide the desired "relevant anatomy / structures at risk / approach-related / landmarks / high-yield pimp / source-backed notes". Perfect candidate for replacement/augmentation by dedicated gold retrieval.

---

## 3. Corpus Integration Readiness (Gold Miller v1)

**Primary files** (in /Users/alexbaur/anatomy_pipeline/):
- `data/anatomy_miller_chapter/canonical_anatomy_fact_corpus_gold_v1.jsonl` (full, with qc/review fields; 717 records).
- `data/anatomy_miller_chapter/anatomy_gold_v1_pinecone_ready.jsonl` (slimmed for ingestion; 717 records).
- Reports: `reports/canonical_gold_v1_recommendation.md`, `reports/anatomy_gold_v1_pinecone_ready_report.md`, `reports/anatomy_relevance_eval_canonical_anatomy_fact_corpus_gold_v1.md` + .json, `reports/vector_db_ingestion_plan.md` (older), `next_phase_local_vector_index_plan.md`, eval packets, holdout, etc.
- Local indexes: `local_indexes/canonical_anatomy_fact_corpus_gold_v1/` (and v1/v1_1 variants; SimpleLocalVectorIndex numpy + sklearn cosine; manifest confirms 717 records).

**Final record count**: 717 (pinecone_ready + local index + evals). Earlier rec noted 706 post-packet (possible timing; use 717 from files + reports).

**Schema** (pinecone_ready — the one for upload):
```json
{
  "id": "miller-canonical-p1-8f0fba39579b",
  "text": "... (canonical_fact / embedding text)",
  "source_quote": "... (exact from Miller)",
  "page": 1,                    // source_page
  "section_path": "...",
  "heading": "...",
  "source": "miller",
  "corpus_version": "gold_v1",
  "metadata": {
    "specialty": "trauma" | ...,
    "region": "upper_extremity" | "hip" | ...,
    "subregion": "...",
    "diagnosis1": null | "...",
    "procedure": null | "...",
    "anatomy_terms": { "neurovascular": [], "tendon_ligament": [], ... },
    "structures_at_risk": ["..."],
    "approach_terms": ["..."],
    "case_associations": [],
    "quality_tier": "high" | "medium" | "low_but_acceptable",
    "metadata_trust": "high" | ...
  }
}
```
- `text` (for embedding) == canonical_fact by construction.
- Full provenance preserved (source_quote, page, section_path, heading).
- No question/answer_form (statement-first, clean).
- Clutter (gold_qc, qc_final, donor_*) removed in slim version.

**Embedding text field**: "text".

**Metadata fields**: Rich but sparse on some (see below). gold_qc carried in full canonical for audit.

**Source quote / page availability**: 100% (717/717).

**Pinecone-style metadata ready?** Yes for slim version:
- All core id/text/quote/page/section/heading/source/version present.
- Quality + trust flags for filtering.
- Region/subregion/specialty/procedure/dx for optional filters/boosts.
- anatomy_* and structures/approach_terms for display, keyword boost, or light rerank (not hard filter — audit warns over-assignment risk in prior versions; gold improved but still "use with caution").

**Field presence (pinecone_ready report)**:
- Core (id/text/quote/page/section/heading/source/version/quality_tier/metadata_trust): 100%.
- specialty/region/subregion/anatomy_terms: ~94.6%.
- approach_terms: 52.4%.
- structures_at_risk: 36.7%.
- case_associations: 16.9%.
- procedure: 10.7%, diagnosis1: 8.1%.

**Eval on seeds (gold)**: 100% cases have clinical signal; avg final_score ~0.118–0.188 (varies by report/version); some red flags (wrong region surfacing, e.g. fibula for wrist case) indicate need for guards (region filter, quality_tier=high/medium, post-rerank). 10/10 seeds covered in benchmarks/anatomy_retrieval/seed_cases*.jsonl (distal_radius_volar, carpal_tunnel_release, tha_posterior, tka_medial_parapatellar, acl_reconstruction, rotator_cuff_repair, ankle_orif_*, cubital_tunnel_release, acetabular_ilioinguinal + extras).

**Cleanup / export remaining before ingestion (per canonical_gold_v1_recommendation.md + pinecone report)**:
- Human skim of 37-item review_holdout_v1 (focus 6 review_holdout + seed-relevant).
- Optional: one-pass metadata normalization (fill obvious missing regions from text per pp_style; normalize case associations to known seeds) → produce gold_v1.1 if changes.
- Re-run seed eval + add real-world case briefs.
- Orthopaedic user confirmation that top results for seeds are "OR-prep useful".
- **No content changes to canonical_fact / source_quote**.
- The pinecone_ready.jsonl is already the slim export (no further export step needed; can copy to caseprep or reference for upsert script).
- Local index already exists for the gold (for Phase 1).

**Is it ready?** High — cleaner/safer than raw v1 (QC passes + human packet). "Yes" for local RAG integration + staging prep. "Gates" above before prod Pinecone per project discipline.

**Other notes**: 717 records small but high-precision (source-faithful, ortho-useful). Hip-heavy distribution. Use quality_tier + hybrid (vector + keyword on anatomy terms / landmarks) recommended. Matches "blank > wrong" ethos.

---

## 4–8. Recommendations, Flow, Prompts, Phases, Tests

See companion reports:
- `reports/anatomy_rag_integration_plan.md` (architecture rec, retrieval flow, prompt/output design, 5-phase roadmap with per-phase files/cmds/tests/rollback).
- `reports/anatomy_rag_test_plan.md` (9 seed cases with expected concepts, structures-at-risk, source behavior, failure criteria + harness notes).

---

## Terminal Summary (Key Facts)

**Current RAG entry point**: `POST /case-prep` (main.py:87) in CasePrep service; exclusively called by web proxy `POST /api/brobot/ask` (route.ts:268) after quota/auth. (Also anki endpoint and direct /anatomy for testing.)

**Current Pinecone/index setup**: Single index via `PINECONE_INDEX` env (no namespace= in any project .py outside venv); default ns; text-embedding-3-small everywhere; metadata filter ladder + GPT filter + dedupe. Mixed corpus (historical Miller + OB + PP + ...). Anatomy facts not isolated.

**Is anatomy currently separate?** Yes (parallel call), but **non-vector / limited**: anatomy_gpt.py + 30 approach catalog JSONL + GPT (selector + quiz). No Miller gold, no source_quote/page, no deep fact retrieval. "Anatomy" card exists in UI but fed by catalog-prompt (hallucination risk on details). General retrieval can leak anatomy-ish content into pimp/facts but not attributed or used for anatomy section.

**Best architecture recommendation**: **Option A (same Pinecone index + separate namespace: `anatomy_miller_gold_v1`)**. Reasons: matches existing embed model (must), zero new index, simple client reuse, perfect isolation for query/upsert/stats/delete while sharing capacity; 2 calls (general + anatomy ns) anyway (same as B). Use C (local) for Phase 1 dev/eval. B (separate index `snaportho-anatomy`) as future escalation if size/access patterns diverge. Vector ID = corpus "id" (e.g. miller-canonical-...); metadata = slim pinecone_ready shape + text/source_quote/page for citations; safe filters = region/subregion/quality_tier (high/medium); rerank/display-only = source_quote/heading/section_path/anatomy lists; embed = text-embedding-3-small; top_k default 15 (post-gate ~8-10); rerank = score thresh + region boost (from refiner) + GPT/keyword filter.

**Files likely needing edits** (plan only; see integration plan): 
- CasePrep: main.py, vector_search.py (or extracted anatomy query), gpt_refiner.py (synth) or new anatomy_retriever.py + anatomy_context_builder.py / anatomy_refiner.py, scripts/ (build local embeds, prepare/upsert dry, test harness), possibly anatomy_gpt.py (keep or evolve for quiz).
- Web: src/types/caseprep.ts (AnatomyPayload update), src/app/brobot/brobotmember.tsx + basic/page.tsx (render new structured anatomy + sources), config if any.
- Cross: copy/reference gold jsonl (or path), update any shared prompts/docs.
- New: local index artifacts under data/ or scripts/, test scripts.

**Key risks**:
- Latency/cost (extra embed + synthesis LLM per query; ~717 small but still).
- Coverage/gaps in 717 (eval shows low avg scores + occasional red flags like wrong-region; rely on low-conf handling + guards).
- Metadata sparsity (structures_at_risk only 37%; do not hard-filter).
- Gold holdout (37) not fully skimmed per rec; risk of including borderline before Phase 2 upload.
- UI clutter if sources/quotes not concise; backward compat for old anatomy shape.
- Embed model sync (local evals MiniLM vs prod openai; Phase 1 must use matching for gold).
- Region bias (hip heavy in gold).
- "Do not invent" hard to enforce 100% without strong extraction + verification in synth prompt.
- No citations today → new display is additive change.

**Next implementation step**: Phase 1 (local anatomy retriever integration only) — (a) script to (re)embed the 717 gold texts with text-embedding-3-small + persist numpy index + slim metas under caseprep/data/anatomy_miller_gold_v1_local/ (manifest), (b) anatomy_retriever.py (load + cosine top_k with score/region guards), (c) basic anatomy_context_builder (or prompt) that consumes chunks + returns structured with "limited" handling + source notes, (d) wire parallel call in main.py:88 (behind env flag), (e) run the 9 seeds + 2 real cases, manual review of chunks vs output (no invention, signal present, sources accurate), (f) update local eval harness if needed. Do not touch Pinecone, do not change prod prompts/UI yet. Validate "works locally with gold" before Phase 2.

**References used (non-exhaustive)**: main.py, vector_search.py, query_refiner.py, gpt_refiner.py, anatomy_gpt.py, anki_ortho_context.py, src/app/api/brobot/ask/route.ts, src/types/caseprep.ts, brobotmember.tsx + basic/page.tsx, web config, anatomy_pipeline reports (canonical_gold_v1_recommendation.md, anatomy_gold_v1_pinecone_ready_report.md, evals, vector plans), gold jsonl + manifests + seed_cases, normalized/output jsonls, embed scripts, metadata_dictionary.json.

**End of audit report**. Proceed to integration + test plans for actionable next steps. All findings derived from file reads, greps, manifests, and reports (no live Pinecone mutations or secret exfil).
