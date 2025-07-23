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
        "You are provided with a case description and a list of flashcard-style notes compiled from vetted orthopaedic resources.\n\n"
        "Your task is to curate and organize:\n"
        "1. High-yield OR questions (i.e., Common Pimp Questions)\n"
        "2. High-yield case-relevant facts (i.e., Other Useful Facts)\n\n"
        "Guidelines for Common Pimp Questions:\n"
        "- Only include questions directly related to the case. Exclude content from unrelated body regions.\n"
        "- Format each question and answer clearly to maximize educational value.\n"
        "- Rank questions by clinical relevance to the specific surgical scenario.\n\n"
        "Guidelines for Other Useful Facts:\n"
        "- Include only facts directly relevant to the case. Exclude content from unrelated body regions.\n"
        "- Rank by importance and utility in the OR.\n\n"
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
