import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI

# Load OpenAI credentials from .env
load_dotenv()
client = OpenAI()  # loads from env by default

# Paths
input_path = "embed_orthoanatomy_an.txt"
output_path = "output_flashcards_orthoanatomy.jsonl"

# Keyword lists
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

orthopaedic_specialties = [
    "Trauma", "Sports", "Recon", "Hand", "Peds",
    "Spine", "Onc", "FootAnkle", "ShoulderElbow"
]

# --- GPT-based helpers ---
def gpt_fix_card(raw_text):
    prompt = f"""
You are a senior orthopaedic attending surgeon educating residents. Here is a poorly formatted Anki cloze deletion flashcard:

\"{raw_text.strip()}\"

Extract and reformat as:
Q: ...
A: ...
Additional Info: ...

Only output that exact format.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ GPT Card Error: {e}")
        return None



def gpt_assign_region(question, answer):
    region_list = [
        "ShoulderGirdle", "Clavicle", "ACJoint", "Scapula", "ProximalHumerus", "HumeralShaft",
        "Elbow", "DistalHumerus", "Olecranon", "RadialHead", "Forearm", "Radius", "Ulna",
        "Wrist", "DistalRadius", "Scaphoid", "Carpus", "TFCC",
        "Hand", "Metacarpal", "Phalanges", "Thumb", "PIPJoint", "DIPJoint",
        "CervicalSpine", "ThoracicSpine", "LumbarSpine", "Sacrum", "Pelvis", "SIJoint",
        "Hip", "FemoralHead", "FemoralNeck", "Intertrochanteric", "Subtrochanteric",
        "FemoralShaft", "DistalFemur", "Knee", "Patella", "TibialPlateau",
        "TibialSpine", "TibialTubercle", "TibialShaft", "ProximalTibia", "DistalTibia",
        "Ankle", "Malleolus", "Talus", "Calcaneus", "Navicular", "Cuboid",
        "Lisfranc", "Midfoot", "Metatarsal", "PhalangesFoot", "Toe"
    ]

    prompt = f"""
You are a senior orthopaedic surgeon classifying the anatomical region for a clinical flashcard.

Choose **one and only one** of the following regions that best fits this flashcard:

{region_list}

DO NOT return anything outside this list. If multiple areas are relevant, choose the most specific one.

---
Q: {question}
A: {answer}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        region = response.choices[0].message.content.strip()
        return region if region in region_list else ""
    except Exception as e:
        print(f"❌ GPT Region Error: {e}")
        return ""

# --- Utilities ---
def clean_field(text):
    if not text:
        return ""
    return re.sub(r"\{\{c\d+::(.*?)\}\}", r"\1", text).strip()

def extract_metadata(tags):
    specialty, region = None, None
    if tags:
        for part in tags.split():
            if "::" in part:
                specialty = part.split("::")[0]
            if any(region in part for region in ["Shoulder", "Elbow", "Hip", "Knee", "Spine", "Wrist", "Hand", "Foot", "Ankle"]):
                region = part
    return specialty, region

def find_match(text, keywords_lower, keywords_original):
    lower = text.lower()
    for i, key in enumerate(keywords_lower):
        if key in lower:
            return keywords_original[i]
    return None

def parse_gpt_format(text):
    q = re.search(r"Q:\s*(.*)", text)
    a = re.search(r"A:\s*(.*)", text)
    info = re.search(r"Additional Info:\s*(.*)", text)
    return (
        q.group(1).strip() if q else "",
        a.group(1).strip() if a else "",
        info.group(1).strip() if info else ""
    )

# --- Main loop ---
with open(input_path, 'r') as infile, open(output_path, 'w') as outfile:
    for i, line in enumerate(infile, 1):
        parts = line.strip().split("\t")
        if not parts or not parts[0].strip():
            continue

        raw_text = parts[0]

        # ❌ Skip if not a question
        if "?" not in raw_text:
            continue

        try:
            q_part, a_part = raw_text.split("?", 1)
            question = clean_field(q_part.strip() + "?")
            answer = clean_field(a_part.strip())
        except ValueError:
            continue  # skip malformed cards

        additional_info = clean_field(parts[1]) if len(parts) > 1 else ""
        combined_text = f"{question} {answer} {additional_info}"

        # Keyword match (optional but kept)
        procedure = find_match(combined_text, procedure_keywords_lower, procedure_keywords)
        diagnosis = find_match(combined_text, diagnosis_keywords_lower, diagnosis_keywords)

        # ✅ Force specialty as "Anatomy"
        specialty = "Anatomy"

        # ✅ Always assign region via GPT
        region = gpt_assign_region(question, answer).strip()

        card = {
            "question": question,
            "answer": answer,
            "additional_info": additional_info,
            "metadata": {
                "specialty": specialty,
                "region": region or "",
                "procedure": procedure or "",
                "diagnosis": diagnosis or ""
            }
        }

        outfile.write(json.dumps(card) + "\n")

        if i % 10 == 0:
            print(f"✅ Processed {i} lines")
