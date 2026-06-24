# Bad Content Failure Analysis

This document traces every realistic way low-quality, irrelevant, or unsupported anatomy can currently reach a user in the production pipeline.

## 1. Weak or Overly Permissive Alias Resolution

**File**: `procedure_registry.py` (`resolve_procedure`, stages A/B/C, `_load_procedure_aliases`)

**Why it allows bad content**:
- The alias list in `data/anatomy/registry/procedure_aliases.jsonl` contains both very specific phrases ("direct anterior hip replacement") and very generic ones ("hip replacement", "total hip", "THA").
- Stage B (contains) and Stage C (fuzzy) can fire on short or partial mentions.
- Alias ordering in the JSONL affects which procedure wins on ambiguous prompts (e.g., a prompt containing both "direct anterior" and "THA" may still match the earlier `tha_posterior` entry if the generic "tha" alias is checked first).

**Example failure**:
- Prompt: "Review anatomy for direct anterior THA"
- Resolver may return `tha_posterior` (via early "tha" alias match) instead of `tha_anterior`, or return a high-confidence wrong slug.
- Consequence: posterior-specific short external rotator or sciatic protection details are presented as the primary anatomy for an anterior case.

**Risk level**: High for non-certified and for any prompt that is not perfectly specific.

## 2. Legacy Trigger Scoring Path Still Reachable

**File**: `approach_router.py` (`get_supported_case` — the fallback after the resolver block, `_score_match`, `_normalize`, loading from `data/approach_playbook/procedure_to_approach_map_v1.jsonl`)

**Why it allows bad content**:
- When the resolver returns no slug (or the exact lookup in the v1 map fails), the code falls back to the old word-overlap scoring against the historical triggers.
- This path has no knowledge of the new canonical slugs or the clean v1 data.
- It can return entries based on very weak signals that happen to be present in old trigger lists.

**Example failure**:
- A prompt with generic words that appear in multiple old playbook entries can cause the wrong `case_family` + `recommended_approach_ids` to be chosen, which then flows into the hybrid builder.

**Risk level**: Medium-High (mainly affects non-certified and ambiguous cases).

## 3. Certified Short-Circuit Depends Entirely on Resolver Quality

**File**: `main.py` (the `if slug and slug in CERTIFIED_PAYLOADS` blocks in both `/case-prep` and `/anatomy`)

**Why it allows bad content**:
- The short-circuit itself is excellent.
- However, there is no minimum confidence gate before trusting the slug for the short-circuit.
- A low-confidence or wrong resolver decision sends the user down the entire weak fallback stack instead of the certified payload.

**Current protection**: Only the resolver's internal stages + the GPT classifier's 0.8 threshold. No second check in `main.py`.

**Risk level**: High if resolver quality ever regresses.

## 4. Miller / Pinecone Retrieval Is Not Constrained by Resolved Procedure or Approach in Fallback Paths

**File**: `main.py` (`run_anatomy_miller_only`), `anatomy_context_builder.py` (`get_miller_anatomy_context`)

**Why it allows bad content**:
- The function receives only the raw (or refined) prompt.
- It does semantic search against the Miller gold index (local or Pinecone).
- There is no mandatory `procedure_id` or `approach_ids` filter passed down from the resolver.
- The old gold index contains mixed content from many procedures and sources.

**Example failure**:
- A non-certified or low-confidence hip case can retrieve knee or shoulder anatomy if the embedding similarity is high enough on generic terms ("approach", "landmarks", "structures at risk").

**Risk level**: High in all fallback paths.

## 5. Hybrid / Playbook Builders Can Still Generate or Mix Unsupported Content

**Files**:
- `playbook_anatomy_builder.py`
- `anatomy_curator.py`
- `hybrid_anatomy_builder.py`
- `anatomy_gpt.py` (`run_pipeline_fast`)

**Why it allows bad content**:
- These components were designed before the strict "certified payloads only" model.
- They synthesize or curate anatomy from modules + Miller chunks + old playbook data.
- Prompt templates and curation logic do not universally enforce "only emit facts that have explicit source support in the provided material."
- They are still called for any `supported` non-certified case (and in error fallbacks).

**Risk level**: High for the ~36 non-certified procedures and any certified case that falls through the resolver.

## 6. Legacy Catalog Path Is Completely Unprotected

**File**: `main.py` (the `else` branch when `not ENABLE_LOCAL_ANATOMY_RAG`, and the final `run_pipeline_fast` call)

**Why it allows bad content**:
- When the flag is false (or in certain error paths), the resolver, certified logic, Miller, and playbook improvements are all bypassed.
- It falls back to the oldest `CATALOG` (loaded from upper/lower extremity approach files + `data/approach_router/approach_mappings.yaml`) + `anatomy_gpt.run_pipeline_fast`.
- This path has none of the post-cleanup improvements.

**Risk level**: Medium (depends on whether the flag is reliably true in production), but extremely dangerous if ever flipped.

## 7. Approach Contamination Inside the Supported Case Gate + Hybrid Path

**Files**: `approach_router.py` (the mapping it returns) + the hybrid builders that consume `recommended_approach_ids`.

**Why it allows bad content**:
- Even when the resolver produces a good slug (e.g. `tha_posterior`), the downstream `sc["recommended_approach_ids"]` can still come from the old map or be empty.
- The hybrid builders then pull modules based on those IDs (or fall back to broad retrieval).
- There is no cross-check that "the modules we are about to use are actually valid for the procedure the resolver decided on."

**Example failure**:
- A prompt that the resolver correctly tags as `tha_posterior` can still pull `approach_hip_lateral_hardinge` + anterior-specific facts if the map or conditional logic is loose.

**Risk level**: High.

## 8. Lack of Post-Generation Validation for Non-Certified Responses

**File**: `main.py` (final return of `anatomy_result`)

**Why it allows bad content**:
- There is no function that inspects the assembled `anatomy` object for the presence of citations, absence of known bad strings, or minimum source coverage before returning it to the client.
- The only real validation is the pre-build hygiene that was done on the 24 certified payloads.

**Risk level**: High for everything that is not a certified short-circuit.

## 9. Old Data and Scripts Can Still Be Accidentally Loaded

**Locations**:
- `data/anatomy_modules/`, `data/anatomy_sources/`, `data/anatomy_integration/`, `data/anatomy_miller_gold_v1/`
- Many root `normalized_*`, `output_vectorversion_*`, embed `*.txt`
- Old reports and test scripts that walk `data/` or hardcode old paths

**Why it allows bad content**:
- Any future script, notebook, or developer who does a recursive load or "use the latest data" can pull legacy placeholder-laden or mixed-procedure content.
- The archive pass moved some of this, but the old directories are still present on disk and some code paths (especially in `scripts/`) still reference versioned v1/v2/v3 files.

**Risk level**: Medium (more of a maintenance / accidental regression risk than direct user-facing today).

## 10. GPT Prompt Templates Do Not Universally Forbid Unsupported Generation

**Files**: Various (inside `anatomy_gpt.py`, `gpt_refiner.py`, the hybrid builders, and any direct calls to OpenAI in the legacy paths).

**Why it allows bad content**:
- The system prompt / instructions used in the fallback paths are not uniformly strict about "only use the provided snippets / modules; if you cannot answer from them, say so."
- Some paths still allow the model to "fill gaps" or produce plausible-sounding anatomy.

**Risk level**: High in fallback paths.

## Summary — The Fundamental Problem

The architecture has one excellent, narrow, high-quality path (resolver → certified payload short-circuit) sitting on top of a very large, still-executable legacy anatomy generation system.

For any input that does not perfectly hit one of the 24 certified procedures with high resolver confidence, the user is routed into one or more of the weak/fake-gated paths above.

Until the fallback paths are either:
- eliminated for production traffic,
- or given the same strict resolver + metadata + citation requirements as the certified path,

adding more cases will mostly add more surface area for bad content rather than increasing overall quality.