# Autonomous Approach Library Completion

Use this runbook to finish every remaining human orthopaedic and spine approach
in the CasePrep v3 approach-library queue. This is a long-running authoring job,
not a request to publish clinical content.

## Copy/paste launch prompt

```text
Finish all remaining human orthopaedic and spine approaches in the CasePrep v3
approach library. Work autonomously until the current work queue has zero
pending source pages. Do not stop after one approach or one batch, and do not
ask me to approve routine continuation between batches.

Use docs/approach-authoring-autonomous-runbook.md as the controlling workflow.
Preserve all unrelated working-tree changes. Author concise original syntheses
in data/approach_library/curated/*.json, compile them with the existing local
compiler, and never hand-write the expanded files in authored/.

Clinical accuracy and traceable evidence are hard gates. Read every primary
source page, add at least one independent authoritative source, cite every
clinical item, and give every high-risk claim at least two sources. Never invent
a detail, citation, PMID, URL, procedure mapping, or unresolved anatomy. If a
page cannot be researched adequately, record it in the blocked ledger and keep
working through all other pages.

Checkpoint after each curated file and validate after each batch. Continue past
ordinary source, formatting, or validation failures by fixing or isolating the
affected approach. Stop only when the completion gate in the runbook passes, or
when every remaining item is documented as genuinely blocked after exhausting
the allowed source strategies.
```

## Scope and authority

- Work only in the current `snaportho-caseprep` repository.
- Preserve unrelated modified and untracked files.
- The in-scope domains are `orthopedic-trauma`, `orthopedics`, and `spine`.
- Exclude `cmf` and `vet` sources.
- Author and compile drafts, but do not mark them reviewed, certified, or
  published.
- Routine file creation, source research, compilation, tests, and queue rebuilds
  are authorized. Do not make unrelated product or runtime changes.
- Do not use source text or illustrations verbatim. Checked-in content must be
  an original, concise synthesis.

## Authoritative state

At the start of a run, execute:

```bash
.venv/bin/python scripts/compile_curated_approaches.py --check
.venv/bin/python scripts/build_approach_work_queue.py --batch-size 20
.venv/bin/python scripts/audit_approach_library.py
```

Read `data/approach_library/work_queue/manifest.json` after rebuilding. Its
`batch_count` and `pending` values define the active queue. Process only
`batch_001.json` through `batch_NNN.json`, where `NNN` is `batch_count`.
Higher-numbered files can be stale remnants from an older queue and must not be
treated as active work.

Before authoring a task, recheck that its source ID or normalized source URL is
not already represented by a non-`source_indexed` packet. Skip duplicates and
rebuild the queue after the current batch.

## Output format

Write concise source definitions to `data/approach_library/curated/*.json`.
Follow the shape of the existing curated files and let
`scripts/compile_curated_approaches.py` generate claim IDs, provenance, review
state, and expanded packets in `data/approach_library/authored/`.

Each approach definition must include:

- a stable, descriptive `approach_id`, name, aliases, region, joint, bones, and
  a precise corridor;
- at least two independent sources, including the queued discovery source;
- procedure applications only when directly supported;
- all required clinical sections used by the schema;
- concise attending-level questions whose answers are supported by citations;
- `source_ids` on every clinical item;
- `risk_level: high` for claims where an error could change incision, interval,
  neurovascular safety, retraction, fixation, imaging, closure, or bailout;
- at least two independent `source_ids` for every high- or critical-risk claim;
- `claim_key` and `normalized_value` where comparable facts need contradiction
  detection.

The minimum nonempty sections enforced by the current validator are:
`positioning`, `surface_landmarks`, `incision`, `layers`,
`structures_at_risk`, `danger_zones`, `exposure`, `limitations`, `indications`,
`closure`, `complications`, and `questions`. Fill other sections when the
sources support them. Do not add generic filler merely to make a section look
complete.

## Evidence workflow for each task

1. Read the queued source page. For AO pages, use
   `scripts/read_ao_approach.py <url>` when helpful; its output is temporary
   evidence, not text to copy.
2. Find and read at least one independent authoritative source. Prefer
   peer-reviewed literature indexed by PubMed/PMC, AO, AAOS, JBJS, or another
   authoritative operative reference accepted by the schema.
3. Use primary or high-quality review evidence for comparative outcome claims.
   Orthobullets must not be the only substantive source.
4. Verify titles, URLs, source identifiers, and PMID values against the actual
   source. Never cite a search-result snippet as evidence.
5. Synthesize only facts supported by the cited sources. When sources conflict,
   narrow the claim, represent the distinction explicitly, or leave it out.
6. Do not infer missing measurements, safe zones, internervous planes,
   positioning, indications, or complications from nearby approaches.

If a detail is unavailable, omit it when optional. If it is required for a
valid and useful packet, mark the approach blocked rather than manufacture
content.

## Continuous batch loop

For each active batch, in order:

1. Inspect every task and group pages that are genuinely variants of one
   approach only when the source evidence supports a shared reusable definition.
2. Author one curated file at a time using an existing file for structural
   reference.
3. Immediately validate the new file:

   ```bash
   .venv/bin/python scripts/compile_curated_approaches.py --check path/to/file.json
   ```

4. Compile only after validation passes:

   ```bash
   .venv/bin/python scripts/compile_curated_approaches.py path/to/file.json
   ```

5. Confirm the generated authored packet represents the queued source ID or URL.
6. After the batch, run the full validation and tests:

   ```bash
   .venv/bin/python scripts/compile_curated_approaches.py --check
   .venv/bin/python -m pytest tests/test_approach_library.py
   .venv/bin/python scripts/build_approach_work_queue.py --batch-size 20
   .venv/bin/python scripts/audit_approach_library.py
   ```

7. Re-read the rebuilt manifest and continue with the new active queue. Queue
   numbering may change after coverage increases; do not rely on an old batch
   number or cached task list.

Keep progress durable: never hold multiple completed approaches only in chat or
memory before writing and validating them.

## Blocked ledger and recovery

Maintain `data/approach_library/work_queue/blocked.jsonl` only when needed. Each
line must contain `task_id`, `source_page_id`, `url`, `reason`,
`attempted_sources`, `attempts`, and `last_attempted_at`.

An item is genuinely blocked only after trying the primary page, a direct URL
read or AO helper where applicable, title/approach search, and at least one
independent authoritative-source search. Temporary network failure, one dead
secondary link, or a validation error is not enough to stop the overall run.
Record the item, continue with the rest, and retry blocked items after the next
batch checkpoint.

Never weaken the validator, trusted-source rules, required review roles, or
clinical safety requirements to reduce the pending count.

## Completion gate

The job is complete only when all of the following are true:

1. Rebuilding the queue reports `pending: 0` for the three in-scope domains, or
   every remaining task is present in the blocked ledger with exhausted attempts.
2. `compile_curated_approaches.py --check` exits successfully for the full
   curated library.
3. `tests/test_approach_library.py` passes.
4. `audit_approach_library.py` reports a passing inventory gate and no new
   source, schema, citation, or duplicate-coverage failures.
5. No packet created by this run is marked published, certified, or independently
   reviewed.

At handoff, report authored approach count, remaining pending count, blocked
count with reasons, validation/test results, and every file changed. Do not
describe the library as publication-ready; all new packets remain
`agent_review_pending` until independent review is completed.
