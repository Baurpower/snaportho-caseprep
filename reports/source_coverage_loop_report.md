# Source Coverage Loop Report

**Run time:** 2026-06-06T17:40:05.174984  
**Iterations:** 1  
**Max gaps acquired this run:** 5

## Phase 1 – Coverage Analysis
- 60 procedures analyzed.
- Source coverage derived from source_library records matched by procedure_id + inferred domains from facts/sections.
- Many v1 records contained legacy map text; v2 applies cleaning.

## Phase 2 – Gap Queue
- 213 total gaps (one per missing domain per procedure).
- Priority formula: (4 - readiness) × clinical_frequency × source_likelihood.
- Written to reports/source_gap_priority_queue.jsonl (ranked descending).

## Phase 3-4 – Acquisition & Extraction
- Candidates taken from router source_url + orthobullets_source_queue_v1.
- v2 library written with cleaned facts (legacy filtered) + references for top gaps.
- Live discovery not requested (used existing + candidates).
- No login, no protected content, no hammering.

## Phase 5 – Recalculation
- In-memory source_coverage_score updated for reporting.
- No modules or router mutated (this loop is source-only).

## Phase 6 – Dashboard
- Written to reports/source_coverage_dashboard.md (procs by score, top gaps, domain/type view, expected gains).

## Stopping condition
Not all procedures at source_coverage_score ≥3. Remaining gaps are listed in the priority queue (many require specific extraction from known pages or catalog-level approach cards that are not yet in the library).

**Repeatable:** Re-run the script after new source material is added to v2 or router is updated. It will re-analyze, re-rank, and (with --use-live) attempt targeted discovery on the new top of the queue.
