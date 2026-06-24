# Anatomy Legacy Archive

This directory documents and quarantines transitional / legacy anatomy artifacts from the pre-v1 modular anatomy database era.

**Canonical v1 anatomy now lives exclusively at:**
`data/anatomy/`

## Runtime Contract
- All BroBot /anatomy and case-prep certified flows MUST use only files under `data/anatomy/`.
- `procedure_registry.py` resolver, `main.py` short-circuit logic, and `approach_router.py` (via resolver) are updated to prefer canonical v1.
- Old paths (see below) are **not loaded** for certified case-prep payloads or procedure resolution in the new flow.
- Approach selection maps (in `data/approach_playbook/`) may still be referenced by legacy hybrid/approach router code for non-certified or approach-only logic; this is separate from the BroBot case-prep certified payload surface.

## What was archived / ignored (preserved in git history)
- All `data/approach_playbook/brobot_anatomy_router_v1*` except the source for v1 copy.
- All `data/anatomy_modules/*_v1`, `*_v1_1`, `*_v1_2`, `*_v1_3` (only *_v1_4 mapped to clean names).
- `data/anatomy_sources/source_library_v1.jsonl`, `v2.jsonl`, old queues/logs (only v3 mapped).
- `data/anatomy_integration/*` (source of the v1 case_prep/ and registry/ copies).
- Old reports: `brobot_anatomy_*_v1_*.md`, freeze lists, gap queues, leaderboards, audits, etc. (key recent ones selectively copied to `data/anatomy/reports/` for reference; most historical in root `reports/`).
- `data/anatomy_miller_gold_v1/`, many miller/hybrid/pinecone old artifacts.
- Old playbooks v1/v2 yaml/jsonl, procedure_to_approach_map v1/v2, etc.
- Source coverage scripts and intermediate gap queues not promoted.

**Do not delete these** – they are the audit trail. Recover via `git checkout` if needed for migration or archaeology.

## Why the reset?
- Accumulated v1/v1_1/...v1_4, source v2/v3, multiple integration passes.
- Risk of legacy placeholder text ("Key approach for this case per OB and map?", "Per map evidence", "Primary structure at risk?", "No free-form guessing", "unknown or uncertain type") leaking into resident-facing BroBot output.
- Inconsistent runtime paths making it hard to know "what is the source of truth".
- Future scaling (more procedures, more modules, BroBot prod) requires obvious layout.

## Next steps after this v1
See `data/anatomy/reports/integration_readiness.md` and the migration report in root `reports/`.

Runtime validation/smoke tests live in `scripts/anatomy/validate_clean_anatomy_v1.py` and `smoke_test_anatomy_runtime.py`.

**If you see old paths in logs or output for certified procedures after this change: bug – fix immediately.**
