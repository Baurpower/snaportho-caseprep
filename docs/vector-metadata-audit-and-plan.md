# Vector DB metadata — audit + remediation plan

Index: `ankiv3` (dim 1536, cosine). Audit tool: `scripts/audit_vector_metadata.py`
(re-runnable; baseline snapshot in `scripts/vector_metadata_audit.json`, dated 2026-09-16).

## What's actually in the index (3 namespaces, 15,832 vectors)

| Namespace | Vectors | Content | Prefix | Health |
|---|---|---|---|---|
| `` (default) | 2,638 | PocketPimp (1,461) + Millers (1,177) Q&A | `pp-` | **Poor — the main problem** |
| `anatomy_miller_gold_v1` | 717 | Miller's anatomy gold chunks | `miller` | Good (minor gaps) |
| `rock-v1` | 12,477 | ROCK curriculum chunks | (none) | Clean (0 empties) |

> Correction to prior notes: the "ankiv3 vectors" that lack `procedures`/`source_collection`
> ARE the default namespace (pp + millers). There is no separate raw-Anki-card namespace here.

## Findings, ranked by impact on CasePrep/Chat retrieval

### P0 — Default namespace has NO `source_collection` field at all
Every scoped retrieval in `caseprep/services/rag_retrieval.py` keys off `source_collection`,
but the default namespace never sets it. The code papers over this with a brittle slug guess
(`"pocketpimp" in _slug(source)`), which works for PocketPimp and **silently fails for Millers**
(1,177 vectors). This is a direct cause of the rescue-mode `semantic_fallback` firing and the
retrieval recall gate sitting at 0.50.

### P1 — `procedures` is 89% empty in the default namespace (2,346 / 2,638)
Only 292 vectors carry any procedure tag. CasePrep packets are procedure-anchored, so the
procedure-scoped branch matches almost nothing and falls back to semantic search. Existing
values are canonical snake_case (`tka`, `tha`, `orif`, `acl_reconstruction`, `tibial_imn`…),
so a backfill must emit the SAME controlled vocabulary, not free text.

### P2 — Other scope fields sparse in default namespace
`diagnoses` 50% empty (1,329), `subregion` 82% empty (2,168), `specialty2` 93% empty (2,460).
`specialty`/`region` are effectively complete (7 and 0 empty) and usable today.

### P3 — Schema drift across namespaces (no shared contract)
- `source_collection` exists only in `rock-v1`.
- Field naming differs: default uses `diagnoses` (plural, list); anatomy uses none; there's
  no single scoping contract any consumer can rely on.
- `anatomy_miller_gold_v1`: ~5.4% (≈39 vectors) missing `specialty`/`region`; no
  `source_collection`. Its anatomy sub-field "empties" (e.g. `anatomy_muscle` empty on 566)
  are **legitimate** — a chunk with no muscle has no muscle tag — do not "fix" those.

## Remediation plan

Guiding principle: **metadata-only updates, no re-embedding.** Use
`index.update(id=..., set_metadata={...}, namespace=...)` — vectors are untouched, so this is
cheap and reversible. The only real cost is the LLM extraction pass for P1/P2.

### Phase A — Define the unified metadata contract (write it down first)
Canonical scoping fields every namespace must carry:
- `source_collection` (controlled: `pocketpimp` | `millers` | `miller_anatomy` | `rock`)
- `specialty`, `region` (existing controlled vocabs — already consistent)
- `diagnoses` (list, canonical), `procedures` (list, canonical snake_case)
- provenance: `schema_version`, `metadata_trust` (e.g. `authored` | `llm_backfill_v1` | `deterministic`), `corpus_version`
Deliverable: `docs/vector-metadata-contract.md` + a validator in `scripts/audit_vector_metadata.py`
that asserts per-namespace coverage thresholds.

### Phase B — Backfill the default namespace (the priority)
1. **`source_collection` (deterministic, zero-risk):** map `source` → collection
   (`pocket pimped`→`pocketpimp`, `millers`→`millers`). Update all 2,638 in place. Ship this alone first.
2. **`procedures` + `diagnoses` (LLM extraction, controlled-vocab constrained):**
   - For each card, feed `question`+`answer` to an extractor that returns candidate procedures/diagnoses.
   - Resolve each candidate to canonical via the existing registry — `procedure_registry.resolve_procedure`
     (wrapped by `caseprep/services/procedure_resolver.py`) + alias files under
     `data/caseprep/` (`alias_index.json`, per-procedure `aliases.json`), and the diagnosis vocab.
   - Keep only confident, resolvable matches; **leave empty rather than guess** (a basic-science
     card legitimately has no procedure). Stamp `metadata_trust: llm_backfill_v1`.
   - Run as `--dry-run` (writes proposed tags to a sidecar for review) → `--apply` (updates in place),
     mirroring the ROCK build-job pattern.
3. Backfill `subregion` opportunistically from `region`+text where cheap; `specialty2` is low value — defer.

### Phase C — Patch `anatomy_miller_gold_v1`
Fill the ~39 missing `specialty`/`region` (deterministic from `section_path`/`heading` where
possible, else LLM). Add `source_collection: miller_anatomy`. Do not touch anatomy sub-fields.

### Phase D — Simplify retrieval to trust the contract
Once `source_collection` is universal, remove the slug-inference hack in `rag_retrieval.py`
and scope purely on `source_collection`. Add the `rock` branch here (ties into the ROCK
runtime-integration plan). This is where the recall gate should recover.

### Phase E — Validate + re-audit
- Re-run `scripts/audit_vector_metadata.py`; assert: default `source_collection` 100%,
  `procedures` present on the procedural subset, 0 unexpected empties.
- Re-run the CasePrep retrieval gold set; confirm recall lifts off 0.50 and the semantic_fallback
  rate drops.

## Suggested sequencing
B.1 (deterministic `source_collection`) is a same-day, zero-risk win that alone should help
Millers scoping and the recall gate. B.2 (LLM procedure/diagnosis backfill) is the larger
effort and the highest functional payoff for procedure-anchored CasePrep. A and E bracket the work.
