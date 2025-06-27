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
def refine_case_snippets(user_query: str, snippets: list[str]) -> str:
    system_prompt = (
        "You are a senior orthopaedic surgeon preparing a medical student the night before a case.\n"
        "You are given a case type and a list of flashcard-style notes from various sources.\n"
        "You must carefully filter the information to make sure all content is relevant to the case.\n"
        "If the case is about a distal radius fracture, exclude anything about the humerus, hip, etc.\n"
        "Then, identify the most relevant pimp-style questions and format them clearly.\n"
        "Only include the highest-yield questions and keep it brief and readable.\n\n"
        "Return only valid JSON in the format: {\n"
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
        return json.dumps(json.loads(response.choices[0].message.content.strip()), indent=2)

    except Exception as e:
        return json.dumps({
            "pimpQuestions": [],
            "otherUsefulFacts": [f"❌ GPT formatting error: {str(e)}"]
        }, indent=2)