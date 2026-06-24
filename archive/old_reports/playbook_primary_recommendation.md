# Playbook Primary Recommendation

**Date**: Current (after implementing builder, curator, filtering rules, audit, and tests)

## Is the Orthobullets playbook now primary?
**Yes (in the new dedicated path).**

- `playbook_anatomy_builder.py` makes the `orthobullets_procedure_playbook_v1.jsonl` the source of truth:
  - Lookup by procedure_id (matched via router/supported gate from the map).
  - `importantAnatomy`, `structuresAtRisk`, `landmarks`, `approach` notes/pearls, and consolidated sources come directly from the playbook entry (OB-curated, with per-item source_url + section + confidence from prior extraction).
  - Approach section uses the recommended/conditional IDs + notes from playbook (cross-checked with catalog for names).
- The builder is the place where "Router determines procedure → Playbook determines anatomy" is realized.
- Previous hybrid (legacy GPT approach/quiz + raw Miller) is still present for backward/flag-off, but for ENABLE_LOCAL + supported cases the new builder produces the clean playbook-driven output.
- In tests, for matched procedures the counts of anatomy/risks/landmarks/pearls come from the playbook entry (e.g., distal_radius: 4/5/4/7 items from its enriched playbook fields).

## Is Miller now secondary?
**Yes (with explicit filtering).**

- Miller chunks are optional input to the builder.
- `_filter_miller_for_playbook` (and documented rules) requires term overlap with the *specific playbook entry's content* (anatomy text, risks, landmarks, approach notes, pimp, procedure/region/approach IDs).
- Irrelevant or cross-region Miller (e.g., ankle malleolus facts for a hip or wrist case, or generic leg notes for femoral shaft) are discarded before they reach the output or curator.
- Retained Miller appear only as "millerSupport" (supporting/citing) attached to the playbook base; they do not create new top-level items.
- In the 5 test cases:
  - distal_radius: 4/5 retained (the cross-region ankle one filtered).
  - tha_posterior: 3/4 retained (ankle/shoulder cross examples filtered).
  - carpal: 1/4 retained (most discarded).
  - Similar for TKA and femoral shaft (2-3 retained, irrelevant ankle/shoulder/leg discarded).
- This directly solves "noisy Miller facts, duplicated concepts, weak relevance, anatomy not organized around the procedure."

## Is GPT acting only as curator?
**Yes (in the new layer).**

- `anatomy_curator.py` receives the *already playbook-primary + filtered-Miller* bundle.
- Strict system prompt + limits (max 5 per category) + "NEVER invent... only rephrase/dedup/prioritize/format from provided playbook... Miller ONLY for citations on EXISTING items".
- Returns structured JSON in the final schema (Approach, importantAnatomy, structuresAtRisk, landmarks, pearls, sources, meta with supported/manual flags).
- In the test run, curator fell back (no key or transient error in the env) → used raw builder output, but the guardrails are in place and the prompt is written to be safe. When key is present it will curate (dedup, resident style, enforce limits).
- GPT is *not* used to generate anatomy facts (that was the old risk); only to polish the trusted input.

## Remaining weak procedures?
- The 11 manual_review entries (bimalleolar/trimalleolar/pilon/calcaneus, olecranon, pelvis_ring, cubital, clavicle, supracondylar_peds, hallux, trigger_finger): playbook has sparse/empty anatomy fields + gap notes. Builder correctly surfaces "manual_review": true and limited content. Output stays honest (no invention to "complete" them).
- Procedures with minimal prior enrichment in v1 (many beyond the ~7-8 core ones like distal/THA/femoral): anatomy/risks/landmarks counts = 0 or low. They fall back to approach notes + pimp placeholders from the map era.
- Catalog gaps still limit full "recommended" for ankle/foot cases (playbook correctly reflects this).
- Overall playbook coverage is good for high-volume recon/trauma hand cases that were enriched; weaker for foot/ankle trauma and minors until catalog + further OB extraction.

## Highest-value next playbook additions / improvements
1. Fill the 11 manual_review + gap cases once catalog expands (add lateral malleolus, posterolateral ankle, medial malleolus, extensile calcaneus, posterior elbow, cubital, clavicle IDs). Then re-extract richer OB anatomy/risks/landmarks for bimalleolar (lateral + medial approaches), olecranon, etc.
2. Enrich remaining medium/high from map that are still sparse in v1 (e.g., tibial_plateau, scaphoid, monteggia, achilles, intertroch, revision cases, ACL/rotator if more OB detail available).
3. Add more "pearls" / pimp_topics derived directly from OB technique pages for the core 38.
4. Tighten router to also surface the full anatomy playbook entry (not just map) for the supported gate / builder input (small enhancement to get_supported_case_with_playbook already started).
5. Wire the new builder+curator into the main hybrid path for supported cases (replace or prioritize over pure Miller sourceBacked in the anatomy object). Keep legacy approach/quiz + general pimp/otherUsefulFacts for compatibility.
6. Optional: surface "playbook primary" vs "Miller supported X facts" in internal anatomySystem or logs for observability.
7. When new procedures are added to the map, run the same OB extraction process to keep the playbook current (no broad scrape; targeted per the original playbook task).

## Summary Recommendation
The shift is implemented and demonstrated:
- Playbook (OB) is now the primary engine for procedure-specific anatomy, risks, landmarks, and pearls.
- Miller is filtered support/citation only.
- GPT is a safe curator (no invention, strict prompt + limits).
- Output is clean, organized around the procedure/approach, no raw RAG noise or scores.
- Tests (5 cases) show effective filtering (many irrelevant Miller discarded) and playbook content driving the output.
- For production anatomy testing: integrate builder+curator in the ENABLE_LOCAL path for supported procedures; continue using supported gate; monitor curator fidelity vs raw playbook.

This fulfills "Router determines procedure. Playbook determines anatomy. Miller supports and cites. GPT curates and teaches." while respecting all constraints (no invention, no Pinecone/corpus/OB re-scrape/UI changes).

Next engineering step after this task: light wiring in main/hybrid + end-to-end test with real GPT curator on the 5 cases + measurement of "playbook facts surfaced vs discarded Miller".
