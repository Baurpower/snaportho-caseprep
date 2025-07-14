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
        "You are an expert orthopaedic surgical educator. Rewrite a surgical case prompt to generate better results from our vector database. "
        "Assign the **closest matching subspecialty** from the list below. Also include orthopaedic region (ie. knee), diagnosis, and procedure "
        "that matches a database of orthopaedic Anki-style flashcards.\n\n"
        "Make sure your output is:\n"
        "- Highly specific\n"
        "- Comma-separated\n"
        "- Includes orthopaedic specialty, region, diagnosis, procedure\n"
        "Avoid filler words. Do not include commentary or formatting. Output only the query string.\n\n"
        f"Subspecialty list: {', '.join(specialty_list)}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
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
