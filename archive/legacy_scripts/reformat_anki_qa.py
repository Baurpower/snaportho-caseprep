import os
import json
import re
import time
from dotenv import load_dotenv
from openai import OpenAI

# Load credentials
load_dotenv()
client = OpenAI()

input_path = "embed_hipknee.txt"
output_path = "output_vectorversion_hipknee_qa.jsonl"
rejected_log_path = "rejected_cards_hipknee.log"

# Rate limit settings
GPT_SLEEP_SECONDS = 1.1  # Space GPT calls to ~60 per minute

# --- Keyword lists ---
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
procedure_keywords_lower = [p.lower() for p in procedure_keywords]
diagnosis_keywords_lower = [d.lower() for d in diagnosis_keywords]

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
specialty_list = [
    "Trauma", "Sports", "Recon", "Hand", "Peds", 
    "Spine", "Onc", "FootAnkle", "ShoulderElbow"
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

# --- Utilities ---
def clean_field(text):
    """Replaces cloze fields like {{c1::text}} with 'text' and strips whitespace."""
    return re.sub(r"\{\{c\d+::(.*?)\}\}", r"\1", text).strip() if text else ""

def extract_clozes(text):
    """Extracts cloze deletions from text, e.g., {{c1::humerus}} → ['humerus']"""
    return re.findall(r"\{\{c\d+::(.*?)\}\}", text) if text else []

def extract_metadata_from_tags(tags):
    """Returns (specialty, region) from tag list."""
    specialty = next((s for s in specialty_list if s in tags), "")
    region = next((r for r in region_list if r in tags), "")
    return specialty, region

def find_match(text, keywords_lower, keywords_original):
    lower = text.lower()
    for i, key in enumerate(keywords_lower):
        if key in lower:
            return keywords_original[i]
    return ""

def split_multiple_questions(text):
    """Splits input text into individual questions based on '?'"""
    parts = [q.strip() + "?" for q in text.split("?") if q.strip()]
    return parts

# --- Parser ---
def parse_line(line):
    """Extracts Q&A pairs from a line, only if the cleaned text has a '?'."""
    parts = line.strip().split("\t")
    if not parts:
        return []

    raw_text = parts[0]
    tags = parts[-1] if len(parts) > 1 else ""

    clozes = extract_clozes(raw_text)
    cleaned = clean_field(raw_text)

    # Only continue if there's a '?' in cleaned text
    if "?" not in cleaned:
        return []

    questions = split_multiple_questions(cleaned)
    answer = "; ".join(clozes).strip() if clozes else ""

    specialty, region = extract_metadata_from_tags(tags)

    qna_pairs = []
    for q in questions:
        qna_pairs.append({
            "question": q,
            "answer": answer,
            "specialty": specialty,
            "region": region
        })

    return qna_pairs


# --- Main loop ---
# --- Build set of already processed questions to avoid duplicates ---
processed_questions = set()
if os.path.exists(output_path):
    with open(output_path, "r") as f:
        for line in f:
            try:
                data = json.loads(line)
                processed_questions.add(data.get("question", "").strip())
            except json.JSONDecodeError:
                continue

print(f"⏩ Skipping {len(processed_questions)} previously processed questions.")

# --- Main loop with deduplication ---
with open(input_path, 'r') as infile, open(output_path, 'a') as outfile, open(rejected_log_path, 'a') as rejected_log:
    for i, line in enumerate(infile, 1):
        parts = line.strip().split("\t")
        if not parts or not parts[0].strip():
            continue

        raw_text = parts[0]

        # ❌ Unclosed cloze
        if re.search(r"\{\{[^}]*$", raw_text):
            rejected_log.write(f"[Line {i}] ❌ Unclosed cloze detected: {raw_text}\n")
            continue

        cleaned = clean_field(raw_text)

        # ❌ No question mark
        if "?" not in cleaned:
            rejected_log.write(f"[Line {i}] ❌ No question mark: {cleaned}\n")
            continue

        try:
            q_part, a_part = cleaned.split("?", 1)
            question = q_part.strip() + "?"
            answer = a_part.strip()
        except ValueError:
            rejected_log.write(f"[Line {i}] ❌ Failed to split Q&A: {cleaned}\n")
            continue

        # ❌ Already processed
        if question in processed_questions:
            continue

        # ❌ Visual/image-based content
        image_keywords = [
            "image", "shown", "depicted", "seen here", "figure", "mri", "radiograph", "x-ray",
            "arthroscopic view", "arthroscopy", "label", "structure is", "identify structure",
            "in the diagram", "on the diagram", "in the figure", "red arrow", "coronal", "axial", "sagittal"
        ]
        if any(keyword in question.lower() for keyword in image_keywords):
            rejected_log.write(f"[Line {i}] 🖼️ Skipped visual-based card: {question}\n")
            continue

        additional_info = clean_field(parts[1]) if len(parts) > 1 else ""
        combined_text = f"{question} {answer} {additional_info}"

        procedure = find_match(combined_text, procedure_keywords_lower, procedure_keywords)
        diagnosis = find_match(combined_text, diagnosis_keywords_lower, diagnosis_keywords)

        try:
            specialty = gpt_assign_specialty(question, answer).strip()
        except Exception as e:
            specialty = ""
            rejected_log.write(f"[Line {i}] ❌ GPT specialty error: {e} | Q: {question}\n")

        try:
            region = gpt_assign_region(question, answer).strip()
        except Exception as e:
            region = ""
            rejected_log.write(f"[Line {i}] ❌ GPT region error: {e} | Q: {question}\n")

        if not specialty or len(specialty) > 30:
            rejected_log.write(f"[Line {i}] ❌ Invalid specialty: '{specialty}' | Q: {question}\n")
            specialty = ""
        if not region or len(region) > 50:
            region = ""

        card = {
            "question": question,
            "answer": answer,
            "additional_info": additional_info,
            "metadata": {
                "specialty": specialty,
                "region": region,
                "procedure": procedure or "",
                "diagnosis": diagnosis or ""
            }
        }

        outfile.write(json.dumps(card) + "\n")
        processed_questions.add(question)  # ✅ Add to dedup set

        if len(processed_questions) % 10 == 0:
            print(f"✅ Processed {len(processed_questions)} total unique questions")
