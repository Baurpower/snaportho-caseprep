# CasePrep v1.2 — real-case quality audit

Evaluated: 2026-08-23T16:56:34.327982+00:00  
Endpoint: `http://127.0.0.1:8013/case-prep/web/v1.2/stream`  
Cohort source: `artifacts/caseprep-v1.2/real-cases-100-2026-08-15-complete.json`. User IDs and historical answers are excluded.

## Executive metrics

- Completed: 100/100; fatal failures: 0
- Confirmed expected-version responses: 100/100 (100%); observed: `{"v1.2": 100}`
- Valid procedure resolution: 95/100 (95%); clarifications: 5; unresolved slugs: 20
- Prompt/slug region mismatches: 0
- Zero pimp-question packets: 6/100 (6%); packets with 8+: 88/100 (88%)
- Pimp questions: mean 13.45, median 15.0
- Packets with citations: 94/100 (94%)
- Empty/malformed content: 0/0 packets
- Section errors: 0/100 (0%)
- Latency: median 1569 ms, p90 3009 ms, p95 3136 ms, max 3412 ms
- Transparent utility score: mean 87.3/100, median 91.0/100, p10 83/100

Quality gates: `{"limited": 7, "passed": 88, "withheld": 5}`  
Coverage: `{"clarification_required": 5, "grounded_complete": 92, "grounded_partial": 2, "unavailable": 1}`  
Omitted sections: decision_points: 100, postop: 100, approach_quick_brief: 91, approach_exposure: 91, approach_safety: 91, approach_strategy: 91, summary: 63, key_takeaways: 63, top_things_to_know: 63, anatomy: 63, operative_flow: 63, evidence: 63, approach_decision: 39, pimp_questions: 6

The utility score weights valid, region-consistent resolution (20), reliable transport (10), eight pimp questions (20), direct procedure relevance (15), direct claim support (15), eleven-section breadth (10), and the stream quality gate (10). It is a triage measure, not a clinical-validity score.

## Lowest-scoring cases for clinical review

| Response | Score | Pimp | Gate | Prompt |
|---:|---:|---:|---|---|
| 907 | 10 | 0 | withheld | Tia |
| 922 | 10 | 0 | withheld | Right car |
| 923 | 10 | 0 | withheld | Total hip and total knee arthroplasty |
| 995 | 10 | 0 | withheld | undifferentiated pleomorphic sarcoma |
| 998 | 10 | 0 | withheld | ACL reconstruction laparoscopic |
| 969 | 35 | 0 | limited | Orif left distal humerus |
| 902 | 71 | 2 | limited | cement spacer for infected TKA |
| 946 | 74 | 3 | limited | Infected total shoulder |
| 959 | 83 | 5 | limited | Supracondylar humerus fracture |
| 960 | 83 | 5 | limited | Supracondylar humerus fractures |
| 985 | 83 | 5 | limited | Orif humeral shaft |
| 986 | 83 | 5 | limited | Orif humeral shaft middiaohaseal |
| 900 | 91 | 15 | passed | ORIF proximal tibia |
| 901 | 91 | 15 | passed | Knee arthroplasty |
| 905 | 91 | 15 | passed | Bimalleolar ankle fracture ORIF |

## Most frequent warnings

- 95× Query refinement degraded: Connection error.
- 26× Which approach should I prepare? Select one or more; I can compare approaches side by side.

## Interpretation boundary

This automated audit measures resolution, output completeness, provenance metadata, citations, and operational reliability. It does not prove factual clinical correctness. The JSON artifact preserves the generated pimp questions and answers for targeted expert review, without user identifiers.
