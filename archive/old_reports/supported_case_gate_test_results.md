# Supported Case Gate Test Results
Generated: 2026-06-06T03:56:15.255681+00:00
Total: 9 | Passed: 9 | Failed: 0

## Key assertions
- Unsupported: supported=false, approachSelection null, retrievalMode=not_run_unsupported_case, limited=true
- Supported: approach/quiz present, Miller runs with gold mode
- Gap cases (manual_review/empty rec): supported=false
- Debug var bypasses Miller gate
- /case-prep pimp/other still present

- PASS | A_unsupported_tibial | tibial shaft fracture ORIF... | {"supported_from_gate": false, "mode": "not_run_unsupported_case", "approach_null": true}
- PASS | A_unsupported_random | random ankle pain after soccer... | {"supported_from_gate": false, "mode": "not_run_unsupported_case", "approach_null": true}
- PASS | A_unsupported_forearm | forearm pain no fracture... | {"supported_from_gate": false, "mode": "not_run_unsupported_case", "approach_null": true}
- PASS | B_supported_distal | distal radius fracture ORIF... | {"supported_from_gate": true, "mode": "miller_gold_local", "has_approach": true}
- PASS | B_supported_carpal | carpal tunnel release... | {"supported_from_gate": true, "mode": "miller_gold_local", "has_approach": true}
- PASS | B_supported_tha | posterior THA... | {"supported_from_gate": true, "mode": "miller_gold_local", "has_approach": true}
- PASS | C_gap_bimalleolar | bimalleolar ankle fracture ORIF... | {"supported": false, "reason": "manual_review (catalog gap or pending review per playbook)", "mode": "not_run_unsupported_case"}
- PASS | D_debug_override_miller | tibial shaft fracture ORIF... | {"mode": "miller_gold_local"}
- PASS | E_caseprep_unsupported | tibial shaft fracture ORIF... | {"has_pimp": true, "anatomy_mode": "not_run_unsupported_case"}

See JSON for full details.
