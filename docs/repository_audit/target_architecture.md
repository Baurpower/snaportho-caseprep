# Target Architecture — Production-Grade CasePrep

The target architecture cleanly separates concerns that are currently tangled across `main.py`, `procedure_registry.py`, `approach_router.py`, multiple builders, and legacy data directories.

## 1. Case Resolver (Pure Identification)

**Responsibility**: Turn any user string into a canonical `procedure_id` + confidence + ambiguity info. Nothing else.

**Interface** (proposed):
```python
def resolve_case(prompt: str) -> ResolveResult:
    # returns
    {
      "procedure_id": "tha_posterior" | None,
      "confidence": 0.0-1.0,
      "match_method": "exact" | "contains" | "fuzzy" | "gpt" | "none",
      "ambiguous_with": [...],   # other plausible procedure_ids
      "suggested_matches": [...]
    }
```

**Implementation notes**:
- Data-driven only: loads from `CaseRegistry` (see below).
- No anatomy, no approaches, no GPT generation of content.
- Stages A–D from current `procedure_registry.py` are good — keep and harden them.
- Must be the single place that ever decides "what procedure is this?"

**Current closest thing**: `procedure_registry.resolve_procedure` (good direction, but still mixed with some old logic in `approach_router`).

## 2. Case Registry (The Single Source of Truth for Procedures)

**Responsibility**: Know every procedure that exists in the system.

**Data model** (JSONL or small DB):
```json
{
  "procedure_id": "tha_posterior",
  "display_name": "Total Hip Arthroplasty (Posterior Approach)",
  "specialty": "adult_reconstruction",
  "body_region": "hip",
  "synonyms": [...],                 # for documentation / UI
  "approaches": ["posterior", "lateral"],
  "certification_status": "certified" | "in_review" | "not_certified",
  "certified_payload_version": "2026-06-06",
  "has_approach_map": true,
  "reviewer": "...",
  "last_reviewed": "2026-..."
}
```

**Implementation**:
- One file: `data/registry/procedures.jsonl` (or equivalent in the clean `data/anatomy/registry/`).
- Loaded once at startup.
- Versioned.
- Used by Resolver, Approach Matcher, Payload Store, Evaluation harness.

**Current closest thing**: `data/anatomy/registry/procedures.jsonl` + `certification_registry.jsonl` + `procedure_aliases.jsonl` (these should be unified or very tightly coupled).

## 3. Certified Payload Store

**Responsibility**: Serve only trusted, reviewed, versioned case-prep content.

**Characteristics**:
- Payloads are immutable once certified.
- Every payload has:
  - `schema_version`
  - `procedure_id`
  - `version` (date or semver)
  - `source_coverage` (which modules/sources were used)
  - `reviewer`, `review_date`
  - Full sections with per-fact `source_url` + `source_quote` where possible.
- Lookup is by exact `procedure_id` only (never by fuzzy text).

**Current state**: `data/anatomy/case_prep/certified_case_prep_payloads.jsonl` + the loading logic in `main.py` startup. This is the strongest part of the current system — protect and formalize it.

## 4. Anatomy Retrieval Layer (Source-Backed Only)

**Responsibility**: Given a `procedure_id` + optional `approach_ids` + query, return only grounded anatomy facts with citations.

**Requirements**:
- Explicit `procedure_id` and `approach_ids` must be passed in (no more "just search the prompt").
- Metadata filtering is mandatory (`used_by_procedure_ids`, `approach`, `body_region`, etc.).
- Every returned fact must include `source_url` and preferably `source_quote`.
- Score thresholds + reranking are procedure/approach-aware.
- Separate namespaces or strong metadata for different corpora (Miller facts vs Orthobullets playbook vs approach catalogs).
- Never generates unsupported statements.

**Current problems**: Miller retrieval (`run_anatomy_miller_only` + `anatomy_context_builder`) and the hybrid builders are too general and not sufficiently constrained by the resolved procedure/approach.

## 5. Playbook / Approach Matcher

**Responsibility**: Given a canonical `procedure_id`, return the allowed/conditional/blocked approach module IDs, with confidence.

**Rules**:
- Strict mapping. A "tha_posterior" slug should never be allowed to pull anterior-only content.
- Approach synonyms live here (not in the general alias resolver).
- Confidence score + "manual_review" flag.
- Fallback only when the map explicitly says the procedure has no strong approach preference (rare for certified cases).

**Current closest thing**: `approach_router.py` + `data/approach_playbook/procedure_to_approach_map_v1.jsonl`. The recent change to prefer resolver slug + exact lookup is good — continue in that direction and make the map data live under the Case Registry.

## 6. Response Builder

**Responsibility**: Assemble the final JSON the client sees.

**Logic (strict priority)**:
1. If resolver gave a high-confidence certified `procedure_id` → return the exact payload from the Certified Payload Store. Add only thin metadata (resolver method, citations summary).
2. Else if the procedure is known but not certified → return case-prep facts + limited anatomy + clear "This procedure is not yet fully certified" + citations.
3. Else → return case-prep facts + minimal anatomy (or none) + the "could not confidently identify" message + suggested matches.

Never mix certified payload content with generated fallback content in the same response.

**Current state**: The short-circuit in `main.py` is the right shape. The rest of the response assembly is scattered across hybrid builders and legacy code.

## 7. Evaluation Harness (Prevents Regressions at Scale)

Must include at minimum:

- **Resolver golden set** (hundreds of real prompts → expected `procedure_id` + min confidence).
- **Approach contamination tests** (posterior THA input must never surface anterior-specific facts; cross-body-region tests).
- **Certified payload contract tests** (schema, source coverage, no placeholders, procedure_id match).
- **Retrieval precision tests** (for top-5 results on known cases).
- **Citation coverage tests**.
- **Bad input suite** (ambiguous, misspelled, garbage, off-topic).
- **Regression suite** that runs on every PR + nightly.
- Automated report (pass rate per category, new failures, coverage of certified vs non-certified).

The existing `scripts/anatomy/smoke_test_anatomy_runtime.py` and `validate_clean_anatomy_v1.py` are a good start but far too small for production at scale.

## Overall Principles of the Target Architecture

- **Resolver is the only text-to-procedure gate.**
- **Certified payloads are the only rich anatomy that can be returned without heavy qualification.**
- **Every retrieval or generation step after the resolver must be told the exact `procedure_id` + `approach_ids`.**
- **No generation of anatomy facts without source quotes/citations in non-certified paths.**
- **Everything is versioned** (registry, payloads, corpora, prompts, embedding model, Pinecone namespace).
- **Evaluation is first-class** and runs automatically.

This separation makes it possible to scale certification, improve retrieval quality, and add new corpora without the current tangled fallback behavior.