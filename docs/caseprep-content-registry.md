# CasePrep Content Registry

Per-procedure folders under `data/caseprep/procedures/` power Phase 2 (Procedure Registry) and Phase 3 (Content Status System).

Runtime **only serves** procedures where:

- `content_status=certified`
- `review_status=certified`
- `runtime_enabled=true`
- `certified_payload.json` exists

Draft, partial, and missing content are **never** served to `/case-prep/v2`.

## Folder structure

```
data/caseprep/procedures/<procedure_slug>/
  manifest.json           # Registry metadata + status
  aliases.json            # Display name + alias strings
  sources.jsonl           # Source URLs / provenance
  modules.json            # Editable authoring sections
  certified_payload.json  # Runtime payload (certified only)
  review_notes.md         # Human QA notes
```

Generated indexes (do not edit by hand):

```
data/caseprep/registry_index.json
data/caseprep/alias_index.json
data/caseprep/certified_payloads_export.jsonl
```

## manifest.json fields

| Field | Description |
|-------|-------------|
| `slug` | Canonical procedure id (must match folder name) |
| `display_name` | Human-readable name |
| `specialty` | e.g. trauma, adult_reconstruction |
| `body_region` | e.g. hip, wrist |
| `procedure_family` | e.g. arthroplasty, trauma_orif |
| `status` | `active` or lifecycle status |
| `content_status` | Content completeness (see below) |
| `review_status` | QA workflow state (see below) |
| `version` | Registry folder version |
| `caseprep_schema_version` | Payload schema e.g. `brobot_case_prep_payload_v2` |
| `coverage_score` | 0–100 automated section coverage |
| `runtime_enabled` | If true + certified, payload may be served |
| `deprecated` | If true, must set `replacement_slug` |
| `replacement_slug` | Successor procedure when deprecated |
| `reviewer` | Who certified (required when certified) |
| `certified_at` | ISO timestamp |
| `last_reviewed_at` | ISO timestamp |
| `source_payload_hash` | SHA256 of certified_payload.json |

### content_status

| Value | Meaning |
|-------|---------|
| `missing` | No usable content |
| `draft` | Work in progress |
| `partial` | Some modules populated |
| `complete` | Ready for clinical review |
| `certified` | Approved for runtime |
| `deprecated` | Replaced; do not serve |

### review_status

| Value | Meaning |
|-------|---------|
| `unreviewed` | Not reviewed |
| `ai_drafted` | AI-generated draft |
| `resident_review` | Resident reviewed |
| `attending_review` | Attending reviewed |
| `certified` | Signed off for runtime |
| `needs_revision` | Failed QA; fix required |

## Migrate from flat JSONL

One-time / idempotent migration from `data/anatomy/`:

```bash
python3 scripts/caseprep/migrate_flat_payloads_to_registry.py
# Overwrite manual edits only when intentional:
python3 scripts/caseprep/migrate_flat_payloads_to_registry.py --force
```

## Add a new procedure

1. Create folder: `data/caseprep/procedures/<slug>/`
2. Add `manifest.json` with `content_status=draft`, `review_status=unreviewed`, `runtime_enabled=false`
3. Add `aliases.json`, empty `sources.jsonl`, `modules.json`, `review_notes.md`
4. Author content in `modules.json`
5. Run scoring + validation

## modules.json sections (clinical order)

| Key | Label | Notes |
|-----|-------|-------|
| `indications` | Indications | Clinical indication bullets (required for new certification) |
| `setup_positioning` | Setup & Positioning | |
| `approach_landmarks` | Approach & Landmarks | |
| `surgical_layers` | Surgical Layers | |
| `structures_at_risk` | Structures at Risk | |
| `implant_strategy` | Implant Strategy | Optional |
| `reduction_or_fluoro_checkpoints` | Reduction / Fluoro Checkpoints | Optional |
| `pitfalls` | Pitfalls | |
| `attending_pimp_questions` | Attending Pimp Questions | |
| `postop_plan` | Post-op Protocol | Weight-bearing, immobilization, DVT, activity restrictions — **not** a night-before checklist |

Coverage weights sum to **120**; `score_modules` clamps the total to **100**.

### Indications transition (2026)

Existing certified procedures may have `indications: []`. Validation emits a **warning** (not a blocking error) until content is authored. Run:

```bash
python3 scripts/caseprep/add_indications_section.py
```

## Certify a procedure

1. Complete `modules.json` sections (see coverage weights in `registry_lib.py`)
2. Build or copy final payload to `certified_payload.json`
3. Update manifest:
   - `content_status=certified`
   - `review_status=certified`
   - `runtime_enabled=true`
   - `reviewer`, `certified_at`, `source_payload_hash`
4. Run:

```bash
python3 scripts/caseprep/score_registry_coverage.py
python3 scripts/caseprep/validate_registry.py
python3 scripts/caseprep/build_registry_index.py
```

## Scripts

| Script | Purpose |
|--------|---------|
| `migrate_flat_payloads_to_registry.py` | Flat JSONL → per-procedure folders |
| `add_indications_section.py` | Backfill `indications: []` into modules.json (idempotent) |
| `score_registry_coverage.py` | Write `coverage_score` to manifests |
| `build_registry_index.py` | Build registry + alias indexes + export JSONL |
| `validate_registry.py` | QA gate (exit nonzero on error) |
| `generate_registry_dashboard.py` | `docs/caseprep-registry-dashboard.md` |

```bash
python3 scripts/caseprep/score_registry_coverage.py
python3 scripts/caseprep/build_registry_index.py
python3 scripts/caseprep/validate_registry.py
python3 scripts/caseprep/generate_registry_dashboard.py
```

Use `--allow-low-coverage` on validate during transition if certified scores are still being improved.

## Runtime loading (`curated_content_store.py`)

Load order:

1. Registry folders (`certified_payload.json` + certified manifest)
2. `certified_payloads_export.jsonl`
3. Legacy `data/anatomy/case_prep/certified_case_prep_payloads.jsonl`

`GET /health` → `curated_store.source` is `registry`, `registry_export`, `flat_jsonl`, or `none`.

v1 `/case-prep` does **not** use the registry. v2 uses it only for certified runtime-enabled procedures.