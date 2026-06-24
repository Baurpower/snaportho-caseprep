# Production-Grade Test Plan for CasePrep

This is the minimum viable test suite required before the system can be considered reliable enough to scale beyond the current ~24 certified procedures.

## 1. Resolver Tests (procedure_registry.resolve_procedure)

**Goal**: The text-to-canonical-procedure mapping must be extremely reliable and observable.

**Required coverage (examples — expand to 100+ real prompts)**:

| Input | Expected procedure_id | Min confidence | Notes / Expected ambiguity |
|-------|-----------------------|----------------|----------------------------|
| "THA" | "tha_posterior" | 0.85 | Default to most common |
| "total hip arthroplasty" | "tha_posterior" | 0.90 | |
| "posterior THA" | "tha_posterior" | 0.95 | |
| "posterior total hip arthroplasty" | "tha_posterior" | 0.95 | |
| "anterior THA" | "tha_anterior" | 0.95 | Must not default to posterior |
| "direct anterior hip replacement" | "tha_anterior" | 0.95 | |
| "TKA" | "tka" | 0.90 | |
| "total knee" | "tka" | 0.85 | |
| "distal radius ORIF" / "volar plate distal radius" | "distal_radius_fracture_orif" | 0.90 | |
| "ACL reconstruction" | "acl_reconstruction" | 0.90 | |
| "72 yo with hip OA undergoing THA" | "tha_posterior" | 0.80 | Contains + alias |
| "help me prepare for a total hip" | "tha_posterior" | 0.80 | |
| "bimalleolar ankle" | "bimalleolar_ankle_orif" | 0.85 | Non-certified but should resolve |
| "something weird with no matching name" | None | — | Must return suggested_matches (top 3-5) + low confidence |
| "totl hip arthroplsty" | "tha_posterior" | 0.75 | Fuzzy should catch |
| "hip replacement" (ambiguous) | "tha_posterior" or None + ambiguity list | — | Resolver should surface that both THA and hemi are possible |

**Test requirements**:
- Every test asserts the exact `procedure_slug`, `match_method`, and `match_score`.
- Every test that expects a slug must also assert that the 4 observability prints were emitted.
- Ambiguous cases must return `suggested_matches`.
- The test must load the real `data/anatomy/registry/procedure_aliases.jsonl` (no mocking the registry in resolver tests).

## 2. Approach Mapping & Contamination Tests

**Goal**: A resolved procedure must never leak anatomy from the wrong approach or wrong body region.

**Core rules that must be enforced in tests**:

- Input that resolves to `tha_posterior` must never return facts/modules that are only valid for direct anterior (e.g., specific anterior interval details without posterior equivalents).
- Input that resolves to `tha_anterior` must never return posterior-only short external rotator release details as the primary approach.
- `tka` input must not surface hip or shoulder content.
- Ankle ORIF inputs must not surface knee ligament or hip material.
- Shoulder arthroplasty must not pull hip or knee content.

**How to implement**:
- For every certified procedure that has a strong approach preference, create at least one "must not contain" test that searches the returned anatomy (or the modules used to build it) for known wrong-approach strings.
- Use the `used_by_procedure_ids` and module metadata from `data/anatomy/modules/*.jsonl`.
- These tests should run against both the certified payload path and the fallback hybrid path.

## 3. Retrieval Quality Tests (Miller / Pinecone / Hybrid)

For a set of 30–50 known good prompts (covering all 24 certified + representative non-certified):

- Top-5 retrieved chunks must be relevant to the resolved `procedure_id`.
- At least 80% of returned facts (in a sampled response) must have a `source_url` or `source_quote`.
- Wrong-region results must be excluded when `procedure_id` + `body_region` metadata is available.
- Score threshold behavior: documents with very low similarity must not appear in the final context unless explicitly allowed by a "sparse metadata" flag (and even then they must be marked limited).

Add explicit "known bad retrieval" tests: prompts that historically pulled wrong content must now be filtered.

## 4. Certified Payload Contract Tests

These must pass for every one of the 24 payloads in `data/anatomy/case_prep/certified_case_prep_payloads.jsonl`:

- JSON schema validation (use a strict schema for `brobot_case_prep_payload_v1`).
- `procedure_id` in the payload exactly matches the filename / registry entry.
- All required sections present and non-empty: `source_urls`, `must_know_anatomy` (≥5–8), `structures_at_risk` (≥5), `attending_pimp_questions` (≥8–10), `night_before_review_checklist` (≥5).
- No legacy placeholder strings (the list from the hygiene pass + any new ones discovered).
- Every anatomy fact that claims a specific structure/landmark/interval has at least one `source_url`.
- `case_prep_status == "certified"`.
- No duplicated large blocks of text across sections unless they are explicitly intentional.
- The payload loads and the `procedure_id` is present in `data/anatomy/registry/certification_registry.jsonl`.

These tests should be part of the `validate_clean_anatomy_v1.py` script and run in CI on every change to the payloads or registry.

## 5. End-to-End Golden Tests (Top 30–50 Common Cases)

For each important case, store:

- raw user prompt
- expected `procedure_id`
- expected `match_method` (or at least min confidence)
- expected output type (`certified_case_prep_payload` vs `fallback`)
- list of modules or sources that *must* appear in the response (for certified cases)
- list of strings that *must not* appear (wrong approach, wrong body region, known placeholders)
- minimum number of citations / source_urls expected

Run the full `/case-prep` (or `/anatomy`) handler against these prompts and assert the above.

Include both "perfect" inputs and realistic noisy ones ("prep me for a hip tomorrow", "pimp on distal radius", "72F with OA for hip replacement").

## 6. Bad Input / Robustness Suite

- Completely garbage ("asdfasdf qwer 1234")
- Off-topic ("I have a headache")
- Extremely short ("hip")
- Highly ambiguous ("ORIF")
- Misspellings of every common procedure
- Inputs that contain multiple procedures ("THA and TKA tomorrow")

For these, the system must:
- Not crash
- Return the new warning text when it cannot identify
- Return `suggested_matches` (never empty when confidence is low)
- Never return a rich certified payload for a non-matching procedure

## 7. Regression Guardrails

- Any change to `procedure_registry.py`, `approach_router.py`, `main.py` (the resolver or certified block), or the files under `data/anatomy/registry/` and `data/anatomy/case_prep/` must not break any of the above tests.
- Nightly job that runs the full golden + bad-input suite against the live (or staging) instance and alerts on new failures.
- Every certified payload change must re-run the full payload contract tests + a spot-check of the smoke tests.

## 8. Non-Functional / Operational Tests

- Schema validation of all JSONL under `data/anatomy/` on every commit.
- Load time of the alias registry and certified payloads (must stay fast).
- Observability: every resolver decision in the golden tests must have produced the four required log lines.
- No leakage of internal paths or old version strings (`v1_4`, `brobot_anatomy_router_v1`, etc.) into user-facing responses for certified cases.

## Execution Strategy

- The existing `scripts/anatomy/validate_clean_anatomy_v1.py` and `smoke_test_anatomy_runtime.py` should be expanded into (or call) the suites above.
- All tests must be runnable with `python -m pytest` or a simple `python scripts/anatomy/run_all_production_tests.py`.
- CI must fail the build if any resolver, approach contamination, or certified payload contract test fails.
- The 120 retrieval tests in `data/anatomy/case_prep/retrieval_tests.jsonl` should be incorporated into the E2E golden set.

This level of testing is what turns the current "mostly works for the 24" system into something that can safely scale.