import os
import json
import re
import time
from dotenv import load_dotenv
from openai import OpenAI

# ── Load environment
load_dotenv()

# ── Initialize OpenAI client
client = OpenAI()

# ── GPT rate limit (approx 60 calls/minute)
GPT_SLEEP_SECONDS = 1.1


# ── File paths
input_path = "embed_orthobullets_an.txt"
output_path = "output_vectorversion_ob_facts.jsonl"
rejected_log_path = "rejected_facts_ob.log"

# ── Metadata keywords
procedure_keywords = [  # Use the full list you verified
    "ORIF", "Closed Reduction", "Open Reduction", "Hemiarthroplasty",
    "Total Shoulder Arthroplasty", "Reverse Total Shoulder Arthroplasty",
    "Arthroscopic Repair", "Rotator Cuff Repair", "Latarjet",
    "Remplissage", "Tenodesis", "Bankart Repair", "Labral Repair",
    "Fasciotomy", "Discectomy", "Spinal Fusion", "Intramedullary Nailing",
    "Plate Fixation", "Meniscectomy", "Meniscal Repair",
    "Superior Capsular Reconstruction", "Debridement", "Capsular Shift",
    "SCR", "Trigger Finger Release", "Carpal Tunnel Release", "Mumford",
    "AC Joint Reconstruction", "Vertebroplasty", "Kyphoplasty",
    "Microfracture", "Osteotomy", "External Fixation", "Amputation"
]

diagnosis_keywords = [  # Expanded list from prior message
    "Shoulder Dislocation", "Rotator Cuff Tear", "Biceps Tendinopathy", "SLAP Lesion",
    "Clavicle Fracture", "Labral Tear", "Frozen Shoulder", "Septic Arthritis",
    "Osteomyelitis", "Osteoporosis", "Compartment Syndrome", "Radial Nerve Palsy",
    "Spinal Fracture", "Pelvic Fracture", "Femoral Shaft Fracture", "Patellar Fracture",
    "Tibial Plateau Fracture", "Lisfranc Injury", "Scaphoid Fracture", "TFCC Tear",
    "Mallet Finger", "Dupuytren’s Contracture", "Monteggia Fracture", "Galeazzi Fracture",
    "Thoracic Outlet Syndrome", "Spondylolysis", "Chance Fracture", "SLAP",
    "Multidirectional Instability", "Posterior Glenoid Bone Loss", "GIRD",
    "Bankart Lesion", "Massive Rotator Cuff Tear", "Cervical Radiculopathy",
    "Hip Dysplasia", "Cam Deformity", "Femoroacetabular Impingement", "ACL Tear",
    "PCL Tear", "Meniscal Root Tear", "OCD", "Achilles Rupture", "Hallux Valgus",
    "Morton’s Neuroma", "Plantar Fasciitis", "Tarsal Coalition", "Trigger Finger"
]

specialty_list = ["Trauma", "Sports", "Recon", "Hand", "Peds", "Spine", "Onc", "FootAnkle", "ShoulderElbow", "BasicScience"]
region_list = [
    # Upper Extremity
    "Clavicle", "ACJoint", "glenohumeralJoint", "ShoulderGirdle", "Scapula",
    "ProximalHumerus", "HumeralShaft", "DistalHumerus",
    "Elbow", "RadialHead", "Olecranon", "Coronoid", "Capitellum",
    "Forearm", "Radius", "Ulna",

    # Wrist
    "Wrist", "DistalRadius", "Scaphoid", "Lunate", "Carpus", "TFCC", "DRUJ",

    # Hand
    "Hand", "Metacarpal", "Thumb", "PhalangesHand", "PIPJoint", "DIPJoint", "CMCJoint",

    # Spine
    "CervicalSpine", "ThoracicSpine", "LumbarSpine", "Sacrum", "Coccyx", "SIJoint",

    # Pelvis & Hip
    "Pelvis", "Acetabulum", "PubicRami", "SIJoint",
    "FemoralHead", "FemoralNeck", "Intertrochanteric", "Subtrochanteric",

    # Femur
    "FemoralShaft", "DistalFemur", "SupracondylarFemur", "FemoralCondyles",

    # Knee
    "Knee", "Patella", "TibialPlateau", "TibialSpine", "TibialTubercle",

    # Tibia & Fibula
    "TibialShaft", "DistalTibia",
    "FibularShaft", "ProximalFibula", "DistalFibula",

    # Ankle
    "Ankle", "Malleolus", "MedialMalleolus", "LateralMalleolus", "PosteriorMalleolus", "Syndesmosis",

    # Foot
    "Talus", "Calcaneus", "Navicular", "Cuboid", "Cuneiforms",
    "Lisfranc", "Midfoot", "Metatarsal", "PhalangesFoot", "Toe", "MTPJoint", "IPJointFoot", "SubtalarJoint",
]

procedure_keywords_lower = [p.lower() for p in procedure_keywords]
diagnosis_keywords_lower = [d.lower() for d in diagnosis_keywords]

image_keywords = [
    "image", "shown", "depicted", "seen here", "figure", "mri", "radiograph", "x-ray",
    "arthroscopic view", "arthroscopy", "label", "structure is", "identify structure",
    "in the diagram", "on the diagram", "in the figure", "red arrow", "coronal", "axial", "sagittal"
]

def gpt_assign_specialty(q, a):
    prompt = f"""You are a senior orthopaedic attending. Assign one and only one subspecialty from this list: 
["Trauma", "Sports", "Recon", "Hand", "Peds", "Spine", "Onc", "FootAnkle", "ShoulderElbow"].

Q: {q}
A: {a}

Return just the subspecialty."""
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    time.sleep(GPT_SLEEP_SECONDS)
    return response.choices[0].message.content.strip()

def gpt_assign_region(q, a):
    prompt = f"""You are an orthopaedic surgeon. Based on the following flashcard, assign the most appropriate anatomical region.

Return only the best-fit anatomical region, even if it's not in a predefined list. Be concise (1–3 words max).

Q: {q}
A: {a}
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    time.sleep(GPT_SLEEP_SECONDS)
    return response.choices[0].message.content.strip()


# ── Utilities
def clean_field(text):
    return re.sub(r"\{\{c\d+::(.*?)\}\}", r"\1", text).strip() if text else ""

def extract_metadata_from_tags(tags):
    specialty = next((s for s in specialty_list if s in tags), "")
    region = next((r for r in region_list if r in tags), "")
    return specialty, region

def find_match(text, keywords_lower, keywords_original):
    lower = text.lower()
    for i, key in enumerate(keywords_lower):
        if key in lower:
            return keywords_original[i]
    return ""

# ── Deduplication
processed_facts = set()
if os.path.exists(output_path):
    with open(output_path, "r") as f:
        for line in f:
            try:
                data = json.loads(line)
                processed_facts.add(data.get("fact", "").strip())
            except json.JSONDecodeError:
                continue


# ── Main loop
with open(input_path, "r") as infile, \
     open(output_path, "a") as outfile, \
     open(rejected_log_path, "a") as rejected_log:

    for i, line in enumerate(infile, 1):

        parts = line.strip().split("\t")
        if not parts or not parts[0].strip():
            print("⏩ Skipped (empty or bad format)")
            continue

        raw_text = parts[0]

        # ❌ Unclosed cloze
        if re.search(r"\{\{[^}]*$", raw_text):
            print("❌ Rejected (unclosed cloze)")
            rejected_log.write(f"[Line {i}] ❌ Unclosed cloze: {raw_text}\n")
            continue

        cleaned = clean_field(raw_text)

        # ❌ Skip question-style cards
        if "?" in cleaned:
            print("❌ Rejected (has question mark)")
            rejected_log.write(f"[Line {i}] Skipped qa: {cleaned}\n")
            continue

        # ❌ Skip visual/image-based facts
        if any(keyword in cleaned.lower() for keyword in image_keywords):
            print("❌ Rejected (image keyword found)")
            rejected_log.write(f"[Line {i}] 🖼️ Skipped image-based fact: {cleaned}\n")
            continue

        fact = f"Fact: {cleaned}"
        if fact in processed_facts:
            print("⏩ Skipped (already processed)")
            continue

        # 🧠 Force GPT to assign metadata
        try:
            specialty = gpt_assign_specialty(fact, "")  # Blank answer
        except Exception as e:
            print(f"❌ GPT specialty error: {e}")
            rejected_log.write(f"[Line {i}] ❌ GPT specialty error: {e} | Fact: {fact}\n")
            specialty = ""

        try:
            region = gpt_assign_region(fact, "")  # Blank answer
        except Exception as e:
            print(f"❌ GPT region error: {e}")
            rejected_log.write(f"[Line {i}] ❌ GPT region error: {e} | Fact: {fact}\n")
            region = ""

        procedure = find_match(cleaned, procedure_keywords_lower, procedure_keywords)
        diagnosis = find_match(cleaned, diagnosis_keywords_lower, diagnosis_keywords)

        card = {
            "fact": fact,
            "additional_info": "",
            "metadata": {
                "specialty": specialty,
                "region": region,
                "procedure": procedure or "",
                "diagnosis": diagnosis or ""
            }
        }

        outfile.write(json.dumps(card) + "\n")
        processed_facts.add(fact)
        print(f"✅ Saved: {fact}")

        if len(processed_facts) % 10 == 0:
            print(f"📈 Total processed: {len(processed_facts)}")