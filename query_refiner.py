import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def refine_query(user_prompt: str) -> str:
    if not user_prompt.strip():
        return ""

    system_prompt = (
    "You are an expert surgical educator. Rewrite a raw clinical prompt into a longer, high-yield query "
    "that matches a database of orthopaedic Anki-style flashcards.\n\n"
    "Make sure your output is:\n"
    "- Highly specific\n"
    "- Comma-separated\n"
    "- Includes anatomy, injury pattern, classification system, surgical approach, common complications, and rehab concerns if relevant\n"
    "- Up to 30 tokens long, resembling a detailed flashcard topic header\n\n"
    "Avoid filler words. Do not include commentary or formatting. Output only the query string."
)


    try:
        response = client.chat.completions.create(
            model="gpt-4o",
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

# Optional CLI test mode
if __name__ == "__main__":
    sample = "I have a terrible triad elbow case tomorrow morning — what should I study?"
    print("🔍 Refined query:", refine_query(sample))
