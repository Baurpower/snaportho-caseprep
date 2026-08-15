# CasePrep V1_2 — newest 100 real-case audit

Evaluated: 2026-08-15T21:00:36.771932+00:00  
Endpoint: `http://127.0.0.1:8012/case-prep/web/v1.2/stream`  
Cohort: newest non-empty `question` rows from `public.brobot_user_responses`, ordered by `created_at DESC, response_id DESC`. User IDs and historical answers were not fetched.

## Executive metrics

- Completed: 100/100; fatal failures: 0
- Confirmed V1_2 responses: 100/100 (100%)
- Valid procedure resolution: 98/100 (98%); clarifications: 2; unresolved slugs: 14
- Zero pimp-question packets: 6/100 (6%); packets with 8+: 73/100 (73%)
- Pimp questions: mean 9.18, median 9.0
- Packets with citations: 94/100 (94%)
- Empty/malformed content: 0/0 packets
- Section errors: 0/100 (0%)
- Latency: median 1484 ms, p90 2430 ms, p95 2913 ms, max 3904 ms
- Transparent utility score: mean 73.4/100, median 83.0/100, p10 41/100

Quality gates: `{"limited": 55, "passed": 43, "withheld": 2}`  
Coverage: `{"certified": 35, "clarification_required": 2, "grounded_complete": 47, "grounded_partial": 12, "unavailable": 4}`  
Omitted sections: postop: 97, decision_points: 94, summary: 56, key_takeaways: 56, top_things_to_know: 56, anatomy: 56, operative_flow: 56, teaching_topics: 56, pitfalls: 56, evidence: 56, pimp_questions: 6

The utility score weights resolution (20), reliable transport (10), eight pimp questions (20), direct procedure relevance (15), direct claim support (15), eleven-section breadth (10), and the V1_2 quality gate (10). It is a triage measure, not a clinical-validity score.

## Lowest-scoring cases for clinical review

| Response | Score | Pimp | Gate | Prompt |
|---:|---:|---:|---|---|
| 923 | 10 | 0 | withheld | Total hip and total knee arthroplasty |
| 998 | 10 | 0 | withheld | ACL reconstruction laparoscopic |
| 907 | 35 | 0 | limited | Tia |
| 922 | 35 | 0 | limited | Right car |
| 954 | 35 | 0 | limited | Hip disarticulation |
| 995 | 35 | 0 | limited | undifferentiated pleomorphic sarcoma |
| 902 | 38 | 1 | limited | cement spacer for infected TKA |
| 940 | 38 | 1 | limited | tillaux fx vs chaput fx |
| 981 | 38 | 1 | limited | Calcaneal tuberosity avulsion fracture |
| 941 | 41 | 2 | limited | Posterior fusion for scoliosis |
| 963 | 41 | 2 | limited | Bilateral hip dislocation with left subtroch fracture |
| 971 | 41 | 2 | limited | Osteochondral defect/possible impingement  foot ankle scope |
| 976 | 41 | 2 | limited | Help me prepare for a posterior cervical fusion C2 to t1 |
| 977 | 41 | 2 | limited | Help me prepare for a posterior cervical fusion C2 to t1 |
| 968 | 44 | 3 | limited | lateral interbody fusion |

## Most frequent warnings

- None

## Interpretation boundary

This automated audit measures resolution, output completeness, provenance metadata, citations, and operational reliability. It does not prove factual clinical correctness. The JSON artifact preserves the generated pimp questions and answers for targeted expert review, without user identifiers.
