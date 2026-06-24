# Scaling Plan — From ~60 Procedures to Hundreds/Thousands

This document addresses how the CasePrep system must evolve to support a much larger number of procedures while maintaining (or improving) quality.

## 1. Data Model Scaling

**Current problems**:
- Procedure identity, aliases, approaches, certification status, and payloads are spread across multiple files and some legacy playbook data.
- No single versioned "Case Registry" that everything else references.
- Aliases live in a Python loader + JSONL that is only loosely coupled to the procedures list.

**Target model**:

A single `CaseRegistry` (JSONL + optional small index or SQLite for speed) containing:

```json
{
  "procedure_id": "tha_posterior",
  "version": "2026-06-06",
  "display_name": "...",
  "specialty": "adult_reconstruction",
  "body_region": "hip",
  "approaches": ["posterior", "lateral"],
  "aliases": ["tha", "total hip arthroplasty", ...],   // moved here from separate file
  "certification": {
    "status": "certified",
    "payload_version": "2026-06-06",
    "reviewer": "...",
    "last_reviewed": "..."
  },
  "has_strong_approach_preference": true,
  "source_coverage": { ... },
  "eligible_for_brobot": true
}
```

**Benefits**:
- Resolver, approach matcher, payload store, and evaluation harness all read from the same source.
- Easy to add new fields (e.g., `primary_approach`, `forbidden_approaches`, `min_source_facts_required`).
- Versioning becomes natural.

**Migration**:
- Unify `data/anatomy/registry/procedures.jsonl`, `procedure_aliases.jsonl`, and `certification_registry.jsonl` (or keep them as derived views from one master file).
- Make `procedure_registry.py` a thin client of the registry rather than owning its own dataclass list.

## 2. Corpus Scaling (Sources & Namespaces)

**Current state**:
- Miller gold (local + Pinecone), Orthobullets-derived facts (in modules + sources under `data/anatomy/`), old playbook data, approach catalogs, and various historical normalized corpora are mixed or only weakly separated.
- Retrieval often does general semantic search on the prompt.

**Recommended separation**:

- **Namespace per major corpus** (or very strong `source_type` + `corpus_version` metadata):
  - `certified_payloads` (static, never searched at runtime for certified cases)
  - `miller_facts` (pure source-backed Miller / textbook facts)
  - `playbook_anatomy` (the cleaned modules + Orthobullets-derived case-prep facts)
  - `approach_catalogs` (lower/upper extremity, spine, etc.)
  - Future: `pocket_pimped`, new textbooks, institutional protocols, etc.

- Every retrieval call after the resolver **must** declare:
  - `required_procedure_ids`
  - `allowed_approach_ids` (or `body_region`)
  - `allowed_corpora` / `source_types`
  - Minimum score + `require_source_quote` flag

- Pinecone (or the vector index) should have metadata filters applied at query time for the above.

**Why this matters at scale**:
Without namespace + metadata discipline, adding hundreds of new procedures will cause cross-contamination to explode. The current "search the prompt and hope the hybrid builder filters it" approach does not scale.

## 3. Certification Workflow (The Only Way New Content Becomes Trusted)

Proposed linear workflow:

1. **Candidate creation**
   - New or improved `procedure_id` is proposed (manually or from gap queue).
   - Source facts are retrieved (targeted Miller + Orthobullets pages + any new corpora).

2. **Draft payload generation**
   - Automated assembly using the modular sources + strict templates (no free-form GPT anatomy at this stage, or GPT is heavily constrained + cited).

3. **Automated validation**
   - Schema, required sections, no legacy placeholders, source coverage %, citation presence, approach consistency with the registry.

4. **Human review queue**
   - Reviewer sees the draft + source links + diff vs previous version.
   - Can approve, request changes, or reject.

5. **Publish**
   - Payload is written to the Certified Payload Store with `version`, `reviewer`, `date`.
   - Registry is updated (`certification.status = "certified"`, `payload_version`).
   - New golden test cases are added to the E2E suite.
   - Regression tests are run.

6. **Observability & rollback**
   - Every certified lookup is logged with the payload version used.
   - Ability to roll back a single procedure's payload version without redeploying code.

This workflow must be the *only* way a rich payload becomes available for the short-circuit path.

## 4. Versioning Strategy

Everything that can affect output quality or behavior must be versioned:

- **Case Registry** (`procedure_id` list + aliases + certification status) — version the whole registry.
- **Certified Payloads** — each payload has its own `version` (date or semver). The registry points at the current version for that procedure.
- **Source Corpora** — Miller index version, playbook modules version, Orthobullets source snapshot date, embedding model + chunking strategy.
- **Embedding / Vector Index** — separate Pinecone namespace or collection per major corpus version.
- **Prompts / Builders** — version the system prompts and the `playbook_anatomy_builder` / `hybrid_*` / `curator` logic. Store the version used in the response metadata.
- **Resolver** — the alias data + fuzzy thresholds + GPT classifier prompt should be versioned together with the registry.

**Rule**: A response for a certified case should be reproducible given the tuple `(procedure_id, registry_version, payload_version, prompt_version)`.

## 5. Evaluation at Scale

Metrics that must be tracked (automated where possible):

- **Resolver accuracy**: % of golden prompts that resolve to the expected `procedure_id` with confidence above threshold. Breakdown by match_method.
- **Approach accuracy / contamination rate**: % of responses that contain facts from a forbidden approach for that procedure (measured on golden cases + synthetic contamination tests).
- **Retrieval precision@5 / recall** for known good facts.
- **Citation coverage**: % of anatomy facts in the final response that have an attached `source_url` + `source_quote` (100% target for certified; high target for fallback).
- **Unsupported claim rate**: Human or LLM-as-judge score for claims that cannot be grounded in the provided sources for that response.
- **Schema / contract pass rate** on certified payloads.
- **Human reviewer pass rate** (when the certification workflow is in use).
- **Regression failure rate** on the golden + bad-input suites.
- **Resolver ambiguity rate** (how often it returns multiple plausible procedures) — useful signal for improving aliases.

**Operational requirements**:
- The full evaluation suite runs on every PR that touches resolver, registry, payloads, retrieval, or builders.
- Nightly job runs against staging + production and posts a dashboard / alert on degradation.
- Failed cases are logged with the exact input, resolved slug, and the generated (or short-circuited) output for later review.

## 6. Operational & Tooling Scaling

- **CI gates**: Resolver tests + payload contract tests + approach contamination tests must be green.
- **Review queue UI** (even a simple shared doc or lightweight web app at first): list of cases in "draft", "in review", "certified".
- **Dashboard** (simple internal page or Grafana):
  - Current certified count vs total procedures.
  - Resolver accuracy trend.
  - Recent fallback rate (how often we are *not* using certified payloads).
  - Top failing test cases.
- **Rollback**: Ability to mark a specific `procedure_id` + `payload_version` as "do not use" and fall back to a previous version or limited mode, without code deploy.
- **Logging**: Every resolver decision, every certified short-circuit, every fallback, and the versions of registry/payload/prompt used must be logged with correlation IDs.
- **Feature flags** (in addition to `ENABLE_LOCAL_ANATOMY_RAG`):
  - `USE_CERTIFIED_SHORT_CIRCUIT` (canary per procedure or globally).
  - `ENFORCE_MIN_RESOLVER_CONFIDENCE`.
  - `REQUIRE_CITATIONS_IN_FALLBACK`.

## 7. People & Process Scaling

- One or more "Case Certifiers" (surgeons or senior residents) who own the review queue for their specialty.
- Clear definition of "certified" criteria (minimum source facts, approach coverage, pimp questions, no placeholders, human sign-off).
- Onboarding process for new contributors who want to add a procedure (they must also add the corresponding golden tests and update the registry).
- Regular (monthly) review of the "fallback rate" metric — if too many common cases are still hitting the weak paths, that is a signal to prioritize more certification work.

## 8. What Breaks at Scale Without These Changes

- Alias collisions explode as the number of procedures grows.
- Retrieval quality collapses because the index becomes a bag of everything.
- Review becomes a bottleneck because there is no disciplined workflow.
- Regressions become undetectable because the test surface is tiny compared to the number of cases.
- "Certified" loses meaning because the fallback paths are still the default experience for most inputs.

The clean v1 work (data/anatomy/ + resolver + hygiene) was the necessary first step. The scaling plan above is what turns that foundation into a system that can grow to hundreds or thousands of procedures without quality collapsing.