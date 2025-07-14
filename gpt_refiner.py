### gpt_refiner.py

import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")

client = OpenAI(api_key=OPENAI_API_KEY, project=OPENAI_PROJECT_ID)

# ── GPT REFINER ───────────────────────────────────────────────
# gpt_refiner.py
def refine_case_snippets(user_query: str, snippets: list[str]) -> dict:
    system_prompt = (
    "You are a senior orthopaedic surgeon preparing a medical student to assist on a specific surgical case tomorrow.\n"
    "You are given a brief case description and a list of flashcard-style notes from vetted orthopaedic resources.\n"
    "Your job is to rank and reformat the high-yield OR questions that a junior resident is expected to know during this specific case.\n"
    "Focus on:\n"
    "- Commonly pimped questions\n"
    "- Operative treatment indications including any relevant classification systems that dictate treatment\n"
    "- Surgical approach and anatomy relevant to exposure\n"
    "- Common intra-op pitfalls and complications\n"
    "Return valid JSON only in the following structure:\n"
    "{\n"
    "  \"pimpQuestions\": [\"Q: … A: …\", …],\n"
    "  \"otherUsefulFacts\": [\"…\"]\n"
    "}"
)


    user_payload = json.dumps({
        "case": user_query,
        "snippets": snippets
    }, indent=2)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_payload}
            ]
        )
        return json.loads(response.choices[0].message.content.strip())

    except Exception as e:
        return {
            "pimpQuestions": [],
            "otherUsefulFacts": [f"❌ GPT formatting error: {str(e)}"]
        }
