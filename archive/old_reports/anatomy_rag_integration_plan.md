# Anatomy RAG Integration Plan — Dedicated Miller Gold Retrieval for BroBot / CasePrep

**Status**: Audit-complete, plan only. **Do not execute edits/uploads here.**
**Date**: 2026-06-05
**Inputs**: current_rag_pipeline_audit.md, anatomy_pipeline gold corpus + reports (canonical_gold_v1_recommendation.md, anatomy_gold_v1_pinecone_ready_report.md, evals, local indexes, seed_cases), CasePrep source, web BroBot UI/types/proxy.
**Goal**: Practical, staged path from current (catalog-GPT anatomy + mixed general RAG) to dedicated, source-backed Miller gold anatomy retrieval + structured output section, with strong guardrails against hallucination/irrelevant.

**Constraints respected**: No prod code modified in this session. No Pinecone uploads/index creates. No .env changes. No secrets. Reports only + planning.

---

## Recommended Vector DB Architecture

**Recommendation: Option A (same Pinecone index + dedicated namespace `anatomy_miller_gold_v1`)**

**Why A over B/C**:
- **Consistency**: Must use `text-embedding-3-small` (current prod embed in vector_search/anki/embed_* + query path). Separate index (B) gains little when embed model is forced to match anyway.
- **Operational simplicity**: No new index provisioning, no extra Pinecone project/index monitoring, no separate billing line, one client (`pc.Index(PINECONE_INDEX_NAME)`). Namespace queries are isolated (stats, delete_all, pagination all per-ns).
- **Query pattern unchanged**: CasePrep already does "general + parallel anatomy". Two queries (general default-ns + anatomy ns) is identical cost/latency to two indexes. Pinecone query is ns-scoped by design.
- **Future flexibility**: Easy to promote gold facts into general ns later (or hybrid), or migrate whole index. Namespace delete/upsert is clean for staging ("upload to ns only after local signoff").
- **Matches project history**: Local indexes + "pinecone_ready" slim export were built for exactly this (see vector_db_ingestion_plan.md + gold reports). Namespace is the natural "staging" surface inside the existing index.
- **When to reconsider B**: If gold corpus grows >10-20k (or mixed with images/multimodal), or if you want independent pod types / serverless vs dedicated, or strict data residency between "core knowledge" and "anatomy reference". Or if one corpus becomes public while other stays internal.
- **C (local-only) is Phase 1 only**: Excellent for fast iteration, zero-cost eval, offline, and "prove the gold works before any cloud dollar". Not sufficient for prod BroBot (web + mobile users, latency SLAs, reliability). Use local for dev harness + seed evals; Pinecone (A) for hosted.

**Vector ID format**: Use the corpus `id` verbatim (stable, unique, traceable). Examples from gold:
- `miller-canonical-p1-8f0fba39579b`
- `miller-canonical-p2-dccbaf820379`
- `miller-canonical-p27-...`
Prefix + page-ish + hash keeps them short, human-auditable, and dedup-safe. Never regenerate ids.

**Metadata fields to upload** (from `anatomy_gold_v1_pinecone_ready.jsonl`; flat for Pinecone):
- `text`: the embedding/display text (canonical_fact).
- `source_quote`: exact Miller excerpt (for citations; keep concise).
- `page`: int (source_page; for "Miller p.XX").
- `section_path`, `heading`: provenance.
- `source`: "miller" (constant).
- `corpus_version`: "gold_v1" (or "gold_v1.1" later).
- `region`, `subregion`, `specialty`: filter/boost (str or null).
- `quality_tier`: "high" | "medium" | "low_but_acceptable" — **primary quality filter**.
- `metadata_trust`: "high" etc.
- `structures_at_risk`: list[str] (display + boost; sparse ~37%).
- `approach_terms`: list[str] (display + boost; ~52%).
- `case_associations`: list[str] (future case linking).
- `anatomy_terms`: promote sublists or store as `anatomy_terms_str` (joined) + individual `neurovascular`, `tendon_ligament`, etc. lists for filter/keyword (the dict form in JSONL must be flattened for Pinecone metadata; lists of str only).
- Optional: `diagnosis1`, `procedure` (sparse; use lightly).
- **Do not** store full gold_qc / donor / build notes in prod metadata (audit only in canonical source).

**Pinecone record shape (upsert)**:
```python
{
  "id": rec["id"],
  "values": embed(rec["text"]),  # text-embedding-3-small
  "metadata": {
    "text": rec["text"],
    "source_quote": rec["source_quote"][:2000],  # guard length
    "page": rec["page"],
    "section_path": rec["section_path"],
    "heading": rec["heading"],
    "source": rec["source"],
    "corpus_version": rec["corpus_version"],
    "region": m.get("region"),
    "subregion": m.get("subregion"),
    "specialty": m.get("specialty"),
    "quality_tier": m.get("quality_tier"),
    "structures_at_risk": m.get("structures_at_risk", []),
    "approach_terms": m.get("approach_terms", []),
    "case_associations": m.get("case_associations", []),
    # flattened anatomy term lists if desired for $in
  }
}
```
Total metadata payload per vector must stay under Pinecone limits (~40KB recommended).

**Fields safe for filters** (pre-filter before ANN for perf):
- `region`, `subregion`, `specialty`, `quality_tier` (exact or $in).
- `page` (numeric range if useful: {"$gte": 20, "$lte": 80}).
- Lists: `structures_at_risk` $in, `approach_terms` $in (if you want "only facts mentioning FCR").
- Prefer soft boost over hard exclusion (audit flagged over-assignment risk in earlier versions; gold improved but conservative).

**Fields for reranking / display only** (do not filter on):
- `source_quote`, `heading`, `section_path`, full `anatomy_terms` (if kept as object/string), `text` (for hybrid keyword fallback).
- Use these in post-processing, UI citations, or LLM context only.

**Embedding model**: `text-embedding-3-small` (must match the index + all other CasePrep queries). Instruction prefix optional but recommended for consistency with nomic-era plans: `"search_document: Orthopaedic anatomy fact: {text}"` at embed time for docs; `"search_query: {case} anatomy"` for queries. (Validate dim=1536.)

**top_k defaults**: Retrieve 15–20 (generous for small 717 corpus + rerank headroom). After score/gate/rerank: feed 6–12 best chunks to synthesis. Configurable per call (e.g. `ANATOMY_TOP_K=15`).

**Rerank strategy** (multi-stage, cheap-first):
1. Pinecone ANN (ns-scoped) + `score >= 0.42` (tune from local evals; current general uses 0.55).
2. Optional pre-filter on `quality_tier in ["high","medium"]` (or boost).
3. Metadata boost (reuse refined payload from query_refiner): +0.05–0.10 if chunk.region == case.region or subregion overlap or anatomy_terms/approach_terms intersect query terms.
4. Post-retrieve dedupe (id or text sig) + lightweight relevance gate:
   - Region heuristic (if case has strong region guess, drop obvious mismatches like "fibula" for wrist).
   - Or reuse/adapt `gpt_refiner._filter_irrelevant_snippets` (anatomy-tuned prompt: "keep only if directly supplies relevant anatomy / structures-at-risk / landmarks for THIS case").
   - Keyword overlap on structures/approach/landmarks (cheap).
5. Final sort by (boosted_score or pinecone_score). Cap at 10 for context budget.
6. Low-confidence exit: if final kept < 2 or max_score < 0.40 → flag "limited" (see prompt rules).

**Hybrid note**: Pinecone filter + vector is primary. For exact landmarks/mnemonics, optionally add a small BM25 or keyword pre-filter before vector (or post). Since corpus is statement-first atomic facts, vector + metadata is usually sufficient.

**Namespace vs index in code**: Add `namespace: str = "anatomy_miller_gold_v1"` param to a new `get_anatomy_snippets(...)`. In Pinecone query: pass `namespace=...`. (Current general code ignores ns → defaults to "").

**Local phase1 equivalent**: Pre-embed the 717 with same model → `data/anatomy_miller_gold_v1_local/embeddings.npy` + `ids.json` + `metas.json` + `manifest.json` (record_count, model, dim=1536, created). Search = query embed + cosine (numpy/sklearn or pure). Same rerank logic. This keeps Phase 1 zero-Pinecone and matches the "local-first" philosophy in anatomy_pipeline plans.

---

## 5. Anatomy Retrieval Flow Design

**High-level (updated case-prep path)**:
```
case_prompt (user)
  → refine_query (existing; produces metadata for filters + region guess)
  → parallel:
       general_snippets = get_case_snippets(refined)          # existing, default ns
       anatomy_chunks   = get_anatomy_chunks(refined/prompt)  # NEW: ns or local gold
  → parallel:
       caseprep_result  = refine_case_snippets(prompt, general_snippets)  # pimp + other
       anatomy_context  = build_anatomy_context(prompt, anatomy_chunks)   # NEW structured
  → return { **caseprep_result, "anatomy": anatomy_context }
```

**Where this lives**:
- Core retrieval: `anatomy_retriever.py` (new; local loader + pinecone ns query + common rerank/gate helpers). Or extend vector_search.py with `get_anatomy_snippets`.
- Synthesis: `anatomy_refiner.py` (new; or add `build_anatomy_section` + schema to gpt_refiner.py). Takes chunks + prompt, returns structured dict.
- Wiring: `main.py` (startup can preload gold if local; the two run_ functions; merge). Keep existing anatomy_gpt call for now (approach quiz) or merge into new anatomy_context.
- Config: env `ANATOMY_RETRIEVER=local|pinecone|off`, `ANATOMY_NAMESPACE=anatomy_miller_gold_v1`, `ANATOMY_TOP_K=15`, `ANATOMY_MIN_SCORE=0.42`, `ANATOMY_QUALITY_TIERS=high,medium`.
- Shared: reuse `embed_text`, OpenAI client, refined payload (for boosts).

**Run for every query or only case-prep?** Every `/case-prep` (and thus every BroBot ask). All inputs are case-oriented ("distal radius volar approach", "posterior THA", etc.). The anki/ortho-context endpoint keeps its own path (or can adopt later). Low-confidence path makes it safe for edge prompts.

**How many anatomy chunks**:
- Retrieve: 15–20 (small corpus; cheap).
- After rerank/gate: 6–12 max into synthesis prompt (char budget ~4–6k).
- Output: 4–8 concise bullets per sub-section (relevant, at-risk, etc.).

**Prevent irrelevant anatomy**:
- Query-time: pass region/subregion from refiner as filter or boost.
- Quality: default filter `quality_tier in ["high","medium"]`.
- Post: region mismatch penalty / drop; GPT keepMask (anatomy-specific: "supplies structures, landmarks, approach relations, or high-yield pimp for THIS case/region"; prefer keep on doubt but drop obvious cross-region like hip facts for ankle).
- Hybrid keyword: require overlap on anatomy_terms or structures_at_risk with query tokens (or approach name).
- Score floor + kept-count floor → low-conf path.
- Never fall back to "just ask GPT for anatomy" — if weak, say so.

**How to display source quote / page**:
- In `anatomy_context` payload: include `sources` list or per-bullet `notes`.
- Example synthesized: 
  - "FCR interval is the key internervous plane (Miller p. 45: \"...FCR...radial artery...median nerve...\")"
  - Or structured: `{"structuresAtRisk": [{"name": "median nerve", "note": "Miller p.45, source_quote excerpt"}] }`
- UI: under each Anatomy sub-section, small "Sources (Miller gold)" collapsible with page + short quote + id (for audit). Keep primary bullets clean.
- Never hide the attribution — this is the value of gold corpus.

**How to handle low-confidence anatomy retrieval**:
- In builder: compute `confidence: "high"|"medium"|"low"`, `limitedContext: bool`, `message?: string`.
- If low: 
  ```json
  {
    "relevantAnatomy": [],
    "structuresAtRisk": [],
    ...
    "limitedContext": true,
    "message": "Limited high-quality anatomy context found in the Miller gold corpus for this query. Core surgical anatomy may be covered in the pimp questions and other facts above.",
    "sources": []
  }
  ```
- Prompt rule (see below): "If retrieved chunks provide <2 clearly relevant facts after filtering, output the limited message and empty lists. Do not invent filler."
- UI: render the message italic + still show approach quiz if present (graceful). Do not suppress the whole Anatomy card.
- Telemetry: log % queries hitting limited (target <15–20% on seeds; investigate gaps).

**Parallelism & perf**: Keep `asyncio.gather` for general + anatomy retrieval + (optional) synthesis. Anatomy synthesis can be lighter (smaller context, lower max_tokens). Target added latency <1.5–2s p95.

**When to run anatomy retrieval**:
- Always for /case-prep.
- Optionally skip for very short/generic prompts (length < 8 words) → return limited immediately.
- Future: case-type classifier could boost anatomy weight for "approach-heavy" cases (volar, ORIF, release, reconstruction) vs pure diagnostic.

**Integration with existing anatomy_gpt**:
- Phase 1–3: Run both in parallel; new vector anatomy populates rich `anatomy.relevantAnatomy` etc.; old catalog populates `approachSelection` + `anatomyQuiz`. Merge in the returned anatomy object.
- Later: evolve — use gold for facts + keep lightweight approach selector, or retire catalog if gold covers approaches well.

---

## 6. Prompt / Output Changes

**New / updated output shape for anatomy** (extend AnatomyPayload or make `anatomy` the primary structured object; keep backward keys during transition):
```ts
export type AnatomySection = {
  relevantAnatomy?: string[];           // key structures, relations, planes, blood supply, innervation
  structuresAtRisk?: Array<{name: string; risk?: string; note?: string}>;
  approachRelatedAnatomy?: string[];    // intervals, internervous planes, windows
  landmarks?: string[];                 // palpable / fluoro / surgical landmarks
  highYieldPimpFacts?: string[];        // "Q: ... A: ..." or terse facts (only if directly supported)
  notesWithSources?: string[];          // "- Volar watershed line: Miller p.47: \"...\""
  limitedContext?: boolean;
  message?: string;                     // the "limited..." text when applicable
  confidence?: "high" | "medium" | "low";
  // legacy compat (optional during transition)
  approachSelection?: ...;
  anatomyQuiz?: ...;
  highYieldAnatomy?: ...;
};
```

**Synthesis prompt rules (strict, in system + reinforced in user)**:
- "You are an orthopaedic attending extracting ONLY from the supplied Miller gold anatomy chunks for ONE specific case."
- "NEVER invent anatomy, structures, landmarks, or facts not present in the chunks. If a chunk does not contain it, omit."
- "If after filtering the chunks yield <2 clearly relevant items for the requested aspects, set limitedContext=true and message= the exact limited phrase; return empty lists for the rest."
- "Prefer concise bullets. One fact/relation per bullet. Include parenthetical source note only in notesWithSources."
- "Keep anatomy SEPARATE from management, diagnosis, or non-anatomic pimp. No surgical steps, no indications, no rehab."
- "For structuresAtRisk and landmarks, quote or closely paraphrase the source_quote when possible."
- Tool-enforced JSON schema (like existing CASEPREP_SCHEMA) with additionalProperties: false.
- Temperature 0.0–0.1 for fidelity.

**Where the prompt lives**: `anatomy_refiner.py:_build_anatomy_synthesis_prompt` (or equivalent function). Called from `build_anatomy_context(case_prompt, chunks)` after rerank/gate.

**General RAG prompt impact**: Minimal. The existing pimp/other synthesis prompt stays focused on "intraop/pimp-style" and "otherUsefulFacts" from general snippets. Anatomy synthesis is a separate call (or could be a second tool in a unified call later). In final response, anatomy block is distinct.

**Rules enforcement in code** (defense in depth):
- Pre-filter chunks before sending to LLM (region/score/keyword).
- Post-process output: if limitedContext false but lists are suspiciously generic or contain known cross-region terms, force limited + log.
- Never concatenate raw chunks into a "tell me the anatomy" free-text prompt without the extraction schema + rules.

**UI/display updates (Phase 3)**:
- Anatomy card title: "Anatomy (Miller Gold v1)" or similar (with tooltip "source-attributed from Miller's Review of Orthopaedics").
- Render sub-sections only if non-empty: Relevant Anatomy (bullets), Structures at Risk (name + risk/note), Landmarks, Approach-Related, High-Yield Pimp, Sources (small text or accordion with page + quote).
- If limitedContext: show message + (still render approach quiz if present).
- No change to pimp/other cards (keep them management/dx focused).

**Backward compat during rollout**: Old `anatomyQuiz` / `approachSelection` keys still populated and rendered until catalog retired. New fields added alongside.

---

## 7. Staged Implementation Roadmap (5 Phases)

Each phase is **self-contained + testable + rollback-safe**. "Files to edit" lists intended changes (do not perform). Prefer feature flags + parallel code over big-bang.

### Phase 1: Local Anatomy Retriever Integration Only (no Pinecone, no prod change)
**Goal**: Prove gold corpus + local retrieval + synthesis works for seeds; measure relevance vs current eval; zero cloud cost/risk.

**Files to edit** (plan):
- `main.py` (add import + parallel run_local_anatomy + merge under flag).
- `requirements.txt` (if any; numpy/sklearn/sentence? but prefer reuse openai embed client + pure numpy cosine to avoid new deps).
- (Optional) `anatomy_gpt.py` for light integration.

**New files to create**:
- `anatomy_retriever.py` (local gold loader, embed via existing OpenAI client, cosine top_k, score/region gate, dedupe).
- `scripts/build_anatomy_local_gold_index.py` (load pinecone_ready or canonical gold jsonl; for each compute embed("text"); save embeddings.npy + ids.json + slim_metas.json + manifest.json with model="text-embedding-3-small", dim=1536, record_count=717, source_hash).
- `anatomy_context_builder.py` (or `anatomy_refiner.py`) — rerank/gate + LLM synthesis with new schema + limited handling. (Reuse OpenAIJson pattern from anatomy_gpt.)
- `scripts/test_anatomy_local.py` (run 9 seeds + 2 real cases; print top chunks + synthesized output; basic has_signal check).
- `data/anatomy_miller_gold_v1_local/` (gitignore the npy; committed manifest + small json only).
- (Optional) `tests/test_anatomy_retriever.py`.

**Commands to run** (after venv):
```bash
cd /Volumes/PS3000/snaportho-caseprep
source venv/bin/activate || true
export PYTHONPATH=.
python scripts/build_anatomy_local_gold_index.py --gold-jsonl /Users/alexbaur/anatomy_pipeline/data/anatomy_miller_chapter/anatomy_gold_v1_pinecone_ready.jsonl --output data/anatomy_miller_gold_v1_local
python scripts/test_anatomy_local.py --cases "distal radius volar approach" "posterior THA" ...
# Then manual: python -c "from anatomy_retriever import ...; print(retrieve(...))"
uvicorn main:app --reload  # (dev only)
curl -X POST http://localhost:8000/case-prep -d '{"prompt":"distal radius fracture volar approach"}' | jq .anatomy
```

**Tests to perform**:
- Build succeeds, 717 vectors, manifest correct, no dim mismatch.
- For each seed: top-3 chunks contain at least 1 expected concept from benchmarks/seed_cases (manual or simple overlap).
- No obvious wrong-region (e.g. hip facts for wrist query) in top-5 after gate.
- Synthesis output for 3 seeds: limited=false, has >=3 relevantAnatomy or structures, all source notes reference "Miller p." + short quote present, no obvious invention (compare vs source_quote in chunks).
- Latency: <1s for retrieval on 717 (cpu ok).
- /case-prep still returns valid BroBotPayload (old anatomy keys + new if wired).
- Eval parity or better vs anatomy_pipeline local_index_eval reports (switch to 1536 embeds should help).

**Rollback plan**:
- Env `USE_ANATOMY_RETRIEVER=0` (or default off) → skip new path, return old `anatomy_gpt` result only.
- Or git revert the 2–3 call sites in main.py.
- Local index dir is additive (delete to rollback storage).
- No Pinecone touch.

**Exit criteria**: 9/9 seeds produce usable anatomy context with sources; ortho spot-check (or self) says "better signal than catalog-only"; limited path triggers cleanly on off-topic prompt.

**Duration estimate**: 1–2 dev sessions (build + retriever + builder + harness + review).

### Phase 2: Pinecone Staging Namespace / Index (prep + dry, no live prod traffic)
**Goal**: Production-ready Pinecone path behind flag; upload happens manually/out-of-band after review; code supports both local and pine.

**Files to edit** (plan):
- `vector_search.py` (add `get_anatomy_snippets(..., namespace="anatomy_miller_gold_v1")` or extract shared query helper; support filter by quality_tier).
- `main.py` (add pine path under flag `ANATOMY_BACKEND=pinecone`; still parallel).
- `anatomy_retriever.py` (pinecone branch using existing pc.Index + namespace kwarg).

**New files**:
- `scripts/prepare_anatomy_pinecone_upload.py` (validate pinecone_ready.jsonl, optionally add embed_model/dim to metas, write a "to_upsert.jsonl" or just echo "ready"; --dry-run default).
- `scripts/upload_anatomy_gold.py` (the real one; prints exact pinecone.upsert calls; requires explicit `--confirm` + `ANATOMY_UPLOAD=1`; by default dry + "DO NOT RUN" banner. Never auto-called from main).
- `data/anatomy_miller_gold_v1_pinecone/` (copy of slim jsonl + manifest for the version that was uploaded).
- Update `audit_vectordb.py` or new `inspect_anatomy_ns.py` (query the ns once populated).

**Commands to run**:
```bash
python scripts/prepare_anatomy_pinecone_upload.py --input /Users/.../anatomy_gold_v1_pinecone_ready.jsonl --out data/anatomy_miller_gold_v1_pinecone/ready.jsonl --dry-run
# (human performs the actual upsert using the prepared file + a one-off script or Pinecone UI/console, targeting the ns; record the timestamp + commit of gold used)
python -c "
from vector_search import get_anatomy_snippets
print(get_anatomy_snippets('distal radius volar', namespace='anatomy_miller_gold_v1')[:3])
"
```

**Tests**:
- Prepare validates 717, all required fields, unique ids, no qc clutter.
- Once ns populated (out of band): describe stats shows ~717 in the ns; sample query returns expected ids + scores >0.4 for seeds.
- Same relevance checks as Phase 1 (now against live ns).
- Code path switch (local vs pine) produces near-identical top ids (modulo embed cache).
- No change to general retrieval (still default ns).
- Cost/latency logged for anatomy ns query.

**Rollback**:
- Flag `ANATOMY_BACKEND=local` (or off).
- Namespace is isolated — delete_all on ns (or ignore) has zero impact on general corpus.
- No index delete.

**Exit criteria**: Pinecone path returns same/better results as local for seeds; prepare script is idempotent + auditable; upload was a conscious human step with recorded gold commit.

**Note**: Per constraints, this phase does **not** perform the upload in this session.

### Phase 3: RAG Prompt / Output Integration + UI
**Goal**: Make the final BroBot response include the rich Anatomy section (relevant / at-risk / landmarks / sources) synthesized from retrieved gold chunks. Update types + rendering. Old catalog path can coexist temporarily.

**Files to edit** (plan):
- `gpt_refiner.py` (add `ANATOMY_SECTION_SCHEMA`, `build_anatomy_section(case, chunks)` using tool call + strict rules) or the new refiner.
- `main.py` (call builder with anatomy_chunks; merge into "anatomy"; keep old for compat).
- `anatomy_context_builder.py` (or refiner) — the guard + limited logic + post-process.
- Web: `src/types/caseprep.ts` (extend AnatomyPayload or new AnatomySection type; keep optionals).
- `src/app/brobot/brobotmember.tsx` + `basic/page.tsx` (in Anatomy card: render new sub-sections if present; show limited message; add Sources accordion with page/quote; keep quiz rendering).
- (Minor) `src/app/api/brobot/ask/route.ts` if shape validation needs update (pimp + anatomy presence is current check).

**New files**:
- `prompts/anatomy_synthesis.txt` (extract the long prompt for iteration; version it).
- `scripts/evaluate_anatomy_output.py` (run seeds, diff vs chunks, flag potential inventions via keyword or manual).

**Commands**:
```bash
# local dev
python -c 'from main import ...' or uvicorn
curl ... | jq '.anatomy | {relevantAnatomy, structuresAtRisk, limitedContext, message}'
# web dev
npm run dev
# test in browser or playwright for the card
```

**Tests**:
- For 9 seeds: output anatomy has limited=false, >=1 structuresAtRisk or landmarks for approach cases, notesWithSources contain "Miller p." + non-empty quote, no cross-region inventions (grep for fibula/hip in wrist outputs etc.).
- UI renders without crash on old + new shape; limited message visible when forced.
- pimp/other unchanged.
- Schema validation (pydantic or zod) passes.
- Manual ortho review: "these facts are accurate and would be useful in OR / pimp" for 5/9.

**Rollback**:
- Flag `ANATOMY_SYNTHESIS=off` → return old anatomy shape (or minimal).
- UI can feature-flag the new sub-sections (show only if new keys present).
- Revert types + 2–3 render blocks.

**Exit criteria**: Every /case-prep now carries the structured anatomy section (or explicit limited); UI shows it; 0 hallucinations on seeds per review; citations visible.

### Phase 4: Testing with Real Orthopaedic Cases
**Goal**: Beyond seeds — real case briefs (de-identified OR notes, resident cases, "pimp me on distal radius" variants). Measure practical utility + failure modes. Expand benchmark.

**Files to edit** (plan):
- `scripts/test_anatomy_rag.py` (or expand Phase1 harness) — now accepts real briefs, logs full chunks + output + scores, writes reports/test_run_YYYY.jsonl + .md summary.
- `benchmarks/anatomy_retrieval/real_cases.jsonl` (add 5–10 real de-id cases; same schema + free-text notes).
- (Optional) wire into existing eval from anatomy_pipeline.

**New files**:
- `reports/anatomy_phase4_results.md` (template: per-case table of expected vs surfaced, limited rate, ortho signoff).
- Harness improvements (e.g. auto red_flag detector for known wrong regions).

**Commands / tests**:
```bash
python scripts/test_anatomy_rag.py --backend pinecone --cases-file benchmarks/.../real_cases.jsonl --out reports/phase4/
# Then: human (ortho) reviews the md, marks pass/fail per case per rubric.
# Compare Phase4 vs Phase1 local numbers.
```
- Run all 9 seeds + reals end-to-end through hosted (after Phase5 deploy? or staging).
- Metrics: % cases with clinical signal, avg # structures_at_risk surfaced, % limited, manual "useful for prep?" 1–5.
- Failure injection: "ankle pilon in 12yo" (peds edge), "revision TKA with bone loss" (may be weak).

**Rollback**: Same flags; results are additive.

**Exit criteria**: 8+/9 seeds + 4+/5 reals pass ortho review (accurate, useful, sources correct, no invention). Limited rate <20% on in-scope cases. Documented gaps (e.g. "rare approaches have thin coverage").

### Phase 5: Production Rollout
**Goal**: Safe, observable, reversible prod enablement for web + mobile users.

**Files to edit** (plan):
- Web: any entitlement/flag plumbing if new "anatomy gold" is a paid differentiator (unlikely; treat as core improvement).
- CasePrep: default `ANATOMY_BACKEND=pinecone`, `USE_ANATOMY_RETRIEVER=1`, `ANATOMY_SYNTHESIS=1` (or remove flags).
- Docs: update README, BroBot help text, "powered by Miller gold v1" note.
- Monitoring: add logs/metrics for anatomy latency, limited rate, top source pages, error rate on synthesis.
- (If hosted CasePrep has deploys) CI or deploy notes.

**Commands**:
- Deploy CasePrep (whatever current process: uvicorn/gunicorn, docker, platform).
- Deploy web (Vercel).
- `curl https://api.snap-ortho.com/case-prep -d ...` smoke.
- Web UI test as member + guest.
- Watch logs for 24–48h (anatomy hit rate, p95 latency delta, limited %).

**Tests**:
- Prod smoke on 3 seeds via public proxy (with entitlements).
- Canary: small % traffic or internal users first.
- A/B or before/after: compare limited rate and manual "better anatomy?" feedback.
- Rollback drill: flip flags off, confirm old behavior, re-deploy.

**Rollback**:
- Immediate: env flags / config to disable new paths → instant revert to catalog + old output shape (no deploy needed if flags are runtime).
- Full: revert deploy to previous image/tag.
- Pinecone: ns untouched; general corpus unaffected.

**Exit criteria**: 48h stable (no spike in failures/latency/quota complaints), positive spot user feedback, limited rate acceptable, citations rendering, zero invention reports. Then remove "experimental" labels.

**Post-Phase5**:
- Iterate gold (promote holdout → v1.1, metadata fill, more seeds).
- Consider unified synthesis (one LLM call with general snippets + anatomy chunks + joint prompt) for token/latency wins.
- Add hybrid keyword or small reranker model if relevance plateaus.
- Monitor Pinecone usage (ns-specific) and cost.

---

## 8. Additional Guardrails & Cross-Cutting

- **Feature flags everywhere** (runtime env or lightweight config) for all new paths.
- **No auto-upload**: upload scripts always default dry-run + explicit confirm banner. Gold jsonl is source of truth; never mutate in place.
- **Logging**: every anatomy retrieval logs (query_hash, backend, top_k, kept_after_gate, max_score, limited, latency_ms, sample_ids). PII-free.
- **Budget**: anatomy synthesis prompt caps chunks at ~6k chars + low max_tokens (400–600).
- **Versioning**: corpus_version in meta + manifest; include in logs + optional in UI.
- **Audit**: keep the full canonical gold jsonl (with gold_qc) alongside slim; link by id.
- **Fallbacks**: if OpenAI/Pinecone down for anatomy, return limited message + old catalog anatomy (never hard fail the whole /case-prep).
- **Testing harness reuse**: integrate or call the anatomy_pipeline `evaluate_retrieval.py` / `evaluate_anatomy_relevance.py` against the integrated retriever.

---

## Risks & Mitigations (Summary)

- **Coverage gaps / low scores** (from gold evals): Mitigate with low-conf message + region guards + future gold expansion. Accept that 717 is high-precision reference, not exhaustive textbook.
- **Latency/cost**: Parallel + small context + flag to disable. Measure in Phase 1/4.
- **Invention**: Strict schema + "only from chunks" + post filters + human review in Phase 4. "Limited" is the safe default.
- **Gold quality**: Complete the holdout skim + user signoff before Phase 2 upload (per rec).
- **Metadata risk**: Never hard-filter on sparse fields; use for boost/display. Carry quality_tier.
- **UI/UX debt**: Phase 3 includes rendering; keep collapsible + backward keys.
- **Drift**: If re-embed gold later (new model), new ns or collection version + dual-write window.
- **Secrets / ops**: All Pinecone work via existing CasePrep client; no new keys.

**Success metrics (example)**:
- 9/9 seeds pass test plan (see anatomy_rag_test_plan.md).
- Limited rate ≤15% on seed + real in-scope cases.
- Ortho review: avg "useful for OR/pimp prep" ≥4/5.
- Added p95 latency <2s; no increase in 5xx or quota complaints.
- Citations present and accurate on 100% non-limited outputs.

---

## Next Steps After This Plan

1. Human: review this + test plan + gold holdout packet (canonical_qc_final_manual_packet.md etc.).
2. Approve Phase 1 scope.
3. Execute Phase 1 (local only) in a branch / worktree.
4. Run tests + ortho review.
5. Decide A (ns) vs B; prep Phase 2 upload (human step).
6. Iterate.

This plan is concrete, file-level, command-level, and rollback-safe. It respects the "local first then Pinecone" spirit of the anatomy_pipeline reports while integrating cleanly into the existing CasePrep + BroBot parallel pipeline and BroBotPayload contract.

**End of integration plan**.
