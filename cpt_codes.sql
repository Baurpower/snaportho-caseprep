-- ============================================================
-- ACGME Orthopaedic Fellowship CPT Code Database
-- ============================================================
-- Sources: ACGME Case Log Guidelines (11/2015)
--   - Adult Reconstructive Orthopaedic Surgery
--   - Foot and Ankle Orthopaedic Surgery
--   - Musculoskeletal Oncology
--   - Orthopaedic Sports Medicine
--   - Spine
--   - Orthopaedic Trauma
--   - Pediatric Orthopaedic Surgery
-- ============================================================

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ------------------------------------------------------------
-- FELLOWSHIPS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fellowships (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT    NOT NULL UNIQUE,   -- short identifier used in queries
    name        TEXT    NOT NULL
);

-- ------------------------------------------------------------
-- CASE CATEGORIES
-- Each category belongs to one fellowship.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS case_categories (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    fellowship_id INTEGER NOT NULL REFERENCES fellowships(id) ON DELETE CASCADE,
    name          TEXT    NOT NULL
);

-- ------------------------------------------------------------
-- CPT CODES
-- A single CPT code may appear in multiple categories / fellowships.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cpt_codes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT    NOT NULL UNIQUE,
    description TEXT    NOT NULL
);

-- ------------------------------------------------------------
-- JUNCTION: category <-> cpt_code  (many-to-many)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS category_cpt (
    category_id INTEGER NOT NULL REFERENCES case_categories(id) ON DELETE CASCADE,
    cpt_id      INTEGER NOT NULL REFERENCES cpt_codes(id)       ON DELETE CASCADE,
    PRIMARY KEY (category_id, cpt_id)
);

-- ------------------------------------------------------------
-- Full-text search virtual table for fast searching
-- ------------------------------------------------------------
CREATE VIRTUAL TABLE IF NOT EXISTS cpt_fts USING fts5(
    code,
    description,
    fellowship,
    category,
    content='',          -- contentless; we populate manually
    tokenize='unicode61'
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_cpt_code        ON cpt_codes(code);
CREATE INDEX IF NOT EXISTS idx_cat_fellowship  ON case_categories(fellowship_id);
CREATE INDEX IF NOT EXISTS idx_catcpt_cat      ON category_cpt(category_id);
CREATE INDEX IF NOT EXISTS idx_catcpt_cpt      ON category_cpt(cpt_id);

-- ============================================================
-- FELLOWSHIPS
-- ============================================================
INSERT OR IGNORE INTO fellowships(code, name) VALUES
  ('ADULT_RECON',  'Adult Reconstructive Orthopaedic Surgery'),
  ('FOOT_ANKLE',   'Foot and Ankle Orthopaedic Surgery'),
  ('MSK_ONC',      'Musculoskeletal Oncology'),
  ('SPORTS',       'Orthopaedic Sports Medicine'),
  ('SPINE',        'Spine'),
  ('HAND',         'Hand'),
  ('TRAUMA',       'Orthopaedic Trauma'),
  ('PEDS',         'Pediatric Orthopaedic Surgery');

-- ============================================================
-- CASE CATEGORIES
-- ============================================================
-- Adult Reconstructive
INSERT OR IGNORE INTO case_categories(fellowship_id, name) VALUES
  ((SELECT id FROM fellowships WHERE code='ADULT_RECON'), 'Primary Total Knee Arthroplasty'),
  ((SELECT id FROM fellowships WHERE code='ADULT_RECON'), 'Revision Total Knee Arthroplasty'),
  ((SELECT id FROM fellowships WHERE code='ADULT_RECON'), 'Uni Knee Arthroplasty'),
  ((SELECT id FROM fellowships WHERE code='ADULT_RECON'), 'Removal Prosthesis for Infection (Hip or Knee)'),
  ((SELECT id FROM fellowships WHERE code='ADULT_RECON'), 'Primary Total Hip Arthroplasty'),
  ((SELECT id FROM fellowships WHERE code='ADULT_RECON'), 'Revision Total Hip Arthroplasty'),
  ((SELECT id FROM fellowships WHERE code='ADULT_RECON'), 'Osteotomy Knee'),
  ((SELECT id FROM fellowships WHERE code='ADULT_RECON'), 'Osteotomy Hip'),
  ((SELECT id FROM fellowships WHERE code='ADULT_RECON'), 'Primary Shoulder Arthroplasty'),
  ((SELECT id FROM fellowships WHERE code='ADULT_RECON'), 'Revision Shoulder Arthroplasty'),
  ((SELECT id FROM fellowships WHERE code='ADULT_RECON'), 'Rotator Cuff Open and Arthroscopic'),
  ((SELECT id FROM fellowships WHERE code='ADULT_RECON'), 'Bony Procedures for Shoulder Instability'),
  ((SELECT id FROM fellowships WHERE code='ADULT_RECON'), 'Soft Tissue Procedures for Shoulder Instability'),
  ((SELECT id FROM fellowships WHERE code='ADULT_RECON'), 'Open Acromioplasty'),
  ((SELECT id FROM fellowships WHERE code='ADULT_RECON'), 'Other Upper Limb Arthroscopic Procedures'),
  ((SELECT id FROM fellowships WHERE code='ADULT_RECON'), 'Arthrodesis Shoulder');

-- Foot and Ankle
INSERT OR IGNORE INTO case_categories(fellowship_id, name) VALUES
  ((SELECT id FROM fellowships WHERE code='FOOT_ANKLE'), 'Elective Reconstruction Forefoot'),
  ((SELECT id FROM fellowships WHERE code='FOOT_ANKLE'), 'Elective Reconstruction Midfoot/Hindfoot'),
  ((SELECT id FROM fellowships WHERE code='FOOT_ANKLE'), 'Arthroscopy'),
  ((SELECT id FROM fellowships WHERE code='FOOT_ANKLE'), 'Arthrodesis'),
  ((SELECT id FROM fellowships WHERE code='FOOT_ANKLE'), 'Arthroplasty'),
  ((SELECT id FROM fellowships WHERE code='FOOT_ANKLE'), 'Trauma Ankle Hindfoot (General)'),
  ((SELECT id FROM fellowships WHERE code='FOOT_ANKLE'), 'Calcaneus'),
  ((SELECT id FROM fellowships WHERE code='FOOT_ANKLE'), 'Talus'),
  ((SELECT id FROM fellowships WHERE code='FOOT_ANKLE'), 'Pilon'),
  ((SELECT id FROM fellowships WHERE code='FOOT_ANKLE'), 'Trauma Midfoot/Forefoot (General)'),
  ((SELECT id FROM fellowships WHERE code='FOOT_ANKLE'), 'Lisfranc'),
  ((SELECT id FROM fellowships WHERE code='FOOT_ANKLE'), 'Tendon Repair/Transfer'),
  ((SELECT id FROM fellowships WHERE code='FOOT_ANKLE'), 'Skin'),
  ((SELECT id FROM fellowships WHERE code='FOOT_ANKLE'), 'Hardware Removal'),
  ((SELECT id FROM fellowships WHERE code='FOOT_ANKLE'), 'Graft'),
  ((SELECT id FROM fellowships WHERE code='FOOT_ANKLE'), 'Infection/Tumor'),
  ((SELECT id FROM fellowships WHERE code='FOOT_ANKLE'), 'Amputation'),
  ((SELECT id FROM fellowships WHERE code='FOOT_ANKLE'), 'Nerves');

-- Musculoskeletal Oncology
INSERT OR IGNORE INTO case_categories(fellowship_id, name) VALUES
  ((SELECT id FROM fellowships WHERE code='MSK_ONC'), 'Spine/Pelvis (Minimum 10)'),
  ((SELECT id FROM fellowships WHERE code='MSK_ONC'), 'Soft Tissue Resections and Reconstruction (Minimum 20)'),
  ((SELECT id FROM fellowships WHERE code='MSK_ONC'), 'Limb Salvage (Minimum 20)'),
  ((SELECT id FROM fellowships WHERE code='MSK_ONC'), 'Surgical Management of Complications (Minimum 5)'),
  ((SELECT id FROM fellowships WHERE code='MSK_ONC'), 'Management of Metastatic Disease (Minimum 20)');

-- Sports Medicine
INSERT OR IGNORE INTO case_categories(fellowship_id, name) VALUES
  ((SELECT id FROM fellowships WHERE code='SPORTS'), 'Glenohumeral Instability'),
  ((SELECT id FROM fellowships WHERE code='SPORTS'), 'Rotator Cuff'),
  ((SELECT id FROM fellowships WHERE code='SPORTS'), 'Acromioclavicular Instability'),
  ((SELECT id FROM fellowships WHERE code='SPORTS'), 'Elbow Arthroscopy'),
  ((SELECT id FROM fellowships WHERE code='SPORTS'), 'Elbow Instability'),
  ((SELECT id FROM fellowships WHERE code='SPORTS'), 'Hip Arthroscopy'),
  ((SELECT id FROM fellowships WHERE code='SPORTS'), 'Knee Instability'),
  ((SELECT id FROM fellowships WHERE code='SPORTS'), 'Knee Multi-Ligament Repair and Reconstruction'),
  ((SELECT id FROM fellowships WHERE code='SPORTS'), 'Knee Osteotomy'),
  ((SELECT id FROM fellowships WHERE code='SPORTS'), 'Patellofemoral Instability'),
  ((SELECT id FROM fellowships WHERE code='SPORTS'), 'Knee Articular Cartilage'),
  ((SELECT id FROM fellowships WHERE code='SPORTS'), 'Meniscus'),
  ((SELECT id FROM fellowships WHERE code='SPORTS'), 'Foot and Ankle');

-- Spine
INSERT OR IGNORE INTO case_categories(fellowship_id, name) VALUES
  ((SELECT id FROM fellowships WHERE code='SPINE'), 'Fractures and Dislocations'),
  ((SELECT id FROM fellowships WHERE code='SPINE'), 'Anterior Arthrodesis'),
  ((SELECT id FROM fellowships WHERE code='SPINE'), 'Posterior Arthrodesis'),
  ((SELECT id FROM fellowships WHERE code='SPINE'), 'Posterior Instrumentation'),
  ((SELECT id FROM fellowships WHERE code='SPINE'), 'Anterior Instrumentation'),
  ((SELECT id FROM fellowships WHERE code='SPINE'), 'Application of Cage'),
  ((SELECT id FROM fellowships WHERE code='SPINE'), 'Removal of Spinal Instrumentation'),
  ((SELECT id FROM fellowships WHERE code='SPINE'), 'Laminectomy'),
  ((SELECT id FROM fellowships WHERE code='SPINE'), 'Laminoplasty'),
  ((SELECT id FROM fellowships WHERE code='SPINE'), 'Thoracic Transpedicular Decompression'),
  ((SELECT id FROM fellowships WHERE code='SPINE'), 'Vertebral Corpectomy');

-- Trauma
INSERT OR IGNORE INTO case_categories(fellowship_id, name) VALUES
  ((SELECT id FROM fellowships WHERE code='TRAUMA'), 'Shoulder - Fracture and/or Dislocation'),
  ((SELECT id FROM fellowships WHERE code='TRAUMA'), 'Humerus/Elbow - Fracture and/or Dislocation'),
  ((SELECT id FROM fellowships WHERE code='TRAUMA'), 'Forearm/Wrist - Fracture and/or Dislocation'),
  ((SELECT id FROM fellowships WHERE code='TRAUMA'), 'Pelvis/Hip - Fracture and/or Dislocation'),
  ((SELECT id FROM fellowships WHERE code='TRAUMA'), 'Femur/Knee - Fracture and/or Dislocation'),
  ((SELECT id FROM fellowships WHERE code='TRAUMA'), 'Leg/Ankle - Fracture and/or Dislocation'),
  ((SELECT id FROM fellowships WHERE code='TRAUMA'), 'Foot/Toes - Fracture and/or Dislocation'),
  ((SELECT id FROM fellowships WHERE code='TRAUMA'), 'Treatment of Nonunion/Malunion'),
  ((SELECT id FROM fellowships WHERE code='TRAUMA'), 'External Fixation'),
  ((SELECT id FROM fellowships WHERE code='TRAUMA'), 'Debridement'),
  ((SELECT id FROM fellowships WHERE code='TRAUMA'), 'Fasciotomy'),
  ((SELECT id FROM fellowships WHERE code='TRAUMA'), 'Intra-Articular Distal Humerus Fracture'),
  ((SELECT id FROM fellowships WHERE code='TRAUMA'), 'Pelvic Ring'),
  ((SELECT id FROM fellowships WHERE code='TRAUMA'), 'Acetabulum'),
  ((SELECT id FROM fellowships WHERE code='TRAUMA'), 'Bicondylar Tibial Plateau'),
  ((SELECT id FROM fellowships WHERE code='TRAUMA'), 'Pilon/Plafond');

-- Pediatric
INSERT OR IGNORE INTO case_categories(fellowship_id, name) VALUES
  ((SELECT id FROM fellowships WHERE code='PEDS'), 'Foot and Ankle Deformity (Excludes Clubfoot)'),
  ((SELECT id FROM fellowships WHERE code='PEDS'), 'Clubfoot'),
  ((SELECT id FROM fellowships WHERE code='PEDS'), 'Limb Deformity (Includes Length Discrepancy and Deranged Growth)'),
  ((SELECT id FROM fellowships WHERE code='PEDS'), 'Spine Deformity'),
  ((SELECT id FROM fellowships WHERE code='PEDS'), 'Trauma Upper Limb'),
  ((SELECT id FROM fellowships WHERE code='PEDS'), 'Treatment of Supracondylar Fractures'),
  ((SELECT id FROM fellowships WHERE code='PEDS'), 'Trauma Lower Limb'),
  ((SELECT id FROM fellowships WHERE code='PEDS'), 'Open Treatment of Femoral Shaft Fracture'),
  ((SELECT id FROM fellowships WHERE code='PEDS'), 'Hip (Reconstruction and Other, Excludes DDH)'),
  ((SELECT id FROM fellowships WHERE code='PEDS'), 'Hip (Developmental Dysplasia)'),
  ((SELECT id FROM fellowships WHERE code='PEDS'), 'Soft Tissue: Transfer, Lengthening and Release'),
  ((SELECT id FROM fellowships WHERE code='PEDS'), 'Treatment of Infection');

-- ============================================================
-- CPT CODES  (INSERT OR IGNORE handles duplicates across fellowships)
-- ============================================================

-- ---- ADULT RECON ----
INSERT OR IGNORE INTO cpt_codes(code, description) VALUES
  ('27445', 'Arthroplasty, knee, hinge prosthesis'),
  ('27446', 'Arthroplasty, knee, condyle and plateau; medial OR lateral compartment'),
  ('27447', 'Arthroplasty, knee, condyle and plateau; medial AND lateral compartments with or without patella resurfacing (total knee arthroplasty)'),
  ('27486', 'Revision of total knee arthroplasty, with or without allograft; 1 component'),
  ('27487', 'Revision of total knee arthroplasty, with or without allograft; femoral and entire tibial component'),
  ('27437', 'Arthroplasty, patella; without prosthesis'),
  ('27438', 'Arthroplasty, patella; with prosthesis'),
  ('27440', 'Arthroplasty, knee, tibial plateau'),
  ('27441', 'Arthroplasty, knee, tibial plateau; with debridement and partial synovectomy'),
  ('27442', 'Arthroplasty, femoral condyles or tibial plateau(s), knee'),
  ('27443', 'Arthroplasty, femoral condyles or tibial plateau(s), knee; with debridement and partial synovectomy'),
  ('27030', 'Arthrotomy, hip, with drainage (e.g., infection)'),
  ('27090', 'Removal of hip prosthesis (separate procedure)'),
  ('27091', 'Removal of hip prosthesis; complicated, including total hip prosthesis, methylmethacrylate with or without insertion of spacer'),
  ('27310', 'Arthrotomy, knee, with exploration, drainage, or removal of foreign body (e.g., infection)'),
  ('27488', 'Removal of prosthesis, including total knee prosthesis, methylmethacrylate with or without insertion of spacer, knee'),
  ('27125', 'Hemiarthroplasty, hip, partial (e.g., femoral stem prosthesis, bipolar arthroplasty)'),
  ('27130', 'Arthroplasty, acetabular and proximal femoral prosthetic replacement (total hip arthroplasty), with or without autograft or allograft'),
  ('27236', 'Open treatment of femoral fracture, proximal end, neck, internal fixation or prosthetic replacement'),
  ('27132', 'Conversion of previous hip surgery to total hip arthroplasty, with or without autograft or allograft'),
  ('27134', 'Revision of total hip arthroplasty; both components, with or without autograft or allograft'),
  ('27137', 'Revision of total hip arthroplasty; acetabular component only, with or without autograft or allograft'),
  ('27138', 'Revision of total hip arthroplasty; femoral component only, with or without allograft'),
  ('27448', 'Osteotomy, femur, shaft or supracondylar; without fixation'),
  ('27450', 'Osteotomy, femur, shaft or supracondylar; with fixation'),
  ('27457', 'Osteotomy, proximal tibia, including fibular excision or osteotomy; after epiphyseal closure'),
  ('27120', 'Hip acetabuloplasty'),
  ('27122', 'Acetabuloplasty; resection, femoral head (e.g., Girdlestone procedure)'),
  ('27146', 'Osteotomy, iliac, acetabular or innominate bone'),
  ('23470', 'Arthroplasty, glenohumeral joint; hemiarthroplasty'),
  ('23472', 'Arthroplasty, glenohumeral joint; total shoulder (glenoid and proximal humeral replacement)'),
  ('23333', 'Removal of foreign body, shoulder; deep (subfascial or intramuscular)'),
  ('23334', 'Removal of prosthesis, includes debridement and synovectomy; humeral or glenoid component'),
  ('23335', 'Removal of prosthesis, includes debridement and synovectomy; humeral and glenoid component (total shoulder)'),
  ('23473', 'Revision of total shoulder arthroplasty, including allograft when performed; humeral or glenoid component'),
  ('23474', 'Revision of total shoulder arthroplasty, including allograft when performed; humeral and glenoid component'),
  ('23395', 'Muscle transfer, any type, shoulder or upper arm; single'),
  ('23397', 'Muscle transfer, any type, shoulder or upper arm; multiple'),
  ('23410', 'Repair of ruptured musculotendinous cuff (e.g., rotator cuff) open; acute'),
  ('23412', 'Repair of ruptured musculotendinous cuff (e.g., rotator cuff) open; chronic'),
  ('23420', 'Reconstruction of complete shoulder (rotator) cuff avulsion, chronic (includes acromioplasty)'),
  ('23430', 'Tenodesis of long tendon of biceps'),
  ('29827', 'Arthroscopy, shoulder, surgical; with rotator cuff repair'),
  ('29828', 'Arthroscopy, shoulder, surgical; biceps tenodesis'),
  ('23460', 'Capsulorrhaphy, anterior, any type; with bone block'),
  ('23462', 'Capsulorrhaphy, anterior, any type; with coracoid process transfer'),
  ('23465', 'Capsulorrhaphy, glenohumeral joint, posterior, with or without bone block'),
  ('23455', 'Capsulorrhaphy, anterior, with labral repair (e.g., Bankart procedure)'),
  ('23466', 'Capsulorrhaphy, glenohumeral joint, any type multi-directional instability'),
  ('29806', 'Arthroscopy, shoulder, surgical; capsulorrhaphy'),
  ('23130', 'Acromioplasty or acromionectomy, partial, with or without coracoacromial ligament release'),
  ('29807', 'Arthroscopy, shoulder, surgical; repair of SLAP lesion'),
  ('29824', 'Arthroscopy, shoulder, surgical; distal claviculectomy including distal articular surface (Mumford procedure)'),
  ('29826', 'Arthroscopy, shoulder, surgical; decompression of subacromial space with partial acromioplasty, with coracoacromial ligament release'),
  ('29830', 'Arthroscopy, elbow, diagnostic, with or without synovial biopsy (separate procedure)'),
  ('29834', 'Arthroscopy, elbow, surgical; with removal of loose or foreign body'),
  ('29835', 'Arthroscopy, elbow, surgical; synovectomy, partial'),
  ('29836', 'Arthroscopy, elbow, surgical; synovectomy, complete'),
  ('29837', 'Arthroscopy, elbow, surgical; debridement, limited'),
  ('29838', 'Arthroscopy, elbow, surgical; debridement, extensive'),
  ('29840', 'Arthroscopy, wrist, diagnostic, with or without synovial biopsy (separate procedure)'),
  ('29843', 'Arthroscopy, wrist, surgical; for infection, lavage and drainage'),
  ('29844', 'Arthroscopy, wrist, surgical; synovectomy, partial'),
  ('29845', 'Arthroscopy, wrist, surgical; synovectomy, complete'),
  ('29846', 'Arthroscopy, wrist, surgical; excision and/or repair of triangular fibrocartilage and/or joint debridement'),
  ('29847', 'Arthroscopy, wrist, surgical; internal fixation for fracture or instability'),
  ('29848', 'Endoscopy, wrist, surgical, with release of transverse carpal ligament'),
  ('23800', 'Arthrodesis, glenohumeral joint');

-- ---- FOOT AND ANKLE ----
INSERT OR IGNORE INTO cpt_codes(code, description) VALUES
  ('28022', 'Arthrotomy, including exploration, drainage, or removal of loose or foreign body; metatarsophalangeal joint'),
  ('28102', 'Excision or curettage of bone cyst or benign tumor, talus or calcaneus; with iliac or other autograft (includes obtaining graft)'),
  ('28103', 'Excision or curettage of bone cyst or benign tumor, talus or calcaneus; with allograft'),
  ('28110', 'Ostectomy, partial excision, fifth metatarsal head (bunionette) (separate procedure)'),
  ('28112', 'Ostectomy, complete excision; other metatarsal head (second, third or fourth)'),
  ('28113', 'Ostectomy, complete excision; fifth metatarsal head'),
  ('28114', 'Ostectomy, complete excision; all metatarsal heads, with partial proximal phalangectomy, excluding first metatarsal (Clayton type procedure)'),
  ('28116', 'Ostectomy, excision of tarsal coalition'),
  ('28118', 'Ostectomy, calcaneus'),
  ('28122', 'Partial excision (craterization, saucerization, sequestrectomy, or diaphysectomy) bone; tarsal or metatarsal bone, except talus or calcaneus'),
  ('28160', 'Hemiphalangectomy or interphalangeal joint excision, toe, proximal end of phalanx, each'),
  ('28200', 'Repair, tendon, flexor, foot; primary or secondary, without free graft, each tendon'),
  ('28210', 'Repair, tendon, extensor, foot; secondary with free graft, each tendon (includes obtaining graft)'),
  ('28230', 'Tenotomy, open, tendon flexor; foot, single or multiple tendon(s) (separate procedure)'),
  ('28285', 'Correction, hammertoe (e.g., interphalangeal fusion, partial or total phalangectomy)'),
  ('28286', 'Correction, cock-up fifth toe, with plastic skin closure (e.g., Ruiz-Mora type procedure)'),
  ('28288', 'Ostectomy, partial, exostectomy or condylectomy, metatarsal head, each metatarsal head'),
  ('28290', 'Correction, hallux valgus (bunion), with or without sesamoidectomy; simple exostectomy (Silver type procedure)'),
  ('28292', 'Correction, hallux valgus (bunion), with or without sesamoidectomy; Keller, McBride, or Mayo type procedure'),
  ('28296', 'Correction, hallux valgus (bunion), with or without sesamoidectomy; with metatarsal osteotomy (Mitchell, Chevron, or concentric type procedures)'),
  ('28297', 'Correction, hallux valgus (bunion), with or without sesamoidectomy; Lapidus-type procedure'),
  ('28298', 'Correction, hallux valgus (bunion), with or without sesamoidectomy; by phalanx osteotomy'),
  ('28306', 'Osteotomy, with or without lengthening, shortening or angular correction, metatarsal; first metatarsal'),
  ('28310', 'Osteotomy, shortening, angular or rotational correction; proximal phalanx, first toe (separate procedure)'),
  ('28315', 'Sesamoidectomy, first toe (separate procedure)'),
  ('27606', 'Tenotomy, percutaneous, Achilles tendon; general anesthesia'),
  ('27635', 'Excision or curettage of bone cyst or benign tumor, tibia or fibula'),
  ('27637', 'Excision or curettage of bone cyst or benign tumor, tibia or fibula; with autograft (includes obtaining graft)'),
  ('27638', 'Excision or curettage of bone cyst or benign tumor, tibia or fibula; with allograft'),
  ('27640', 'Partial excision (craterization, saucerization, or diaphysectomy), bone (e.g., osteomyelitis); tibia'),
  ('27641', 'Partial excision (craterization, saucerization, or diaphysectomy), bone (e.g., osteomyelitis); fibula'),
  ('27646', 'Radical resection of tumor; fibula'),
  ('27647', 'Radical resection of tumor; talus or calcaneus'),
  ('27690', 'Transfer or transplant of single tendon (with muscle redirection or rerouting); superficial (e.g., anterior tibial extensors into midfoot)'),
  ('27695', 'Repair, primary, disrupted ligament, ankle; collateral'),
  ('27696', 'Repair, primary, disrupted ligament, ankle; both collateral ligaments'),
  ('27698', 'Repair, secondary, disrupted ligament, ankle, collateral (e.g., Watson-Jones procedure)'),
  ('27705', 'Osteotomy; tibia'),
  ('27707', 'Osteotomy; fibula'),
  ('27709', 'Osteotomy; tibia and fibula'),
  ('27720', 'Repair of nonunion or malunion, tibia; without graft (e.g., compression technique)'),
  ('27726', 'Repair of fibular nonunion/malunion with internal fixation'),
  ('28060', 'Fasciectomy, plantar fascia; partial (separate procedure)'),
  ('28100', 'Excision or curettage of bone cyst or benign tumor, talus or calcaneus'),
  ('28104', 'Excision or curettage of bone cyst or benign tumor, tarsal or metatarsal, except talus or calcaneus'),
  ('28120', 'Partial excision (craterization, saucerization, sequestrectomy, or diaphysectomy) bone; talus or calcaneus'),
  ('28130', 'Talectomy (astragalectomy)'),
  ('28238', 'Reconstruction (advancement), posterior tibial tendon with excision of accessory tarsal navicular bone (Kidner type procedure)'),
  ('28300', 'Osteotomy; calcaneus (e.g., Dwyer or Chambers type procedure), with or without internal fixation'),
  ('28705', 'Arthrodesis; pantalar'),
  ('28715', 'Arthrodesis; triple'),
  ('29891', 'Arthroscopy, ankle, surgical; excision of osteochondral defect of talus and/or tibia including drilling of the defect'),
  ('29892', 'Arthroscopic aided repair of large osteochondritis dissecans lesion, talar dome fracture, or tibial plateau fracture, with or without internal fixation'),
  ('29895', 'Arthroscopy, ankle (tibiotalar and fibulotalar joints), surgical; synovectomy, partial'),
  ('29897', 'Arthroscopy, ankle (tibiotalar and fibulotalar joints), surgical; debridement, limited'),
  ('27700', 'Arthroplasty, ankle'),
  ('27870', 'Arthrodesis, ankle, open'),
  ('27871', 'Arthrodesis, tibiofibular joint, proximal or distal'),
  ('28725', 'Arthrodesis; subtalar'),
  ('28730', 'Arthrodesis, midtarsal or tarsometatarsal, multiple or transverse'),
  ('28735', 'Arthrodesis, midtarsal or tarsometatarsal, multiple or transverse; with osteotomy (e.g., flatfoot correction)'),
  ('28737', 'Arthrodesis, with tendon lengthening and advancement, midtarsal, tarsal navicular-cuneiform (Miller type procedure)'),
  ('28740', 'Arthrodesis, midtarsal or tarsometatarsal, single joint'),
  ('28750', 'Arthrodesis, great toe; metatarsophalangeal joint'),
  ('29899', 'Arthroscopy, ankle (tibiotalar and fibulotalar joints), surgical; with ankle arthrodesis'),
  ('27702', 'Arthroplasty, ankle; with implant (total ankle)'),
  ('27703', 'Arthroplasty, ankle; revision, total ankle'),
  ('27704', 'Removal of ankle implant'),
  ('20690', 'Application of a uniplane (pins or wires in 1 plane), unilateral, external fixation system'),
  ('20692', 'Application of a multiplane (pins or wires in more than 1 plane), unilateral, external fixation system (e.g., Ilizarov, Monticelli type)'),
  ('20693', 'Adjustment or revision of external fixation system requiring anesthesia'),
  ('20694', 'Removal, under anesthesia, of external fixation system'),
  ('20696', 'Application of multiplane external fixation with stereotactic computer-assisted adjustment (e.g., spatial frame); initial and subsequent alignment(s), assessment(s), and computation(s) of adjustment schedule(s)'),
  ('20697', 'Application of multiplane external fixation with stereotactic computer-assisted adjustment (e.g., spatial frame); exchange (i.e., removal and replacement) of strut, each'),
  ('27600', 'Decompression fasciotomy, leg; anterior and/or lateral compartments only'),
  ('27603', 'Incision and drainage, leg or ankle; deep abscess or hematoma'),
  ('27607', 'Incision (e.g., osteomyelitis or bone abscess), leg or ankle'),
  ('27610', 'Arthrotomy, ankle, including exploration, drainage, or removal of foreign body'),
  ('27620', 'Arthrotomy, ankle, with joint exploration, with or without biopsy, with or without removal of loose or foreign body'),
  ('27625', 'Arthrotomy, with synovectomy, ankle'),
  ('27756', 'Percutaneous skeletal fixation of tibial shaft fracture (with or without fibular fracture) (e.g., pins or screws)'),
  ('27758', 'Open treatment of tibial shaft fracture (with or without fibular fracture), with plate/screws, with or without cerclage'),
  ('27759', 'Treatment of tibial shaft fracture (with or without fibular fracture) by intramedullary implant, with or without interlocking screws and/or cerclage'),
  ('27762', 'Closed treatment of medial malleolus fracture; with manipulation, with or without skin or skeletal traction'),
  ('27766', 'Open treatment of medial malleolus fracture, includes internal fixation when performed'),
  ('27769', 'Open treatment of posterior malleolus fracture, includes internal fixation when performed'),
  ('27784', 'Open treatment of proximal fibula or shaft fracture, includes internal fixation when performed'),
  ('27792', 'Open treatment of distal fibular fracture (lateral malleolus), includes internal fixation when performed'),
  ('27814', 'Open treatment of bimalleolar ankle fracture, includes internal fixation when performed'),
  ('27822', 'Open treatment of trimalleolar ankle fracture, includes internal fixation when performed; without fixation of posterior lip'),
  ('27823', 'Open treatment of trimalleolar ankle fracture, includes internal fixation when performed; with fixation of posterior lip'),
  ('27826', 'Open treatment of fracture of weight bearing articular surface/portion of distal tibia (e.g., pilon or tibial plafond), with internal fixation when performed; of fibula only'),
  ('27829', 'Open treatment of distal tibiofibular joint (syndesmosis) disruption, includes internal fixation when performed'),
  ('27842', 'Closed treatment of ankle dislocation; requiring anesthesia, with or without percutaneous skeletal fixation'),
  ('27846', 'Open treatment of ankle dislocation; without repair or internal fixation'),
  ('27848', 'Open treatment of ankle dislocation; with repair or internal or external fixation'),
  ('28400', 'Closed treatment of calcaneal fracture; without manipulation'),
  ('28405', 'Closed treatment of calcaneal fracture; with manipulation'),
  ('28445', 'Open treatment of talus fracture, includes internal fixation when performed'),
  ('28446', 'Open osteochondral allograft, talus (includes obtaining grafts)'),
  ('28406', 'Percutaneous skeletal fixation of calcaneal fracture, with manipulation'),
  ('28415', 'Open treatment of calcaneal fracture, includes internal fixation when performed'),
  ('28420', 'Open treatment of calcaneal fracture, includes internal fixation when performed; with primary iliac or other autogenous bone graft (includes obtaining graft)'),
  ('28435', 'Closed treatment of talus fracture; with manipulation'),
  ('28436', 'Percutaneous skeletal fixation of talus fracture, with manipulation'),
  ('27827', 'Open treatment of fracture of weight bearing articular surface/portion of distal tibia (e.g., pilon or tibial plafond), with internal fixation when performed; of tibia only'),
  ('27828', 'Open treatment of fracture of weight bearing articular surface/portion of distal tibia (e.g., pilon or tibial plafond), with internal fixation when performed; of both tibia and fibula'),
  ('28456', 'Percutaneous skeletal fixation of tarsal bone fracture (except talus and calcaneus), with manipulation, each'),
  ('28465', 'Open treatment of tarsal bone fracture (except talus and calcaneus), includes internal fixation when performed, each'),
  ('28475', 'Closed treatment of metatarsal fracture; with manipulation, each'),
  ('28476', 'Percutaneous skeletal fixation of metatarsal fracture, with manipulation, each'),
  ('28485', 'Open treatment of metatarsal fracture, includes internal fixation when performed, each'),
  ('28496', 'Percutaneous skeletal fixation of fracture great toe, phalanx or phalanges, with manipulation'),
  ('28505', 'Open treatment of fracture, great toe, phalanx or phalanges, includes internal fixation when performed'),
  ('28515', 'Closed treatment of fracture, phalanx or phalanges, other than great toe; with manipulation, each'),
  ('28525', 'Open treatment of fracture, phalanx or phalanges, other than great toe, includes internal fixation when performed, each'),
  ('28531', 'Open treatment of sesamoid fracture, with or without internal fixation'),
  ('28545', 'Closed treatment of tarsal bone dislocation, other than talotarsal; requiring anesthesia'),
  ('28546', 'Percutaneous skeletal fixation of tarsal bone dislocation, other than talotarsal, with manipulation'),
  ('28555', 'Open treatment of tarsal bone dislocation, includes internal fixation when performed'),
  ('28575', 'Closed treatment of talotarsal joint dislocation; requiring anesthesia'),
  ('28576', 'Percutaneous skeletal fixation of talotarsal joint dislocation, with manipulation'),
  ('28585', 'Open treatment of talotarsal joint dislocation, includes internal fixation when performed'),
  ('28636', 'Percutaneous skeletal fixation of metatarsophalangeal joint dislocation, with manipulation'),
  ('28645', 'Open treatment of metatarsophalangeal joint dislocation, includes internal fixation when performed'),
  ('28666', 'Percutaneous skeletal fixation of interphalangeal joint dislocation, with manipulation'),
  ('28675', 'Open treatment of interphalangeal joint dislocation, includes internal fixation when performed'),
  ('28606', 'Percutaneous skeletal fixation of tarsometatarsal joint dislocation, with manipulation'),
  ('28615', 'Open treatment of tarsometatarsal joint dislocation, includes internal fixation when performed'),
  ('27650', 'Repair, primary, open or percutaneous, ruptured Achilles tendon'),
  ('27652', 'Repair, primary, open or percutaneous, ruptured Achilles tendon; with graft (includes obtaining graft)'),
  ('27654', 'Repair, secondary, Achilles tendon, with or without graft'),
  ('27658', 'Repair, flexor tendon, leg; primary, without graft, each tendon'),
  ('27664', 'Repair, extensor tendon, leg; primary, without graft, each tendon'),
  ('27675', 'Repair, dislocating peroneal tendons; without fibular osteotomy'),
  ('27676', 'Repair, dislocating peroneal tendons; with fibular osteotomy'),
  ('27685', 'Lengthening or shortening of tendon, leg or ankle; single tendon (separate procedure)'),
  ('27687', 'Gastrocnemius recession (e.g., Strayer procedure)'),
  ('27691', 'Transfer or transplant of single tendon (with muscle redirection or rerouting); deep (e.g., anterior tibial or posterior tibial through interosseous space)'),
  ('14001', 'Adjacent tissue transfer or rearrangement, trunk; defect 10.1 sq cm to 30.0 sq cm'),
  ('14020', 'Adjacent tissue transfer or rearrangement, scalp, arms and/or legs; defect 10 sq cm or less'),
  ('14350', 'Filleted finger or toe flap, including preparation of recipient site'),
  ('20670', 'Removal of implant; superficial (e.g., buried wire, pin or rod) (separate procedure)'),
  ('20680', 'Removal of implant; deep (e.g., buried wire, pin, screw, metal band, nail, rod, plate)'),
  ('20900', 'Bone graft, any donor area; minor or small (e.g., dowel or button)'),
  ('20902', 'Bone graft, any donor area; major or large'),
  ('20924', 'Tendon graft, from a distance (e.g., palmaris, toe extensor, plantaris)'),
  ('20926', 'Tissue grafts, other (e.g., paratenon, fat, dermis)'),
  ('27604', 'Incision and drainage, leg or ankle; infected bursa'),
  ('27618', 'Excision, tumor, soft tissue of leg or ankle area, subcutaneous; less than 3 cm'),
  ('27619', 'Excision, tumor, soft tissue of leg or ankle area, subfascial (e.g., intramuscular); less than 5 cm'),
  ('27630', 'Excision of lesion of tendon sheath or capsule (e.g., cyst or ganglion), leg and/or ankle'),
  ('28001', 'Incision and drainage, bursa, foot'),
  ('28002', 'Incision and drainage below fascia, with or without tendon sheath involvement, foot; single bursal space'),
  ('28005', 'Incision, bone cortex (e.g., osteomyelitis or bone abscess), foot'),
  ('28043', 'Excision, tumor, soft tissue of foot or toe, subcutaneous; less than 1.5 cm'),
  ('28050', 'Arthrotomy with biopsy; intertarsal or tarsometatarsal joint'),
  ('28052', 'Arthrotomy with biopsy; metatarsophalangeal joint'),
  ('28090', 'Excision of lesion, tendon, tendon sheath, or capsule (including synovectomy) (e.g., cyst or ganglion); foot'),
  ('27881', 'Amputation, leg, through tibia and fibula; with immediate fitting technique, including application of first cast'),
  ('27882', 'Amputation, leg, through tibia and fibula; open, circular (guillotine)'),
  ('27884', 'Amputation, leg, through tibia and fibula; secondary closure or scar revision'),
  ('27886', 'Amputation, leg, through tibia and fibula; re-amputation'),
  ('27888', 'Amputation, ankle, through malleoli of tibia and fibula (Syme, Pirogoff type procedures), with plastic closure and resection of nerves'),
  ('27889', 'Ankle disarticulation'),
  ('28800', 'Amputation, foot; midtarsal (e.g., Chopart type procedure)'),
  ('28805', 'Amputation, foot; transmetatarsal'),
  ('28810', 'Amputation, metatarsal, with toe, single'),
  ('28820', 'Amputation, toe; metatarsophalangeal joint'),
  ('28825', 'Amputation, toe; interphalangeal joint'),
  ('28035', 'Release, tarsal tunnel (posterior tibial nerve decompression)'),
  ('28055', 'Neurectomy, intrinsic musculature of foot'),
  ('28080', 'Excision, interdigital (Morton) neuroma, single, each'),
  ('64774', 'Excision of neuroma; cutaneous nerve, surgically identifiable'),
  ('64834', 'Suture of 1 nerve; hand or foot, common sensory nerve');

-- ---- MUSCULOSKELETAL ONCOLOGY ----
INSERT OR IGNORE INTO cpt_codes(code, description) VALUES
  ('22112', 'Partial excision of vertebral body, for intrinsic bony lesion, without decompression; thoracic, single vertebral segment'),
  ('22114', 'Partial excision of vertebral body, for intrinsic bony lesion, without decompression; lumbar, single vertebral segment'),
  ('22101', 'Partial excision of posterior vertebral component for intrinsic bony lesion; thoracic, single vertebral segment'),
  ('22102', 'Partial excision of posterior vertebral component for intrinsic bony lesion; lumbar, single vertebral segment'),
  ('27075', 'Radical resection of tumor; wing of ilium, 1 pubic or ischial ramus or symphysis pubis'),
  ('27076', 'Radical resection of tumor; ilium, including acetabulum, both pubic rami, or ischium and acetabulum'),
  ('27077', 'Radical resection of tumor; innominate bone, total'),
  ('27078', 'Radical resection of tumor; ischial tuberosity and greater trochanter of femur'),
  ('21936', 'Radical resection of tumor (e.g., sarcoma), soft tissue of back or flank; 5 cm or greater'),
  ('22905', 'Radical resection of tumor (e.g., sarcoma), soft tissue of abdominal wall; 5 cm or greater'),
  ('23078', 'Radical resection of tumor (e.g., sarcoma), soft tissue of shoulder area; 5 cm or greater'),
  ('24079', 'Radical resection of tumor (e.g., sarcoma), soft tissue of upper arm or elbow area; 5 cm or greater'),
  ('25078', 'Radical resection of tumor (e.g., sarcoma), soft tissue of forearm and/or wrist area; 3 cm or greater'),
  ('27059', 'Radical resection of tumor (e.g., sarcoma), soft tissue of pelvis and hip area; 5 cm or greater'),
  ('27364', 'Radical resection of tumor (e.g., sarcoma), soft tissue of thigh or knee area; 5 cm or greater'),
  ('27616', 'Radical resection of tumor (e.g., sarcoma), soft tissue of leg or ankle area; 5 cm or greater'),
  ('28047', 'Radical resection of tumor (e.g., sarcoma), soft tissue of foot or toe; 3 cm or greater'),
  ('23210', 'Radical resection of tumor; scapula'),
  ('23220', 'Radical resection of tumor; proximal humerus'),
  ('24150', 'Radical resection of tumor; shaft or distal humerus'),
  ('25170', 'Radical resection of tumor; radius or ulna'),
  ('27365', 'Radical resection of tumor; femur or knee'),
  ('27645', 'Radical resection of tumor; tibia'),
  ('15736', 'Muscle, myocutaneous, or fasciocutaneous flap; upper extremity'),
  ('15738', 'Muscle, myocutaneous, or fasciocutaneous flap; lower extremity'),
  ('24435', 'Repair of nonunion or malunion, humerus; with iliac or other autograft (includes obtaining graft)'),
  ('24515', 'Open treatment of humeral shaft fracture with plate/screws, with or without cerclage'),
  ('27506', 'Open treatment of femoral shaft fracture, with or without external fixation, with insertion of intramedullary implant, with or without cerclage and/or locking screws'),
  ('27472', 'Repair, nonunion or malunion, femur, distal to head and neck; with iliac or other autogenous bone graft (includes obtaining graft)'),
  ('27724', 'Repair of nonunion or malunion, tibia; with iliac or other autograft (includes obtaining graft)'),
  ('23491', 'Prophylactic treatment (nailing, pinning, plating or wiring) with or without methylmethacrylate; proximal humerus'),
  ('23616', 'Open treatment of proximal humeral fracture, includes internal fixation when performed; with proximal humeral prosthetic replacement'),
  ('24498', 'Prophylactic treatment (nailing, pinning, plating or wiring), with or without methylmethacrylate; humeral shaft'),
  ('27187', 'Prophylactic treatment (nailing, pinning, plating or wiring) with or without methylmethacrylate; femoral neck and proximal femur'),
  ('27244', 'Treatment of intertrochanteric, peritrochanteric, or subtrochanteric femoral fracture; with plate/screw type implant, with or without cerclage'),
  ('27245', 'Treatment of intertrochanteric, peritrochanteric, or subtrochanteric femoral fracture; with intramedullary implant, with or without interlocking screws and/or cerclage'),
  ('27495', 'Prophylactic treatment (nailing, pinning, plating, or wiring) with or without methylmethacrylate; femur'),
  ('27511', 'Open treatment of femoral supracondylar or transcondylar fracture without intercondylar extension, includes internal fixation when performed'),
  ('27513', 'Open treatment of femoral supracondylar or transcondylar fracture with intercondylar extension, includes internal fixation when performed'),
  ('27745', 'Prophylactic treatment (nailing, pinning, plating or wiring) with or without methylmethacrylate; tibia');

-- ---- SPORTS MEDICINE ----
INSERT OR IGNORE INTO cpt_codes(code, description) VALUES
  ('23450', 'Capsulorrhaphy, anterior; Putti-Platt procedure or Magnuson type operation'),
  ('23415', 'Coracoacromial ligament release, with or without acromioplasty'),
  ('23440', 'Resection or transplantation of long tendon of biceps'),
  ('23120', 'Claviculectomy; partial'),
  ('23550', 'Open treatment of acromioclavicular dislocation, acute or chronic'),
  ('23552', 'Open treatment of acromioclavicular dislocation, acute or chronic; with fascial graft (includes obtaining graft)'),
  ('29860', 'Arthroscopy, hip, diagnostic with or without synovial biopsy (separate procedure)'),
  ('29861', 'Arthroscopy, hip, surgical; with removal of loose body or foreign body'),
  ('29862', 'Arthroscopy, hip, surgical; with debridement/shaving of articular cartilage (chondroplasty), abrasion arthroplasty, and/or resection of labrum'),
  ('29863', 'Arthroscopy, hip, surgical; with synovectomy'),
  ('24345', 'Repair medial collateral ligament, elbow, with local tissue'),
  ('24346', 'Reconstruction medial collateral ligament, elbow, with tendon graft (includes harvesting of graft)'),
  ('27405', 'Repair, primary, torn ligament and/or capsule, knee; collateral'),
  ('27407', 'Repair, primary, torn ligament and/or capsule, knee; cruciate'),
  ('27409', 'Repair, primary, torn ligament and/or capsule, knee; collateral and cruciate ligaments'),
  ('27427', 'Ligamentous reconstruction (augmentation), knee; extra-articular'),
  ('27428', 'Ligamentous reconstruction (augmentation), knee; intra-articular (open)'),
  ('27429', 'Ligamentous reconstruction (augmentation), knee; intra-articular (open) and extra-articular'),
  ('29888', 'Arthroscopically aided anterior cruciate ligament repair/augmentation or reconstruction'),
  ('29889', 'Arthroscopically aided posterior cruciate ligament repair/augmentation or reconstruction'),
  ('27556', 'Open treatment of knee dislocation, includes internal fixation when performed; without primary ligamentous repair or augmentation/reconstruction'),
  ('27557', 'Open treatment of knee dislocation, includes internal fixation when performed; with primary ligamentous repair'),
  ('27558', 'Open treatment of knee dislocation, includes internal fixation when performed; with primary ligamentous repair, with augmentation/reconstruction'),
  ('27420', 'Reconstruction of dislocating patella (e.g., Hauser type procedure)'),
  ('27422', 'Reconstruction of dislocating patella; with extensor realignment and/or muscle advancement or release (e.g., Campbell, Goldwaite type procedure)'),
  ('27424', 'Reconstruction of dislocating patella; with patellectomy'),
  ('27425', 'Lateral retinacular release, open'),
  ('29873', 'Arthroscopy, knee, surgical; with lateral release'),
  ('27566', 'Open treatment of patellar dislocation, with or without partial or total patellectomy'),
  ('27412', 'Autologous chondrocyte implantation, knee'),
  ('27415', 'Osteochondral allograft, knee, open'),
  ('29877', 'Arthroscopy, knee, surgical; debridement/shaving of articular cartilage (chondroplasty)'),
  ('29885', 'Arthroscopy, knee, surgical; drilling for osteochondritis dissecans with bone grafting, with or without internal fixation'),
  ('29886', 'Arthroscopy, knee, surgical; drilling for intact osteochondritis dissecans lesion'),
  ('29887', 'Arthroscopy, knee, surgical; drilling for intact osteochondritis dissecans lesion with internal fixation'),
  ('29879', 'Arthroscopy, knee, surgical; abrasion arthroplasty (includes chondroplasty where necessary)'),
  ('29866', 'Arthroscopy, knee, surgical; osteochondral autograft(s) (e.g., mosaicplasty) (includes harvesting of the autograft(s))'),
  ('29867', 'Arthroscopy, knee, surgical; osteochondral allograft (e.g., mosaicplasty)'),
  ('27403', 'Arthrotomy with meniscus repair, knee'),
  ('29868', 'Arthroscopy, knee, surgical; meniscal transplantation (includes arthrotomy for meniscal insertion)'),
  ('29880', 'Arthroscopy, knee, surgical; with meniscectomy (medial AND lateral, including any meniscal shaving)'),
  ('29881', 'Arthroscopy, knee, surgical; with meniscectomy (medial OR lateral, including any meniscal shaving)'),
  ('29882', 'Arthroscopy, knee, surgical; with meniscus repair (medial OR lateral)'),
  ('29883', 'Arthroscopy, knee, surgical; with meniscus repair (medial AND lateral)'),
  ('29894', 'Arthroscopy, ankle (tibiotalar and fibulotalar joints), surgical; with removal of loose body or foreign body');

-- ---- SPINE ----
INSERT OR IGNORE INTO cpt_codes(code, description) VALUES
  ('22325', 'Open treatment and/or reduction of vertebral fracture(s) and/or dislocation(s), posterior approach; lumbar'),
  ('22326', 'Open treatment and/or reduction of vertebral fracture(s) and/or dislocation(s), posterior approach; cervical'),
  ('22327', 'Open treatment and/or reduction of vertebral fracture(s) and/or dislocation(s), posterior approach; thoracic'),
  ('22551', 'Arthrodesis, anterior interbody, including disc space preparation, discectomy, osteophytectomy and decompression; cervical below C2'),
  ('22554', 'Arthrodesis, anterior interbody technique, including minimal discectomy to prepare interspace; cervical below C2'),
  ('22558', 'Arthrodesis, anterior interbody technique, including minimal discectomy to prepare interspace; lumbar'),
  ('22595', 'Arthrodesis, posterior technique, Atlas-axis (C1-C2)'),
  ('22600', 'Arthrodesis, posterior or posterolateral technique, single level; cervical below C-2'),
  ('22610', 'Arthrodesis, posterior or posterolateral technique, single level; thoracic'),
  ('22612', 'Arthrodesis, posterior or posterolateral technique, single level; lumbar'),
  ('22802', 'Arthrodesis, posterior, for spinal deformity, with or without cast; 7 to 12 vertebral segments'),
  ('22804', 'Arthrodesis, posterior, for spinal deformity, with or without cast; 13 or more vertebral segments'),
  ('22630', 'Arthrodesis, posterior interbody technique, including laminectomy and/or discectomy to prepare interspace; lumbar, single interspace'),
  ('22633', 'Arthrodesis, combined posterior or posterolateral technique with posterior interbody technique; lumbar, single interspace and segment'),
  ('22830', 'Exploration of spinal fusion'),
  ('22840', 'Posterior non-segmental instrumentation (e.g., Harrington rod technique, pedicle fixation across 1 interspace, atlantoaxial transarticular screw fixation)'),
  ('22842', 'Posterior segmental instrumentation (e.g., pedicle fixation, dual rods with multiple hooks and sublaminar wires); 3 to 6 vertebral segments'),
  ('22843', 'Posterior segmental instrumentation (e.g., pedicle fixation, dual rods with multiple hooks and sublaminar wires); 7 to 12 vertebral segments'),
  ('22844', 'Posterior segmental instrumentation (e.g., pedicle fixation, dual rods with multiple hooks and sublaminar wires); 13 or more vertebral segments'),
  ('22845', 'Anterior instrumentation; 2 to 3 vertebral segments'),
  ('22846', 'Anterior instrumentation; 4 to 7 vertebral segments'),
  ('22848', 'Pelvic fixation (attachment of caudal end of instrumentation to pelvic bony structures) other than sacrum'),
  ('22849', 'Reinsertion of spinal fixation device'),
  ('22851', 'Application of intervertebral biomechanical device(s) (e.g., synthetic cage(s), methylmethacrylate) to vertebral defect or interspace'),
  ('22850', 'Removal of posterior non-segmental instrumentation (e.g., Harrington rod)'),
  ('22852', 'Removal of posterior segmental instrumentation'),
  ('22855', 'Removal of anterior instrumentation'),
  ('63001', 'Laminectomy with exploration and/or decompression of spinal cord and/or cauda equina, without facetectomy, foraminotomy or discectomy; 1 or 2 vertebral segments, cervical'),
  ('63003', 'Laminectomy with exploration and/or decompression of spinal cord and/or cauda equina, without facetectomy, foraminotomy or discectomy; 1 or 2 vertebral segments, thoracic'),
  ('63005', 'Laminectomy with exploration and/or decompression of spinal cord and/or cauda equina, without facetectomy, foraminotomy or discectomy; 1 or 2 vertebral segments, lumbar'),
  ('63012', 'Laminectomy with removal of abnormal facets and/or pars inter-articularis with decompression of cauda equina and nerve roots for spondylolisthesis, lumbar (Gill type procedure)'),
  ('63015', 'Laminectomy with exploration and/or decompression of spinal cord and/or cauda equina, without facetectomy, foraminotomy or discectomy; more than 2 vertebral segments, cervical'),
  ('63016', 'Laminectomy with exploration and/or decompression of spinal cord and/or cauda equina, without facetectomy, foraminotomy or discectomy; more than 2 vertebral segments, thoracic'),
  ('63017', 'Laminectomy with exploration and/or decompression of spinal cord and/or cauda equina, without facetectomy, foraminotomy or discectomy; more than 2 vertebral segments, lumbar'),
  ('63020', 'Laminotomy (hemilaminectomy) with decompression of nerve root(s), including partial facetectomy, foraminotomy and/or excision of herniated intervertebral disc; 1 interspace, cervical'),
  ('63030', 'Laminotomy (hemilaminectomy) with decompression of nerve root(s), including partial facetectomy, foraminotomy and/or excision of herniated intervertebral disc; 1 interspace, lumbar'),
  ('63045', 'Laminectomy, facetectomy and foraminotomy (unilateral or bilateral with decompression of spinal cord, cauda equina and/or nerve root(s)); single vertebral segment, cervical'),
  ('63047', 'Laminectomy, facetectomy and foraminotomy (unilateral or bilateral with decompression of spinal cord, cauda equina and/or nerve root(s)); single vertebral segment, lumbar'),
  ('63050', 'Laminoplasty, cervical, with decompression of the spinal cord, 2 or more vertebral segments'),
  ('63051', 'Laminoplasty, cervical, with decompression of the spinal cord, 2 or more vertebral segments; with reconstruction of the posterior bony elements'),
  ('63055', 'Transpedicular approach with decompression of spinal cord, equina and/or nerve root(s) (e.g., herniated intervertebral disc); single segment, thoracic'),
  ('63081', 'Vertebral corpectomy (vertebral body resection), partial or complete, anterior approach; cervical, single segment'),
  ('63085', 'Vertebral corpectomy (vertebral body resection), partial or complete, transthoracic approach; thoracic, single segment'),
  ('63086', 'Vertebral corpectomy (vertebral body resection), partial or complete, transthoracic approach; thoracic, each additional segment');

-- ---- TRAUMA ----
INSERT OR IGNORE INTO cpt_codes(code, description) VALUES
  ('23500', 'Closed treatment of clavicular fracture; without manipulation'),
  ('23515', 'Open treatment of clavicular fracture, includes internal fixation when performed'),
  ('23520', 'Closed treatment of sternoclavicular dislocation; without manipulation'),
  ('23530', 'Open treatment of sternoclavicular dislocation, acute or chronic'),
  ('23532', 'Open treatment of sternoclavicular dislocation, acute or chronic; with fascial graft (includes obtaining graft)'),
  ('23540', 'Closed treatment of acromioclavicular dislocation; without manipulation'),
  ('23570', 'Closed treatment of scapular fracture; without manipulation'),
  ('23585', 'Open treatment of scapular fracture (body, glenoid or acromion), includes internal fixation when performed'),
  ('23600', 'Closed treatment of proximal humeral (surgical or anatomical neck) fracture; without manipulation'),
  ('23615', 'Open treatment of proximal humeral (surgical or anatomical neck) fracture, includes internal fixation when performed'),
  ('23620', 'Closed treatment of greater humeral tuberosity fracture; without manipulation'),
  ('23630', 'Open treatment of greater humeral tuberosity fracture, includes internal fixation when performed'),
  ('23660', 'Open treatment of acute shoulder dislocation'),
  ('23670', 'Open treatment of shoulder dislocation, with fracture of greater humeral tuberosity, includes internal fixation when performed'),
  ('23680', 'Open treatment of shoulder dislocation, with surgical or anatomical neck fracture, includes internal fixation when performed'),
  ('24500', 'Closed treatment of humeral shaft fracture; without manipulation'),
  ('24516', 'Treatment of humeral shaft fracture, with insertion of intramedullary implant, with or without cerclage and/or locking screws'),
  ('24530', 'Closed treatment of supracondylar or transcondylar humeral fracture; without manipulation'),
  ('24538', 'Percutaneous skeletal fixation of supracondylar or transcondylar humeral fracture, with or without intercondylar extension'),
  ('24545', 'Open treatment of humeral supracondylar or transcondylar fracture, includes internal fixation when performed; without intercondylar extension'),
  ('24546', 'Open treatment of humeral supracondylar or transcondylar fracture, includes internal fixation when performed; with intercondylar extension'),
  ('24560', 'Closed treatment of humeral epicondylar fracture, medial or lateral; without manipulation'),
  ('24566', 'Percutaneous skeletal fixation of humeral epicondylar fracture, medial or lateral, with manipulation'),
  ('24575', 'Open treatment of humeral epicondylar fracture, medial or lateral, includes internal fixation when performed'),
  ('24576', 'Closed treatment of humeral condylar fracture, medial or lateral; without manipulation'),
  ('24579', 'Open treatment of humeral condylar fracture, medial or lateral, includes internal fixation when performed'),
  ('24582', 'Percutaneous skeletal fixation of humeral condylar fracture, medial or lateral, with manipulation'),
  ('24586', 'Open treatment of periarticular fracture and/or dislocation of the elbow (fracture distal humerus and proximal ulna and/or proximal radius)'),
  ('24587', 'Open treatment of periarticular fracture and/or dislocation of the elbow; with implant arthroplasty'),
  ('24615', 'Open treatment of acute or chronic elbow dislocation'),
  ('24635', 'Open treatment of Monteggia type of fracture dislocation at elbow, includes internal fixation when performed'),
  ('24650', 'Closed treatment of radial head or neck fracture; without manipulation'),
  ('24665', 'Open treatment of radial head or neck fracture, includes internal fixation or radial head excision when performed'),
  ('24666', 'Open treatment of radial head or neck fracture, includes internal fixation or radial head excision; with radial head prosthetic replacement'),
  ('24670', 'Closed treatment of ulnar fracture, proximal end (e.g., olecranon or coronoid process); without manipulation'),
  ('24685', 'Open treatment of ulnar fracture, proximal end (e.g., olecranon or coronoid process), includes internal fixation when performed'),
  ('25500', 'Closed treatment of radial shaft fracture; without manipulation'),
  ('25515', 'Open treatment of radial shaft fracture, includes internal fixation when performed'),
  ('25525', 'Open treatment of radial shaft fracture, includes internal fixation when performed, and closed treatment of distal radioulnar joint dislocation (Galeazzi fracture/dislocation)'),
  ('25526', 'Open treatment of radial shaft fracture, includes internal fixation, and open treatment of distal radioulnar joint dislocation (Galeazzi fracture/dislocation)'),
  ('25530', 'Closed treatment of ulnar shaft fracture; without manipulation'),
  ('25545', 'Open treatment of ulnar shaft fracture, includes internal fixation when performed'),
  ('25560', 'Closed treatment of radial and ulnar shaft fractures; without manipulation'),
  ('25574', 'Open treatment of radial AND ulnar shaft fractures, with internal fixation when performed; of radius OR ulna'),
  ('25575', 'Open treatment of radial AND ulnar shaft fractures, with internal fixation when performed; of radius AND ulna'),
  ('25600', 'Closed treatment of distal radial fracture (e.g., Colles or Smith type) or epiphyseal separation; without manipulation'),
  ('25606', 'Percutaneous skeletal fixation of distal radial fracture or epiphyseal separation'),
  ('25607', 'Open treatment of distal radial extra-articular fracture or epiphyseal separation, with internal fixation'),
  ('25608', 'Open treatment of distal radial intra-articular fracture or epiphyseal separation; with internal fixation of 2 fragments'),
  ('25609', 'Open treatment of distal radial intra-articular fracture or epiphyseal separation; with internal fixation of 3 or more fragments'),
  ('25622', 'Closed treatment of carpal scaphoid (navicular) fracture; without manipulation'),
  ('25628', 'Open treatment of carpal scaphoid (navicular) fracture, includes internal fixation when performed'),
  ('25630', 'Closed treatment of carpal bone fracture (excluding carpal scaphoid); without manipulation, each bone'),
  ('25645', 'Open treatment of carpal bone fracture (other than carpal scaphoid), each bone'),
  ('25650', 'Closed treatment of ulnar styloid fracture'),
  ('25651', 'Percutaneous skeletal fixation of ulnar styloid fracture'),
  ('25652', 'Open treatment of ulnar styloid fracture'),
  ('25670', 'Open treatment of radiocarpal or intercarpal dislocation, 1 or more bones'),
  ('25671', 'Percutaneous skeletal fixation of distal radioulnar dislocation'),
  ('25676', 'Open treatment of distal radioulnar dislocation, acute or chronic'),
  ('25685', 'Open treatment of trans-scaphoperilunar type of fracture dislocation'),
  ('25695', 'Open treatment of lunate dislocation'),
  ('27193', 'Closed treatment of pelvic ring fracture, dislocation, diastasis or subluxation; without manipulation'),
  ('27200', 'Closed treatment of coccygeal fracture'),
  ('27202', 'Open treatment of coccygeal fracture'),
  ('27215', 'Open treatment of iliac spine(s), tuberosity avulsion, or iliac wing fracture(s), unilateral, includes internal fixation when performed'),
  ('27216', 'Percutaneous skeletal fixation of posterior pelvic bone fracture and/or dislocation for fracture patterns that disrupt the pelvic ring, unilateral'),
  ('27217', 'Open treatment of anterior pelvic bone fracture and/or dislocation for fracture patterns that disrupt the pelvic ring, unilateral, includes internal fixation when performed'),
  ('27218', 'Open treatment of posterior pelvic bone fracture and/or dislocation, for fracture patterns that disrupt the pelvic ring, unilateral, includes internal fixation when performed'),
  ('27220', 'Closed treatment of acetabulum (hip socket) fracture(s); without manipulation'),
  ('27226', 'Open treatment of posterior or anterior acetabular wall fracture, with internal fixation'),
  ('27227', 'Open treatment of acetabular fracture(s) involving anterior or posterior (one) column, with internal fixation'),
  ('27228', 'Open treatment of acetabular fracture(s) involving anterior and posterior (two) columns, with internal fixation'),
  ('27230', 'Closed treatment of femoral fracture, proximal end, neck; without manipulation'),
  ('27235', 'Percutaneous skeletal fixation of femoral fracture, proximal end, neck'),
  ('27238', 'Closed treatment of intertrochanteric, peritrochanteric, or subtrochanteric femoral fracture; without manipulation'),
  ('27246', 'Closed treatment of greater trochanteric fracture, without manipulation'),
  ('27248', 'Open treatment of greater trochanteric fracture, includes internal fixation when performed'),
  ('27253', 'Open treatment of hip dislocation, traumatic, without internal fixation'),
  ('27254', 'Open treatment of hip dislocation, traumatic, with acetabular wall and femoral head fracture, with or without internal or external fixation'),
  ('27256', 'Treatment of spontaneous hip dislocation (developmental, including congenital or pathological), by abduction, splint or traction; without anesthesia, without manipulation'),
  ('27258', 'Open treatment of spontaneous hip dislocation (developmental, including congenital or pathological), replacement of femoral head in acetabulum (including tenotomy, etc.)'),
  ('27259', 'Open treatment of spontaneous hip dislocation (developmental), replacement of femoral head in acetabulum; with femoral shaft shortening'),
  ('27500', 'Closed treatment of femoral shaft fracture, without manipulation'),
  ('27501', 'Closed treatment of supracondylar or transcondylar femoral fracture with or without intercondylar extension, without manipulation'),
  ('27507', 'Open treatment of femoral shaft fracture with plate/screws, with or without cerclage'),
  ('27508', 'Closed treatment of femoral fracture, distal end, medial or lateral condyle, without manipulation'),
  ('27509', 'Percutaneous skeletal fixation of femoral fracture, distal end, medial or lateral condyle, or supracondylar or transcondylar, with or without intercondylar extension, or distal femoral epiphyseal separation'),
  ('27514', 'Open treatment of femoral fracture, distal end, medial or lateral condyle, includes internal fixation when performed'),
  ('27516', 'Closed treatment of distal femoral epiphyseal separation; without manipulation'),
  ('27519', 'Open treatment of distal femoral epiphyseal separation, includes internal fixation when performed'),
  ('27520', 'Closed treatment of patellar fracture, without manipulation'),
  ('27524', 'Open treatment of patellar fracture, with internal fixation and/or partial or complete patellectomy and soft tissue repair'),
  ('27530', 'Closed treatment of tibial fracture, proximal (plateau); without manipulation'),
  ('27535', 'Open treatment of tibial fracture, proximal (plateau); unicondylar, includes internal fixation when performed'),
  ('27536', 'Open treatment of tibial fracture, proximal (plateau); bicondylar, with or without internal fixation'),
  ('27540', 'Open treatment of intercondylar spine(s) and/or tuberosity fracture(s) of the knee, includes internal fixation when performed'),
  ('27750', 'Closed treatment of tibial shaft fracture (with or without fibular fracture); without manipulation'),
  ('27760', 'Closed treatment of medial malleolus fracture; without manipulation'),
  ('27780', 'Closed treatment of proximal fibula or shaft fracture; without manipulation'),
  ('27786', 'Closed treatment of distal fibular fracture (lateral malleolus); without manipulation'),
  ('27808', 'Closed treatment of bimalleolar ankle fracture; without manipulation'),
  ('27816', 'Closed treatment of trimalleolar ankle fracture; without manipulation'),
  ('27824', 'Closed treatment of fracture of weight bearing articular portion of distal tibia (e.g., pilon or tibial plafond); without manipulation'),
  ('27832', 'Open treatment of proximal tibiofibular joint dislocation, includes internal fixation when performed, or with excision of proximal fibula'),
  ('28430', 'Closed treatment of talus fracture; without manipulation'),
  ('28450', 'Treatment of tarsal bone fracture (except talus and calcaneus); without manipulation, each'),
  ('28470', 'Closed treatment of metatarsal fracture; without manipulation, each'),
  ('28490', 'Closed treatment of fracture great toe, phalanx or phalanges; without manipulation'),
  ('28510', 'Closed treatment of fracture, phalanx or phalanges, other than great toe; without manipulation, each'),
  ('28530', 'Closed treatment of sesamoid fracture'),
  ('23485', 'Osteotomy, clavicle, with or without internal fixation; with bone graft for nonunion or malunion (includes obtaining graft and/or necessary fixation)'),
  ('24400', 'Osteotomy, humerus, with or without internal fixation'),
  ('24430', 'Repair of nonunion or malunion, humerus; without graft (e.g., compression technique)'),
  ('25400', 'Repair of nonunion or malunion, radius OR ulna; without graft (e.g., compression technique)'),
  ('25405', 'Repair of nonunion or malunion, radius OR ulna; with autograft (includes obtaining graft)'),
  ('25415', 'Repair of nonunion or malunion, radius AND ulna; without graft (e.g., compression technique)'),
  ('25420', 'Repair of nonunion or malunion, radius AND ulna; with autograft (includes obtaining graft)'),
  ('25425', 'Repair of defect with autograft; radius OR ulna'),
  ('25426', 'Repair of defect with autograft; radius AND ulna'),
  ('27161', 'Osteotomy, femoral neck (separate procedure)'),
  ('27165', 'Osteotomy, intertrochanteric or subtrochanteric including internal or external fixation and/or cast'),
  ('27170', 'Bone graft, femoral head, neck, intertrochanteric or subtrochanteric area (includes obtaining bone graft)'),
  ('27470', 'Repair, nonunion or malunion, femur, distal to head and neck; without graft (e.g., compression technique)'),
  ('27720', 'Repair of nonunion or malunion, tibia; without graft (e.g., compression technique)'),
  ('27722', 'Repair of nonunion or malunion, tibia; with sliding graft'),
  ('27725', 'Repair of nonunion or malunion, tibia; by synostosis, with fibula, any method'),
  ('11010', 'Debridement including removal of foreign material at the site of an open fracture and/or an open dislocation; skin and subcutaneous tissues'),
  ('11011', 'Debridement including removal of foreign material at the site of an open fracture and/or an open dislocation; skin, subcutaneous tissue, muscle fascia, and muscle'),
  ('11012', 'Debridement, including removal of foreign material at the site of an open fracture and/or an open dislocation; skin, subcutaneous tissue, muscle fascia, muscle, and bone'),
  ('11040', 'Debridement; skin, partial thickness'),
  ('11041', 'Debridement; skin, full thickness'),
  ('11042', 'Debridement, subcutaneous tissue (includes epidermis and dermis if performed); first 20 sq cm or less'),
  ('11043', 'Debridement, muscle and/or fascia (includes epidermis, dermis, and subcutaneous tissue if performed); first 20 sq cm or less'),
  ('11044', 'Debridement, bone (includes epidermis, dermis, subcutaneous tissue, muscle and/or fascia if performed); first 20 sq cm or less'),
  ('25020', 'Decompression fasciotomy, forearm and/or wrist, flexor OR extensor compartment; without debridement of non-viable muscle and/or nerve'),
  ('25023', 'Decompression fasciotomy, forearm and/or wrist, flexor OR extensor compartment; with debridement of non-viable muscle and/or nerve'),
  ('25024', 'Decompression fasciotomy, forearm and/or wrist, flexor AND extensor compartment; without debridement of non-viable muscle and/or nerve'),
  ('25025', 'Decompression fasciotomy, forearm and/or wrist, flexor AND extensor compartment; with debridement of non-viable muscle and/or nerve'),
  ('27601', 'Decompression fasciotomy, leg; posterior compartment(s) only'),
  ('27602', 'Decompression fasciotomy, leg; anterior and/or lateral, and posterior compartment(s)');

-- ---- PEDIATRIC ----
INSERT OR IGNORE INTO cpt_codes(code, description) VALUES
  ('27605', 'Tenotomy, percutaneous, Achilles tendon (separate procedure); local anesthesia'),
  ('27612', 'Arthrotomy, posterior capsular release, ankle, with or without Achilles tendon lengthening'),
  ('27686', 'Lengthening or shortening of tendon, leg or ankle; multiple tendons (through same incision), each'),
  ('27692', 'Transfer or transplant of single tendon (with muscle redirection or rerouting)'),
  ('28232', 'Tenotomy, open, tendon flexor; toe, single tendon (separate procedure)'),
  ('28234', 'Tenotomy, open, extensor, foot or toe, each tendon'),
  ('28240', 'Tenotomy, lengthening, or release, abductor hallucis muscle'),
  ('28250', 'Division of plantar fascia and muscle (e.g., Steindler stripping) (separate procedure)'),
  ('28264', 'Capsulotomy, midtarsal (e.g., Heyman type procedure)'),
  ('28270', 'Capsulotomy; metatarsophalangeal joint, with or without tenorrhaphy, each joint (separate procedure)'),
  ('28272', 'Capsulotomy; interphalangeal joint, each joint (separate procedure)'),
  ('28280', 'Syndactylization, toes (e.g., webbing or Kelikian type procedure)'),
  ('28293', 'Correction, hallux valgus (bunion), with or without sesamoidectomy; resection of joint with implant'),
  ('28294', 'Correction, hallux valgus (bunion), with or without sesamoidectomy; with tendon transplants (Joplin type procedure)'),
  ('28299', 'Correction, hallux valgus (bunion), with or without sesamoidectomy; by double osteotomy'),
  ('28302', 'Osteotomy; talus'),
  ('28304', 'Osteotomy, tarsal bones, other than calcaneus or talus'),
  ('28305', 'Osteotomy, tarsal bones, other than calcaneus or talus; with autograft (includes obtaining graft) (e.g., Fowler type)'),
  ('28307', 'Osteotomy, with or without lengthening, shortening or angular correction, metatarsal; first metatarsal with autograft (other than first toe)'),
  ('28308', 'Osteotomy, with or without lengthening, shortening or angular correction, metatarsal; other than first metatarsal, each'),
  ('28309', 'Osteotomy, with or without lengthening, shortening or angular correction, metatarsal; multiple (e.g., Swanson type cavus foot procedure)'),
  ('28312', 'Osteotomy, shortening, angular or rotational correction; other phalanges, any toe'),
  ('28313', 'Reconstruction, angular deformity of toe, soft tissue procedures only (e.g., overlapping second toe, fifth toe, curly toes)'),
  ('28340', 'Reconstruction, toe, macrodactyly; soft tissue resection'),
  ('28341', 'Reconstruction, toe, macrodactyly; requiring bone resection'),
  ('28344', 'Reconstruction, toe(s); polydactyly'),
  ('28345', 'Reconstruction, toe(s); syndactyly, with or without skin graft(s), each web'),
  ('28360', 'Reconstruction, cleft foot'),
  ('28260', 'Capsulotomy, midfoot; medial release only (separate procedure)'),
  ('28261', 'Capsulotomy, midfoot; with tendon lengthening'),
  ('28262', 'Capsulotomy, midfoot; extensive, including posterior talotibial capsulotomy and tendon(s) lengthening (e.g., resistant clubfoot deformity)'),
  ('29450', 'Application of clubfoot cast with molding or manipulation, long or short leg'),
  ('29750', 'Wedging of clubfoot cast'),
  ('24410', 'Multiple osteotomies with realignment on intramedullary rod, humeral shaft (Sofield type procedure)'),
  ('24420', 'Osteoplasty, humerus (e.g., shortening or lengthening)'),
  ('24470', 'Hemiepiphyseal arrest (e.g., cubitus varus or valgus, distal humerus)'),
  ('25370', 'Multiple osteotomies, with realignment on intramedullary rod (Sofield type procedure); radius OR ulna'),
  ('25375', 'Multiple osteotomies, with realignment on intramedullary rod (Sofield type procedure); radius and ulna'),
  ('25390', 'Osteoplasty, radius OR ulna; shortening'),
  ('25391', 'Osteoplasty, radius OR ulna; lengthening with autograft'),
  ('25392', 'Osteoplasty, radius AND ulna; shortening'),
  ('25393', 'Osteoplasty, radius AND ulna; lengthening with autograft'),
  ('25394', 'Osteoplasty, carpal bone, shortening'),
  ('27454', 'Osteotomy, multiple, with realignment on intramedullary rod, femoral shaft (e.g., Sofield type procedure)'),
  ('27455', 'Osteotomy, proximal tibia, including fibular excision or osteotomy (includes correction of genu varus or genu valgus); before epiphyseal closure'),
  ('27465', 'Osteoplasty, femur; shortening'),
  ('27466', 'Osteoplasty, femur; lengthening'),
  ('27468', 'Osteoplasty, femur; combined, lengthening and shortening with femoral segment transfer'),
  ('27475', 'Arrest, epiphyseal, any method (e.g., epiphysiodesis); distal femur'),
  ('27477', 'Arrest, epiphyseal, any method (e.g., epiphysiodesis); tibia and fibula, proximal'),
  ('27479', 'Arrest, epiphyseal, any method (e.g., epiphysiodesis); combined distal femur, proximal tibia and fibula'),
  ('27485', 'Arrest, hemiepiphyseal, distal femur or proximal tibia or fibula (e.g., genu varus or valgus)'),
  ('27712', 'Osteotomy; multiple, with realignment on intramedullary rod (e.g., Sofield type procedure)'),
  ('27715', 'Osteoplasty, tibia and fibula, lengthening or shortening'),
  ('27727', 'Repair of congenital pseudarthrosis, tibia'),
  ('27730', 'Arrest, epiphyseal (epiphysiodesis), open; distal tibia'),
  ('27732', 'Arrest, epiphyseal (epiphysiodesis), open; distal fibula'),
  ('27734', 'Arrest, epiphyseal (epiphysiodesis), open; distal tibia and fibula'),
  ('27740', 'Arrest, epiphyseal (epiphysiodesis), any method, combined, proximal and distal tibia and fibula'),
  ('27742', 'Arrest, epiphyseal (epiphysiodesis), any method, combined, proximal and distal tibia and fibula; and distal femur'),
  ('22800', 'Arthrodesis, posterior, for spinal deformity, with or without cast; up to 6 vertebral segments'),
  ('22808', 'Arthrodesis, anterior, for spinal deformity, with or without cast; 2 to 3 vertebral segments'),
  ('22810', 'Arthrodesis, anterior, for spinal deformity, with or without cast; 4 to 7 vertebral segments'),
  ('22812', 'Arthrodesis, anterior, for spinal deformity, with or without cast; 8 or more vertebral segments'),
  ('22212', 'Osteotomy of spine, posterior or posterolateral approach, 1 vertebral segment; thoracic'),
  ('22214', 'Osteotomy of spine, posterior or posterolateral approach, 1 vertebral segment; lumbar'),
  ('22216', 'Osteotomy of spine, posterior or posterolateral approach, 1 vertebral segment; each additional vertebral segment (list separately in addition to primary procedure)'),
  ('22841', 'Internal spinal fixation by wiring of spinous processes (list separately in addition to code for primary procedure)'),
  ('22847', 'Anterior instrumentation; 8 or more vertebral segments'),
  ('24535', 'Closed treatment of supracondylar or transcondylar humeral fracture; with manipulation, with or without skin or skeletal traction'),
  ('24565', 'Closed treatment of humeral epicondylar fracture, medial or lateral; with manipulation'),
  ('24577', 'Closed treatment of humeral condylar fracture, medial or lateral; with manipulation'),
  ('24620', 'Closed treatment of Monteggia type of fracture dislocation at elbow, with manipulation'),
  ('24640', 'Closed treatment of radial head subluxation in child, nursemaid elbow, with manipulation'),
  ('24655', 'Closed treatment of radial head or neck fracture; with manipulation'),
  ('25505', 'Closed treatment of radial shaft fracture; with manipulation'),
  ('25520', 'Closed treatment of radial shaft fracture and closed treatment of dislocation of distal radioulnar joint (Galeazzi fracture/dislocation)'),
  ('25535', 'Closed treatment of ulnar shaft fracture; with manipulation'),
  ('25565', 'Closed treatment of radial and ulnar shaft fractures; with manipulation'),
  ('25605', 'Closed treatment of distal radial fracture (e.g., Colles or Smith type) or epiphyseal separation; with manipulation'),
  ('27502', 'Closed treatment of femoral shaft fracture, with manipulation, with or without skin or skeletal traction'),
  ('27140', 'Osteotomy and transfer of greater trochanter of femur (separate procedure)'),
  ('27147', 'Osteotomy, iliac, acetabular or innominate bone; with open reduction of hip'),
  ('27151', 'Osteotomy, iliac, acetabular or innominate bone; with femoral osteotomy'),
  ('27156', 'Osteotomy, iliac, acetabular or innominate bone; with femoral osteotomy and with open reduction of hip'),
  ('27158', 'Osteotomy, pelvis, bilateral (e.g., congenital malformation)'),
  ('27175', 'Treatment of slipped femoral epiphysis; by traction, without reduction'),
  ('27176', 'Treatment of slipped femoral epiphysis; by single or multiple pinning, in situ'),
  ('27177', 'Open treatment of slipped femoral epiphysis; single or multiple pinning or bone graft (includes obtaining graft)'),
  ('27178', 'Open treatment of slipped femoral epiphysis; closed manipulation with single or multiple pinning'),
  ('27179', 'Open treatment of slipped femoral epiphysis; osteoplasty of femoral neck (Heyman type procedure)'),
  ('27181', 'Open treatment of slipped femoral epiphysis; osteotomy and internal fixation'),
  ('23400', 'Scapulopexy (e.g., Sprengels deformity or for paralysis)'),
  ('23405', 'Tenotomy, shoulder area; single tendon'),
  ('24301', 'Muscle or tendon transfer, any type, upper arm or elbow, single'),
  ('24305', 'Tendon lengthening, upper arm or elbow, each tendon'),
  ('24310', 'Tenotomy, open, elbow to shoulder, each tendon'),
  ('24320', 'Tenoplasty, with muscle transfer, with or without free graft, elbow to shoulder, single (Seddon-Brookes type procedure)'),
  ('24330', 'Flexor-plasty, elbow (e.g., Steindler type advancement)'),
  ('24331', 'Flexor-plasty, elbow (e.g., Steindler type advancement); with extensor advancement'),
  ('25280', 'Lengthening or shortening of flexor or extensor tendon, forearm and/or wrist, single, each tendon'),
  ('25290', 'Tenotomy, open, flexor or extensor tendon, forearm and/or wrist, single, each tendon'),
  ('25295', 'Tenolysis, flexor or extensor tendon, forearm and/or wrist, single, each tendon'),
  ('25300', 'Tenodesis at wrist; flexors of fingers'),
  ('25301', 'Tenodesis at wrist; extensors of fingers'),
  ('25310', 'Tendon transplantation or transfer, flexor or extensor, forearm and/or wrist, single; each tendon'),
  ('25312', 'Tendon transplantation or transfer, flexor or extensor, forearm and/or wrist, single; with tendon graft(s) (includes obtaining graft), each tendon'),
  ('25315', 'Flexor origin slide (e.g., for cerebral palsy, Volkmann contracture), forearm and/or wrist'),
  ('25316', 'Flexor origin slide (e.g., for cerebral palsy, Volkmann contracture), forearm and/or wrist; with tendon(s) transfer'),
  ('27000', 'Tenotomy, adductor of hip, percutaneous (separate procedure)'),
  ('27001', 'Tenotomy, adductor of hip, open'),
  ('27003', 'Tenotomy, adductor, subcutaneous, open, with obturator neurectomy'),
  ('27005', 'Tenotomy, hip flexor(s), open (separate procedure)'),
  ('27006', 'Tenotomy, abductors and/or extensor(s) of hip, open (separate procedure)'),
  ('27097', 'Release or recession, hamstring, proximal'),
  ('27098', 'Transfer, adductor to ischium'),
  ('27100', 'Transfer external oblique muscle to greater trochanter including fascial or tendon extension (graft)'),
  ('27105', 'Transfer paraspinal muscle to hip (includes fascial or tendon extension graft)'),
  ('27110', 'Transfer iliopsoas; to greater trochanter of femur'),
  ('27111', 'Transfer iliopsoas; to femoral neck'),
  ('27306', 'Tenotomy, percutaneous, adductor or hamstring; single tendon (separate procedure)'),
  ('27307', 'Tenotomy, percutaneous, adductor or hamstring; multiple tendons'),
  ('27390', 'Tenotomy, open, hamstring, knee to hip; single tendon'),
  ('27391', 'Tenotomy, open, hamstring, knee to hip; multiple tendons, 1 leg'),
  ('27392', 'Tenotomy, open, hamstring, knee to hip; multiple tendons, bilateral'),
  ('27393', 'Lengthening of hamstring tendon; single tendon'),
  ('27394', 'Lengthening of hamstring tendon; multiple tendons, 1 leg'),
  ('27395', 'Lengthening of hamstring tendon; multiple tendons, bilateral'),
  ('27396', 'Transplant or transfer (with muscle redirection or rerouting), thigh (e.g., extensor to flexor); single tendon'),
  ('27397', 'Transplant or transfer (with muscle redirection or rerouting), thigh (e.g., extensor to flexor); multiple tendons'),
  ('27400', 'Transfer, tendon or muscle, hamstrings to femur (e.g., Eggers type procedure)'),
  ('23030', 'Incision and drainage, shoulder area; deep abscess or hematoma'),
  ('23031', 'Incision and drainage, shoulder area; infected bursa'),
  ('23035', 'Incision, bone cortex (e.g., osteomyelitis or bone abscess), shoulder area'),
  ('23040', 'Arthrotomy, glenohumeral joint, including exploration, drainage, or removal of foreign body'),
  ('23930', 'Incision and drainage, upper arm or elbow area; deep abscess or hematoma'),
  ('23931', 'Incision and drainage, upper arm or elbow area; bursa'),
  ('23935', 'Incision, deep, with opening of bone cortex (e.g., for osteomyelitis or bone abscess), humerus or elbow'),
  ('24000', 'Arthrotomy, elbow, including exploration, drainage, or removal of foreign body'),
  ('25028', 'Incision and drainage, forearm and/or wrist; deep abscess or hematoma'),
  ('25031', 'Incision and drainage, forearm and/or wrist; bursa'),
  ('25035', 'Incision, deep, bone cortex, forearm and/or wrist (e.g., osteomyelitis or bone abscess)'),
  ('25040', 'Arthrotomy, radiocarpal or midcarpal joint, with exploration, drainage, or removal of foreign body'),
  ('26990', 'Incision and drainage, pelvis or hip joint area; deep abscess or hematoma'),
  ('26991', 'Incision and drainage, pelvis or hip joint area; infected bursa'),
  ('26992', 'Incision, bone cortex, pelvis and/or hip joint (e.g., osteomyelitis or bone abscess)'),
  ('27301', 'Incision and drainage, deep abscess, bursa, or hematoma, thigh or knee region'),
  ('27303', 'Incision, deep, with opening of bone cortex, femur or knee (e.g., osteomyelitis or bone abscess)'),
  ('29850', 'Arthroscopically aided treatment of intercondylar spine(s) and/or tuberosity fracture(s) of the knee; without internal or external fixation (includes arthroscopy)'),
  ('29851', 'Arthroscopically aided treatment of intercondylar spine(s) and/or tuberosity fracture(s) of the knee; with internal or external fixation (includes arthroscopy)');

-- Hand Surgery CPT codes
INSERT OR IGNORE INTO cpt_codes(code, description) VALUES
  ('14000', 'Adjacent tissue transfer or rearrangement, trunk; defect 10 sq cm or less'),
  ('14020', 'Adjacent tissue transfer or rearrangement, scalp, arms and/or legs; defect 10 sq cm or less'),
  ('14021', 'Adjacent tissue transfer or rearrangement, scalp, arms and/or legs; defect 10.1 to 30 sq cm'),
  ('14040', 'Adjacent tissue transfer or rearrangement, forehead/cheeks/chin/mouth/neck/axillae/genitalia/hands/feet; defect 10 sq cm or less'),
  ('14041', 'Adjacent tissue transfer or rearrangement, forehead/cheeks/chin/mouth/neck/axillae/genitalia/hands/feet; defect 10.1 to 30 sq cm'),
  ('14350', 'Filleted finger or toe flap, including preparation of recipient site'),
  ('15050', 'Pinch graft, single or multiple, to cover small ulcer/tip of digit/minimal open area up to 2 cm'),
  ('15100', 'Split-thickness autograft, trunk/arms/legs; first 100 sq cm or less'),
  ('15101', 'Split-thickness autograft, trunk/arms/legs; each additional 100 sq cm'),
  ('15110', 'Epidermal autograft, trunk/arms/legs; first 100 sq cm or less'),
  ('15111', 'Epidermal autograft, trunk/arms/legs; each additional 100 sq cm'),
  ('15115', 'Epidermal autograft, face/scalp/eyelids/mouth/neck/ears/orbits/genitalia/hands/feet/multiple digits; first 100 sq cm or less'),
  ('15116', 'Epidermal autograft, face/scalp/eyelids/mouth/neck/ears/orbits/genitalia/hands/feet/multiple digits; each additional 100 sq cm'),
  ('15120', 'Split-thickness autograft, face/scalp/eyelids/mouth/neck/ears/orbits/genitalia/hands/feet/multiple digits; first 100 sq cm or less'),
  ('15121', 'Split-thickness autograft, face/scalp/eyelids/mouth/neck/ears/orbits/genitalia/hands/feet/multiple digits; each additional 100 sq cm'),
  ('15130', 'Dermal autograft, trunk/arms/legs; first 100 sq cm or less'),
  ('15131', 'Dermal autograft, trunk/arms/legs; each additional 100 sq cm'),
  ('15135', 'Dermal autograft, face/scalp/eyelids/mouth/neck/ears/orbits/genitalia/hands/feet/multiple digits; first 100 sq cm or less'),
  ('15136', 'Dermal autograft, face/scalp/eyelids/mouth/neck/ears/orbits/genitalia/hands/feet/multiple digits; each additional 100 sq cm'),
  ('15220', 'Full-thickness skin graft, scalp/arms/legs; 20 sq cm or less'),
  ('15221', 'Full-thickness skin graft, scalp/arms/legs; each additional 20 sq cm'),
  ('15572', 'Formation of direct or tubed pedicle, with or without transfer; scalp, arms or legs'),
  ('15574', 'Formation of direct or tubed pedicle, with or without transfer; hands, feet or multiple digits'),
  ('15610', 'Delay of flap or sectioning of flap; trunk'),
  ('15620', 'Delay of flap or sectioning of flap; forehead, cheeks, chin, neck, axillae, genitalia, hands or feet'),
  ('15734', 'Muscle, myocutaneous, or fasciocutaneous flap; trunk'),
  ('15736', 'Muscle, myocutaneous, or fasciocutaneous flap; upper extremity'),
  ('15740', 'Flap; island pedicle requiring identification and dissection of anatomically named axial vessel'),
  ('15750', 'Neurovascular pedicle procedure'),
  ('15756', 'Free muscle or myocutaneous flap with microvascular anastomosis'),
  ('15757', 'Free skin flap with microvascular anastomosis'),
  ('15758', 'Free fascial flap with microvascular anastomosis'),
  ('20802', 'Replantation, arm; complete amputation'),
  ('20805', 'Replantation, forearm; complete amputation'),
  ('20808', 'Replantation, hand; complete amputation'),
  ('20816', 'Replantation, digit excluding thumb; complete amputation'),
  ('20822', 'Replantation, digit excluding thumb; distal to flexor sublimis insertion, complete amputation'),
  ('20824', 'Replantation, thumb; complete amputation'),
  ('20827', 'Replantation, thumb; distal to MCP joint, complete amputation'),
  ('20924', 'Tendon graft, from a distance'),
  ('20955', 'Bone graft with microvascular anastomosis; fibula'),
  ('20956', 'Bone graft with microvascular anastomosis; iliac crest'),
  ('20962', 'Bone graft with microvascular anastomosis; other than fibula/iliac crest/metatarsal'),
  ('20969', 'Free osteocutaneous flap with microvascular anastomosis; other than iliac crest/metatarsal/great toe'),
  ('20970', 'Free osteocutaneous flap with microvascular anastomosis; iliac crest'),
  ('20972', 'Free osteocutaneous flap with microvascular anastomosis; metatarsal'),
  ('20973', 'Free osteocutaneous flap with microvascular anastomosis; great toe with web space'),
  ('25107', 'Arthrotomy, distal radioulnar joint including repair of triangular cartilage complex'),
  ('25210', 'Carpectomy; one bone'),
  ('25260', 'Repair, tendon or muscle, flexor, forearm and/or wrist; primary, single, each tendon or muscle'),
  ('25263', 'Repair, tendon or muscle, flexor, forearm and/or wrist; secondary, single, each tendon or muscle'),
  ('25265', 'Repair, tendon or muscle, flexor, forearm and/or wrist; secondary with free graft, each tendon or muscle'),
  ('25270', 'Repair, tendon or muscle, extensor, forearm and/or wrist; primary, single, each tendon or muscle'),
  ('25272', 'Repair, tendon or muscle, extensor, forearm and/or wrist; secondary, single, each tendon or muscle'),
  ('25274', 'Repair, tendon or muscle, extensor, forearm and/or wrist; secondary with free graft, each tendon or muscle'),
  ('25280', 'Lengthening or shortening of flexor or extensor tendon, forearm/wrist, single, each tendon'),
  ('25310', 'Tendon transplantation or transfer, flexor or extensor, forearm/wrist, single; each tendon'),
  ('25312', 'Tendon transplantation or transfer, flexor or extensor, forearm/wrist, single; with tendon graft, each tendon'),
  ('25320', 'Open capsulorrhaphy or reconstruction of wrist for carpal instability'),
  ('25337', 'Secondary stabilization reconstruction of unstable distal ulna or distal radioulnar joint'),
  ('25430', 'Insertion of vascular pedicle into carpal bone'),
  ('25440', 'Repair of nonunion, scaphoid carpal bone, with or without radial styloidectomy'),
  ('25445', 'Arthroplasty with prosthetic replacement; trapezium'),
  ('25447', 'Interposition arthroplasty, intercarpal or carpometacarpal joints'),
  ('25606', 'Percutaneous skeletal fixation of distal radius fracture or epiphyseal separation'),
  ('25607', 'Open treatment of distal radial extra-articular fracture or epiphyseal separation with internal fixation'),
  ('25608', 'Open treatment of distal radial intra-articular fracture/epiphyseal separation with fixation of 2 fragments'),
  ('25609', 'Open treatment of distal radial intra-articular fracture/epiphyseal separation with fixation of 3 or more fragments'),
  ('25628', 'Open treatment of carpal scaphoid fracture, includes internal fixation when performed'),
  ('25645', 'Open treatment of carpal bone fracture other than scaphoid, each bone'),
  ('25670', 'Open treatment of radiocarpal or intercarpal dislocation, one or more bones'),
  ('25671', 'Percutaneous fixation of distal radioulnar dislocation'),
  ('25676', 'Open treatment of distal radioulnar dislocation, acute or chronic'),
  ('25685', 'Open treatment of trans-scaphoperilunar fracture-dislocation'),
  ('25695', 'Open treatment of lunate dislocation'),
  ('25800', 'Complete wrist arthrodesis without bone graft'),
  ('25805', 'Wrist arthrodesis with sliding graft'),
  ('25810', 'Wrist arthrodesis with iliac or other autograft'),
  ('25820', 'Limited wrist arthrodesis without bone graft'),
  ('25825', 'Limited wrist arthrodesis with autograft'),
  ('25830', 'Distal radioulnar joint arthrodesis with segmental ulnar resection, with or without bone graft'),
  ('25900', 'Amputation, forearm, through radius and ulna'),
  ('25905', 'Amputation, forearm, through radius and ulna; open circular/guillotine'),
  ('25907', 'Amputation, forearm, through radius and ulna; secondary closure or scar revision'),
  ('25909', 'Amputation, forearm, through radius and ulna; reamputation'),
  ('25920', 'Disarticulation through wrist'),
  ('25922', 'Disarticulation through wrist; secondary closure or scar revision'),
  ('25924', 'Disarticulation through wrist; reamputation'),
  ('25927', 'Transmetacarpal amputation'),
  ('25929', 'Transmetacarpal amputation; secondary closure or scar revision'),
  ('25931', 'Transmetacarpal amputation; reamputation'),
  ('26350', 'Flexor tendon repair/advancement, not in zone 2; primary or secondary without free graft, each tendon'),
  ('26352', 'Flexor tendon repair/advancement, not in zone 2; secondary with free graft, each tendon'),
  ('26356', 'Flexor tendon repair/advancement, zone 2; primary without free graft, each tendon'),
  ('26357', 'Flexor tendon repair/advancement, zone 2; secondary without free graft, each tendon'),
  ('26358', 'Flexor tendon repair/advancement, zone 2; secondary with free graft, each tendon'),
  ('26370', 'Profundus tendon repair/advancement with intact superficialis tendon; primary, each tendon'),
  ('26372', 'Profundus tendon repair/advancement with intact superficialis tendon; secondary with free graft, each tendon'),
  ('26373', 'Profundus tendon repair/advancement with intact superficialis tendon; secondary without free graft, each tendon'),
  ('26390', 'Excision of flexor tendon with synthetic rod implantation for delayed tendon graft, hand/finger'),
  ('26392', 'Removal of synthetic rod and insertion of flexor tendon graft, hand/finger'),
  ('26410', 'Extensor tendon repair, hand, primary or secondary; without free graft, each tendon'),
  ('26412', 'Extensor tendon repair, hand, primary or secondary; with free graft, each tendon'),
  ('26415', 'Excision of extensor tendon with synthetic rod implantation for delayed tendon graft, hand/finger'),
  ('26416', 'Removal of synthetic rod and insertion of extensor tendon graft, hand/finger'),
  ('26418', 'Extensor tendon repair, finger, primary or secondary; without free graft, each tendon'),
  ('26420', 'Extensor tendon repair, finger, primary or secondary; with free graft, each tendon'),
  ('26426', 'Secondary central slip extensor tendon repair, including lateral bands, each finger'),
  ('26428', 'Extensor tendon repair, finger, primary or secondary; with free graft, each finger'),
  ('26432', 'Closed treatment of distal extensor tendon insertion injury/mallet finger'),
  ('26433', 'Extensor tendon distal insertion repair, primary or secondary; without graft'),
  ('26434', 'Extensor tendon distal insertion repair, primary or secondary; with free graft'),
  ('26437', 'Realignment of extensor tendon, hand, each tendon'),
  ('26476', 'Lengthening of extensor tendon, hand or finger, each tendon'),
  ('26477', 'Shortening of extensor tendon, hand or finger, each tendon'),
  ('26478', 'Lengthening of flexor tendon, hand or finger, each tendon'),
  ('26479', 'Shortening of flexor tendon, hand or finger, each tendon'),
  ('26485', 'Transfer or transplant of tendon, palmar; without free graft, each tendon'),
  ('26530', 'Arthroplasty, metacarpophalangeal joint, each joint'),
  ('26531', 'Arthroplasty, metacarpophalangeal joint with prosthetic implant, each joint'),
  ('26535', 'Arthroplasty, interphalangeal joint, each joint'),
  ('26536', 'Arthroplasty, interphalangeal joint with prosthetic implant, each joint'),
  ('26546', 'Repair nonunion, metacarpal or phalanx, with bone graft and/or fixation'),
  ('26551', 'Toe-to-hand transfer with microvascular anastomosis; great toe wrap-around with bone graft'),
  ('26553', 'Toe-to-hand transfer with microvascular anastomosis; other than great toe, single'),
  ('26554', 'Toe-to-hand transfer with microvascular anastomosis; other than great toe, double'),
  ('26556', 'Free toe joint transfer with microvascular anastomosis'),
  ('26560', 'Syndactyly repair, each web space; with skin flaps'),
  ('26561', 'Syndactyly repair, each web space; with skin flaps and grafts'),
  ('26562', 'Complex syndactyly repair, each web space, involving bone and/or nails'),
  ('26565', 'Osteotomy, metacarpal, each'),
  ('26567', 'Osteotomy, phalanx of finger, each'),
  ('26568', 'Osteoplasty, lengthening, metacarpal or phalanx'),
  ('26580', 'Repair of cleft hand'),
  ('26587', 'Reconstruction of polydactylous digit, soft tissue and bone'),
  ('26590', 'Repair of macrodactylia, each digit'),
  ('26596', 'Excision of constricting ring of finger with multiple Z-plasties'),
  ('26608', 'Percutaneous skeletal fixation of metacarpal fracture, each bone'),
  ('26615', 'Open treatment of metacarpal fracture, includes internal fixation when performed, each bone'),
  ('26650', 'Percutaneous skeletal fixation of Bennett fracture-dislocation of thumb CMC joint'),
  ('26665', 'Open treatment of Bennett fracture-dislocation of thumb CMC joint, includes internal fixation when performed'),
  ('26706', 'Percutaneous skeletal fixation of metacarpophalangeal dislocation, single'),
  ('26715', 'Open treatment of metacarpophalangeal dislocation, includes internal fixation when performed'),
  ('26727', 'Percutaneous skeletal fixation of unstable proximal/middle phalangeal shaft fracture'),
  ('26735', 'Open treatment of proximal/middle phalangeal shaft fracture, includes internal fixation when performed'),
  ('26746', 'Open treatment of articular fracture involving MCP or IP joint, includes internal fixation when performed'),
  ('26756', 'Percutaneous skeletal fixation of distal phalangeal fracture, finger or thumb'),
  ('26765', 'Open treatment of distal phalangeal fracture, includes internal fixation when performed'),
  ('26776', 'Percutaneous skeletal fixation of interphalangeal joint dislocation, single'),
  ('26785', 'Open treatment of interphalangeal joint dislocation, includes internal fixation when performed'),
  ('26841', 'Arthrodesis, thumb carpometacarpal joint, with or without internal fixation'),
  ('26850', 'Arthrodesis, metacarpophalangeal joint, with or without internal fixation'),
  ('26852', 'Arthrodesis, metacarpophalangeal joint with autograft'),
  ('26860', 'Arthrodesis, interphalangeal joint, with or without internal fixation'),
  ('26861', 'Arthrodesis, each additional interphalangeal joint'),
  ('26862', 'Arthrodesis, interphalangeal joint with autograft'),
  ('26863', 'Arthrodesis, each additional interphalangeal joint with autograft'),
  ('26910', 'Ray amputation, metacarpal with finger or thumb, with or without interosseous transfer'),
  ('26951', 'Amputation, finger or thumb, with direct closure'),
  ('26952', 'Amputation, finger or thumb, with local advancement flaps'),
  ('29840', 'Diagnostic wrist arthroscopy with or without synovial biopsy'),
  ('29843', 'Wrist arthroscopy, surgical; infection lavage and drainage'),
  ('29844', 'Wrist arthroscopy, surgical; partial synovectomy'),
  ('29845', 'Wrist arthroscopy, surgical; complete synovectomy'),
  ('29846', 'Wrist arthroscopy, surgical; TFCC excision and/or joint debridement'),
  ('29847', 'Wrist arthroscopy, surgical; internal fixation for fracture or instability'),
  ('29848', 'Endoscopic carpal tunnel release'),
  ('35045', 'Direct repair of radial or ulnar artery aneurysm/false aneurysm with or without graft'),
  ('35206', 'Direct repair of blood vessel; upper extremity'),
  ('35207', 'Direct repair of blood vessel; hand or finger'),
  ('35236', 'Repair of blood vessel with vein graft; upper extremity'),
  ('35266', 'Repair of blood vessel with graft other than vein; upper extremity'),
  ('64718', 'Ulnar nerve neuroplasty and/or transposition at elbow'),
  ('64719', 'Ulnar nerve neuroplasty and/or transposition at wrist'),
  ('64721', 'Median nerve neuroplasty and/or transposition at carpal tunnel'),
  ('64820', 'Sympathectomy; digital arteries, each digit'),
  ('64821', 'Sympathectomy; radial artery'),
  ('64822', 'Sympathectomy; ulnar artery'),
  ('64823', 'Sympathectomy; superficial palmar arch'),
  ('64831', 'Suture of digital nerve, hand or foot; one nerve'),
  ('64832', 'Suture of digital nerve, hand or foot; each additional digital nerve'),
  ('64834', 'Suture of one nerve, hand or foot; common sensory nerve'),
  ('64835', 'Suture of one nerve, hand or foot; median motor thenar nerve'),
  ('64836', 'Suture of one nerve, hand or foot; ulnar motor nerve'),
  ('64837', 'Suture of each additional nerve, hand or foot'),
  ('64856', 'Suture of major peripheral nerve, arm or leg, except sciatic; including transposition'),
  ('64857', 'Suture of major peripheral nerve, arm or leg, except sciatic; without transposition'),
  ('64859', 'Suture of each additional major peripheral nerve'),
  ('64861', 'Suture of brachial plexus'),
  ('64872', 'Secondary or delayed nerve suture, add-on to primary neurorrhaphy'),
  ('64874', 'Nerve suture requiring extensive mobilization or transposition'),
  ('64876', 'Nerve suture requiring shortening of bone'),
  ('64890', 'Nerve graft, single strand, hand or foot; up to 4 cm'),
  ('64891', 'Nerve graft, single strand, hand or foot; more than 4 cm'),
  ('64892', 'Nerve graft, single strand, arm or leg; up to 4 cm'),
  ('64893', 'Nerve graft, single strand, arm or leg; more than 4 cm'),
  ('64895', 'Nerve graft, multiple strands/cable, hand or foot; up to 4 cm'),
  ('64896', 'Nerve graft, multiple strands/cable, hand or foot; more than 4 cm'),
  ('64897', 'Nerve graft, multiple strands/cable, arm or leg; up to 4 cm'),
  ('64898', 'Nerve graft, multiple strands/cable, arm or leg; more than 4 cm'),
  ('64901', 'Nerve graft, each additional nerve; single strand'),
  ('64902', 'Nerve graft, each additional nerve; multiple strands/cable'),
  ('64905', 'Nerve pedicle transfer; first stage'),
  ('64907', 'Nerve pedicle transfer; second stage'),
  ('64910', 'Nerve repair with synthetic conduit or vein allograft, each nerve'),
  ('64911', 'Nerve repair with synthetic conduit or vein allograft plus autogenous vein graft, each nerve');
-- ============================================================
-- JUNCTION TABLE POPULATION
-- ============================================================

-- Helper: insert junction rows by looking up category name + fellowship code
-- Adult Recon - Primary TKA
INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Primary Total Knee Arthroplasty'
  AND p.code IN ('27445','27446','27447');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Revision Total Knee Arthroplasty'
  AND p.code IN ('27486','27487');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Uni Knee Arthroplasty'
  AND p.code IN ('27437','27438','27440','27441','27442','27443');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Removal Prosthesis for Infection (Hip or Knee)'
  AND p.code IN ('27030','27090','27091','27310','27488');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Primary Total Hip Arthroplasty'
  AND p.code IN ('27125','27130','27236');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Revision Total Hip Arthroplasty'
  AND p.code IN ('27132','27134','27137','27138');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Osteotomy Knee'
  AND p.code IN ('27448','27450','27457');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Osteotomy Hip'
  AND p.code IN ('27120','27122','27146');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Primary Shoulder Arthroplasty'
  AND p.code IN ('23470','23472');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Revision Shoulder Arthroplasty'
  AND p.code IN ('23333','23334','23335','23470','23473','23474');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Rotator Cuff Open and Arthroscopic'
  AND p.code IN ('23395','23397','23410','23412','23420','23430','29827','29828');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Bony Procedures for Shoulder Instability'
  AND p.code IN ('23460','23462','23465');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Soft Tissue Procedures for Shoulder Instability'
  AND p.code IN ('23455','23466','29806');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Open Acromioplasty'
  AND p.code IN ('23130');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Other Upper Limb Arthroscopic Procedures'
  AND p.code IN ('29807','29824','29826','29828','29830','29834','29835','29836','29837','29838','29840','29843','29844','29845','29846','29847','29848');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Arthrodesis Shoulder' AND p.code IN ('23800');

-- Foot & Ankle
INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Elective Reconstruction Forefoot'
  AND p.code IN ('28022','28102','28103','28110','28112','28113','28114','28116','28118','28122','28160','28200','28210','28230','28285','28286','28288','28290','28292','28296','28297','28298','28306','28310','28315');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Elective Reconstruction Midfoot/Hindfoot'
  AND p.code IN ('27606','27635','27637','27638','27640','27641','27646','27647','27690','27695','27696','27698','27705','27707','27709','27720','27726','28060','28100','28104','28120','28130','28238','28300','28705','28715');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Arthroscopy' AND c.fellowship_id=(SELECT id FROM fellowships WHERE code='FOOT_ANKLE')
  AND p.code IN ('29891','29892','29895','29897');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Arthrodesis' AND c.fellowship_id=(SELECT id FROM fellowships WHERE code='FOOT_ANKLE')
  AND p.code IN ('27700','27870','27871','28725','28730','28735','28737','28740','28750','29899');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Arthroplasty' AND c.fellowship_id=(SELECT id FROM fellowships WHERE code='FOOT_ANKLE')
  AND p.code IN ('27702','27703','27704');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Trauma Ankle Hindfoot (General)'
  AND p.code IN ('20690','20692','20693','20694','20696','20697','27600','27603','27607','27610','27620','27625','27756','27758','27759','27762','27766','27769','27784','27792','27814','27822','27823','27826','27829','27842','27846','27848','28400','28405','28445','28446');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Calcaneus' AND p.code IN ('28406','28415','28420');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Talus' AND p.code IN ('28435','28436');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Pilon' AND c.fellowship_id=(SELECT id FROM fellowships WHERE code='FOOT_ANKLE')
  AND p.code IN ('27827','27828');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Trauma Midfoot/Forefoot (General)'
  AND p.code IN ('28456','28465','28475','28476','28485','28496','28505','28515','28525','28531','28545','28546','28555','28575','28576','28585','28636','28645','28666','28675');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Lisfranc' AND p.code IN ('28606','28615');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Tendon Repair/Transfer' AND c.fellowship_id=(SELECT id FROM fellowships WHERE code='FOOT_ANKLE')
  AND p.code IN ('27650','27652','27654','27658','27664','27675','27676','27685','27687','27691');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Skin' AND p.code IN ('14001','14020','14350');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Hardware Removal' AND p.code IN ('20670','20680');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Graft' AND p.code IN ('20900','20902','20924','20926');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Infection/Tumor'
  AND p.code IN ('27604','27607','27618','27619','27630','28001','28002','28005','28043','28050','28052','28090');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Amputation'
  AND p.code IN ('27881','27882','27884','27886','27888','27889','28800','28805','28810','28820','28825');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Nerves' AND p.code IN ('28035','28055','28080','64774','64834');

-- MSK Oncology
INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Spine/Pelvis (Minimum 10)'
  AND p.code IN ('22112','22114','22101','22102','27075','27076','27077','27078');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Soft Tissue Resections and Reconstruction (Minimum 20)'
  AND p.code IN ('21936','22905','23078','24079','25078','27059','27364','27616','28047');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Limb Salvage (Minimum 20)'
  AND p.code IN ('23210','23220','24150','25170','27365','27645','27646','27647');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Surgical Management of Complications (Minimum 5)'
  AND p.code IN ('15736','15738','23334','24435','27091','27488','24515','27506','27472','27724');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Management of Metastatic Disease (Minimum 20)'
  AND p.code IN ('23491','23616','24498','27187','27125','27130','27244','27245','27447','27495','27511','27513','27745');

-- Sports Medicine
INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Glenohumeral Instability'
  AND p.code IN ('23450','23455','23460','23462','23465','23466','29806','29807');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Rotator Cuff' AND c.fellowship_id=(SELECT id FROM fellowships WHERE code='SPORTS')
  AND p.code IN ('23120','23130','23410','23412','23415','23420','23430','23440','29828','29826','29827','29824');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Acromioclavicular Instability' AND p.code IN ('23550','23552');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Elbow Arthroscopy'
  AND p.code IN ('29830','29834','29835','29836','29837','29838');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Elbow Instability' AND p.code IN ('24345','24346');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Hip Arthroscopy' AND p.code IN ('29860','29861','29862','29863');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Knee Instability'
  AND p.code IN ('27405','27407','27409','27427','27428','27429','29888','29889');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Knee Multi-Ligament Repair and Reconstruction'
  AND p.code IN ('27556','27557','27558');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Knee Osteotomy' AND p.code IN ('27457');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Patellofemoral Instability'
  AND p.code IN ('27420','27422','27424','27425','29873','27566');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Knee Articular Cartilage'
  AND p.code IN ('27412','27415','29877','29885','29886','29887','29879','29866','29867');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Meniscus'
  AND p.code IN ('27403','29868','29880','29881','29882','29883');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Foot and Ankle' AND c.fellowship_id=(SELECT id FROM fellowships WHERE code='SPORTS')
  AND p.code IN ('27650','27652','27654','27675','27676','27695','27696','27698','28060','28485','29891','29892','29894');

-- Spine
INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Fractures and Dislocations' AND c.fellowship_id=(SELECT id FROM fellowships WHERE code='SPINE')
  AND p.code IN ('22325','22326','22327');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Anterior Arthrodesis' AND c.fellowship_id=(SELECT id FROM fellowships WHERE code='SPINE')
  AND p.code IN ('22551','22554','22558');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Posterior Arthrodesis'
  AND p.code IN ('22595','22600','22610','22612','22802','22804','22630','22633','22830');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Posterior Instrumentation' AND c.fellowship_id=(SELECT id FROM fellowships WHERE code='SPINE')
  AND p.code IN ('22840','22842','22843','22844');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Anterior Instrumentation' AND c.fellowship_id=(SELECT id FROM fellowships WHERE code='SPINE')
  AND p.code IN ('22845','22846','22848','22849');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Application of Cage' AND p.code IN ('22851');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Removal of Spinal Instrumentation' AND p.code IN ('22850','22852','22855');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Laminectomy'
  AND p.code IN ('63001','63003','63005','63012','63015','63016','63017','63020','63030','63045','63047');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Laminoplasty' AND p.code IN ('63050','63051');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Thoracic Transpedicular Decompression' AND p.code IN ('63055');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Vertebral Corpectomy' AND p.code IN ('63081','63085','63086');

-- Trauma
INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Shoulder - Fracture and/or Dislocation'
  AND p.code IN ('23500','23515','23520','23530','23532','23540','23550','23552','23570','23585','23600','23615','23616','23620','23630','23660','23670','23680');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Humerus/Elbow - Fracture and/or Dislocation'
  AND p.code IN ('24500','24515','24516','24530','24538','24545','24546','24560','24566','24575','24576','24579','24582','24586','24587','24615','24635','24650','24665','24666','24670','24685');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Forearm/Wrist - Fracture and/or Dislocation'
  AND p.code IN ('25500','25515','25525','25526','25530','25545','25560','25574','25575','25600','25606','25607','25608','25609','25622','25628','25630','25645','25650','25651','25652','25670','25671','25676','25685','25695');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Pelvis/Hip - Fracture and/or Dislocation'
  AND p.code IN ('27193','27200','27202','27215','27216','27217','27218','27220','27226','27227','27228','27230','27235','27236','27238','27244','27245','27246','27248','27253','27254','27256','27258','27259');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Femur/Knee - Fracture and/or Dislocation'
  AND p.code IN ('27500','27501','27506','27507','27508','27509','27511','27513','27514','27516','27519','27520','27524','27530','27535','27536','27540','27556','27557','27558','27566');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Leg/Ankle - Fracture and/or Dislocation'
  AND p.code IN ('27750','27756','27758','27759','27760','27766','27769','27780','27784','27786','27792','27808','27814','27816','27822','27823','27824','27826','27827','27828','27829','27832','27846','27848');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Foot/Toes - Fracture and/or Dislocation'
  AND p.code IN ('28400','28406','28415','28420','28430','28436','28445','28450','28456','28465','28470','28476','28485','28490','28496','28505','28510','28525','28530','28531','28546','28555','28576','28585','28606','28615','28636','28645','28666','28675');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Treatment of Nonunion/Malunion'
  AND p.code IN ('23485','24400','24430','24435','25400','25405','25415','25420','25425','25426','27161','27165','27170','27450','27470','27472','27705','27707','27709','27720','27722','27724','27725');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='External Fixation' AND c.fellowship_id=(SELECT id FROM fellowships WHERE code='TRAUMA')
  AND p.code IN ('20690','20692','20693','20696','20697');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Debridement'
  AND p.code IN ('11010','11011','11012','11040','11041','11042','11043','11044');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Fasciotomy'
  AND p.code IN ('25020','25023','25024','25025','27600','27601','27602');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Intra-Articular Distal Humerus Fracture' AND p.code IN ('24546');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Pelvic Ring' AND p.code IN ('27216','27217','27218');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Acetabulum' AND p.code IN ('27226','27227','27228');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Bicondylar Tibial Plateau' AND p.code IN ('27536');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Pilon/Plafond' AND p.code IN ('27826','27827','27828');

-- Pediatric
INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Foot and Ankle Deformity (Excludes Clubfoot)'
  AND p.code IN ('27605','27606','27612','27685','27686','27687','27690','27691','27692','28230','28232','28234','28238','28240','28250','28264','28270','28272','28280','28285','28286','28288','28290','28292','28293','28294','28296','28297','28298','28299','28300','28302','28304','28305','28306','28307','28308','28309','28310','28312','28313','28340','28341','28344','28345','28360');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Clubfoot' AND p.code IN ('28260','28261','28262','29450','29750');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Limb Deformity (Includes Length Discrepancy and Deranged Growth)'
  AND p.code IN ('20696','20697','24400','24410','24420','24430','24435','24470','25370','25375','25390','25391','25392','25393','25394','25400','25405','25415','25420','27448','27450','27454','27455','27457','27465','27466','27468','27475','27477','27479','27485','27705','27707','27709','27712','27715','27727','27730','27732','27734','27740','27742');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Spine Deformity'
  AND p.code IN ('22800','22802','22804','22808','22810','22812','22212','22214','22216','22840','22841','22842','22843','22844','22845','22846','22847','22848','22849','22850','22852','22855');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Trauma Upper Limb' AND c.fellowship_id=(SELECT id FROM fellowships WHERE code='PEDS')
  AND p.code IN ('24530','24560','24566','24575','24576','24579','24582','24635','24535','24565','24577','24620','24640','24655','25560','25574','25575','25600','25606','25607','25505','25520','25535','25565','25605');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Treatment of Supracondylar Fractures'
  AND p.code IN ('24538','24545','24546');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Trauma Lower Limb' AND c.fellowship_id=(SELECT id FROM fellowships WHERE code='PEDS')
  AND p.code IN ('27230','27235','27236','27238','27244','27245','27246','27248','29850','29851','27500','27501','27502','27508','27509','27511','27513','27514','27516','27519','27520','27524','27540','27750','27756','27758','27759','27760','27766','27769','27780','27784','27786','27792','27808','27814','27816','27822','27823','27824','27826','27827','27828','27829','28400','28406','28415','28420','28430','28436','28445','28450','28456','28465','28470','28476','28485','28490','28496','28505','28510','28525','28530','28531','28546');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Open Treatment of Femoral Shaft Fracture'
  AND p.code IN ('27506','27507');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Hip (Reconstruction and Other, Excludes DDH)'
  AND p.code IN ('27140','27146','27147','27151','27156','27158','27161','27165','27175','27176','27177','27178','27179','27181');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Hip (Developmental Dysplasia)'
  AND p.code IN ('27256','27258','27259');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Soft Tissue: Transfer, Lengthening and Release'
  AND p.code IN ('23395','23397','23400','23405','24301','24305','24310','24320','24330','24331','25280','25290','25295','25300','25301','25310','25312','25315','25316','27000','27001','27003','27005','27006','27097','27098','27100','27105','27110','27111','27306','27307','27390','27391','27392','27393','27394','27395','27396','27397','27400');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c, cpt_codes p
WHERE c.name='Treatment of Infection' AND c.fellowship_id=(SELECT id FROM fellowships WHERE code='PEDS')
  AND p.code IN ('23030','23031','23035','23040','23930','23931','23935','24000','25028','25031','25035','25040','27030','27301','27303','26990','26991','26992','27310','27603','27604','27607','27610','28001','28002','28003','28005');


-- ============================================================
-- HAND SURGERY (ACGME Hand Surgery Case Log Guidelines, 10/2020)
-- ============================================================
INSERT OR IGNORE INTO fellowships(code, name) VALUES
  ('HAND', 'Hand');

-- Hand Surgery case categories
INSERT OR IGNORE INTO case_categories(fellowship_id, name) VALUES
  ((SELECT id FROM fellowships WHERE code='HAND'), 'Amputations'),
  ((SELECT id FROM fellowships WHERE code='HAND'), 'Carpal tunnel decompression'),
  ((SELECT id FROM fellowships WHERE code='HAND'), 'Extensor tendon repair'),
  ((SELECT id FROM fellowships WHERE code='HAND'), 'Finger arthrodesis or arthroplasty'),
  ((SELECT id FROM fellowships WHERE code='HAND'), 'Fixation of metacarpal fractures'),
  ((SELECT id FROM fellowships WHERE code='HAND'), 'Fixation of phalangeal fractures'),
  ((SELECT id FROM fellowships WHERE code='HAND'), 'Flexor tendon repair'),
  ((SELECT id FROM fellowships WHERE code='HAND'), 'Nerve repair'),
  ((SELECT id FROM fellowships WHERE code='HAND'), 'ORIF/CREF distal radius fractures'),
  ((SELECT id FROM fellowships WHERE code='HAND'), 'Scaphoid fracture'),
  ((SELECT id FROM fellowships WHERE code='HAND'), 'Soft tissue reconstruction'),
  ((SELECT id FROM fellowships WHERE code='HAND'), 'Tendon transfers'),
  ((SELECT id FROM fellowships WHERE code='HAND'), 'Thumb CMC reconstruction'),
  ((SELECT id FROM fellowships WHERE code='HAND'), 'Ulnar nerve decompression, with or without transposition'),
  ((SELECT id FROM fellowships WHERE code='HAND'), 'Vascular repair'),
  ((SELECT id FROM fellowships WHERE code='HAND'), 'Wrist arthrodesis, limited or complete'),
  ((SELECT id FROM fellowships WHERE code='HAND'), 'Wrist arthroscopy'),
  ((SELECT id FROM fellowships WHERE code='HAND'), 'Wrist instability or dislocation');



-- Hand Surgery category-to-CPT mappings
INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c JOIN fellowships f ON f.id=c.fellowship_id, cpt_codes p
WHERE f.code='HAND' AND c.name='Amputations'
  AND p.code IN ('25900','25905','25907','25909','25920','25922','25924','25927','25929','25931','26910','26951','26952');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c JOIN fellowships f ON f.id=c.fellowship_id, cpt_codes p
WHERE f.code='HAND' AND c.name='Carpal tunnel decompression'
  AND p.code IN ('29848','64721');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c JOIN fellowships f ON f.id=c.fellowship_id, cpt_codes p
WHERE f.code='HAND' AND c.name='Extensor tendon repair'
  AND p.code IN ('20924','25270','25272','25274','25280','26410','26412','26415','26416','26418','26420','26426','26428','26432','26433','26434','26437','26476','26477');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c JOIN fellowships f ON f.id=c.fellowship_id, cpt_codes p
WHERE f.code='HAND' AND c.name='Finger arthrodesis or arthroplasty'
  AND p.code IN ('26530','26531','26535','26536','26841','26850','26852','26860','26861','26862','26863');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c JOIN fellowships f ON f.id=c.fellowship_id, cpt_codes p
WHERE f.code='HAND' AND c.name='Fixation of metacarpal fractures'
  AND p.code IN ('26546','26565','26568','26608','26615','26650','26665','26706','26715','26746');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c JOIN fellowships f ON f.id=c.fellowship_id, cpt_codes p
WHERE f.code='HAND' AND c.name='Fixation of phalangeal fractures'
  AND p.code IN ('26546','26567','26568','26727','26735','26746','26756','26765','26776','26785');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c JOIN fellowships f ON f.id=c.fellowship_id, cpt_codes p
WHERE f.code='HAND' AND c.name='Flexor tendon repair'
  AND p.code IN ('20924','25260','25263','25265','25280','26350','26352','26356','26357','26358','26370','26372','26373','26390','26392','26478','26479');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c JOIN fellowships f ON f.id=c.fellowship_id, cpt_codes p
WHERE f.code='HAND' AND c.name='Nerve repair'
  AND p.code IN ('20802','20805','20808','20816','20822','20824','20827','26551','26553','26554','26556','64831','64832','64834','64835','64836','64837','64856','64857','64859','64861','64872','64874','64876','64890','64891','64892','64893','64895','64896','64897','64898','64901','64902','64905','64907','64910','64911');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c JOIN fellowships f ON f.id=c.fellowship_id, cpt_codes p
WHERE f.code='HAND' AND c.name='ORIF/CREF distal radius fractures'
  AND p.code IN ('25606','25607','25608','25609');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c JOIN fellowships f ON f.id=c.fellowship_id, cpt_codes p
WHERE f.code='HAND' AND c.name='Scaphoid fracture'
  AND p.code IN ('25430','25440','25628','25685');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c JOIN fellowships f ON f.id=c.fellowship_id, cpt_codes p
WHERE f.code='HAND' AND c.name='Soft tissue reconstruction'
  AND p.code IN ('14000','14020','14021','14040','14041','14350','15050','15100','15101','15110','15111','15115','15116','15120','15121','15130','15131','15135','15136','15220','15221','15572','15574','15610','15620','15734','15736','15740','15750','15756','15757','15758','20969','20970','20972','20973','26551','26553','26554','26556','26560','26561','26562','26580','26587','26590','26596');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c JOIN fellowships f ON f.id=c.fellowship_id, cpt_codes p
WHERE f.code='HAND' AND c.name='Tendon transfers'
  AND p.code IN ('25310','25312','26485');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c JOIN fellowships f ON f.id=c.fellowship_id, cpt_codes p
WHERE f.code='HAND' AND c.name='Thumb CMC reconstruction'
  AND p.code IN ('25210','25445','25447');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c JOIN fellowships f ON f.id=c.fellowship_id, cpt_codes p
WHERE f.code='HAND' AND c.name='Ulnar nerve decompression, with or without transposition'
  AND p.code IN ('64718','64719');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c JOIN fellowships f ON f.id=c.fellowship_id, cpt_codes p
WHERE f.code='HAND' AND c.name='Vascular repair'
  AND p.code IN ('15756','15757','15758','20802','20805','20808','20816','20822','20824','20827','20955','20956','20962','20969','20970','20972','20973','26551','26553','26554','26556','35045','35206','35207','35236','35266','64820','64821','64822','64823');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c JOIN fellowships f ON f.id=c.fellowship_id, cpt_codes p
WHERE f.code='HAND' AND c.name='Wrist arthrodesis, limited or complete'
  AND p.code IN ('25800','25805','25810','25820','25825','25830');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c JOIN fellowships f ON f.id=c.fellowship_id, cpt_codes p
WHERE f.code='HAND' AND c.name='Wrist arthroscopy'
  AND p.code IN ('29840','29843','29844','29845','29846','29847');

INSERT OR IGNORE INTO category_cpt(category_id, cpt_id)
SELECT c.id, p.id FROM case_categories c JOIN fellowships f ON f.id=c.fellowship_id, cpt_codes p
WHERE f.code='HAND' AND c.name='Wrist instability or dislocation'
  AND p.code IN ('25107','25320','25337','25645','25670','25671','25676','25685','25695');

-- ============================================================
-- POPULATE FTS TABLE
-- (Run after all inserts are complete)
-- ============================================================
DELETE FROM cpt_fts;
INSERT INTO cpt_fts(code, description, fellowship, category)
SELECT
    p.code,
    p.description,
    f.name,
    c.name
FROM cpt_codes p
JOIN category_cpt cc ON cc.cpt_id = p.id
JOIN case_categories c ON c.id = cc.category_id
JOIN fellowships f ON f.id = c.fellowship_id;

-- ============================================================
-- USEFUL VIEWS
-- ============================================================

-- Flat view joining everything
CREATE VIEW IF NOT EXISTS v_cpt_full AS
SELECT
    p.code          AS cpt_code,
    p.description   AS cpt_description,
    f.code          AS fellowship_code,
    f.name          AS fellowship_name,
    c.name          AS category_name
FROM cpt_codes p
JOIN category_cpt cc ON cc.cpt_id = p.id
JOIN case_categories c ON c.id = cc.category_id
JOIN fellowships f ON f.id = c.fellowship_id
ORDER BY p.code;

-- ============================================================
-- EXAMPLE QUERIES FOR SWIFT
-- ============================================================
-- 1. Full-text search across code + description + fellowship + category:
--    SELECT * FROM cpt_fts WHERE cpt_fts MATCH 'bunion';
--
-- 2. Prefix search (good for a search-as-you-type text field):
--    SELECT * FROM cpt_fts WHERE cpt_fts MATCH 'arthrosc*';
--
-- 3. Look up a specific CPT code:
--    SELECT * FROM v_cpt_full WHERE cpt_code = '27447';
--
-- 4. All codes in a fellowship:
--    SELECT * FROM v_cpt_full WHERE fellowship_code = 'SPORTS';
--
-- 5. All codes in a category:
--    SELECT * FROM v_cpt_full WHERE category_name = 'Meniscus';
--
-- 6. Distinct codes only (no duplicate rows from multi-category membership):
--    SELECT DISTINCT cpt_code, cpt_description FROM v_cpt_full
--    WHERE fellowship_code = 'TRAUMA';
