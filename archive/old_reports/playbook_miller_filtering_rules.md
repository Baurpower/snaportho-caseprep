# Playbook Miller Filtering Rules

**Purpose**: Before any Miller facts reach the GPT curator or final output, apply strict relevance filtering so that only supporting/citing facts from the Orthobullets playbook are retained. Miller is never primary and never introduces new anatomy.

## Core Rules (enforced in playbook_anatomy_builder.py _filter_miller_for_playbook and/or pre-curator step)

1. **Term Overlap Requirement** (mandatory):
   - Collect a set of key terms from the matched playbook entry:
     - procedure_id (normalized, e.g. "distal radius fracture orif")
     - region
     - all recommended/conditional approach_ids (normalized, e.g. "wrist volar distal henry")
     - text from important_anatomy, structures_at_risk (structure + why), landmarks (landmark + why), approach_notes, pimp_topics.
   - A Miller chunk (text + source_quote + heading + region/subregion) must contain at least 1 (ideally 2+) exact or stemmed overlap with the term set.
   - Chunks with 0 overlap are discarded.

2. **Procedure / Approach Specificity**:
   - Chunk must be consistent with the selected procedure_id and at least one recommended/conditional approach_id.
   - Example: for "distal_radius_fracture_orif" + "approach_wrist_volar_distal_henry", keep volar FCR/PQ details, watershed line, median palmar branch, etc. Discard pure ankle or hip facts even if "radius" or "volar" appears coincidentally.

3. **Region / Subregion Guard**:
   - If the chunk has explicit region/subregion metadata and it does not match the playbook entry's region (or a directly related one via the approach), require higher overlap (>=2) to retain.
   - Cross-region (e.g., "ankle" chunk for "femoral_shaft" case) is discarded unless extremely strong direct support of a playbook item.

4. **Miller-Only vs Playbook Override**:
   - Never use a Miller fact that contradicts or extends beyond a playbook item.
   - Miller facts are attached only as "supporting" / citations (e.g., extra quote or page reference under an existing playbook anatomy/risk/landmark/pearl).
   - If a Miller chunk would introduce a brand-new concept not present in the playbook entry, discard it (even if relevant to the broad anatomic area).

5. **Quality / Confidence Heuristics** (secondary):
   - Prefer chunks with higher retrieval score (but do not expose scores to user).
   - Prefer chunks whose source_quote or text closely matches phrasing in the playbook's OB sources.
   - Discard very low-score or very short/generic chunks.
   - For manual_review playbook entries: apply even stricter filtering (or skip Miller entirely unless debug override).

6. **Deduplication**:
   - After overlap filter, dedup Miller chunks by normalized signature (first 120 chars of text/quote).
   - When merging into playbook items, avoid duplicating text that is already in the playbook's important_anatomy etc.

7. **Unsupported / Low-Confidence Playbook Entries**:
   - For entries with manual_review=true or empty important_* fields: Miller facts are not used to "fill in" missing anatomy. The output stays limited/gap-noted. Miller may still provide general region support only if it overlaps existing (sparse) playbook content.

## Implementation Notes
- Filtering happens in `playbook_anatomy_builder.py` (see _filter_miller_for_playbook) before returning millerSupport list.
- The curator (anatomy_curator.py) receives the already-filtered millerSupport + full playbook fields and must further respect "use only to support existing playbook items".
- This prevents the "irrelevant Miller from ankle/hip/hand for tibial shaft" problem.
- Rules are conservative by design: better to return clean (possibly shorter) playbook-driven anatomy than noisy RAG output.
- Debug: ANATOMY_ALLOW_UNSUPPORTED_RETRIEVAL or similar can bypass for testing, but never in normal production flow for unsupported cases.

These rules + the playbook as primary + strict curator prompt ensure GPT curates/teaches within bounds and Miller only supports/cites.
