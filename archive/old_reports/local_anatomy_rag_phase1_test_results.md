# Local Anatomy RAG Phase 1 – Test Results

Generated: 2026-06-05T23:41:00.069108+00:00

Corpus: 717 records from anatomy_gold_v1_pinecone_ready.jsonl
Embed model: text-embedding-3-small (matches production)
Retriever: cosine + post-filter (min_score, dedupe, quality boost, region soft boost)

## Per-Case Summary

### distal radius fracture volar approach
- retrieved: 10
- limitedAnatomyContext: False
- relevantAnatomy: 1
- structuresAtRisk: 2
- approachLandmarks: 0
- highYieldFacts: 0
- sources: 3
  - Miller p.33: An approach through the radial aspect of the FCR sheath: often easier and protects the radial artery
  - Miller p.28: Radial nerve: limits proximal extension of approach
  - Miller p.33: Risks: FCU stripped subperiosteally to protect ulnar nerve and artery I Surgical approaches to the wrist and hand

**Top chunks (score, page, preview):**
- 0.688 p.27 miller-canonical-p27-2269428c1e6c: May be extended distally to the forearm when combined with a volar Henry approach...
- 0.669 p.33 miller-canonical-p33-d41b150ba1ec: Distally, retract the APL and EPB to gain access to the middle and distal portions of the ...
- 0.666 p.81 miller-canonical-p81-58f143236d1c: Dissection: use a subcutaneous approach for ORIF of distal fibula fractures....

### carpal tunnel release
- retrieved: 10
- limitedAnatomyContext: False
- relevantAnatomy: 8
- structuresAtRisk: 2
- approachLandmarks: 0
- highYieldFacts: 0
- sources: 6
  - Miller p.7: Transverse articulations between proximal and distal rows are reinforced by palmar and dorsal intercarpal ligaments and carpal...
  - Miller p.20: Median nerve passes through the carpal tunnel between FDS and flexor carpi radialis (FCR) to supply the radial lumbricals, thenar...
  - Miller p.33: Risks: FCU stripped subperiosteally to protect ulnar nerve and artery I Surgical approaches to the wrist and hand

**Top chunks (score, page, preview):**
- 0.551 p.7 miller-canonical-p7-ab4253d41beb: Space of Poirier: central weak area in floor of carpal tunnel; implicated in volar disloca...
- 0.543 p.7 miller-canonical-p7-d7a3b1806c8a: Transverse articulations between proximal and distal rows are reinforced by palmar and dor...
- 0.535 p.20 miller-canonical-p20-b5ac282be521: Median nerve passes through the carpal tunnel between FDS and flexor carpi radialis (FCR) ...

### posterior total hip arthroplasty
- retrieved: 10
- limitedAnatomyContext: False
- relevantAnatomy: 3
- structuresAtRisk: 1
- approachLandmarks: 0
- highYieldFacts: 0
- sources: 4
  - Miller p.64: Particularly at risk for injury during psoas tenotomy through an anteromedial approach for developmental dysplasia of the hip
  - Miller p.63: Can be injured by placement of acetabular screws in the anterosuperior quadrant during total hip arthroplasty I Cruciate anastomosis:...
  - Miller p.40: Adult posterior hip approach: do not completely transect the quadratus femoris muscle (to prevent damage to medial femoral circumflex...

**Top chunks (score, page, preview):**
- 0.696 p.72 miller-canonical-p72-73a8a0145f93: Distal extension of posterior acetabular approach (Kocher-Langenbeck)...
- 0.689 p.69 miller-canonical-p69-b88af56366cd: Anterior (Smith-Peterson) approach to the hip (Fig....
- 0.646 p.64 miller-canonical-p64-a0ace2d9a1bf: Particularly at risk for injury during psoas tenotomy through an anteromedial approach for...

### total knee arthroplasty medial parapatellar approach
- retrieved: 10
- limitedAnatomyContext: False
- relevantAnatomy: 3
- structuresAtRisk: 1
- approachLandmarks: 0
- highYieldFacts: 0
- sources: 4
  - Miller p.79: Posteromedial approach behind the medial malleolus through the tendon sheath of the posterior tibialis Iliotibial band Lateral...
  - Miller p.62: Infrapatellar branch supplies skin of the medial side of the front of the knee and patellar ligament and can be damaged during total...
  - Miller p.63: Can be injured by placement of acetabular screws in the anterosuperior quadrant during total hip arthroplasty I Cruciate anastomosis:...

**Top chunks (score, page, preview):**
- 0.955 p.77 miller-canonical-p77-ee16edb85354: Anterior approach (medial parapatellar)...
- 0.722 p.77 miller-canonical-p77-5437b4f123d1: Dissection: midline skin incision and a medial parapatellar capsular incision...
- 0.721 p.79 miller-canonical-p79-83f37d8afd60: Posteromedial approach behind the medial malleolus through the tendon sheath of the poster...

### ACL reconstruction
- retrieved: 10
- limitedAnatomyContext: False
- relevantAnatomy: 7
- structuresAtRisk: 2
- approachLandmarks: 0
- highYieldFacts: 0
- sources: 6
  - Miller p.63: Can be injured by placement of acetabular screws in the anterosuperior quadrant during total hip arthroplasty I Cruciate anastomosis:...
  - Miller p.107: ACL has anteromedial (tight in flexion) and posterolateral (tight in extension) bundles; PL bundle assessed with pivot shift test.
  - Miller p.46: Anterior cruciate ligament (ACL) has anteromedial (tight in flexion) and posterolateral (tight in extension) bundles; posterior ligament...

**Top chunks (score, page, preview):**
- 0.623 p.63 miller-canonical-p63-8ae3e0123f86: Can be injured by placement of acetabular screws in the anterosuperior quadrant during tot...
- 0.595 p.45 miller-canonical-p45-b9a7e2bdd071: Accessory or “bipartite” patella may represent failure of fusion of the superolateral corn...
- 0.593 p.107 miller-canonical-p107-ea7b2f38d44c: ACL has anteromedial (tight in flexion) and posterolateral (tight in extension) bundles; P...

### rotator cuff repair
- retrieved: 10
- limitedAnatomyContext: False
- relevantAnatomy: 8
- structuresAtRisk: 0
- approachLandmarks: 0
- highYieldFacts: 0
- sources: 6
  - Miller p.26: Supraspinatus tendon is exposed, which allows for repairs of the rotator cuff.
  - Miller p.107: Rotator cuff function: depress and stabilize the humeral head against the glenoid; force-couple larger shoulder muscles to maintain...
  - Miller p.2: Coracoacromial ligament contributes to anterosuperior stability in rotator cuff deficiency and should be preserved with irreparable cuff...

**Top chunks (score, page, preview):**
- 0.829 p.26 miller-canonical-p26-965baf69ba4a: Supraspinatus tendon is exposed, which allows for repairs of the rotator cuff....
- 0.744 p.107 miller-canonical-p107-59b9fb758b7d: Rotator cuff function: depress and stabilize the humeral head against the glenoid; force-c...
- 0.742 p.2 miller-canonical-p2-2153db809135: Coracoacromial ligament contributes to anterosuperior stability in rotator cuff deficiency...

### ankle ORIF lateral malleolus
- retrieved: 10
- limitedAnatomyContext: False
- relevantAnatomy: 3
- structuresAtRisk: 1
- approachLandmarks: 0
- highYieldFacts: 0
- sources: 4
  - Miller p.52: Lateral fibular ligaments: anterior talofibular ligament (ATFL), calcaneofibular ligament (CFL), and posterior
  - Miller p.81: Risks: lesser saphenous vein and sural nerve posterior to lateral malleolus
  - Miller p.79: Posteromedial approach behind the medial malleolus through the tendon sheath of the posterior tibialis Iliotibial band Lateral...

**Top chunks (score, page, preview):**
- 0.765 p.52 miller-canonical-p52-cf5833e957d4: ATFL is the weakest and is intracapsular (intracapsular thickening). Injured with lateral ...
- 0.753 p.48 miller-canonical-p48-a8b8874675e7: Lateral malleolus: distal fibula expansion that extends beyond distal tip of medial malleo...
- 0.723 p.81 miller-canonical-p81-6798967ca674: Lateral approach to the ankle...

### cubital tunnel release
- retrieved: 10
- limitedAnatomyContext: False
- relevantAnatomy: 7
- structuresAtRisk: 3
- approachLandmarks: 0
- highYieldFacts: 0
- sources: 6
  - Miller p.6: Osborne’s ligament stabilizes ulnar nerve in cubital
  - Miller p.33: Risks: FCU stripped subperiosteally to protect ulnar nerve and artery I Surgical approaches to the wrist and hand
  - Miller p.20: Cubital tunnel: Osborne ligament (roof), medial collateral ligament (MCL) (floor)

**Top chunks (score, page, preview):**
- 0.691 p.20 miller-canonical-p20-6fe22f4d3227: Crosses elbow posterior to medial epicondyle at elbow through the cubital tunnel...
- 0.661 p.6 miller-canonical-p6-22739fcd3da1: Osborne’s ligament stabilizes ulnar nerve in cubital...
- 0.616 p.33 miller-canonical-p33-a4899f384068: Risks: FCU stripped subperiosteally to protect ulnar nerve and artery I Surgical approache...

### acetabular fracture ilioinguinal approach
- retrieved: 10
- limitedAnatomyContext: False
- relevantAnatomy: 3
- structuresAtRisk: 1
- approachLandmarks: 1
- highYieldFacts: 0
- sources: 4
  - Miller p.40: Adult posterior hip approach: do not completely transect the quadratus femoris muscle (to prevent damage to medial femoral circumflex...
  - Miller p.40: Iliopsoas muscle/tendon traverses a groove between iliopectineal eminence and AIIS. I Acetabulum: normally anteverted (15 degrees) and...
  - Miller p.64: Ascending branch (at risk for injury during anterolateral approaches) proceeds to greater trochanteric region between TFL and rectus

**Top chunks (score, page, preview):**
- 0.904 p.69 miller-canonical-p69-4899d1caa158: Ilioinguinal (anterior) approach to the acetabulum...
- 0.754 p.72 miller-canonical-p72-73a8a0145f93: Distal extension of posterior acetabular approach (Kocher-Langenbeck)...
- 0.737 p.40 miller-canonical-p40-acd2c40e8819: Adult posterior hip approach: do not completely transect the quadratus femoris muscle (to ...
