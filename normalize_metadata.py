# normalize_metadata.py
# ------------------------------------------------------------
# Purpose:
#   Standardize specialty + region (+ optional procedure/diagnosis normalization)
#   for your JSONL flashcards before upserting to Pinecone.
#
# Usage:
#   python normalize_metadata.py input.jsonl output.normalized.jsonl
#
# Notes:
#   - Leaves diagnosis/procedure blank unless we can normalize confidently.
#   - Preserves original values in *_raw fields so you can debug.
#   - Adds optional fields: region_raw, subregion, subregion_raw, approach, concept (list)
# ------------------------------------------------------------

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

# =========================
# 1) Canonical allowlists
# =========================

STANDARD_SPECIALTIES = [
    "recon",
    "basicscience",
    "sports",
    "footankle",
    "spine",
    "onc",
    "peds",
    "hand",
    "shoulderelbow",
    "trauma",
]

STANDARD_REGIONS = [
    # Lower Extremity
    "hip",
    "knee",
    "ankle",
    "foot",
    "midfoot",
    "pelvis",
    "thigh",
    "leg",
    # Upper Extremity
    "shoulder",
    "elbow",
    "forearm",
    "wrist",
    "hand",
    # Spine
    "cervical spine",
    "thoracic spine",
    "lumbar spine",
    "spine",
    # Other
    "non-anatomic",
]

# Keep these tight. Add as you grow.
STANDARD_PROCEDURES = [
    # Arthroplasty
    "total hip arthroplasty",
    "revision total hip arthroplasty",
    "total knee arthroplasty",
    "revision total knee arthroplasty",
    "total shoulder arthroplasty",
    "reverse total shoulder arthroplasty",
    "total ankle arthroplasty",
    "revision total shoulder arthroplasty",
    "revision reverse total shoulder arthroplasty",
    "hemiarthroplasty",
    "hip hemiarthroplasty",
    "shoulder hemiarthroplasty",
    "unicompartmental knee arthroplasty",
    "patellofemoral arthroplasty",
    "arthroplasty spacer placement",
    "two-stage revision arthroplasty",
    "irrigation and debridement with polyethylene exchange",

    # Spine
    "spinal fusion",
    "lumbar fusion",
    "cervical fusion",
    "laminectomy",
    "laminotomy",
    "foraminotomy",
    "discectomy",
    "microdiscectomy",
    "cervical discectomy",
    "anterior cervical discectomy and fusion",
    "acdf",
    "posterior spinal fusion",
    "tlif",
    "plif",
    "alif",
    "lateral interbody fusion",
    "xlif",
    "kyphoplasty",
    "vertebroplasty",
    "halo traction",
    "selective dorsal rhizotomy",

    # Trauma / fracture care
    "open reduction internal fixation",
    "orif",
    "intramedullary nailing",
    "external fixation",
    "closed reduction",
    "closed reduction percutaneous pinning",
    "fracture fixation",
    "plate fixation",
    "percutaneous pinning",
    "k-wire fixation",
    "tension band wiring",
    "cerclage wiring",
    "lag screw fixation",
    "screw fixation",
    "bridge plating",
    "unicortical plating",
    "exchange nailing",
    "dynamization",
    "syndesmotic fixation",
    "syndesmotic screw fixation",
    "suture button fixation",
    "fasciotomy",
    "compartment release",
    "wound vac placement",
    "negative pressure wound therapy",
    "open reduction",
    "in situ pinning",

    # Arthrodesis (fusion)
    "midfoot arthrodesis",
    "ankle arthrodesis",
    "subtalar arthrodesis",
    "triple arthrodesis",
    "tibiotalocalcaneal fusion",
    "wrist arthrodesis",
    "elbow arthrodesis",
    "shoulder arthrodesis",
    "hip arthrodesis",
    "knee arthrodesis",
    "first metatarsophalangeal arthrodesis",
    "first tarsometatarsal arthrodesis",

    # Bone graft / biologics
    "bone grafting",
    "autograft harvest",
    "allograft bone grafting",
    "iliac crest bone graft",
    "bmp-2 use",
    "bmp-7 use",

    # Arthroscopy / sports / cartilage
    "arthroscopy",
    "shoulder arthroscopy",
    "hip arthroscopy",
    "meniscectomy",
    "meniscus repair",
    "microfracture",
    "osteochondral autograft transfer",
    "osteochondral allograft transplantation",
    "autologous chondrocyte implantation",
    "acl reconstruction",
    "pcl reconstruction",
    "lateral release",
    "subacromial decompression",
    "acromioplasty",
    "distal clavicle excision",
    "biceps tenodesis",
    "biceps tenotomy",
    "rotator cuff repair",
    "labral repair",
    "bankart repair",
    "slap repair",
    "latarjet procedure",
    "mpfl reconstruction",
    "fai osteoplasty",
    "femoroplasty",
    "acetabuloplasty",

    # Hand / upper extremity
    "trigger finger release",
    "A1 pulley release",
    "carpal tunnel release",
    "de quervain release",
    "cubital tunnel release",
    "ulnar nerve transposition",
    "guys canal release",
    "dupuytren fasciectomy",
    "cmc arthroplasty",
    "ligament reconstruction tendon interposition",
    "l r t i",
    "wrist arthroscopy",
    "tfcc repair",
    "distal radioulnar joint reconstruction",
    "distal radius open reduction internal fixation",
    "olecranon open reduction internal fixation",
    "scaphoid open reduction internal fixation",
    "phalangeal fracture fixation",
    "metacarpal fracture fixation",
    "ulnar shortening osteotomy",
    "radial shortening osteotomy",
    "capitohamate fusion",
    "scaphotrapeziotrapezoid fusion",
    "scaphocapitate fusion",
    "proximal row carpectomy",

    # Tendon / nerve
    "tendon repair",
    "flexor tendon repair",
    "epitendinous repair",
    "tenolysis",
    "tendon advancement",
    "tendon lengthening",
    "tendon transfer",
    "nerve repair",
    "nerve grafting",
    "fascicular nerve repair",
    "central slip reconstruction",

    # Tendon transfers (specific)
    "anterior tibialis tendon transfer",
    "split posterior tibialis transfer",
    "latissimus dorsi transfer",
    "teres major transfer",
    "triceps transfer",

    # Foot & ankle
    "ankle open reduction internal fixation",
    "bimalleolar open reduction internal fixation",
    "trimalleolar open reduction internal fixation",
    "calcaneus open reduction internal fixation",
    "talar neck open reduction internal fixation",
    "lapidus procedure",
    "lisfranc fixation",
    "lisfranc open reduction internal fixation",
    "achilles tendon repair",
    "gastrocnemius recession",
    "strayer procedure",
    "tendo-achilles lengthening",
    "austin bunionectomy",
    "chevron osteotomy",
    "akin osteotomy",
    "scarf osteotomy",
    "calcaneal osteotomy",
    "calcaneal lengthening osteotomy",
    "evans osteotomy",
    "cotton osteotomy",
    "plantar fascia release",
    "talectomy",
    "subtalar coalition resection",
    "ponseti casting",
    "clubfoot casting",

    # Pediatric
    "closed reduction and spica casting",
    "spica casting",
    "supracondylar humerus closed reduction percutaneous pinning",
    "slipped capital femoral epiphysis pinning",
    "scfe pinning",
    "periacetabular osteotomy",
    "pavlik harness",
    "epiphysiodesis",
    "adductor tenotomy",
    "psoas release",
    "psoas recession",
    "hip arthrography",

    # Osteotomy (general)
    "osteotomy",
    "varus derotation osteotomy",
    "pelvic osteotomy",
    "femoral osteotomy",

    # Deformity / limb reconstruction
    "limb lengthening",
    "circular external fixation",
    "hexapod external fixation",
    "bone transport",
    "ilizarov fixation",

    # Infection
    "irrigation and debridement",
    "debridement",
    "hardware removal with irrigation and debridement",
    "septic joint irrigation and debridement",
    "arthrotomy and drainage",
    "resection arthroplasty",
    "antibiotic bead placement",

    # General
    "hardware removal",
    "implant removal",
    "foreign body removal",
    "bursectomy",
    "exostectomy",
    "prophylactic fixation",

    # Oncology – biopsy
    "biopsy",
    "open biopsy",
    "core needle biopsy",
    "incisional biopsy",
    "excisional biopsy",

    # Oncology – excision
    "intralesional resection",
    "curettage",
    "extended curettage",
    "marginal excision",
    "wide excision",
    "wide margin resection",
    "radical resection",

    # Oncology – reconstruction / ablative
    "limb salvage surgery",
    "tumor resection",
    "en bloc resection",
    "resection with reconstruction",
    "amputation",
    "hemipelvectomy",
    "rotationplasty",

    # Oncology – adjuvant / local control
    "synovectomy",
    "complete synovectomy",
    "radiofrequency ablation",
    "ct-guided radiofrequency ablation",

    # Bone defect / tumor adjuncts
    "curettage and bone grafting",
    "cement augmentation",
    "polymethylmethacrylate cementation",
    "sacrectomy",
    "vertebral tumor resection",
    "cyst curettage",
]



STANDARD_DIAGNOSES = [

    # ---------------- Hip ----------------
    "hip osteoarthritis",
    "inflammatory hip arthritis",
    "avascular necrosis of the femoral head",
    "hip dysplasia",
    "developmental dysplasia of the hip",
    "femoroacetabular impingement",
    "cam-type femoroacetabular impingement",
    "pincer-type femoroacetabular impingement",
    "hip labral tear",
    "hip instability",
    "greater trochanteric pain syndrome",
    "trochanteric bursitis",
    "iliopsoas tendinitis",
    "iliopsoas impingement",
    "snapping hip syndrome",
    "hip fracture",
    "femoral neck fracture",
    "intertrochanteric femur fracture",
    "subtrochanteric femur fracture",
    "periprosthetic hip fracture",
    "prosthetic hip instability",
    "total hip arthroplasty dislocation",
    "prosthetic hip impingement",
    "aseptic loosening of hip prosthesis",
    "periprosthetic joint infection of the hip",
    "heterotopic ossification of the hip",

    # ---------------- Knee ----------------
    "knee osteoarthritis",
    "inflammatory knee arthritis",
    "post-traumatic knee arthritis",
    "varus knee deformity",
    "valgus knee deformity",
    "patellofemoral osteoarthritis",
    "patellofemoral pain syndrome",
    "patellar instability",
    "recurrent patellar dislocation",
    "patellar maltracking",
    "trochlear dysplasia",
    "patella alta",
    "patella baja",
    "quadriceps tendon rupture",
    "patellar tendon rupture",
    "meniscus tear",
    "degenerative meniscus tear",
    "acl tear",
    "pcl tear",
    "mcl injury",
    "lcl injury",
    "posterolateral corner injury",
    "knee stiffness",
    "arthrofibrosis of the knee",
    "tibial plateau fracture",
    "distal femur fracture",
    "periprosthetic knee fracture",
    "aseptic loosening of knee prosthesis",
    "prosthetic knee instability",
    "periprosthetic joint infection of the knee",

    # ---------------- Spine ----------------
    "degenerative disc disease",
    "lumbar spinal stenosis",
    "cervical spinal stenosis",
    "thoracic spinal stenosis",
    "lumbar disc herniation",
    "cervical disc herniation",
    "radiculopathy",
    "myelopathy",
    "spondylosis",
    "spondylolisthesis",
    "isthmic spondylolisthesis",
    "degenerative spondylolisthesis",
    "flatback syndrome",
    "spinopelvic imbalance",
    "adjacent segment disease",
    "pseudoarthrosis",
    "failed back surgery syndrome",
    "vertebral compression fracture",
    "osteoporotic compression fracture",
    "burst fracture",
    "chance fracture",
    "spinal deformity",
    "adult spinal deformity",
    "scoliosis",
    "kyphosis",
    "lordosis",
    "spinal infection",
    "discitis",
    "osteomyelitis of the spine",
    "epidural abscess",
    "prior lumbar fusion",

    # ---------------- Shoulder ----------------
    "glenohumeral osteoarthritis",
    "inflammatory shoulder arthritis",
    "rotator cuff tear",
    "massive rotator cuff tear",
    "rotator cuff arthropathy",
    "shoulder instability",
    "anterior shoulder instability",
    "posterior shoulder instability",
    "multidirectional shoulder instability",
    "labral tear of the shoulder",
    "bankart lesion",
    "slap tear",
    "biceps tendinopathy",
    "adhesive capsulitis",
    "shoulder impingement syndrome",
    "acromioclavicular joint arthritis",
    "proximal humerus fracture",
    "periprosthetic shoulder fracture",
    "aseptic loosening of shoulder prosthesis",
    "periprosthetic joint infection of the shoulder",

    # ---------------- Elbow ----------------
    "elbow osteoarthritis",
    "post-traumatic elbow arthritis",
    "lateral epicondylitis",
    "medial epicondylitis",
    "elbow instability",
    "ulnar collateral ligament injury",
    "distal biceps tendon rupture",
    "triceps tendon rupture",
    "elbow stiffness",
    "heterotopic ossification of the elbow",
    "radial head fracture",
    "olecranon fracture",
    "supracondylar humerus fracture",

    # ---------------- Hand / Wrist ----------------
    "distal radius fracture",
    "scaphoid fracture",
    "scaphoid nonunion",
    "wrist osteoarthritis",
    "scapholunate ligament injury",
    "tfcc tear",
    "carpal tunnel syndrome",
    "cubital tunnel syndrome",
    "ulnar neuropathy",
    "trigger finger",
    "de quervain tenosynovitis",
    "dupuytren contracture",
    "cmc joint arthritis",
    "phalanx fracture",
    "metacarpal fracture",

    # ---------------- Foot & Ankle ----------------
    "ankle osteoarthritis",
    "post-traumatic ankle arthritis",
    "ankle instability",
    "chronic ankle instability",
    "ankle fracture",
    "bimalleolar ankle fracture",
    "trimalleolar ankle fracture",
    "talar neck fracture",
    "calcaneus fracture",
    "achilles tendon rupture",
    "achilles tendinopathy",
    "plantar fasciitis",
    "hallux valgus",
    "hallux rigidus",
    "flatfoot deformity",
    "cavovarus foot",
    "posterior tibial tendon dysfunction",
    "peroneal tendon tear",
    "lisfranc injury",
    "charcot neuroarthropathy",
    "diabetic foot infection",
    "osteomyelitis of the foot",

    # ---------------- Pediatric ----------------
    "developmental dysplasia of the hip",
    "slipped capital femoral epiphysis",
    "leg length discrepancy",
    "clubfoot",
    "blount disease",
    "perthes disease",
    "toddler fracture",
    "supracondylar humerus fracture",
    "pediatric elbow fracture",

    # ---------------- Oncology ----------------
    "benign bone tumor",
    "malignant bone tumor",
    "soft tissue sarcoma",
    "metastatic bone disease",
    "pathologic fracture",
    "giant cell tumor of bone",
    "osteosarcoma",
    "chondrosarcoma",
    "ewing sarcoma",
    "bone cyst",
    "aneurysmal bone cyst",

    # ---------------- Infection ----------------
    "septic arthritis",
    "osteomyelitis",
    "periprosthetic joint infection",
    "infected nonunion",

]

# =========================
# 2) Normalization helpers
# =========================

_WS = re.compile(r"\s+")

def norm_text(s: Any) -> str:
    if s is None:
        return ""
    s = str(s)
    s = s.replace("\u2019", "'")
    s = s.strip().lower()
    s = _WS.sub(" ", s)
    return s

def contains_any(haystack: str, needles: Iterable[str]) -> bool:
    h = haystack
    return any(n in h for n in needles)

def safe_list(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [norm_text(i) for i in x if norm_text(i)]
    return [norm_text(x)] if norm_text(x) else []

# =========================
# 3) Specialty mapping
# =========================

SPECIALTY_SYNONYMS = {
    "recon": "recon",
    "adult reconstruction": "recon",
    "arthroplasty": "recon",
    "tja": "recon",
    "basicscience": "basicscience",
    "basic science": "basicscience",
    "sports": "sports",
    "sports medicine": "sports",
    "footankle": "footankle",
    "foot & ankle": "footankle",
    "foot and ankle": "footankle",
    "spine": "spine",
    "onc": "onc",
    "ortho oncology": "onc",
    "peds": "peds",
    "pediatrics": "peds",
    "hand": "hand",
    "shoulderelbow": "shoulderelbow",
    "shoulder/elbow": "shoulderelbow",
    "shoulder and elbow": "shoulderelbow",
    "trauma": "trauma",
}

def normalize_specialty(raw: Any) -> Tuple[str, str]:
    raw_s = norm_text(raw)
    if not raw_s:
        return "", ""
    canon = SPECIALTY_SYNONYMS.get(raw_s, "")
    # also handle already-canonical but with case differences
    if not canon and raw_s in STANDARD_SPECIALTIES:
        canon = raw_s
    return canon, raw_s

# =========================
# 4) Region + subregion + concept
# =========================

# Things that must NEVER be treated as region
BANNED_REGION_TOKENS = {
    "valgus",
    "varus",
    "alignment",
    "posterior approach",
    "anterior approach",
    "approach",
    "mental health",
    "this flashcard does not pertain to a specific anatomical region.",
    "this clinical flashcard does not pertain to a specific anatomical region.",
}

# Map common raw region strings -> canonical region AND optional subregion
REGION_SYNONYMS: Dict[str, Tuple[str, Optional[str]]] = {
    # Hip / pelvis
    "hip": ("hip", None),
    "anterior hip": ("hip", "anterior"),
    "posterior hip": ("hip", "posterior"),
    "proximal femur": ("hip", "proximal femur"),
    "acetabulum": ("pelvis", "acetabulum"),
    "pelvis": ("pelvis", None),
    "pelvic region": ("pelvis", None),

    # Femur buckets (choose your preference: thigh vs knee vs hip)
    # If your cards are arthroplasty-recon heavy, many "femur" cards are hip-related.
    "femur": ("thigh", None),
    "distal femur": ("knee", "distal femur"),
    "femoral shaft": ("thigh", "femoral shaft"),
    "femoralshaft": ("thigh", "femoral shaft"),

    # Knee
    "knee": ("knee", None),
    "knee joint": ("knee", None),
    "patella": ("knee", "patella"),
    "patellofemoral": ("knee", "patellofemoral"),
    "popliteal fossa": ("knee", "popliteal fossa"),
    "posteromedial corner": ("knee", "posteromedial corner"),
    "posterolateral corner": ("knee", "posterolateral corner"),

    # Tibia / leg
    "tibia": ("leg", "tibia"),
    "tibial shaft": ("leg", "tibial shaft"),
    "tibialshaft": ("leg", "tibial shaft"),
    "tibial plateau": ("knee", "tibial plateau"),

    # Ankle / foot
    "ankle": ("ankle", None),
    "foot": ("foot", None),
    "midfoot": ("midfoot", None),
    "forefoot": ("foot", "forefoot"),
    "hindfoot": ("foot", "hindfoot"),
    "footankle": ("ankle", None),

    # Upper extremity
    "shoulder": ("shoulder", None),
    "elbow": ("elbow", None),
    "forearm": ("forearm", None),
    "wrist": ("wrist", None),
    "hand": ("hand", None),

    # Spine
    "spine": ("spine", None),
    "cervical spine": ("cervical spine", None),
    "thoracic spine": ("thoracic spine", None),
    "lumbar spine": ("lumbar spine", None),

    # Whole limb
    "lower limb": ("global", "lower limb"),
    "lower extremity": ("global", "lower extremity"),
}

# Concept detection (stored as list of tags)
CONCEPT_RULES: List[Tuple[str, List[str]]] = [
    ("alignment", ["valgus", "varus", "mechanical axis", "anatomic axis", "joint line"]),
    ("implant positioning", ["cup version", "anteversion", "retroversion", "inclination", "combined anteversion", "offset", "leg length"]),
    ("biomechanics", ["lever arm", "joint reactive", "rollback", "radius of curvature", "tracking"]),
    ("classification", ["dorr", "ranawat", "classification"]),
    ("instability", ["instability", "sublux", "dislocat", "maltracking"]),
    ("spinopelvic mechanics", ["pelvic tilt", "sacral slope", "pelvic incidence", "lumbo-pelvic", "spinopelvic"]),
]

APPROACH_RULES: List[Tuple[str, List[str]]] = [
    ("direct anterior", ["direct anterior", "anterior approach"]),
    ("posterior", ["posterior approach"]),
    ("anterolateral", ["antero-lateral", "anterolateral"]),
]

def infer_concepts(fulltext: str) -> List[str]:
    tags: List[str] = []
    for concept, needles in CONCEPT_RULES:
        if contains_any(fulltext, needles):
            tags.append(concept)
    # de-dupe preserving order
    out = []
    seen = set()
    for t in tags:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out

def infer_approach(fulltext: str) -> str:
    for app, needles in APPROACH_RULES:
        if contains_any(fulltext, needles):
            return app
    return ""

def normalize_region(raw_region: Any, fulltext: str, specialty: str) -> Tuple[str, str, str, str, List[str]]:
    """
    Returns:
      region, subregion, region_raw, subregion_raw, concepts
    """
    rr = norm_text(raw_region)
    concepts = infer_concepts(fulltext)

    # If region is missing or banned/junk, try infer from text
    if (not rr) or (rr in BANNED_REGION_TOKENS) or rr.startswith("trauma::") or rr.startswith("sports::"):
        rr_clean = rr
        # infer from text keywords
        region = infer_region_from_text(fulltext, specialty)
        return region, "", rr_clean, rr_clean, concepts

    # direct synonym mapping
    if rr in REGION_SYNONYMS:
        region, sub = REGION_SYNONYMS[rr]
        return region, (sub or ""), rr, rr if sub else "", concepts

    # heuristic: if rr mentions a canonical region word
    region_guess = infer_region_from_text(rr + " " + fulltext, specialty)
    return region_guess, "", rr, rr, concepts

def infer_region_from_text(text: str, specialty: str) -> str:
    t = norm_text(text)

    # Strong spine detection
    if contains_any(t, ["cervical", "c-spine"]):
        return "cervical spine"
    if contains_any(t, ["thoracic", "t-spine"]):
        return "thoracic spine"
    if contains_any(t, ["lumbar", "l-spine"]):
        return "lumbar spine"
    if "spine" in t:
        return "spine"

    # Hip/pelvis
    if contains_any(t, ["acetabul", "pelvic", "ilium", "isch", "pubic", "sacrum", "sacroiliac", "si joint"]):
        # if explicitly acetabulum/pelvis bony words → pelvis
        return "pelvis"
    if contains_any(t, ["hip", "femoral head", "femoral neck", "trochanter", "tha", "total hip"]):
        return "hip"

    # Knee
    if contains_any(t, ["knee", "patell", "troch", "acl", "pcl", "mcl", "lcl", "menisc", "tka", "total knee", "tibial plateau"]):
        return "knee"

    # Ankle / foot
    if contains_any(t, ["ankle", "malleol", "talus", "pilon"]):
        return "ankle"
    if contains_any(t, ["midfoot", "lisfranc", "navicular", "cuneiform", "cuboid"]):
        return "midfoot"
    if contains_any(t, ["foot", "forefoot", "hindfoot", "calcane", "metatars", "toe"]):
        return "foot"

    # Leg / thigh / upper limb
    if contains_any(t, ["tibia", "tibial shaft", "fibula", "shaft fracture of tibia"]):
        return "leg"
    if contains_any(t, ["femur", "femoral shaft", "thigh"]):
        return "thigh"
    if contains_any(t, ["shoulder", "glenoid", "labrum", "rotator cuff", "humerus"]):
        return "shoulder"
    if contains_any(t, ["elbow", "olecranon", "radial head", "distal humerus"]):
        return "elbow"
    if contains_any(t, ["forearm", "radius", "ulna"]):
        return "forearm"
    if contains_any(t, ["wrist", "distal radius", "carpal"]):
        return "wrist"
    if "hand" in t or contains_any(t, ["metacarp", "phalange"]):
        return "hand"

    # Fallback by specialty
    if specialty in ("basicscience",):
        return "non-anatomic"
    return "global"

# =========================
# 5) Procedure / Diagnosis normalization (lightweight)
# =========================

PROCEDURE_SYNONYMS = {
    "tha": "total hip arthroplasty",
    "total hip arthroplasty": "total hip arthroplasty",
    "total hip replacement": "total hip arthroplasty",
    "tka": "total knee arthroplasty",
    "total knee arthroplasty": "total knee arthroplasty",
    "total knee replacement": "total knee arthroplasty",
    "revision tha": "revision total hip arthroplasty",
    "revision total hip arthroplasty": "revision total hip arthroplasty",
    "revision tka": "revision total knee arthroplasty",
    "revision total knee arthroplasty": "revision total knee arthroplasty",
    "lumbar fusion": "lumbar fusion",
    "meniscectomy": "meniscectomy",
    "orif": "orif",
    "external fixation": "external fixation",
    "intramedullary nailing": "intramedullary nailing",
    "im nailing": "intramedullary nailing",
    "im nail": "intramedullary nailing",
    "arthroscopy": "arthroscopy",
}

DIAGNOSIS_SYNONYMS = {
    "hip djd": "hip osteoarthritis",
    "hip osteoarthritis": "hip osteoarthritis",
    "knee djd": "knee osteoarthritis",
    "knee osteoarthritis": "knee osteoarthritis",
    "avn": "avascular necrosis of femoral head",
    "avascular necrosis": "avascular necrosis of femoral head",
    "trochanteric bursitis": "trochanteric bursitis",
    "patellofemoral pain": "patellofemoral pain syndrome",
    "pfps": "patellofemoral pain syndrome",
    "patella baja": "patella baja",
    "mcl deficiency": "MCL deficiency",
    "tha dislocation": "THA dislocation",
    "tha impingement": "THA impingement",
}

def normalize_procedure(raw_proc: Any, fulltext: str) -> Tuple[str, str]:
    rp = norm_text(raw_proc)
    if rp:
        canon = PROCEDURE_SYNONYMS.get(rp, "")
        if canon:
            return canon, rp

    # infer from text (light)
    t = norm_text(fulltext)
    if contains_any(t, [" total hip arthroplasty", " tha ", " hip arthroplasty", "total hip replacement"]):
        return "total hip arthroplasty", rp
    if contains_any(t, [" total knee arthroplasty", " tka ", " knee arthroplasty", "total knee replacement"]):
        return "total knee arthroplasty", rp
    if "meniscectomy" in t:
        return "meniscectomy", rp
    if "lumbar fusion" in t:
        return "lumbar fusion", rp
    if "orif" in t:
        return "orif", rp
    if contains_any(t, ["external fix", "ex fix", "external fixation"]):
        return "external fixation", rp

    return "", rp

def normalize_diagnosis(raw_dx: Any, fulltext: str) -> Tuple[str, str]:
    rd = norm_text(raw_dx)
    if rd:
        canon = DIAGNOSIS_SYNONYMS.get(rd, "")
        if canon:
            return canon, rd

    # infer from text (very conservative)
    t = norm_text(fulltext)

    # only infer if the card is clearly about the condition (keywords)
    if contains_any(t, [" trochanteric bursitis"]):
        return "trochanteric bursitis", rd
    if contains_any(t, [" patella baja"]):
        return "patella baja", rd
    if contains_any(t, [" trochlear dysplasia", " hypoplastic trochlear"]):
        return "trochlear dysplasia", rd
    if contains_any(t, [" patellar maltracking", " patellar tracking"]):
        return "patellar maltracking", rd
    if contains_any(t, ["tha dislocat", "hip dislocat after tha"]):
        return "THA dislocation", rd
    if contains_any(t, ["impingement in tha", "acetabular impingement"]):
        return "THA impingement", rd
    if contains_any(t, ["mcl is completely absent", "mcl deficient", "mcl deficiency"]):
        return "MCL deficiency", rd

    return "", rd

# =========================
# 6) Record normalization
# =========================

def build_fulltext(record: Dict[str, Any]) -> str:
    parts: List[str] = []
    for k in ("question", "answer", "additional_info", "fact"):
        v = record.get(k)
        if v:
            parts.append(str(v))
    md = record.get("metadata") or {}
    # include raw metadata to help inference
    for k in ("specialty", "region", "procedure", "diagnosis"):
        v = md.get(k)
        if v:
            parts.append(f"{k}: {v}")
    return norm_text(" ".join(parts))

def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    md = record.get("metadata") or {}
    fulltext = build_fulltext(record)

    # specialty
    specialty, specialty_raw = normalize_specialty(md.get("specialty"))

    # region + subregion + concepts
    region, subregion, region_raw, subregion_raw, concepts = normalize_region(
        md.get("region"),
        fulltext=fulltext,
        specialty=specialty or "",
    )

    # approach (optional)
    approach = infer_approach(fulltext)

    # procedure/diagnosis
    procedure, procedure_raw = normalize_procedure(md.get("procedure"), fulltext)
    diagnosis, diagnosis_raw = normalize_diagnosis(md.get("diagnosis"), fulltext)

    # Validate against allowlists (hard stop → blank)
    if specialty and specialty not in STANDARD_SPECIALTIES:
        specialty = ""
    if region and region not in STANDARD_REGIONS:
        region = "global"

    if procedure and procedure not in STANDARD_PROCEDURES:
        procedure = ""
    if diagnosis and diagnosis not in STANDARD_DIAGNOSES:
        diagnosis = ""

    # write back standardized metadata
    new_md = dict(md)  # preserve any extras you already have
    new_md["specialty"] = specialty
    new_md["region"] = region
    new_md["procedure"] = procedure
    new_md["diagnosis"] = diagnosis

    # debug / trace fields
    new_md["specialty_raw"] = specialty_raw
    new_md["region_raw"] = region_raw or norm_text(md.get("region"))
    if subregion:
        new_md["subregion"] = subregion
    else:
        new_md.pop("subregion", None)

    if subregion_raw:
        new_md["subregion_raw"] = subregion_raw
    else:
        # keep original if it was not mapped but existed
        rr = norm_text(md.get("region"))
        if rr and rr not in (region, ""):
            new_md["subregion_raw"] = rr

    if concepts:
        new_md["concept"] = concepts
    else:
        new_md.pop("concept", None)

    if approach:
        new_md["approach"] = approach
    else:
        new_md.pop("approach", None)

    # keep procedure_raw/diagnosis_raw only if they existed or differ
    pr = norm_text(md.get("procedure"))
    dx = norm_text(md.get("diagnosis"))
    if pr and pr != norm_text(procedure):
        new_md["procedure_raw"] = pr
    else:
        new_md.pop("procedure_raw", None)

    if dx and dx != norm_text(diagnosis):
        new_md["diagnosis_raw"] = dx
    else:
        new_md.pop("diagnosis_raw", None)

    record["metadata"] = new_md
    return record

# =========================
# 7) JSONL IO
# =========================

def iter_jsonl(path: str) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON decode error at line {line_no}: {e}")

def write_jsonl(path: str, records: Iterable[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def main(argv: List[str]) -> int:
    if len(argv) != 3:
        print("Usage: python normalize_metadata.py input.jsonl output.normalized.jsonl")
        return 2

    inp, outp = argv[1], argv[2]
    normalized = (normalize_record(r) for r in iter_jsonl(inp))
    write_jsonl(outp, normalized)
    print(f"✅ Wrote normalized JSONL → {outp}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
