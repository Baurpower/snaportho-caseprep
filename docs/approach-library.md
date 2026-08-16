# Surgical Approach Library

The approach library is the source-aware backbone for CasePrep v3. It treats
an approach as reusable clinical content rather than a paragraph embedded in a
single procedure packet.

## Current inventory

The synchronized inventory contains public page metadata and deep links only:

- 575 AO Surgery Reference approach pages
- 66 Orthobullets approach pages
- 641 unique source pages total
- 405 human orthopaedic/spine pages in the authoring queue
- 102 CMF and 134 veterinary pages retained in the source registry but excluded
  from SnapOrtho CasePrep authoring

Inventory completeness does **not** imply clinical publication readiness.
Source-indexed records cannot be rendered as operative guidance.

## Files

- `source_registry.jsonl`: immutable source-page identity, scope, URL, and
  verification metadata. It contains no mirrored source prose or images.
- `approach_packets.jsonl`: conservative one-source seed identities. Ambiguous
  names remain separate.
- `authored_approach_packets.jsonl`: migrated reusable modules from the first
  CasePrep v3 approach packets.
- `procedure_mappings.jsonl`: many-to-many, conditional procedure mappings.
- `work_queue/`: deterministic batches for an authoring agent.
- `authored/`: validated clinical drafts imported from an authoring agent.
- `reviews/`: append-only, content-hash-bound independent review artifacts.

## Refresh the inventory

The online sync reads AO's public sitemap and the public Orthobullets approach
navigation. It obeys the source inventory boundary: metadata and links are
stored, source content is not mirrored.

```bash
.venv/bin/python scripts/sync_approach_library.py
.venv/bin/python scripts/audit_approach_library.py
```

Use `--offline` to regenerate derived files without network access.

## Authoring workflow

```bash
.venv/bin/python scripts/build_approach_work_queue.py --batch-size 20
.venv/bin/python scripts/compile_curated_approaches.py --check
.venv/bin/python scripts/compile_curated_approaches.py
```

The normal workflow is fully local to the Codex workspace. Concise original
syntheses live in `data/approach_library/curated/*.json`; the deterministic
compiler expands them into claim-bound packets in `authored/`. It makes no LLM
or external API calls. `import_approach_packet.py` remains available for a
manually prepared full-schema packet.

For AO pages, `read_ao_approach.py <url>` prints a temporary evidence brief
from the page's public structured payload. It does not save the source text;
the checked-in packet must remain an original synthesis. Rebuilding the work
queue excludes source pages already represented by authored packets.

Each agent-authored draft must:

1. use original synthesis rather than copied source prose;
2. include at least two independent sources;
3. attach every clinical claim to source identifiers;
4. attach high-risk claims to at least two sources;
5. leave uncertain fields unresolved rather than infer missing technique;
6. enter `agent_review_pending`, never self-publish.

## Publication gate

The exact packet content hash must pass these independent roles:

1. approach anatomy;
2. operative exposure;
3. procedure applicability;
4. evidence;
5. adversarial safety;
6. educational value.

Unresolved high/critical findings make a passing review invalid. Editing the
packet changes its content hash and invalidates previous reviews. Only packets
that pass schema, evidence, citation, and every review role become `published`.

## Copyright and provenance

AO and Orthobullets remain external sources. The library stores deep links and
original structured synthesis. It does not reproduce their illustrations,
tables, or page text. Orthobullets should not be the sole source for a
publishable packet; AO, peer-reviewed literature, or another authoritative
source is required.
