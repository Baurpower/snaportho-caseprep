import json
from openai import OpenAI
from dotenv import load_dotenv

# Load credentials
load_dotenv()
client = OpenAI()

input_path = "output_flashcards_pp.jsonl"
output_path = "output_vectorversion_pp.jsonl"

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


def gpt_force_assign_region(question, answer):
    prompt = f"""
You are a senior orthopaedic surgeon classifying the anatomical region for a clinical flashcard.

Choose **one and only one** region that best fits this flashcard. You should ideally choose from the following known orthopaedic regions:

{region_list}

But if the flashcard does not match any of those, you must still choose a region name that best fits based on anatomy or procedure. You may invent a new one if absolutely necessary.

Return only the region name. Do not write anything else.

---
Q: {question}
A: {answer}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ GPT Region Error: {e}")
        return "UnknownRegion"


# Process file
with open(input_path, 'r') as infile, open(output_path, 'w') as outfile:
    for i, line in enumerate(infile, 1):
        try:
            card = json.loads(line)
            region = card["metadata"].get("region", "").strip()

            if not region:
                print(f"🧠 Assigning region for card {i}...")
                question = card.get("question", "")
                answer = card.get("answer", "")
                new_region = gpt_force_assign_region(question, answer)

                if new_region in region_list:
                    print(f"→ Region matched: {new_region}")
                else:
                    print(f"→ ⚠️ Region created: {new_region}")

                card["metadata"]["region"] = new_region

            outfile.write(json.dumps(card) + "\n")

            if i % 10 == 0:
                print(f"✅ Processed {i} cards")

        except Exception as e:
            print(f"❌ Skipped a line due to error: {e}")
