# CasePrep v1.1 Real-Prompt Replay Audit

Date: 2026-08-12  
Source cohort: privacy-filtered prompts sampled read-only from `public.brobot_user_responses` in the SnapOrtho Supabase project.  
Replay target: production `POST /case-prep/web/v1.1/stream`.

## Executive finding

v1.1 is two materially different products behind one packet contract:

1. **Certified procedures are strong.** They return structured, source-backed anatomy, operative flow, pitfalls, and attending questions. Typo tolerance is excellent.
2. **Uncertified procedures look complete but are mostly generated.** The packet often contains 40–47 items, yet 64–78% are uncited model gap-fill. RAG contributes almost exclusively to `pimp_questions`; the rest of the apparent packet is generated.

The highest-leverage improvement is not a larger model. It is stricter retrieval scoping, an honest coverage state, and source-backed section retrieval before any generation.

## Method

- Supabase contained 867 stored BroBot responses from 2025-08-05 through 2026-08-12.
- No stored row was explicitly tagged `caseprep_version = v1.1`; stored questions were therefore used as the replay cohort, not their legacy answers.
- Excluded prompts over 100 characters, prompts containing digits, and prompts containing common patient descriptors.
- Selected frequent, recent, ambiguous, misspelled, approach-specific, and coverage-edge prompts.
- Reconstructed the final state from all SSE events, replacing repeated section emissions by `section_id`.
- Measured section coverage, provenance, generation rate, confidence, duplicate candidates, source payloads, warnings, and latency.

## Cohort

- ACL reconstruction
- Distal radius fracture
- Carpal tunnel release
- Distal radius ORIF
- Total knee arthroplasty
- Olecranon fracture
- ORIF ankle
- Rotator cuff repair
- Total hip posterior approach
- MPFL reconstruction
- Orif humeral shaft middiaohaseal
- Undifferentiated pleomorphic sarcoma
- Additional resolver probe: ACL reconstruction laparoscopic

## What worked

### Certified packets

ACL reconstruction, distal radius ORIF, posterior THA, and misspelled humeral-shaft ORIF resolved successfully to certified modules. These packets contained 55–60 certified items plus a smaller RAG question set. No section failed, no answer was empty, and misspelling tolerance was notably good.

The misspelled `Orif humeral shaft middiaohaseal` prompt resolved to `humeral_shaft_fracture_orif` and returned 63 grounded items.

### Clarification

`Carpal tunnel release` correctly stopped before generation and requested open versus endoscopic clarification. This is the desired safety behavior and should become the model for other diagnosis-only or underspecified prompts.

### Caching

Cold uncached packets took as long as 22–32 seconds. Subsequent cache hits generally completed in 0.7–1.3 seconds, demonstrating that cache performance is excellent once populated.

## Major defects

### P0 — RAG scope drift

Low-scoring retrieved questions are often related only to the broad body region, not the requested procedure.

- Olecranon fracture retrieved questions about coronoid fractures, Monteggia fractures, radial-head fractures, distal-humerus classifications, and Holstein–Lewis fractures. Many scored only 0.46–0.53.
- Ankle ORIF retrieved calcaneus, Lisfranc, and talus questions alongside ankle-fracture content.
- MPFL reconstruction retrieved ACL/PCL bundles, meniscus repair, MCL injury, osteochondral allograft, and pivot-shift questions. Only a small minority were directly MPFL-specific.
- Rotator cuff repair drifted into adhesive capsulitis, labrum, and football-lineman posterior labral injury.
- Distal radius ORIF included a scaphoid-fracture treatment question and a proximal/midshaft dorsal-radius approach question.
- Undifferentiated pleomorphic sarcoma returned a general sarcoma/translocation quiz rather than a case-preparation packet.

Recommended change:

- Require procedure/entity match for the primary retrieval branch.
- Treat region/specialty branches as controlled backfill, not equal-ranked candidates.
- Apply a minimum calibrated score by branch and a procedure-keyword/entity-overlap gate.
- Use maximal marginal relevance or topic-family caps so adjacent diagnoses cannot dominate.
- Emit `retrieval_relevance = weak` and withhold unrelated rows instead of filling to 15.

### P0 — Generated completeness masquerades as evidence-backed completeness

For five common uncertified procedures, generated content comprised 147 of 216 displayed items (68%). Including the unresolved sarcoma packet, generated content was 147 of 229 items (64%).

Examples of thin generated content include:

- “Perform the tibial and femoral cuts according to preoperative planning.”
- “Expose the fracture site and assess the fracture pattern.”
- “Reduce the fracture and secure fixation with plates and screws.”
- “The area near the medial femoral condyle where neurovascular structures are located.”

These statements create visual completeness but provide little attending-level preparation and sometimes omit clinically important specificity.

Recommended change:

- Make enrichment gap-fill only.
- Never append generated rows to a section that already has grounded content.
- Do not add generated pimp questions when at least eight grounded questions exist.
- Return a visible `coverage_status: limited` packet rather than synthesizing every missing section.
- Do not advertise an uncertified, mostly generated packet with the same visual weight as a certified packet.

The local `enrichment_v1_1.py` changes already implement the first three safeguards but were not deployed in the production responses audited here.

### P0 — Unsupported procedural steps

Uncertified packets generate operative-flow steps without citations. This is the riskiest place to use generic prose. Examples included broad positioning, incision, exposure, and fixation instructions for TKA, ankle ORIF, olecranon ORIF, rotator-cuff repair, and MPFL reconstruction.

Recommended change:

- Do not generate operative flow from model knowledge alone.
- Require a published module or retrieved source passages that explicitly support each step.
- Otherwise omit the section and explain that operative-flow coverage is not yet verified.

### P1 — Resolver accepts contradictions and overcommits diagnoses to operations

- `ACL reconstruction laparoscopic` silently ignored the incompatible modifier and returned certified ACL reconstruction rather than clarifying or warning.
- `Distal radius fracture` was automatically converted to Distal Radius Fracture ORIF.
- `Olecranon fracture` was automatically converted to Olecranon Fracture ORIF.
- A sarcoma diagnosis with no canonical procedure produced a thin question-only packet instead of asking what operation or clinical context the user was preparing for.

Recommended change:

- Add modifier compatibility validation after canonical resolution.
- Require clarification when a diagnosis maps to both operative and nonoperative pathways.
- Require a procedure/approach for operative CasePrep when the prompt is disease-only.
- Preserve and surface ignored tokens so contradictions cannot disappear silently.

### P1 — Enrichment latency is paid even when enrichment adds no value

Certified packets waited approximately eight seconds for enrichment and sometimes emitted `Enrichment timed out after 8s`, even when the final packet contained zero generated content. Uncertified cold packets waited up to 30 seconds for enrichment.

Recommended change:

- Skip enrichment entirely when certified sections and grounded questions already meet coverage thresholds.
- Stream `done` without waiting for optional pedagogy.
- If enrichment remains optional, run it as a separately requested follow-up rather than delaying the trusted packet.

### P1 — Source text encoding corruption

Retrieved data contained mojibake such as `90Â°`, malformed punctuation, and `_Ðdeep-seated ... dark on Y1, bright on Y2`. This is an ingestion/data-cleaning issue, not a rendering issue.

Recommended change:

- Normalize UTF-8 during ingestion.
- Repair common Latin-1/UTF-8 double-decoding sequences.
- Add source-quality rejection for control characters and suspicious replacement patterns.
- Correct likely OCR substitutions only through reviewed source repair; do not silently guess medically meaningful text.

### P2 — Repetition is structurally baked into certified packets

Many exact items intentionally appear once in `top_things_to_know` and again in anatomy, pitfalls, or pimp questions. This supports a high-yield preview, but clients currently render both as full sections, producing a long and repetitive packet.

Recommended change:

- Mark preview items with `references_item_id` rather than duplicating full content.
- Render Top Things as jump links or a compact summary.
- Track exact versus intentional preview duplication separately in evaluation metrics.

### P2 — Packet status is too coarse

An uncertified packet with 15 RAG questions and 29 generated rows ends as `done`, just like a certified 60-item packet.

Recommended contract additions:

- `coverage_status`: `certified | grounded_partial | generated_fallback | unavailable`
- Per-section `grounded_count`, `generated_count`, and `citation_count`
- `retrieval_relevance_score` and `retrieval_scope`
- `unresolved_prompt_tokens`
- `omission_reason` for absent sections
- A terminal quality summary with grounded percentage and warnings

## Recommended implementation order

1. Tighten RAG procedure scoping and enforce a minimum relevance threshold.
2. Deploy the existing gap-fill-only enrichment safeguards.
3. Disable unsupported operative-flow generation.
4. Add resolver contradiction and diagnosis/procedure clarification rules.
5. Skip enrichment when grounded coverage is already sufficient.
6. Add encoding-quality gates at ingestion and retrieval.
7. Add honest coverage/provenance fields to the stream contract.
8. Add v1.1 packet telemetry so future audits do not require replaying legacy prompts.

## Measurement targets

- At least 80% of displayed clinical items source-backed for any packet labeled complete.
- At least 90% direct procedure relevance among retrieved pimp questions.
- Zero uncited generated operative steps.
- Zero silently ignored incompatible modifiers.
- Certified packet P50 terminal latency below 3 seconds on cache miss when enrichment is unnecessary.
- No known mojibake patterns in emitted content.
- User feedback and evaluator scores segmented by `coverage_status`, canonical slug, and retrieval branch.

## Reproduction

The read-only replay and packet summarizer is in `scripts/audit_v11_real_prompts.py`. It contains no user IDs and sends only the reviewed privacy-filtered prompt cohort.
