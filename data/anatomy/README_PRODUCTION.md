# data/anatomy/ - PRODUCTION ONLY

This directory is the canonical production source for BroBot certified anatomy case-prep.

## Rules
- All runtime code (main.py, procedure_registry.py, validate/smoke scripts) MUST read ONLY from here for certified payloads, aliases, registry, modules, sources.
- Do NOT import or load anything from data/approach_playbook/, old anatomy_* dirs, or archive/ for production certified paths.
- Development / extraction / old versions live in archive/ or (if needed) data/anatomy/development/ (currently minimal).
- Before promoting new payload: run scripts/anatomy/audit_payloads.py + validate_clean + smoke_test.
- All files here should pass the v2 schema and no-legacy checks.

See PRODUCTION_MANIFEST.json for current certified list and status.
See case_prep/ for the 24 hardened payloads (brobot_case_prep_payload_v2).
See registry/ for procedures, aliases (with is_certified), certification.
