import json
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")

client = OpenAI(api_key=OPENAI_API_KEY, project=OPENAI_PROJECT_ID)

# ── STRUCTURED OUTPUT SCHEMA ────────────────────────────────
SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "pimpQuestions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Ranked Q/A strings formatted as 'Q: … A: …'."
        },
        "otherUsefulFacts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Ranked, case-relevant facts (concise, de-duplicated)."
        }
    },
    "required": ["pimpQuestions", "otherUsefulFacts"],
    "additionalProperties": False
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "emit_refined_output",
            "description": "Return the final curated output as strict JSON.",
            "parameters": SCHEMA
        }
    }
]

def _looks_like_qa(s: str) -> bool:
    s = (s or "").strip()
    return s.startswith("Q:") and " A:" in s


def refine_case_snippets(user_query: str, snippets: List[str]) -> Dict[str, Any]:
    """
    Curate high-yield OR questions and case-relevant facts from vetted notes,
    strictly for the provided case, using GPT-5 with function-calling JSON output.
    """
    system_prompt = (
        "You are a senior orthopaedic surgeon preparing a medical student to assist on a specific case tomorrow.\n"
        "Inputs: (1) a case description, (2) vetted flashcard-style notes.\n\n"
        "Output exactly two ranked lists for THIS case:\n"
        "1) Common Pimp Questions — formatted 'Q: … A: …'\n"
        "2) Other Useful Facts — concise, clinically relevant bullets.\n\n"
        "Rules:\n"
        "• Exclude unrelated anatomy or pathology.\n"
        "• De-duplicate and rank by OR relevance.\n"
        "• Keep each item short but complete.\n"
        "• Return only valid JSON via the provided function."
    )

    user_payload = {"case": user_query, "snippets": snippets}

    try:
        chat = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}
            ],
            tools=TOOLS,
            tool_choice={"type": "function", "function": {"name": "emit_refined_output"}}
            # ✅ temperature omitted → uses default (1.0)
        )

        msg = chat.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None)

        if tool_calls:
            args_str = tool_calls[0].function.arguments
            parsed = json.loads(args_str)
        else:
            content = (msg.content or "").strip()
            parsed = json.loads(content) if content else {}

        pimp = parsed.get("pimpQuestions", [])
        facts = parsed.get("otherUsefulFacts", [])

        pimp_clean = []
        for s in pimp:
            if not isinstance(s, str):
                continue
            s2 = s.strip()
            if not _looks_like_qa(s2):
                if "?" in s2:
                    q, a = s2.split("?", 1)
                    s2 = f"Q: {q.strip()}? A:{a.strip() or ' (answer not provided)'}"
                else:
                    s2 = f"Q: {s2} A: (answer not provided)"
            pimp_clean.append(s2)

        facts_clean = [f.strip() for f in facts if isinstance(f, str) and f.strip()]

        return {"pimpQuestions": pimp_clean, "otherUsefulFacts": facts_clean}

    except Exception as e:
        return {
            "pimpQuestions": [],
            "otherUsefulFacts": [f"❌ GPT-5 formatting error: {str(e)}"]
        }
