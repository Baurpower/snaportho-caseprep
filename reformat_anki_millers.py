import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI

# ── Load OpenAI credentials ─────────────────────────────────
load_dotenv()
client = OpenAI()

input_path = "embed_millers.txt"
output_path = "output_flashcards_millers.jsonl"
log_path = "rejected_cards.log"

# ── Step 1: Load previously processed questions ─────────────
seen_questions = set()
if os.path.exists(output_path):
    with open(output_path, 'r', encoding='utf-8') as existing:
        for line in existing:
            try:
                card = json.loads(line)
                q = card.get("question", "").strip()
                if q:
                    seen_questions.add(q)
            except:
                continue
print(f"🔁 Resuming: {len(seen_questions):,} flashcards already processed.")

# ── Keyword lists ───────────────────────────────────────────
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
    "Spine", "Onc", "FootAnkle", "ShoulderElbow", "BasicScience"
]

# ── GPT Helpers ─────────────────────────────────────────────
def gpt_assign_specialty(question, answer):
    prompt = f"""
You are a senior orthopaedic attending. Assign the **closest matching subspecialty** from the list below based on the following flashcard content. Return only one subspecialty exactly as written in the list.

Subspecialty list:
{', '.join(specialty_list)}

Flashcard:
Q: {question}
A: {answer}

Return only the closest matching subspecialty from the list above. Do not add extra text.
"""
    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        result = resp.choices[0].message.content.strip()
        if result not in specialty_list:
            from difflib import get_close_matches
            match = get_close_matches(result, specialty_list, n=1)
            return match[0] if match else ""
        return result
    except Exception as e:
        print(f"❌ GPT Specialty Error: {e}")
        return ""

def gpt_assign_region(question, answer):
    prompt = f"""
You are an orthopaedic attending. Based on the following flashcard, choose the **most appropriate anatomical region** related to the content.

You must try to select from this list:
{', '.join(region_list)}

If none of these apply, generate a brief new region label (1-3 words max) that best describes the anatomical focus. Return only the region name with no extra text.

Flashcard:
Q: {question}
A: {answer}
"""
    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ GPT Region Error: {e}")
        return ""

def gpt_rewrite_flashcard(raw_line):
    prompt = f"""
You are a senior orthopaedic attending educator. Reformat the following flashcard into a clean, high-yield Q&A format.

Raw:
{raw_line.strip()}

Return only:
Q: ...
A: ...
"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        content = response.choices[0].message.content.strip()
        q = re.search(r"Q:\s*(.+)", content)
        a = re.search(r"A:\s*(.+)", content)
        if q and a:
            return q.group(1).strip(), a.group(1).strip()
    except Exception as e:
        print(f"❌ GPT rewrite error: {e}")
    return None, None

# ── Matching helper ─────────────────────────────────────────
def find_match(text, keywords_lower, keywords_original):
    lower = text.lower()
    for i, key in enumerate(keywords_lower):
        if key in lower:
            return keywords_original[i]
    return ""

# ── Main Loop ───────────────────────────────────────────────
with open(input_path, 'r', encoding='utf-8') as infile, \
     open(output_path, 'a', encoding='utf-8') as outfile, \
     open(log_path, 'a', encoding='utf-8') as log:

    for i, line in enumerate(infile, 1):
        parts = line.strip().split("\t")
        if len(parts) < 2:
            print(f"⚠️ Skipping malformed line {i}")
            log.write(f"{i}: Malformed line (missing tab)\n")
            continue

        question = parts[0].strip()
        answer = parts[1].strip()

        if question in seen_questions:
            continue  # skip duplicate

        if not question or not answer or len(question) < 10 or not question.endswith("?"):
            print(f"⚠️ Invalid Q/A on line {i}, trying GPT fix...")
            try:
                fixed = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an orthopaedic educator. Reformat this malformed flashcard into a useful Q&A pair."},
                        {"role": "user", "content": f"Input:\n{line.strip()}\n\nReturn JSON with keys: question, answer."}
                    ],
                    temperature=0
                )
                json_result = json.loads(fixed.choices[0].message.content)
                question = json_result["question"].strip()
                answer = json_result["answer"].strip()
                if question in seen_questions:
                    continue  # prevent duplicates after GPT fix
            except Exception as e:
                print(f"❌ GPT failed to fix line {i}: {e}")
                log.write(f"{i}: GPT failed to fix → {line.strip()}\n")
                continue

        # Find keywords
        full_text = f"{question} {answer}"
        diagnosis = find_match(full_text, diagnosis_keywords_lower, diagnosis_keywords)
        procedure = find_match(full_text, procedure_keywords_lower, procedure_keywords)

        # Assign GPT-based metadata
        specialty = gpt_assign_specialty(question, answer)
        region = gpt_assign_region(question, answer)

        card = {
            "question": question,
            "answer": answer,
            "additional_info": "",
            "metadata": {
                "specialty": specialty,
                "region": region,
                "diagnosis": diagnosis,
                "procedure": procedure
            }
        }

        outfile.write(json.dumps(card) + "\n")
        seen_questions.add(question)

        if i % 10 == 0:
            print(f"✅ Processed {i} lines")

print("🏁 Script complete – new cards added to output.")
