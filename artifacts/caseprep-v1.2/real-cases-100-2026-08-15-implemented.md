# CasePrep V1_2 — newest 100 real-case audit

Evaluated: 2026-08-15T21:03:30.939258+00:00  
Endpoint: `http://127.0.0.1:8012/case-prep/web/v1.2/stream`  
Cohort: newest non-empty `question` rows from `public.brobot_user_responses`, ordered by `created_at DESC, response_id DESC`. User IDs and historical answers were not fetched.

## Executive metrics

- Completed: 100/100; fatal failures: 0
- Confirmed V1_2 responses: 100/100 (100%)
- Valid procedure resolution: 95/100 (95%); clarifications: 5; unresolved slugs: 13
- Zero pimp-question packets: 6/100 (6%); packets with 8+: 74/100 (74%)
- Pimp questions: mean 9.64, median 10.0
- Packets with citations: 94/100 (94%)
- Empty/malformed content: 0/0 packets
- Section errors: 0/100 (0%)
- Latency: median 1530 ms, p90 2530 ms, p95 2898 ms, max 3671 ms
- Transparent utility score: mean 73.1/100, median 85.0/100, p10 41/100

Quality gates: `{"limited": 52, "passed": 43, "withheld": 5}`  
Coverage: `{"certified": 34, "clarification_required": 5, "grounded_complete": 50, "grounded_partial": 10, "unavailable": 1}`  
Omitted sections: postop: 97, decision_points: 94, summary: 56, key_takeaways: 56, top_things_to_know: 56, anatomy: 56, operative_flow: 56, teaching_topics: 56, pitfalls: 56, evidence: 56, pimp_questions: 6

The utility score weights resolution (20), reliable transport (10), eight pimp questions (20), direct procedure relevance (15), direct claim support (15), eleven-section breadth (10), and the V1_2 quality gate (10). It is a triage measure, not a clinical-validity score.

## Lowest-scoring cases for clinical review

| Response | Score | Pimp | Gate | Prompt |
|---:|---:|---:|---|---|
| 907 | 10 | 0 | withheld | Tia |
| 922 | 10 | 0 | withheld | Right car |
| 923 | 10 | 0 | withheld | Total hip and total knee arthroplasty |
| 995 | 10 | 0 | withheld | undifferentiated pleomorphic sarcoma |
| 998 | 10 | 0 | withheld | ACL reconstruction laparoscopic |
| 954 | 35 | 0 | limited | Hip disarticulation |
| 902 | 38 | 1 | limited | cement spacer for infected TKA |
| 940 | 38 | 1 | limited | tillaux fx vs chaput fx |
| 962 | 41 | 2 | limited | Bilateral hip dislocation with left subtroch fracture |
| 963 | 41 | 2 | limited | Bilateral hip dislocation with left subtroch fracture |
| 971 | 41 | 2 | limited | Osteochondral defect/possible impingement  foot ankle scope |
| 968 | 44 | 3 | limited | lateral interbody fusion |
| 978 | 51 | 6 | limited | Glenoid fx with extension into scapula body |
| 900 | 56 | 8 | limited | ORIF proximal tibia |
| 917 | 56 | 8 | limited | Triceps tendon repair |

## Most frequent warnings

- None

## Interpretation boundary

This automated audit measures resolution, output completeness, provenance metadata, citations, and operational reliability. It does not prove factual clinical correctness. The JSON artifact preserves the generated pimp questions and answers for targeted expert review, without user identifiers.
