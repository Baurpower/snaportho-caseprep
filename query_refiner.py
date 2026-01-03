import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

specialty_list = [
    "Trauma", "Sports", "Recon", "Hand", "Peds", 
    "Spine", "Onc", "FootAnkle", "ShoulderElbow", "BasicScience"
]

def refine_query(user_prompt: str) -> str:
    if not user_prompt.strip():
        return ""

    system_prompt = (
        "You are an expert orthopaedic surgical educator. Rewrite the user's surgical case prompt "
        "to generate better results from our vector database.\n\n"
        "Tasks:\n"
        "1) Interpret and expand any common orthopaedic acronyms (e.g., ACL, TKA, THA, TSA, PAO, ACDF) "
        "   into their full forms before processing.\n"
        "2A) Assign the single most relevant orthopaedic subspecialty from the list below.\n"
    "    Use ONLY these exact tokens for subspecialties:\n"
    f"    {', '.join(specialty_list)}\n"
    "2B) If a second orthopaedic subspecialty is clearly and strongly clinically relevant, "
    "you may include up to TWO subspecialties in total.\n"
    "    Again, use ONLY these exact tokens for subspecialties:\n"
    f"    {', '.join(specialty_list)}\n"
        "3) Provide the orthopaedic region (e.g., knee, hip, cervical spine), diagnosis, and procedure "
        "   that best match a database of orthopaedic Anki-style flashcards.\n\n"
        "SUBSPECIALTY MAPPING RULES:\n"
         "- Any case involving the elbow joint MUST include 'ShoulderElbow' and 'Hand' as the subspecialty tokens.\n"
        "- Cases involving the shoulder joint should include 'ShoulderElbow' and 'Sports' as the subspecialty tokens if discussing rotator cuff.\n"
        "SPINE RULE:\n"
        "- If the case involves the cervical, thoracic, lumbar, or sacral spine, mentions vertebral levels "
        "  (e.g., C5–C6, L4–L5, T11), or procedures such as ACDF, PCDF, PLIF, TLIF, ALIF, laminectomy, "
        "  decompression, or spinal fusion, you MUST include the subspecialty token 'Spine' in the output, "
        "  even if other subspecialties (e.g., Trauma) also apply.\n"
        "- Do NOT use 'Recon' instead of 'Spine' for spine surgery.\n\n"
        "OUTPUT FORMAT:\n"
        "- Output MUST be a single comma-separated list of short tokens/phrases.\n"
        "- Start with 1–3 subspecialty tokens taken verbatim from the subspecialty list.\n"
        "- Then include one region token (e.g., 'Cervical Spine', 'Knee', 'Hip').\n"
        "- Then include one diagnosis phrase and one procedure phrase.\n"
        "- You may optionally add 1–2 extra short modifiers (e.g., 'revision', 'open fracture') if useful.\n"
        "- Do NOT include explanations, labels, or extra prose. Output ONLY the comma-separated query string."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # recommended upgrade; can keep 3.5 if you want
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Original prompt: {user_prompt.strip()}"}
            ],
            temperature=0.2,
            max_tokens=80
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Error: {str(e)}"


# ── INTERACTIVE MODE ─────────────────────────────────────────
if __name__ == "__main__":
    print("🧠 Ortho Prompt Refiner")
    while True:
        user_input = input("\nEnter a surgical case prompt (or 'q' to quit): ").strip()
        if user_input.lower() in {"q", "quit", "exit"}:
            break

        refined = refine_query(user_input)
        print(f"\n🛠️ Refined metadata query:\n{refined}")
