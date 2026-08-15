# SnapOrtho Case Prep Comprehensive v1.2 Audit

**Date:** 2026-07-23  
**Scope:** Full product pipeline (resolver → registry → certified content → retrieval → enrichment → KG → BroBot → web/iOS UX → performance → safety → competitive position)  
**Stance:** Not a bug hunt. Answer: *If I were an MS4 / resident / fellow / attending preparing for tomorrow’s case, what would still disappoint me?*  
**Assumption:** Recent resolver token-matching improvements are treated as **in progress / landed locally** (not yet a release gate by themselves).

---

## Executive summary

**Case Prep is not yet the best orthopaedic case-preparation tool available.**

It is a **promising architecture with a narrow high-quality island** (anatomy-first certified packets on ~21 runtime-enabled procedures) sitting beside **legacy surfaces, incomplete content, dual APIs, and aggressive LLM fallback**. The best path (web v1.1 SSE packet) is flag-gated, text-only, and still anatomy-skewed. iOS and default production still speak a thinner legacy contract.

### Overall readiness

| Dimension | Score (/100) | One-line verdict |
|-----------|-------------:|------------------|
| **Resolver** | **68** | Much safer than pre-fix for exact aliases; still overconfident on common shorthand; weak on typos/abbreviations without GPT |
| **Content** | **41** | 24 “certified,” ~21 runtime; strong SAR/anatomy on best cases; missing clinical decision stack systemically |
| **Educational quality** | **28** | One-size-fits-all; PGY chips are keyword theater |
| **Retrieval** | **54** | Solid branch design; tiny gold set (10); metadata flag off; contamination pathways remain |
| **Performance** | **48** | Fast *header* is feasible; complete packet target &lt;4s is not real once enrichment/RAG run |
| **Safety** | **44** | Wrong-procedure confidence is the primary harm mode; generic pitfalls and generative evidence are secondary |
| **User experience** | **52** | Best layout exists on web stream; judgment content collapsed; iOS years behind; no media |
| **Launch readiness** | **36** | **Not ready for wider “best-in-class” release.** Ready for **labeled beta** on the runtime-certified subset only |

**Composite launch readiness: 36/100.**

### Brutal one-sentence answer

A resident with 30 minutes before surgery will still open Orthobullets (figures + topic depth), flip Pocket Pimped (instant Q/A), and watch VuMedi (approach video) — Case Prep only wins when it happens to hit a strong certified packet *and* the web stream flags are on *and* the resident already trusts the product enough to wait for it.

---

## What was evaluated (evidence base)

| Source | Evidence |
|--------|----------|
| Code | `procedure_registry.py`, `v1_1_web_stream.py`, `packet_sections.py`, `rag_retrieval.py`, `enrichment_prompts.py`, `curated_content_store.py`, web packet UI, iOS BroBot CasePrep |
| Data | 60 registry procedures, 24 certified payloads, manifests (21 `runtime_enabled=true`), modules, CTR clinical_review tree |
| Offline resolver stress | ~320 alias-heavy prompts + **53 adversarial** prompts (ambiguity, slang, typos, diagnoses) |
| Content scoring | Field coverage across all 24 certified; deep sample of ACL, TKA, THA, RSA, distal radius, SCH, etc. |
| Prior internal audits | `docs/repository_audit/*`, failure-mode reports, product audits under `snaportho-web/docs/audits/` |
| Live E2E | **Not re-run** against production Pinecone/OpenAI in this audit (performance/retrieval live numbers treated as architecture + gold-set only) |

---

## 1. Resolver audit

### What improved
Token-anchored ranking (alias covered by prompt; specific tokens required; ambiguity margin; classifier may return `none` with lexical anchor) is the correct design direction. Exact display/alias prompts resolve extremely well. Concept questions like “how does bone heal” correctly return no procedure.

### Offline measurements (this audit)

**A. Alias-heavy corpus (~320 prompts, no GPT):** ~99.7% exact match when the expected slug was a clear alias/template. This **overstates** real-world readiness.

**B. Adversarial suite (53 prompts, no GPT):**

| Outcome | n | Interpretation |
|---------|--:|----------------|
| ok | 28 | Correct resolve *or* appropriately null/clarify |
| wrong | 13 | Missed true procedure (often short abbr / typo) |
| fp_overconfident | 11 | Picked a specific procedure when should clarify or stay diagnosis-level |
| clarify_instead | 1 | CTR forces clarify even when open CTR intended |

**Accuracy under adversarial conditions ≈ 53% “product-safe” (ok only).** That is the number that matters.

### Critical resolver failures (examples)

| Prompt | Got | Why it hurts |
|--------|-----|--------------|
| `hip replacement` / `THA` / `total hip replacement` | `tha_posterior` | **Silent approach assumption** — wrong approach packet is unsafe teaching |
| `DAA THA` | `tha_posterior` | Explicit approach ignored / lost |
| `hemi vs total hip` | `tha_posterior` | Comparison forced into one procedure |
| `revision vs primary TKA` | `tka` | Drops revision intent |
| `rotator cuff tear` | `rotator_cuff_repair` | Diagnosis → surgery without consent language |
| `supracondylar fracture` | pediatric SCH | Adult vs peds not asked |
| `ACL` / `MPFL` / `IMN femur` / `PFN` / `aTSA` | null (suggest only) | Common shorthand fails offline; depends on GPT stage |
| Typos: `carpel tunnel`, `disal radius`, `byceps`, `total nee` | null | Voice dictation still brittle without classifier |

### Clarification rate
Near-zero on the alias-heavy corpus. On adversarial ambiguous prompts, clarification is **underused** precisely where residents speak (`hip replacement`, `ankle fracture`, `ORIF ankle`).

### Verdict
Resolver is **no longer the main structural disaster**, but it is **not “done.”** Remaining failures are product-level (default approach aliases, diagnosis→procedure leaps), not string-matching trivia.

**Resolver score: 68/100.**

---

## 2. Certified content audit

### Inventory

| Metric | Count |
|--------|------:|
| Registry procedures | 60 |
| Content certified | 24 |
| **Runtime-enabled certified** | **21** |
| Certified but **runtime_enabled=false** | **3** (`tka`, `reverse_shoulder_arthroplasty`, `hip_hemiarthroplasty`) |
| Partial / unreviewed | 36 |
| Procedure aliases in runtime registry (expanded) | ~78 |

**This is a blocker:** three of the highest-volume recon cases have certified files on disk but the store will not serve them when the registry folder path wins.

### What “certified” actually means today

Payloads are **anatomy / approach / structures-at-risk playbooks**, often Orthobullets-sourced, frequently limited in their own text:

> *“Anatomy-focused case prep only; does not replace full surgical technique or attending-specific preferences.”*

That is honest. It is also **not** a complete case-prep product.

### Field coverage (all 24 certified payloads)

| Field | Empty / thin | Notes |
|-------|-------------:|-------|
| `must_know_anatomy` | 0/24 empty | Best layer of the product |
| `structures_at_risk` | 0/24 empty | Often excellent (why / avoid / consequence) |
| `attending_pimp_questions` | 0/24 empty | **Almost always exactly 5** |
| `common_mistakes` | 0/24 empty | Quality highly variable |
| `arthroscopy_or_portal_anatomy` | **24/24 empty** | Sports arthroscopy gap |
| `reduction_or_implant_anatomy` | **~18/24 empty** | Implants/reduction missing |
| `fluoroscopy_checkpoints` | **~17/24 empty** | Trauma fluoro missing on most |
| Real indications / alternatives / bailouts / rehab | **systemically absent as first-class fields** | Decision pipelines keyword-scrape pimps |
| True postop protocols | **≈0/24** | `postop_plan` / checklist often **night-before study bullets** |

### Section scores (clinical rubric, not registry weight)

Registry `coverage_score` 90–100 **overstates readiness** (missing implant + fluoro + true postop can still score high).

| Procedure | Strength | Weakness | Clinical score (~/5) |
|-----------|----------|----------|---------------------:|
| Monteggia ORIF | Full stack: implants, fluoro, specific pimps | Still light on rehab | **4.7** |
| SCH pediatric | Reduction + fluoro + nerves/vascular | Still not full trauma protocol | **4.5** |
| SCFE pinning | Decision-rich, AVN awareness | Rehab thin | **4.4** |
| THA posterior | SAR, layers, dislocation thinking | Implant algorithm thin | **4.0** |
| ACL | Excellent footprints / harvest SAR | No graft choice tree, rehab, portals field empty | **3.5** |
| TKA | Strong approach SAR | No gap balancing, constraint ladder, true postop; **runtime disabled** | **3.4** |
| Distal radius | Good pimps (watershed, skyline) | **Generic pitfalls**, empty implant/fluoro fields | **2.8** |
| Reverse shoulder | — | **Template pimps + generic pitfalls**, wrong anatomy_category tag, **runtime disabled** | **2.1** |
| Carpal tunnel | Clinical review packet is *better than many certified* | **Not certified / not runtime** | N/A |

### Template rot (must fix before more “certification”)

**Generic pitfalls** still ship on certified content (distal radius, RSA):

- “Inadequate identification of structures at risk leading to iatrogenic injury”
- “Missing key landmarks resulting in malpositioned hardware”
- …

**Generic night-before checklist** (many certified):

- “Review linked modules and source URLs”
- “Practice the 10+ pimp questions” *(while only 5 exist)*

**Placeholder landmarks** still present (“Essential palpable landmark from approach or reduction content.”).

**Cross-contamination residues** (e.g. distal femur landmarks mentioning ACL harvest language; wrong OB URLs on some foot content).

### Content score: **41/100**

---

## 3. Educational quality audit (by learner)

| Learner | What they need 30 min pre-op | What Case Prep delivers | Gap |
|---------|------------------------------|-------------------------|-----|
| **MS4** | Orientation: what surgery is, what to scrub for, safe questions | Sometimes good overview + anatomy; often too approach-technical without decision context | No MS4 track; study-guide path hard-codes medical_student but packet doesn’t teach “how to be useful in the room” |
| **PGY-1** | Anatomy SAR, positioning, “don’t hurt X,” basic steps | **Best fit** when certified hit is strong | Missing postop, implants, “who not to operate” |
| **PGY-2** | Decision forks, common attending pimps, reduction/implant choices | Anatomy heavy; decisions often enrichment-only | Weak decision banks |
| **PGY-4** | Complications, bailouts, revision thinking, evidence that changes plan | Almost none curated; LLM evidence is soft-constrained | Fellow-lite content missing |
| **Fellow** | Preference-sensitive technique, failure modes, literature | Not a product surface | Would not use |

Header `difficulty` / `pgy_level` are **keyword heuristics by procedure type** (`arthroplasty` → intermediate / PGY2–4, etc.). They do **not** change content.

**Educational quality score: 28/100.**

### Recommendation
Ship **three explicit prep modes** (not chips):

1. **Room Ready (10 min)** — 5 must-not-miss + 8 pimps + SAR  
2. **Case Ready (25 min)** — + decisions, flow, pitfalls, postop  
3. **Chief Ready (45 min)** — + evidence, bailouts, alternatives, preference notes  

Same packet schema; different default expansion + item filters by mode *and* user level.

---

## 4. Pocket Pimped audit (hallmark feature)

### Architecture (good)
- Curated attending questions first  
- RAG Pocket-Pimped Q/A second  
- Dedup + optional enrichment pedagogy (pearl / why / difficulty / common mistake)  
- UI: staged reveal cards on web stream  

### Reality check

| Dimension | Finding |
|-----------|---------|
| Curated count | **5 per certified procedure** (checklist still says “10+”) |
| Mix | Rough offline classification of 120 curated pimps: **~79% anatomy**, ~6% technique, **~3% decision**, ~2% postop |
| Duplicates | Rare exact dups; more near-duplicates / restatements within banks |
| Template Qs | RSA bank includes non-specific stems |
| Difficulty progression | No ordered easy→hard curriculum; enrichment assigns difficulty after the fact |
| OR readiness | Strong for “what nerve is at risk?” Weak for “when do you convert / stop / choose implant B?” |
| Retrieval gold | **Only 10 cases** in `pocket_pimp_retrieval_gold_v1.jsonl` |
| Metadata flag | `CASEPREP_POCKET_PIMP_METADATA_READY` still off by design until backfill audited |

### Recommended pimp hierarchy (replace flat 5)

For every certified procedure, enforce banks:

| Tier | n | Content |
|------|--:|---------|
| Must-not-miss (intern) | 5 | SAR + one fatal mistake |
| Technique (junior) | 5 | Steps, reduction, portals, fluoro |
| Decision (mid) | 5 | operate / not / convert / implant / graft |
| Attending favorites (senior) | 5 | preference-sensitive + classic traps |
| Evidence (optional) | 3 | landmark trials that change practice |

**Pimp subscore (within content): ~45/100 as shipped.**

---

## 5. Retrieval audit

### Design strengths
- One embedding, parallel scoped branches  
- Procedure/approach scope guards  
- Semantic fallback now requires shared **anchor tokens** (good recent fix)  
- Near-dup suppression  
- TTL cache  

### Contamination pathways that remain

1. **`regional_backup`** (region + specialty only) — can surface same-region wrong procedure Qs when procedure metadata sparse  
2. **`semantic_fallback`** — still embedding-driven; anchors reduce but do not eliminate soft contamination  
3. **Pocket-pimp filter without complete metadata** — migration-safe dual query mode until flag on  
4. **Query refiner LLM** — can drift diagnoses/approaches (mitigated by registry override for specialty/region when resolved)  
5. **Wrong resolver slug** — retrieval faithfully contaminates *everything* downstream (primary pathway)  
6. **Legacy iOS `/case-prep`** — older retrieval/synthesis path; not the v1.1 stack  

### Measurement status
- Gold set: **10 prompts** (too small for release claims)  
- Release gates in README (90% term recall, 70% top-k, 0 contamination, ≤4s) are **aspirational until gold expands and live CI runs**  
- This audit did **not** re-benchmark live Pinecone  

**Retrieval score: 54/100.**

---

## 6. KG audit

| Question | Finding |
|----------|---------|
| Does KG improve answers in Case Prep? | **Only if** `CASEPREP_WEB_V1_1_KG_ENABLED` and stream path; injects `related_concepts` on the web BFF |
| Unique value | Concept neighborhood / curriculum links — **not** operative judgment |
| Redundancy | Often overlaps “teaching topics” / related diagnoses already known |
| Should move to certified? | No — keep KG as **graph navigation**, not clinical authority |
| Optimal balance | Certified = clinical truth; RAG pimps = quizzing; KG = “what else to review tonight”; never overwrite SAR/steps |

**KG is a nice-to-have sidebar, not a readiness driver.** Score contribution limited until clinical core is complete.

---

## 7. BroBot / LLM generation audit

### Surfaces
| Surface | Generation role |
|---------|-----------------|
| Web stream enrichment | Pedagogy + gap-fill for decisions/evidence/(uncertified anatomy/flow/pitfalls/postop) |
| Resolver classifier | Only on unresolved prompts |
| Query refiner | Scope metadata for RAG |
| Legacy iOS `/case-prep` | Older GPT pimp/anatomy synthesis |
| BroBot Chat OR Prep | Explicitly told **not** to duplicate CasePrep; complements it |

### Enrichment prompt quality
**Good:** junior OR voice; curated authoritative; bans inventing implant brands/measurements; operative_flow blocked when certified.

**Still weak:**
- Evidence is “up to 4 landmark trials” with only soft anti-hallucination — **high risk of confident wrong citations**  
- Single 6k curated trim can drop the best facts  
- Cache key `{slug}|{model}` **ignores payload hash** → stale pedagogy after content edits  
- Uncertified path: enrichment *is* the product (8–30s), quality unbounded by certification  

### Tone failure modes
Too textbook when gap-filling; too cautious when evidence unsure (sometimes correctly empty); missing attending preference language; missing “what I will be asked at the scrub sink.”

**BroBot/enrichment subscore: ~47/100.**

---

## 8. Performance audit

### Design targets (from product intent)
| Milestone | Target | Realistic today |
|-----------|--------|-----------------|
| Above-the-fold (header + takeaways) | **&lt;1.5s** | **Achievable** on cache-warm alias resolve + local curated transforms |
| Pimp questions | &lt;2.5s | Depends on embed + Pinecone; **4s hard timeout** on pipelines |
| Complete packet | **&lt;4s** | **Not achievable** with enrichment (~8–30s budgets) and cold RAG |

### Measured architecture budgets
| Stage | Budget |
|-------|--------|
| Deterministic pipelines / resolve / refine / retrieval thread calls | **4.0s hard** (`PIPELINE_TIMEOUT_SECONDS`) |
| Enrichment (certified decorate) | **8s** default |
| Enrichment (uncertified gap-fill) | **30s** default |
| iOS legacy ask | ~40–60s client timeouts historically |

### Bottlenecks
1. OpenAI embedding + multi-branch Pinecone (cold)  
2. Enrichment single large JSON completion  
3. In-process caches only (multi-instance cold)  
4. Click-to-start stream + multi-step Prepare funnel (product latency, not just API)

### Achievable latency roadmap
- **Warm certified, enrichment off:** ATF &lt;1s, pimps 1–3s if retrieval cached — meets partial target  
- **Enrichment on:** treat as progressive enhancement (already partially designed) but **do not claim &lt;4s complete**  
- Precompute enrichment at certification time (offline) → online packet becomes pure deterministic + cached RAG  

**Performance score: 48/100.**

---

## 9. Competitive audit

| Competitor | Where SnapOrtho wins | Where SnapOrtho loses | Why users leave |
|------------|----------------------|----------------------|-----------------|
| **Orthobullets** | Case-scoped packet; SAR consequence language on best certified | Breadth, figures, videos, questions ecosystem, trust | Need a figure, classification, or full topic |
| **AAOS / OVT** | Faster skimmable prep shell | Authority, guidelines, peer review | Need citable standard of care |
| **VuMedi** | Structured text prep | **Zero video** | “Show me the approach” |
| **Pocket Pimped** | Integrated with case identity + streaming packet | Instant open book of Qs; brand trust; density | Want pure pimp drill without product friction |
| **Campbell’s / Miller** | OR-tomorrow framing | Depth, classic technique, figures | Board / deep technique night |
| **Real resident prep** (OB + PP + senior + YouTube) | Could unify if complete | Completeness + media + social proof | Time pressure defaults to known tools |

**Competitive position today:** *best architecture for “tomorrow’s case packet” among early products; not yet best daily driver.*

---

## 10. Safety audit

### Induced / observed failure classes

| Failure | Severity | Evidence |
|---------|----------|----------|
| **Wrong procedure / wrong approach with high confidence** | **Critical** | `hip replacement`→posterior THA; `DAA THA`→posterior |
| Diagnosis auto-escalated to surgery | High | `rotator cuff tear`→repair |
| Adult/peds mis-route | High | bare `supracondylar fracture`→pediatric SCH |
| Empty/generic pitfalls on certified | Medium | distal radius, RSA |
| Hallucinated evidence via enrichment | High (when flag on) | Prompt allows “landmark trials” without verification store |
| Contaminated retrieval Qs | Medium–High | residual pathways; gold set tiny |
| Runtime-disabled high-volume certified | High (silent empty) | TKA, RSA, hemi |
| Legacy iOS path quality | High | thinner contract, older synthesis |
| Source attribution hidden from users | Medium | debug badges only |

### Safety score: **44/100**

**Rule for wider release:** *Never present a specific approach packet unless the user stated the approach or chose a clarification option.*

---

## 11. UX audit

### Best surface (web stream packet)
Order is largely right for learning:

Summary → Takeaways → Top things → **Pimps** → Anatomy → Flow → Teaching → Decisions → Pitfalls → Postop → Evidence → KG → Sources  

### What still disappoints at T−30 min

1. **Multi-step entry** (Prepare → topic → Case Readiness → Build packet)  
2. **Judgment modules collapsed by default** (flow, decisions, pitfalls, postop)  
3. **Pimp answer reveal friction** (great for study, bad for scrub-sink skim)  
4. **No media**  
5. **Provenance hidden**  
6. **iOS is a different, thinner product** (pimps + facts + anatomy text)  
7. **Flags off by default** in production-shaped configs  
8. **Quota / paywall** mid-prep is a trust killer  

### Recommended reorder for “Room Ready” mode
1. Must-not-miss (SAR + fatal mistakes) — always open  
2. Pimps — answers visible in skim mode  
3. Decision points  
4. Operative flow / fluoro  
5. Pitfalls & bailouts  
6. Postop  
7. Anatomy deep dive (collapsed)  
8. Evidence / sources (collapsed)  

**UX score: 52/100.**

---

## 12. Missing feature audit (attending bar)

What would make an attending *recommend* this:

| Feature | Priority | Status |
|---------|----------|--------|
| Approach-disambiguated packets | P0 | Partial (aliases; often wrong defaults) |
| Indications / who-not-to-operate | P0 | Mostly missing as first-class |
| Bailouts & conversion criteria | P0 | Missing |
| Implant selection ladders | P0 | Rare |
| True postop / WB / DVT / red flags | P0 | Mis-modeled as study checklist |
| Radiograph / fluoro example images | P1 | None |
| Approach diagrams / layers illustration | P1 | Text only |
| VuMedi / OVT deep links | P1 | Sources are raw OB URLs only |
| Instrument tray / setup | P1 | None |
| Attending preference packs (program-level) | P2 | None |
| Case schedule import → auto packet | P2 | Partial product vision only |
| Training-level adaptive banks | P1 | Chips only |
| Offline / OR-wifi-poor mode | P2 | None |

---

## Critical blockers (prevent broader release)

1. **Silent wrong-approach resolution** (`hip replacement` / `THA` → posterior)  
2. **Runtime-disabled certified high-volume cases** (TKA, RSA, hip hemi)  
3. **Certified ≠ complete case prep** (anatomy playbook marketed as case prep)  
4. **Generic pitfalls / template pimps still certified**  
5. **True postop missing**; night-before checklist mislabeled as postop  
6. **iOS still on legacy contract** while web invents the real product  
7. **Enrichment evidence hallucination risk** if flags enabled without citation store  
8. **Coverage cliff:** most real OR lists miss the 21 runtime packets (CTR, rotator cuff, IT hip, ankle ORIF variants, etc.)  
9. **No media** while competitors are visual  
10. **Evaluation harness too thin** (10 retrieval gold; no clinical section gold)  

---

## Top 25 highest-impact improvements

Ranked by **educational benefit × feasibility** (P0 = do before growth marketing).

| # | Improvement | Benefit | Effort | Priority |
|---|-------------|---------|--------|----------|
| 1 | Force clarification for multi-approach procedures (THA, TSA/RSA, ankle ORIF, hip fracture) — kill default posterior | Safety + trust | S | **P0** |
| 2 | Flip `runtime_enabled` correctly for TKA/RSA/hemi **or** remove “certified” claims | Coverage | XS | **P0** |
| 3 | Delete generic pitfalls/template pimps; block cert if present | Safety | S | **P0** |
| 4 | Replace night-before checklist with real postop fields (WB, immobilize, DVT, red flags, f/u) | Education | M | **P0** |
| 5 | Author decision banks (operate / not / convert / stop) for top 21 runtime cases | Education | M | **P0** |
| 6 | Expand curated pimps to 15–20 with tiered hierarchy | Hallmark feature | M | **P0** |
| 7 | Ship CTR clinical_review → certified after human sign-off | Coverage (high demand) | M | **P0** |
| 8 | Align iOS CasePrep to v1.1 packet contract (or explicitly label legacy) | Product honesty | L | **P0** |
| 9 | Expand retrieval gold to ≥100 cases; run contamination CI | Safety | M | **P0** |
| 10 | Resolver: common abbreviations (`ACL`, `IMN`, `PFN`, `aTSA`) + typo synonym table | Reliability | S | **P0** |
| 11 | Precompute enrichment at cert time; online = deterministic | Perf + safety | M | **P1** |
| 12 | Evidence only from curated citation objects (no free-gen trials) | Safety | M | **P1** |
| 13 | Implant/fluoro modules for trauma + arthroplasty top 15 | Education | L | **P1** |
| 14 | Room Ready / Case Ready / Chief Ready modes | UX + education | M | **P1** |
| 15 | Default-expand decisions/pitfalls/flow in Room Ready | UX | S | **P1** |
| 16 | Skim mode: pimp answers visible without multi-tap | UX | S | **P1** |
| 17 | Per-bullet source chips for users (not debug only) | Trust | S | **P1** |
| 18 | One-tap prep from schedule/case title | UX | M | **P1** |
| 19 | Enable pocket-pimp metadata after audited backfill | Retrieval | M | **P1** |
| 20 | Media: 3–5 classic fluoro/approach images per certified case | Competitive | L | **P1** |
| 21 | Deep-link VuMedi/OVT/OB approach videos in operative_flow | Competitive | S | **P1** |
| 22 | Kill dual non-stream v1.1 section model or freeze it as deprecated | Engineering clarity | S | **P1** |
| 23 | Content hash in enrichment cache keys | Correctness | XS | **P1** |
| 24 | Program preference packs (attending note overlays) | Differentiation | L | **P2** |
| 25 | Adaptive PGY filtering of banks | Education | M | **P2** |

---

## Quick wins (≤1 day each)

1. Enable runtime for TKA / RSA / hip hemi **after** scrubbing generic content — or keep disabled and stop advertising them as certified.  
2. Remove alias `hip replacement` → posterior; require clarification options (anterior / posterior / lateral / hemi).  
3. Add abbreviation aliases: `ACL`, `IMN femur`, `PFN`, `aTSA`, `DAA`, `IT fx`.  
4. CI lint: fail certification if pitfalls match generic template strings.  
5. CI lint: fail if `postop` equals night-before boilerplate.  
6. UI: Room Ready default expansion set.  
7. UI: “Skim” toggle on pimp cards.  
8. Show `source: certified|rag|generated` badges in non-debug UI (honest labeling).  
9. Fix enrichment cache key to include payload hash.  
10. Rebuild `registry_index.json` after manifest drift.  
11. Expand adversarial resolver tests from this audit into `resolver_test_matrix.py`.  
12. Empty-state copy: “Anatomy packet only — not full case prep” when limitations say so.

---

## Long-term roadmap — Case Prep v2

### North star
**The only app a trainee opens the night before and the morning of** — case-scoped, approach-correct, media-backed, preference-aware, honest about uncertainty.

### Phase 0 — Honesty & safety (2 weeks)
- Approach clarification mandatory  
- Runtime flags correct  
- Generic content purge  
- Label anatomy-only packets  
- Resolver adversarial suite in CI  

### Phase 1 — Complete the island (6–8 weeks)
- Top 40 procedures by real demand (from `brobot_messages` / demand events)  
- Full clinical schema: indications, alternatives, implants, fluoro, bailouts, postop, rehab, tiered pimps  
- CTR + rotator cuff + IT hip + common ankle ORIF first  
- Retrieval gold ≥100; contamination = release blocker  

### Phase 2 — One product surface (6 weeks)
- Web stream packet = canonical  
- iOS consumes same section contract  
- Deprecate dual v1.1 non-stream shape  
- Offline-precomputed enrichment  

### Phase 3 — Competitive parity features (quarter)
- Images + fluoro examples  
- Video deep links  
- Instrument/setup  
- Program preference overlays  
- True training-level modes  

### Phase 4 — Differentiation (ongoing)
- Schedule-aware auto prep  
- Attending-specific pimp packs  
- Outcome-linked “what was actually asked in the OR” feedback loop  
- Multi-case day packs (trauma list mode)

### What to stop doing
- Certifying more anatomy-only migrations under the word “certified”  
- Growing registry aliases without clinical packets  
- Enabling enrichment evidence generation without a citation DB  
- Measuring success as “sections non-empty”  

---

## Scores recap

| Dimension | /100 |
|-----------|-----:|
| Resolver | 68 |
| Content | 41 |
| Educational quality | 28 |
| Retrieval | 54 |
| Performance | 48 |
| Safety | 44 |
| UX | 52 |
| **Launch readiness** | **36** |

---

## Final judgment

Case Prep’s **architecture is closer to “best” than its content and distribution are.**

The system already knows the right product shape: resolve the *case*, stream a *packet*, put pimps above the fold, keep curated facts authoritative, use RAG for quiz density, use LLM only to decorate.

It is not the best tool available until:

1. It **refuses to guess approach**,  
2. Its **certified set is clinically complete** (not anatomy-only),  
3. **High-volume cases** (TKA, cuff, CTR, IT hip, ankle) are first-class,  
4. **Mobile matches web**, and  
5. **Visual media** exists for the steps that cannot be taught as prose.

Until then, the honest product promise is:

> **“Best-in-class anatomy/SAR prep for a small certified set; experimental case packet for everything else.”**

That can be a powerful beta. It is not yet a wider release as the best orthopaedic case preparation platform.

---

## Appendix A — Runtime-enabled certified (n=21)

acetabulum anterior/posterior, ACL, distal femur, distal radius, femoral shaft, hallux valgus, humeral shaft, lateral ankle ligament, meniscus, monteggia, pelvis ring, plantar fascia, PLDF, quadriceps tendon, SCFE, SCH peds, THA anterior, THA posterior, tibial shaft, TSA  

**Certified but not runtime:** TKA, reverse shoulder, hip hemiarthroplasty  

## Appendix B — Adversarial resolver snapshot (53 prompts)

- ok: 28  
- wrong: 13  
- fp_overconfident: 11  
- clarify_instead: 1  

## Appendix C — Primary code references

- Packet section order: `caseprep/schemas_v1_1_packet.py`  
- Stream engine: `caseprep/engines/v1_1_web_stream.py`  
- Deterministic pipelines: `caseprep/pipelines/packet_sections.py`  
- RAG: `caseprep/services/rag_retrieval.py`
- Enrichment prompts: `caseprep/services/enrichment_prompts.py`  
- Web UI order: `snaportho-web/src/components/caseprep-packet/CasePrepPacket.tsx`  
- Flags: `snaportho-web/src/lib/caseprep-v1-1/flags.ts`  
- iOS versions: `RemoteConfigManager.supportedCasePrepVersions = {v1, legacy}`  
