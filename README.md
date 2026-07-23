# SnapOrtho Case Prep

## Local bootstrap

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Python 3.12 is required. The pinned NumPy and Pydantic stack does not currently
build on Python 3.14.

Curated-only startup does not require OpenAI:

```bash
set -a
source .env
set +a
.venv/bin/uvicorn main:app --reload
```

## Checks

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python scripts/caseprep/validate_registry.py
.venv/bin/python scripts/caseprep/score_registry_coverage.py --check-only
```

Production must set `CASEPREP_ENV=production`, `CASEPREP_INTERNAL_API_KEY`, and
`CASEPREP_CORS_ORIGINS` to the comma-separated web origins allowed to call the API.

Case Prep web clients must explicitly call `POST /case-prep/v2`. The legacy
`POST /case-prep` route remains for older clients and is not part of the
curated-first contract.

## Website-only v1.1 preview

The faster Pocket-Pimp Q/A retriever is exposed only at
`POST /case-prep/web/v1.1` and requires `ENABLE_CASEPREP_WEB_V1_1=true`.
It uses one embedding, bounded parallel Pinecone queries, metadata-aware
reranking, and semantic deduplication. `POST /case-prep` never dispatches to
this engine, so unversioned and iOS clients retain the legacy contract.

### Pocket Pimp metadata migration

Preview the non-destructive metadata patch locally:

```bash
python3 scripts/caseprep/backfill_pocket_pimp_metadata.py --preview 3
```

Test a small live cohort before a full backfill:

```bash
python3 scripts/caseprep/backfill_pocket_pimp_metadata.py --limit 25 --apply
```

Only after the live metadata is audited should
`CASEPREP_POCKET_PIMP_METADATA_READY=true` be enabled. Until then v1.1 runs a
Pocket-Pimp-filtered query alongside migration-safe scoped queries.

### Retrieval benchmark

Run the seed clinical benchmark against configured services:

```bash
python3 scripts/caseprep/benchmark_v1_1_retrieval.py --live --output /tmp/caseprep-v1-1-report.json
```

Use `--check` to enforce the default release gates (90% required-term recall,
70% top-k relevance, zero contamination/empty results, and <=4s worst-case latency).

The gold set lives at
`data/caseprep/evaluation/pocket_pimp_retrieval_gold_v1.jsonl` and should be
expanded through clinical review before rollout decisions are made.
