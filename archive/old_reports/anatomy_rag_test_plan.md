# Anatomy RAG Test Plan — Miller Gold v1 Integration

**Date**: 2026-06-05
**Related**: current_rag_pipeline_audit.md, anatomy_rag_integration_plan.md (esp. Phases 1/4 + recommended guards), anatomy_pipeline/benchmarks/anatomy_retrieval/seed_cases*.jsonl + evals.
**Purpose**: Concrete, reproducible test cases for the 9 (of 10) seed orthopaedic procedures/approaches. Each includes expected anatomy concepts, structures at risk, source behavior (Miller gold attribution), and explicit failure criteria. Used in Phase 1 (local), Phase 4 (real + seeds), and ongoing regression.

**Test Harness Notes (to implement in Phase 1/4)**:
- Script: `scripts/test_anatomy_rag.py` (or extend anatomy_pipeline evaluate).
- Inputs: list of queries (seeds + reals).
- For each: call the integrated retriever (local or pine ns), capture top 10 chunks (id, score, page, region, preview, matched expected), then synthesis output.
- Compute simple overlap scores (anatomy_terms hit rate, structures hit, red_flag count = wrong region hits).
- Log full: chunks + raw synthesis + normalized output.
- Output: per-run JSON + markdown table (query, limited?, #relevant, #at_risk, red_flags, notes, pass/fail).
- Manual layer: ortho reviewer marks "clinically accurate + useful?" + "sources correct?" per case.
- Reuse anatomy_pipeline `evaluate_anatomy_relevance.py` or `evaluate_retrieval.py` where possible (adapt for new backend).
- Always compare against gold jsonl source_quote for "invention" checks.
- Failure on any seed = block phase exit until fixed or explicitly waived with rationale.

**Invocation examples** (after integration):
```bash
python scripts/test_anatomy_rag.py --backend local --seeds-only --out reports/test_run_local_$(date +%Y%m%d).json
python scripts/test_anatomy_rag.py --backend pinecone --namespace anatomy_miller_gold_v1 --all --verbose
# Then: python -m src.local_index.evaluate_retrieval --index ... --backend caseprep (if wired)
```

**General Pass Criteria (all cases)**:
- limitedContext = false (or explicitly expected for edge).
- At least 1–2 expected concepts or structures surfaced in relevantAnatomy / structuresAtRisk / landmarks.
- No dominant red flags (wrong region facts in top 5 after gate).
- All non-empty source notes contain "Miller p." + non-trivial quote excerpt that actually appears in the gold corpus for that id.
- Synthesis contains nothing that contradicts the source_quote of its cited chunks.
- Manual ortho signoff: "would help in OR or pimp session" (yes/no + comment).

**Red Flag Examples** (auto or manual detect):
- Wrist case returns hip/pelvis/femur dominant facts.
- "fibula", "tibia shaft", "acetabulum" in top results for upper extremity.
- "no source" or invented page numbers.
- Structures at risk list containing structures not in any retrieved chunk's text/quote.
- High yield pimp that is pure management ("use 3.5mm screws") instead of anatomy.

---

## Seed Test Cases (9 + notes on the 10th)

The seeds align with `benchmarks/anatomy_retrieval/seed_cases.jsonl` (and v2). User-listed 9 covered; distal_biceps_repair is the extra in the file.

### 1. distal_radius_volar : distal radius fracture volar approach
**Query**: "distal radius fracture volar approach" (or "volar Henry approach distal radius ORIF")

**Expected anatomy concepts** (from seed + Miller gold):
- FCR interval / internervous plane (FCR + brachioradialis)
- Pronator quadratus (PQ) elevation / subperiosteal
- Volar watershed line (key for plate placement)
- Radial artery (lateral to FCR)
- Median nerve (ulnar to FCR, carpal tunnel)
- Lister's tubercle (dorsal landmark for reference / indirect)
- EPL groove / 3rd compartment relation
- Carpal tunnel / flexor tendons relations
- Volar radiocarpal ligaments / capsule

**Expected structures at risk**:
- Median nerve (direct / traction / during PQ elevation or carpal tunnel release extension)
- Radial artery (and its branches)
- FCR tendon itself
- Palmar cutaneous branch of median n.
- (Possibly) superficial radial n. sensory (if extended)

**Expected source behavior**:
- Must surface ≥1 chunk with page in distal radius / forearm / wrist sections (Miller p. ~40–60 range for radius/forearm anatomy).
- At least one source_quote containing "FCR", "watershed", "median", "radial artery", or "Lister".
- Synthesis cites Miller p. + short quote for watershed or interval.
- No dominant lower-extremity or hip facts.

**Failure criteria**:
- limitedContext=true (unless query deliberately vague).
- 0 structures_at_risk or landmarks surfaced.
- Top-3 chunks all "general bone" or hip/pelvis (red_flag count >1).
- Synthesis mentions "volar" but quotes a chunk whose source_quote does not contain volar/FCR/median/radius anatomy.
- Any invented structure (e.g. "ulnar artery is primary risk" when not supported).

**Manual signoff question**: "Does the at-risk list + watershed note match what you worry about during actual volar approach?"

### 2. carpal_tunnel_release : carpal tunnel release
**Query**: "carpal tunnel release" or "CTR open / endoscopic"

**Expected anatomy concepts**:
- Carpal tunnel borders (floor = carpal bones + TCL, walls = carpal bones, roof = transverse carpal ligament)
- Contents: median nerve + 9 tendons (FDS 4, FDP 4, FPL)
- Recurrent motor branch of median (extraligamentous / subligamentous / transligamentous variants)
- Palmar cutaneous branch (radial to FCR, outside tunnel — at risk in incision)
- Guyon's canal / ulnar neurovascular proximity (ulnar to hook of hamate)
- Flexor retinaculum / TCL attachments (scaphoid/trapezium to pisiform/hamate)
- Safe zones / landmarks (Kaplan's cardinal line, hook of hamate, FCR)

**Expected structures at risk**:
- Median nerve (main + recurrent motor branch — most common complication source)
- Palmar cutaneous branch
- Ulnar nerve/artery (if incision too ulnar or Guyon release)
- Superficial palmar arch
- FDS/FDP/FPL tendons (injury during release)

**Expected source behavior**:
- Chunks from wrist/hand / carpal tunnel sections (Miller pages for hand ~70+?).
- Quotes mentioning "transverse carpal ligament", "recurrent motor", "palmar cutaneous", "hook of hamate".
- No shoulder or knee dominant.

**Failure criteria**:
- No mention of recurrent motor branch or palmar cutaneous in output when query is CTR.
- Structures at risk empty or only generic "nerves".
- Source quotes from non-wrist Miller pages.
- Synthesis describes endoscopic vs open steps instead of pure anatomy.

### 3. tha_posterior : total hip arthroplasty posterior approach (or posterior THA)
**Query**: "posterior THA" / "posterior approach total hip arthroplasty"

**Expected anatomy concepts**:
- Short external rotators (piriformis, gemelli, obturator internus, quadratus femoris) — "conjoined tendon"
- Sciatic nerve (posterior, lateral to ischium; "safe" posterior retraction)
- Gluteus maximus split / posterior border
- Medial femoral circumflex artery (MFCA) — critical for femoral head blood supply in fractures; at risk in posterior
- Quadratus femoris (constant landmark for sciatic)
- Capsule / labrum / acetabular exposure
- Piriformis tendon as landmark for sciatic / posterior column

**Expected structures at risk**:
- Sciatic nerve (peroneal division more lateral/vulnerable)
- Inferior gluteal nerve / vessels
- MFCA (femoral head viability in native or fracture cases)
- Posterior column / wall of acetabulum
- (In fracture variants) superior gluteal neurovascular

**Expected source behavior**:
- Hip / pelvis / thigh Miller sections (hip heavy in gold ~228 records).
- Quotes with "sciatic notch", "short external rotators", "medial femoral circumflex", "quadratus femoris".
- Page numbers consistent with hip osteology / pelvis (higher pages?).

**Failure criteria**:
- Knee or ankle facts in top results for pure hip query.
- No sciatic or MFCA surfaced for posterior approach.
- Synthesis talks "anterior approach" anatomy.

### 4. tka_medial_parapatellar : total knee arthroplasty medial parapatellar approach
**Query**: "TKA medial parapatellar" / "medial parapatellar approach knee"

**Expected anatomy concepts**:
- Medial parapatellar arthrotomy (quad tendon split, medial to patella, along medial gutter)
- Medial retinaculum / vastus medialis obliquus (VMO)
- Infrapatellar fat pad / ligamentum patellae
- Medial collateral ligament (MCL) — deep to retinaculum; protect during exposure
- Patellar blood supply (inferior geniculate, descending genicular)
- Suprapatellar pouch / quad tendon junction
- (For revision) scar plane identification

**Expected structures at risk**:
- MCL (over-release or buttonhole)
- Infrapatellar saphenous nerve / medial cutaneous branches (incision neuromas)
- Patellar tendon (avulsion risk with eversion or poor closure)
- Popliteal vessels / tibial n. (if posterior capsular release aggressive)
- Superior/inferior genicular arteries

**Expected source behavior**:
- Knee / distal femur / proximal tibia sections.
- Quotes containing "medial parapatellar", "VMO", "MCL", "fat pad", "genicular".
- No hip or shoulder dominant.

**Failure criteria**:
- Lateral structures only (e.g. only IT band / LCL without medial).
- Empty structures at risk for a TKA query.
- Source pages from forearm or spine Miller.

### 5. acl_reconstruction : ACL reconstruction
**Query**: "ACL reconstruction" / "ACL recon" (hamstring or BTB)

**Expected anatomy concepts**:
- ACL bundles (anteromedial / posterolateral) — femoral + tibial footprints
- Lateral femoral condyle / resident's ridge / bifurcate ridge
- Medial tibial spine / ACL tibial footprint (anterior to PCL)
- Notch geometry / roof impingement
- Hamstring harvest: gracilis/semitendinosus (pes anserinus, saphenous n. proximity)
- Patellar tendon (BTB): patella → tibial tubercle, fat pad, infrapatellar branch
- Menisci relations (lateral meniscus posterior horn near ACL tibial)

**Expected structures at risk**:
- Saphenous nerve / infrapatellar branch (hamstring harvest or incision)
- MCL (if medial incision or over-tension)
- Lateral geniculate / popliteal (rare, tunnel misdrill)
- PCL (if notchplasty aggressive)
- Patellar tendon / patella (BTB harvest fracture or rupture)

**Expected source behavior**:
- Knee / ACL / ligaments knee sections.
- Quotes with "anteromedial bundle", "resident ridge", "pes anserinus", "infrapatellar branch".
- Good match to seed expected_structures (ACL, PCL, MCL, LCL, PLC if mentioned).

**Failure criteria**:
- Only hip THA facts.
- No footprint or bundle anatomy for ACL query.
- Structures at risk lists only "infection" (non-anatomic).

### 6. rotator_cuff_repair : rotator cuff repair
**Query**: "rotator cuff repair" / "RCR" (supraspinatus etc.)

**Expected anatomy concepts**:
- Rotator cuff tendons (supra, infra, teres minor, subscap) + insertions on greater/lesser tuberosity
- Subacromial space / bursa / coracoacromial ligament / arch
- Suprascapular nerve (notch, spinoglenoid notch) — at risk in releases or chronic
- Axillary nerve (quadrangular space, inferior capsule) — for inferior tears or releases
- Long head biceps tendon / groove (often tenodesed)
- Greater tuberosity morphology / footprint
- Deltoid split / raphe (for open)

**Expected structures at risk**:
- Suprascapular nerve
- Axillary nerve
- Long head biceps
- Coracoacromial ligament / arch (if acromioplasty)
- Deltoid detachment (open approaches)

**Expected source behavior**:
- Shoulder / scapula / proximal humerus / rotator cuff Miller sections (scapula, prox humerus, miller_shoulder data).
- Quotes with "suprascapular notch", "quadrangular space", "greater tuberosity footprint", "subacromial".
- Matches seed (rotator cuff, labrum, etc.).

**Failure criteria**:
- Only clavicle or elbow facts.
- No nerve risks for cuff repair.
- Source from lower extremity.

### 7. ankle_orif_lateral : ankle ORIF (lateral malleolus / bimalleolar)
**Query**: "ankle ORIF lateral malleolus" / "ankle fracture ORIF"

**Expected anatomy concepts**:
- Lateral malleolus / fibula (Weber A/B/C, syndesmosis)
- Anterior talofibular ligament (ATFL), calcaneofibular (CFL), posterior talofibular
- Syndesmosis (AITFL, PITFL, interosseous, inferior transverse)
- Peroneal tendons (longus/brevis) — posterior to fibula, in groove
- Superficial peroneal n. (crosses lateral ankle ~7–10cm proximal; at risk in proximal incision)
- Sural n. (posterolateral)
- Deltoid ligament (medial, for bimalleolar)
- Talus dome / plafond relations

**Expected structures at risk**:
- Superficial peroneal nerve (sensory loss / neuroma)
- Sural nerve
- Peroneal tendons (sublux or injury)
- Syndesmotic ligaments / tibiofibular joint
- (If medial) deltoid / posterior tibial tendon / neurovascular bundle

**Expected source behavior**:
- Ankle / foot / distal fibula / ligaments ankle sections.
- Quotes with "syndesmosis", "ATFL", "peroneal groove", "superficial peroneal".
- No wrist or shoulder.

**Failure criteria**:
- Upper extremity or hip facts dominant.
- No nerve (SPN/sural) risks listed for lateral approach.
- Syndesmosis anatomy absent.

### 8. cubital_tunnel_release : cubital tunnel release
**Query**: "cubital tunnel release" / "ulnar nerve decompression elbow"

**Expected anatomy concepts**:
- Cubital tunnel (roof = Osborne's ligament / FCU fascia, floor = medial epicondyle + olecranon, walls)
- Ulnar nerve course (medial intermuscular septum, arcade of Struthers, cubital tunnel, FCU two heads, Guyon's)
- Medial epicondyle, olecranon, medial head triceps
- Osborne's ligament / ligament of Osborne
- Flexor carpi ulnaris (FCU) heads
- Medial antebrachial cutaneous n. (crosses in field; neuroma risk)
- Arcade of Struthers (proximal)

**Expected structures at risk**:
- Ulnar nerve (main trunk + branches)
- Medial antebrachial cutaneous nerve (MACN)
- FCU motor branches
- Medial collateral ligament (if extensive release or transposition)

**Expected source behavior**:
- Elbow / distal humerus / forearm neuro sections (elbow_ligaments, neuroanatomic_relationships data).
- Quotes with "Osborne", "cubital tunnel", "ulnar nerve", "medial antebrachial cutaneous".
- Matches cubital seed.

**Failure criteria**:
- Carpal tunnel or wrist median facts only.
- No MACN or Osborne.
- Ulnar nerve not listed as at-risk.

### 9. acetabular_ilioinguinal : acetabular fracture ilioinguinal approach
**Query**: "acetabular fracture ilioinguinal approach"

**Expected anatomy concepts**:
- Ilioinguinal approach windows (lateral = iliac fossa / pelvic brim, middle = quadrilateral surface / pelvic brim, medial = Stoppa / retropubic)
- Iliopectineal eminence / arcuate line
- Femoral nerve / vessels (in lacuna, mobilized medially or laterally)
- Lateral femoral cutaneous n. (LFCN — under inguinal ligament, at risk)
- Spermatic cord / round ligament (medial window)
- Obturator nerve / vessels (quad window, Stoppa)
- Corona mortis (anastomosis obturator + external iliac / inferior epigastric — "crown of death")
- Quadrilateral surface / pelvic brim / anterior column / wall
- Psoas, iliacus, rectus (direct head)

**Expected structures at risk**:
- LFCN (neuropathy / meralgia)
- Femoral n./vessels (traction, laceration)
- Obturator n./vessels
- Corona mortis (massive bleed if missed)
- Spermatic cord / vas (hernia risk, injury)
- Bladder / peritoneum (medial)
- External iliac vessels

**Expected source behavior**:
- Pelvis / acetabulum / hip / thigh Miller sections (pelvis heavy?).
- Quotes containing "iliopectineal", "corona mortis", "lateral femoral cutaneous", "quadrilateral surface", "Stoppa".
- High page or specific pelvis osteology / approaches.

**Failure criteria**:
- Only femoral shaft or knee facts.
- No corona mortis or LFCN for ilioinguinal query.
- Synthesis describes Kocher-Langenbeck (posterior) anatomy.

---

## Additional Test Cases / Variants (Phase 4+)

- Edge / low-coverage: "pediatric supracondylar humerus pinning" (if gold weak on peds).
- "revision THA with trochanteric osteotomy" (may hit limited).
- Real de-id case briefs (add to real_cases.jsonl): e.g. "35M polytrauma acetabular + pelvic ring, ilioinguinal + posterior", "42F diabetic ankle pilon, ORIF + exfix".
- Off-topic probe: "plantar fasciitis" or "shoulder impingement non-op" → expect limitedContext + message (no hallucinated anatomy).
- High-yield pimp probe: after synthesis, spot-check that highYieldPimpFacts are anatomy-derived (not "fix with 3.5 mm recon plate").

---

## Test Execution & Reporting Rubric (per case)

1. **Automated**:
   - limitedContext == expected (false for these 9).
   - has_signal = (len(relevantAnatomy) + len(structuresAtRisk) + len(landmarks) >= 2) or structures hit rate >0.
   - red_flag_count == 0 (or < threshold; log the bad regions).
   - source_citations_valid: every notesWithSources / structure note parses to a real id + page in the gold jsonl + quote substring matches source_quote.
   - no_invention_heuristic: key nouns in output appear in at least one retrieved chunk's text/quote.

2. **Manual (ortho or trained reviewer)**:
   - Accuracy: 1–5 (facts match Miller + real anatomy).
   - Usefulness for case prep / pimp / OR: 1–5.
   - Sources helpful / correct: 1–5.
   - Overall pass/fail + comment.
   - Any invented fact? (list).

3. **Aggregate report** (Phase 4 md):
   - Table: case | limited | #chunks | #surfaced_at_risk | red_flags | auto_pass | manual_score | notes.
   - % pass, avg limited rate, common failure modes, coverage gaps (e.g. "distal biceps and rare peds approaches thin").
   - Comparison: Phase1 (local) vs Phase2 (pine) vs baseline (catalog-only).

**Blockers for Phase Exit**:
- Any seed with manual "invention found".
- >2 seeds with red_flag dominant or limited unexpectedly.
- Synthesis fails schema or crashes.
- UI does not render citations or limited message.

**Success Gate (Phase 4 → 5)**: 8/9 seeds + 4/5 reals fully pass (auto + manual); documented gaps + mitigation (low-conf + future gold v1.1); latency/cost acceptable.

---

## Maintenance

- Add new seeds from real cases that expose gaps.
- Re-run full suite after any gold promotion or rerank change.
- If new embed model: re-build local + re-upload ns (new ns version) + update tests.
- Link failing runs back to specific gold commit + index manifest.

**End of test plan**. Use in conjunction with the integration plan phases. All tests emphasize "only from retrieved gold" + source attribution + "better than hallucinated catalog".
