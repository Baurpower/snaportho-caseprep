# CasePrep V1_2 — newest 100 real-case audit

Evaluated: 2026-08-15T20:58:03.079397+00:00  
Endpoint: `http://127.0.0.1:8012/case-prep/web/v1.2/stream`  
Cohort: newest non-empty `question` rows from `public.brobot_user_responses`, ordered by `created_at DESC, response_id DESC`. User IDs and historical answers were not fetched.

## Executive metrics

- Completed: 100/100; fatal failures: 0
- Confirmed V1_2 responses: 100/100 (100%)
- Valid procedure resolution: 99/100 (99%); clarifications: 1; unresolved slugs: 14
- Zero pimp-question packets: 6/100 (6%); packets with 8+: 76/100 (76%)
- Pimp questions: mean 9.52, median 9.0
- Packets with citations: 94/100 (94%)
- Empty/malformed content: 0/0 packets
- Section errors: 1/100 (1%)
- Latency: median 1400 ms, p90 2303 ms, p95 2692 ms, max 4574 ms
- Transparent utility score: mean 76.1/100, median 85.0/100, p10 41/100

Quality gates: `{"limited": 23, "passed": 76, "withheld": 1}`  
Coverage: `{"certified": 37, "clarification_required": 1, "grounded_complete": 47, "grounded_partial": 10, "unavailable": 5}`  
Omitted sections: postop: 97, decision_points: 94, summary: 55, key_takeaways: 55, top_things_to_know: 55, anatomy: 55, operative_flow: 55, teaching_topics: 55, pitfalls: 55, evidence: 55, pimp_questions: 6

The utility score weights resolution (20), reliable transport (10), eight pimp questions (20), direct procedure relevance (15), direct claim support (15), eleven-section breadth (10), and the V1_2 quality gate (10). It is a triage measure, not a clinical-validity score.

## Lowest-scoring cases for clinical review

| Response | Score | Pimp | Gate | Prompt |
|---:|---:|---:|---|---|
| 998 | 10 | 0 | withheld | ACL reconstruction laparoscopic |
| 907 | 35 | 0 | limited | Tia |
| 922 | 35 | 0 | limited | Right car |
| 938 | 35 | 0 | limited | thumb ligament reconstruction and tendon interposition |
| 954 | 35 | 0 | limited | Hip disarticulation |
| 995 | 35 | 0 | limited | undifferentiated pleomorphic sarcoma |
| 940 | 38 | 1 | limited | tillaux fx vs chaput fx |
| 902 | 41 | 2 | limited | cement spacer for infected TKA |
| 941 | 41 | 2 | limited | Posterior fusion for scoliosis |
| 971 | 41 | 2 | limited | Osteochondral defect/possible impingement  foot ankle scope |
| 976 | 41 | 2 | limited | Help me prepare for a posterior cervical fusion C2 to t1 |
| 977 | 41 | 2 | limited | Help me prepare for a posterior cervical fusion C2 to t1 |
| 968 | 44 | 3 | limited | lateral interbody fusion |
| 936 | 54 | 4 | limited | Hip arthroscopy |
| 900 | 61 | 8 | passed | ORIF proximal tibia |

## Most frequent warnings

- 1× Pocket Pimped retrieval failed: 

## Interpretation boundary

This automated audit measures resolution, output completeness, provenance metadata, citations, and operational reliability. It does not prove factual clinical correctness. The JSON artifact preserves the generated pimp questions and answers for targeted expert review, without user identifiers.
