# Implementation Roadmap — Making CasePrep Production-Grade

This roadmap is deliberately incremental and prioritizes "make the flow understandable and the good path reliable" before "add hundreds more cases."

## Phase 1 — Make the Flow Understandable and Safe (Foundation)

**Goal**: Anyone (new engineer, reviewer, or surgeon) can look at the code + docs and understand exactly what will happen for any input, and the dangerous legacy paths are no longer silently reachable for production traffic.

**Tasks**:
- Create (or update) a top-level `ARCHITECTURE.md` that points to the documents in `docs/repository_audit/` (especially `pipeline_plain_english.md`, `production_pipeline_diagram.md`, `source_of_truth.md`).
- Add a single canonical sequence diagram (ASCII or Mermaid) at the top of `ARCHITECTURE.md` showing the resolver → certified short-circuit vs. the guarded fallback.
- In `main.py`:
  - Make the certified short-circuit even more prominent (early return with clear comment).
  - Add an explicit `MIN_RESOLVER_CONFIDENCE_FOR_CERTIFIED = 0.75` (or similar) constant and respect it in the short-circuit condition.
  - In the fallback branches, always include the `suggested_matches` from the resolver and set `limitedAnatomyContext: True` + clear warning.
  - Consider a hard environment variable or feature flag (`ENFORCE_CERTIFIED_ONLY_FOR_PROD`) that makes non-certified paths return a very limited response or error in production deploys.
- Audit and document every remaining call to `run_pipeline_fast`, `build_hybrid_anatomy`, and the old catalog path. Add TODOs or deprecation warnings.
- Update the two scripts in `scripts/anatomy/` (`validate_clean_anatomy_v1.py` and `smoke_test_anatomy_runtime.py`) to also assert that the four resolver log lines were emitted on every test case.
- Remove or heavily comment out any code that still loads old `data/anatomy_modules/`, `data/anatomy_sources/`, or `data/anatomy_integration/` in the hot path (they should only be referenced from archive/ or migration scripts).

**Files likely involved**:
- `main.py`
- `procedure_registry.py`
- `approach_router.py`
- `docs/` (new or updated top-level architecture doc)
- `scripts/anatomy/validate_clean_anatomy_v1.py` and `smoke_test_anatomy_runtime.py`

**Acceptance criteria**:
- A new developer can read `ARCHITECTURE.md` + `pipeline_plain_english.md` and correctly predict the code path + output type for a certified case vs. a random non-certified case.
- All golden tests in the smoke/validate scripts pass and exercise the resolver observability.
- No production code path for a certified procedure can reach the old `run_pipeline_fast` + legacy catalog without an explicit "I know what I'm doing" flag.

**Risks**: Over-restricting the fallback too early could break existing non-certified usage. Mitigate by keeping a generous `ANATOMY_ALLOW_UNSUPPORTED_RETRIEVAL` escape hatch during the transition.

**Priority**: Highest — do this before touching anything else.

## Phase 2 — Lock Down the Resolver (The New Front Door)

**Goal**: The text → canonical `procedure_id` mapping is the single most important quality gate. Make it trustworthy and observable.

**Tasks**:
- Move the alias data and the resolver logic into a clean module under `data/registry/` or keep it under `data/anatomy/registry/` but treat `procedure_registry.py` as the implementation of the Case Resolver component.
- Add explicit `confidence` (0–1) and `ambiguity` fields to the return value of `resolve_procedure`.
- Add a small set of negative examples / "must not match" rules (e.g., "direct anterior" should strongly prefer `tha_anterior` even if a generic "tha" alias exists earlier).
- Implement the minimum confidence gate from Phase 1.
- Expand the resolver tests (see `production_test_plan.md`) with 50–100 real prompts (including the ones from the user query and common misspellings/partial phrases). These tests must live in `scripts/anatomy/` or a `tests/` directory and run in CI.
- Add logging (or structured output) of every resolver decision (input, chosen slug, confidence, method, alternatives) so that production logs can be audited.

**Files likely involved**:
- `procedure_registry.py`
- `data/anatomy/registry/procedure_aliases.jsonl` (and possibly a new `procedures.jsonl` master)
- `main.py` and `approach_router.py` (they both call the resolver — make the call site consistent)
- New or expanded test file under `scripts/anatomy/`

**Acceptance criteria**:
- All resolver golden tests pass with the documented min confidence.
- The resolver is the *only* place that turns raw text into a `procedure_id` (approach_router should only do exact lookup after the resolver has spoken).
- Every production resolver decision is logged with enough context to debug later.

**Priority**: High.

## Phase 3 — Lock Down Certified Payloads (Make "Certified" Mean Something)

**Goal**: The 24 (and future) certified payloads are contractually guaranteed to be high-quality, and changes to them are gated.

**Tasks**:
- Formalize a JSON Schema for `brobot_case_prep_payload_v1` and add it to the repo (or under `data/anatomy/registry/`).
- Extend `scripts/anatomy/validate_clean_anatomy_v1.py` (or create a dedicated `validate_payloads.py`) so that it is a strict contract test: schema + required sections + no legacy strings + citation presence + procedure_id consistency.
- Make this validation run on every PR that touches anything under `data/anatomy/case_prep/` or the registry.
- Add a simple "payload linter" step that also checks for duplicated large text blocks, missing source_urls on major sections, etc.
- For every certified payload, ensure the corresponding entries exist in `retrieval_tests.jsonl` and the golden E2E suite (Phase 5).

**Files likely involved**:
- `data/anatomy/case_prep/certified_case_prep_payloads.jsonl`
- `data/anatomy/registry/certification_registry.jsonl`
- `scripts/anatomy/validate_clean_anatomy_v1.py` (expand)
- New schema file
- CI workflow (`.github/workflows/` or equivalent)

**Acceptance criteria**:
- Changing a certified payload without passing the full contract tests fails CI.
- All 24 current payloads (and any new ones) pass the expanded validation with zero legacy strings and full required sections + sources.

**Priority**: High (protects the one strong quality path that already exists).

## Phase 4 — Fix Retrieval Quality in the Fallback Paths

**Goal**: Even when we are not using a certified payload, the anatomy that comes back is grounded, procedure-aware, and approach-aware.

**Tasks** (in rough order):
- Modify the call sites in `main.py` so that `run_anatomy_miller_only` (and the hybrid builders) receive the `canonical_slug` (and resolved approach IDs if known) from the resolver.
- Update `anatomy_context_builder.get_miller_anatomy_context` (or wrap it) to accept and apply `procedure_id` / `approach_ids` / `body_region` filters via metadata.
- Add or enforce `require_source_quote` and minimum score thresholds when the call is coming from a non-certified path.
- In the hybrid/playbook builders, filter or heavily mark any modules/facts whose `used_by_procedure_ids` do not contain the resolved procedure.
- Add retrieval precision tests (see test plan) that assert the above filtering behavior.

**Files likely involved**:
- `main.py`
- `anatomy_context_builder.py`
- `hybrid_anatomy_builder.py`, `playbook_anatomy_builder.py`
- `data/anatomy/modules/*.jsonl` (they already have `used_by_procedure_ids` — start using them strictly)
- New or expanded retrieval tests

**Acceptance criteria**:
- For a set of golden non-certified cases, the top results after filtering are relevant to the resolved procedure and do not contain known wrong-approach or wrong-region content.
- Score and citation requirements are enforced (or the response is marked `limitedAnatomyContext`).

**Priority**: High for anything that still uses the fallback paths.

## Phase 5 — Build the Evaluation Harness (Prevent Regressions)

**Goal**: We can add new cases and improve the system without silently breaking existing behavior.

**Tasks**:
- Implement the core suites described in `production_test_plan.md`:
  - Resolver golden + bad input tests
  - Approach contamination tests
  - Certified payload contract tests (already partially in validate script)
  - Retrieval quality tests
  - End-to-end golden tests for the top 30–50 cases
- Make the harness runnable as a single command and integrate it into CI (fail the build on new failures).
- Add a nightly job that runs the full suite against staging/production and posts results.
- Expand the existing 120 retrieval tests in `data/anatomy/case_prep/retrieval_tests.jsonl` and wire them into the harness.
- Add logging of test failures with the exact input + resolved slug + actual vs expected output.

**Files likely involved**:
- `scripts/anatomy/` (expand validate + smoke, or new `run_production_tests.py`)
- `data/anatomy/case_prep/retrieval_tests.jsonl`
- CI configuration
- Possibly a small `tests/` directory

**Acceptance criteria**:
- The full harness runs in < 5–10 minutes on a normal machine/CI runner.
- Any change that would have caused a previously passing golden case to now resolve to the wrong procedure, pull wrong-approach anatomy, or return a payload missing required sections now fails the build with a clear message.

**Priority**: High (this is what makes scaling safe).

## Phase 6 — Scale Certification (The Long-Term Growth Engine)

**Goal**: A repeatable, low-friction process for taking a new procedure from "someone wants it" to "certified and protected by tests."

**Tasks**:
- Define the exact criteria for "certified" (minimum source facts per section, approach coverage, pimp questions, human sign-off, test coverage).
- Build (even a simple shared spreadsheet + folder at first) a review queue: candidate → draft payload → automated validation → human review → publish + registry update + test addition.
- For new procedures, the person proposing the case must also add the corresponding golden resolver tests and E2E cases.
- Add a lightweight dashboard (or section in the existing reports) showing certified count, fallback rate, and review queue size.
- Version the act of publishing a payload (update the registry entry + payload `version` field).

**Files / artifacts**:
- Documentation of the certification criteria (new doc under `docs/` or in the registry).
- Process tooling (can start as docs + scripts; later a small internal app).
- Updates to `data/anatomy/registry/` on every publish.
- Expansion of the test suites.

**Acceptance criteria**:
- Adding the 25th certified procedure follows a documented checklist that includes tests and does not require a full repo audit.
- The fallback rate (how often production traffic misses the certified short-circuit) is tracked and trending down as more procedures are certified.

**Priority**: Medium (start this in parallel with Phases 4–5, but it is the main ongoing work after the quality gates are in place).

## Sequencing Guidance

- Phases 1–3 can and should be done with relatively small, reviewable changes.
- Phase 4 and 5 can be done in parallel with 1–3 once the basic resolver + certified path is hardened.
- Phase 6 is the "business as usual" mode once the harness exists and the dangerous legacy paths are contained.

Do not attempt to scale the number of certified procedures significantly until at least Phases 1–3 + the core of Phase 5 are in place. Adding more cases on top of the current tangled fallback architecture will mostly add more surface area for the problems documented in the failure analysis.