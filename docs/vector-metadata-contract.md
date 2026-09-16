# Vector metadata contract (`ankiv3` index)

The scoping contract every namespace should honor so CasePrep/Chat retrieval can filter
consistently. Enforced by `scripts/audit_vector_metadata.py` (coverage thresholds).

## Scoping fields (all namespaces)

| Field | Type | Controlled? | Notes |
|---|---|---|---|
| `source_collection` | string | yes | `pocket_pimped` \| `millers` \| `miller_anatomy` \| `rock` |
| `schema_version` | string | yes | provenance of the metadata schema, e.g. `ankiv3-meta-v1`, `rock-v1` |
| `metadata_trust` | string | yes | `authored` \| `deterministic` \| `authored_plus_llm_v1` \| `llm_backfill_v1` |

## Content scoping (default + anatomy namespaces)

| Field | Type | Notes |
|---|---|---|
| `specialty` | string | controlled: peds, hand, trauma, sports, onc, footankle, basicscience, shoulderelbow, recon, spine, general |
| `region` | string | controlled anatomic region; `non-anatomic` for basic science |
| `procedures` | list[str] | canonical snake_case surgical-procedure slugs; empty ⇒ `procedures_none: true` |
| `diagnoses` | list[str] | canonical snake_case condition slugs; empty ⇒ `diagnoses_none: true` |

Canonical procedure/diagnosis slugs are normalized via `scripts/backfill_default_metadata.py`
(`canon_proc` / `canon_diag` + `PROC_SYNONYMS` / `DIAG_SYNONYMS`). Empty lists are stored as a
`<field>_none: true` sentinel because Pinecone rejects empty-list metadata values.

## Per-namespace specifics

- **`` (default)** — PocketPimp + Millers Q&A. Carries `question`, `answer`, `text`,
  `specialty`, `region`, `subregion`, `diagnoses`, `procedures`, `source`, `source_collection`.
- **`anatomy_miller_gold_v1`** — Miller anatomy gold. Rich anatomy sub-fields
  (`anatomy_muscle`, `anatomy_neurovascular`, `structures_at_risk`, …). These are legitimately
  sparse (a chunk with no muscle has none) and are NOT subject to coverage thresholds.
- **`rock-v1`** — ROCK chunks. `chapter_id`, `canonical_id`, `title`, `url`, `page_start/end`,
  `chunk_index`, `char_len`, `text`. See `../snaportho-web/docs/education/rock-v1-schema.md`.

## Coverage thresholds (audit asserts)

- default: `source_collection` = 100%, `specialty` ≥ 99%, `region` ≥ 99%,
  `procedures`+`diagnoses` present-or-sentinel on 100% (a card may legitimately have neither).
- anatomy: `source_collection` = 100%, `specialty`/`region` ≥ 99%.
- rock-v1: all core fields = 100% (already met).
