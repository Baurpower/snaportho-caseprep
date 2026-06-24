# Quality Gates Audit

This document evaluates every stage of the current pipeline for the presence of real, enforceable quality control.

**Legend**
- **Real gate**: Code actually rejects or heavily penalizes bad input/output.
- **Partial**: Some filtering or logging exists, but it is weak, bypassable, or only advisory.
- **Fake / None**: The stage exists in the flow but provides no meaningful protection against low-quality or wrong content.

## 1. User Input Normalization
- **Current file/function**: `query_refiner.py` (called as `refine_query`), also internal normalization inside `procedure_registry._normalize`.
- **Current behavior**: Lowercasing, some cleaning, prompt refinement for retrieval.
- **Is there a quality gate?** Partial (refinement helps retrieval, but no validation that the input looks like a real surgical case).
- **Failure modes**: Garbage input, extremely short prompts, non-orthopedic text still flow through.
- **Recommended fix**: Add a cheap "is this plausibly an ortho case?" classifier or length + keyword heuristic early. Log and short-circuit obviously bad inputs.
- **Priority**: Medium

## 2. Procedure Alias Matching
- **Current file/function**: `procedure_registry.resolve_procedure` (stages A–D).
- **Current behavior**: Exact (normalized), contains, rapidfuzz (>=85), GPT fallback (conf >=0.8). Prints observability.
- **Is there a quality gate?** Partial (the 4-stage design + confidence is good; the data-driven aliases.jsonl is the right direction).
- **Failure modes**:
  - Ordering of aliases in the JSONL can cause "direct anterior THA" to sometimes hit a generic "tha" alias first.
  - No strong disambiguation signal when multiple procedures could match (e.g., generic "hip replacement" vs specific approaches).
  - GPT fallback (stage D) is only used when everything else fails and can still return low-confidence results that are accepted downstream.
- **Recommended fix**:
  - Add explicit `confidence` + `ambiguity` fields to the resolver return value.
  - Require minimum confidence (e.g. 0.75) before trusting a slug for certified short-circuit.
  - Add a small set of "must not match" negative examples per procedure.
- **Priority**: High (this is the new front door)

## 3. Procedure ID Resolution / Canonicalization
- **Current file/function**: `procedure_registry` (the `REGISTRY` + `SLUG_TO_DEF`) + `approach_router.get_supported_case` (which calls the resolver then does exact lookup).
- **Current behavior**: Resolver produces slug; approach_router does exact `procedure_id` match in the old v1 map when possible.
- **Is there a quality gate?** Partial (exact slug lookup is good when it hits; the resolver is the real gate).
- **Failure modes**: When resolver returns None or low confidence, it falls back to legacy trigger scoring on raw text against the old playbook.
- **Recommended fix**: Make the resolver the single source of canonical procedure IDs everywhere. Remove or heavily guard the legacy text trigger path.
- **Priority**: High

## 4. Approach Selection
- **Current file/function**: `approach_router.get_supported_case` / legacy `_score_match` + the data in `data/approach_playbook/procedure_to_approach_map_v1.jsonl`.
- **Current behavior**: Returns `recommended_approach_ids`, `conditional_approach_ids`, `blocked_approach_ids`, `supported` flag.
- **Is there a quality gate?** Partial (the map exists and the resolver slug is now preferred for lookup).
- **Failure modes**:
  - The old trigger scoring path can still fire.
  - No strong enforcement that a "posterior THA" slug cannot return anterior-only modules in the hybrid path.
  - Many non-certified procedures have empty or low-confidence approach recommendations.
- **Recommended fix**:
  - Make approach selection take the canonical slug + explicit approach hint from the user prompt as first-class inputs.
  - Add "forbidden approach" lists per procedure in the registry.
  - In hybrid paths, filter Miller/playbook results by the chosen approach IDs.
- **Priority**: High (this is a major source of "wrong anatomy" complaints)

## 5. Certified Payload Lookup
- **Current file/function**: `main.py` (`if slug and slug in CERTIFIED_PAYLOADS`), startup loading from `data/anatomy/case_prep/certified_case_prep_payloads.jsonl`.
- **Current behavior**: Direct return of the pre-built payload. This is the strongest gate in the system today.
- **Is there a quality gate?** **Real** (for the 24 certified procedures).
- **Failure modes**: Only works if the resolver produces the exact slug. If the resolver is wrong or low-confidence, the system falls through to the weak paths.
- **Recommended fix**: Strengthen the resolver (see stage 2) and add a hard minimum confidence before allowing the short-circuit. Log every short-circuit decision.
- **Priority**: Low (this gate is already good; protect it)

## 6. Anatomy Retrieval (Miller / Pinecone / Playbook)
- **Current file/function**: `run_anatomy_miller_only` (main.py → `anatomy_context_builder.get_miller_anatomy_context`), `playbook_anatomy_builder`, `hybrid_anatomy_builder`, `anatomy_gpt.run_pipeline_fast`.
- **Current behavior**: General semantic retrieval on the (refined) prompt + hybrid assembly.
- **Is there a quality gate?** Mostly fake / weak.
- **Failure modes**:
  - Retrieval is not strongly constrained by the canonical procedure slug or chosen approach.
  - No per-chunk "must have source_quote" or minimum provenance requirement in all paths.
  - Legacy `run_pipeline_fast` can generate approach/quiz content with very little grounding.
  - Miller index (especially the old gold v1) contains mixed content.
- **Recommended fix**:
  - Retrieval layer should receive `procedure_id` + `approach_ids` as explicit filters/metadata requirements.
  - Enforce citation/source presence for any anatomy facts returned in non-certified paths.
  - Add score thresholds + reranking that are aware of procedure/approach.
- **Priority**: Critical

## 7. Metadata Filtering
- **Current file/function**: Scattered (some in miller context builder, some in hybrid builders, some in old playbook data).
- **Current behavior**: Limited. Some `used_by_procedure_ids` exist in modules, but enforcement is weak outside the certified payloads.
- **Is there a quality gate?** Partial / fake in fallback paths.
- **Failure modes**: Wrong-region or wrong-approach content can leak when the hybrid or legacy paths run.
- **Recommended fix**: Centralize metadata filtering in a single `AnatomyFilter` class that all retrieval paths must go through. Make `procedure_id` + `approach_id` required filters.
- **Priority**: High

## 8. Source Citation Validation
- **Current file/function**: Mostly only inside the pre-built certified payloads (they contain `source_urls`).
- **Current behavior**: Certified payloads are good. Fallback/generated content often has weak or missing per-fact citations.
- **Is there a quality gate?** Real for certified; mostly absent for fallback.
- **Failure modes**: GPT or hybrid builders can emit plausible-sounding anatomy without a traceable source in the response.
- **Recommended fix**: For any non-certified response, require that every anatomy fact include a `source_quote` + `source_url`. Reject or heavily mark responses that don't meet this.
- **Priority**: High

## 9. GPT Prompt Assembly
- **Current file/function**: `gpt_refiner.py`, `anatomy_gpt.py`, `playbook_anatomy_builder`, `hybrid_anatomy_builder`, and the final assembly in `main.py`.
- **Current behavior**: Multiple different prompt templates exist across the legacy and hybrid code.
- **Is there a quality gate?** None visible in the code (no system prompt that strictly forbids unsupported statements, no "only use the provided snippets" hard rule enforced everywhere).
- **Failure modes**: Classic RAG hallucination / over-generation, especially in the legacy `run_pipeline_fast` path.
- **Recommended fix**:
  - Single, strict system prompt template for anatomy generation.
  - "You may only use facts that appear in the provided snippets or certified modules. If you cannot answer from the provided material, say so explicitly."
  - Add output validation that checks for unsupported claims.
- **Priority**: High

## 10. Final Response Validation
- **Current file/function**: Almost none at runtime (some schema expectations in tests, but not enforced on every response).
- **Current behavior**: The response shape is assembled and returned; almost no post-generation checks.
- **Is there a quality gate?** Fake / none.
- **Failure modes**: Bad content reaches the client.
- **Recommended fix**: Add a lightweight `validate_caseprep_response` function that runs on every non-certified response (and optionally on certified for safety). Check for required citations, absence of known placeholder strings, minimum source coverage, etc.
- **Priority**: Medium-High

## 11. Smoke Testing
- **Current file/function**: `scripts/anatomy/smoke_test_anatomy_runtime.py`
- **Current behavior**: Good basic coverage of the three main behaviors (certified resolve + payload, non-certified fallback, unknown → suggestedMatches + logs).
- **Is there a quality gate?** Real (but small and manual-run).
- **Failure modes**: Not run in CI, doesn't cover approach contamination or retrieval precision deeply.
- **Recommended fix**: Make this (and the validate script) part of CI. Expand it with the test cases from Phase 5 of this audit.
- **Priority**: Medium

## 12. Regression Testing
- **Current file/function**: `scripts/anatomy/validate_clean_anatomy_v1.py` + the 120 tests in `data/anatomy/case_prep/retrieval_tests.jsonl` + various old `test_*.py` scripts.
- **Current behavior**: The v1 validate script is excellent for structure, counts, no-legacy, and path correctness. Retrieval tests exist but are limited.
- **Is there a quality gate?** Partial (good for certified payload hygiene; weak for runtime retrieval/approach accuracy at scale).
- **Failure modes**: Easy to regress alias behavior or approach matching without noticing.
- **Recommended fix**: Build the full production test harness described in the test plan. Run it on every PR + nightly.
- **Priority**: High

**Overall Assessment**

The only *strong* quality gate in the current system is the certified payload short-circuit (resolver + `data/anatomy/case_prep/...`).

Everything else is partial at best and fake in many fallback branches. The system currently relies on "the certified path will be used for the important cases" rather than robust gates across the board. This is fragile as soon as you move beyond the 24 certified procedures.