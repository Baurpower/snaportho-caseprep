# ── refine_caseprep.py ────────────────────────────────────────────
"""
Turn a messy list of text snippets into a concise, high-yield payload
that a Next.js front-end can render without further massaging.

Returns:
{
  "keyAnatomy":        ["• bullet", "• bullet", ...],
  "pimpQuestions":     ["Q: …  A: …", ...],
  "otherUsefulFacts":  ["fact1", "fact2", ...]
}
"""
from __future__ import annotations

import os, json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"),
                project=os.getenv("OPENAI_PROJECT_ID"))

GPT_MODEL = "gpt-4o-mini"
TEMPERATURE = 0.3


def _chat(system: str, user: str) -> str:
    """Light wrapper around the chat API."""
    resp = client.chat.completions.create(
        model=GPT_MODEL,
        temperature=TEMPERATURE,
        messages=[{"role": "system", "content": system},
                  {"role": "user",   "content": user}],
    )
    return resp.choices[0].message.content.strip()


# ────────────────────────────────────────────────────────────────
def refine_snippets(case_query: str, snippets: list[str]) -> dict[str, list[str]]:
    """
    1. Deduplicate & truncate long snippets
    2. Ask GPT to:
       • discard irrelevant lines
       • re-write in short, exam-style bullets
       • bucket into our three sections
    3. Return **structured JSON** (NOT markdown)
    """
    if not snippets:
        return {
            "keyAnatomy": [],
            "pimpQuestions": [],
            "otherUsefulFacts": []
        }

    # De-dup & trim
    seen: set[str] = set()
    clean_snips: list[str] = []
    for raw in snippets:
        s = raw.replace("\n", " ").strip()
        if s and s not in seen:
            seen.add(s)
            clean_snips.append(s[:400])  # keep each snippet manageable

    system_msg = (
        "You are an orthopaedic surgery educator.\n"
        "Task: Review the raw flashcard snippets for one surgical case.\n"
        "• Remove duplicates & off-topic info.\n"
        "• Rewrite each surviving idea into a SHORT, high-yield bullet.\n"
        "• Prioritize the MOST important facts and frequently pimped questions.\n"
        "• Emphasize surgical relevance, decision-making, and exam-likelihood.\n"
        "• Bucket bullets into EXACTLY these keys:\n"
        "  - keyAnatomy\n"
        "  - pimpQuestions (Q&A format). Include the most likely to be asked questions first.\n"
        "  - otherUsefulFacts\n"
        "Return ONLY valid JSON — no markdown, no comments."
    )

    user_msg = json.dumps(
        {
            "case": case_query,
            "rawSnippets": clean_snips
        },
        indent=2
    )

    # Call GPT
    raw_json = _chat(system_msg, user_msg)

    # Super-defensive parse — GPT should give valid JSON, but guard anyway
    try:
        payload = json.loads(raw_json)
        # Guarantee keys exist, even if blank
        for k in ("keyAnatomy", "pimpQuestions", "otherUsefulFacts"):
            payload.setdefault(k, [])
        return payload
    except Exception as e:
        # Fallback → wrap everything under "otherUsefulFacts"
        return {
            "keyAnatomy": [],
            "pimpQuestions": [],
            "otherUsefulFacts": [f"GPT-formatting error: {e}", raw_json]
        }
