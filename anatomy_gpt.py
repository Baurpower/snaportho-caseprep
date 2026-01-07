import json
from pathlib import Path  # ✅ needed
from typing import Any, Dict, List, Optional

from openai import OpenAI


def load_catalog_from_jsonl_file(path: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Catalog file not found: {path}")

    with p.open("r", encoding="utf-8") as f:
        for i, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {i} of {path}") from e

    return items

def compact_catalog_for_prompt(catalog: List[Dict[str, Any]], max_chars: int = 12000) -> str:
    rows = []
    for a in catalog:
        aliases = a.get("aliases") or []
        meta = a.get("meta") or {}
        rows.append({
            "id": a.get("id"),
            "name": a.get("name"),
            "aliases": aliases[:5],
            "region": meta.get("region"),
            "anatomic_area": meta.get("anatomic_area"),
            "joint": meta.get("joint"),
            "summary": a.get("text", "")[:280],
        })
    s = json.dumps(rows, ensure_ascii=False)
    return s[:max_chars]


# -----------------------------
# OpenAI JSON-schema helper
# -----------------------------

class OpenAIJson:
    """
    Small helper to enforce JSON schema using Structured Outputs via Responses API.
    """

    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model

    def run(
        self,
        *,
        instructions: str,
        user_input: str,
        json_schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        resp = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=[{"role": "user", "content": user_input}],
            text={
                "format": {
                    "type": "json_schema",
                    "name": json_schema.get("name", "output"),
                    "schema": json_schema["schema"],
                    "strict": True,
                }
            },
        )
        return json.loads(resp.output_text)


# -----------------------------
# Stage 1: Approach selector
# -----------------------------

APPROACH_SELECTOR_SCHEMA = {
    "name": "approach_selection",
    "schema": {
        "type": "object",
        "properties": {
            "selected": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "rationale": {"type": "string"},
                    },
                    "required": ["id", "confidence", "rationale"],
                    "additionalProperties": False,
                },
            },
            "notes": {"type": "string"},
        },
        "required": ["selected", "notes"],
        "additionalProperties": False,
    },
}

def select_approaches(
    llm: OpenAIJson,
    *,
    case_prompt: str,
    catalog: List[Dict[str, Any]],
    n_min: int = 1,
    n_max: int = 3,
) -> Dict[str, Any]:
    catalog_compact = compact_catalog_for_prompt(catalog)

    instructions = (
        "You are an orthopaedic surgical approach selector.\n"
        "Task: Given a case scenario and a catalog of predefined approaches, choose the best 1–3 approach IDs.\n"
        "Hard rules:\n"
        "- Only output IDs that exist in the provided catalog.\n"
        "- Prefer the most anatomically appropriate approach(es) given the case.\n"
        "- Keep rationales short and practical.\n"
    )

    user_input = (
        f"CASE:\n{case_prompt}\n\n"
        f"CATALOG (JSON array; each has id/name/aliases/region/anatomic_area/joint/summary):\n{catalog_compact}\n\n"
        f"Pick {n_min} to {n_max} approach IDs."
    )

    result = llm.run(
        instructions=instructions,
        user_input=user_input,
        json_schema=APPROACH_SELECTOR_SCHEMA,
    )

    valid_ids = {a.get("id") for a in catalog if a.get("id")}
    result["selected"] = [x for x in result["selected"] if x.get("id") in valid_ids]

    if not result["selected"]:
        return {"selected": [], "notes": "No valid approach IDs returned."}

    return result


# -----------------------------
# Stage 2: Anatomy quiz generator
# -----------------------------

ANATOMY_QUIZ_SCHEMA = {
    "name": "approach_anatomy_quiz",
    "schema": {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "minItems": 3,
                "maxItems": 12,
                "items": {
                    "type": "object",
                    "properties": {
                        "approach_id": {"type": "string"},
                        "q": {"type": "string"},
                        "answer": {"type": "string"},
                        "tag": {"type": "string"},
                        "difficulty": {"type": "integer", "minimum": 1, "maximum": 3},
                    },
                    "required": ["approach_id", "q", "answer", "tag", "difficulty"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["questions"],
        "additionalProperties": False,
    },
}

def build_quiz(
    llm: OpenAIJson,
    *,
    selected_ids: List[str],
    catalog: List[Dict[str, Any]],
    num_questions: int = 8,
) -> Dict[str, Any]:
    by_id = {a["id"]: a for a in catalog if "id" in a}
    selected = [by_id[i] for i in selected_ids if i in by_id]

    instructions = (
    "You are an orthopaedic anatomy tutor generating quiz questions.\n"
    "Task: Create high-yield anatomy questions based primarily on the provided catalog entries.\n"
    "\n"
    "Guidelines:\n"
    "- Base questions on information explicitly stated in the catalog text and metadata whenever possible.\n"
    "- Prefer rephrasing or testing catalog facts rather than introducing new concepts.\n"
    "- Do not invent anatomic intervals, structures, or risks that are not clearly implied or mentioned in the catalog.\n"
    "- If a structure or concept is not present in the catalog, avoid asking about it.\n"
    "- Use common surgical phrasing only to clarify catalog content, not to add new facts.\n"
    "- Favor structures at risk, key landmarks, incision paths, and exposure details described in the catalog.\n"
    "- Keep questions concise, practical, and appropriate for board-style or intra-operative recall.\n"
)

    user_input = (
        f"SELECTED APPROACHES (JSON):\n{json.dumps(selected, ensure_ascii=False)[:14000]}\n\n"
        f"Create ~{num_questions} questions total, spread across the approaches."
    )

    return llm.run(
        instructions=instructions,
        user_input=user_input,
        json_schema=ANATOMY_QUIZ_SCHEMA,
    )


# -----------------------------
# Stage 3: High-yield structures extractor
# -----------------------------

HIGH_YIELD_SCHEMA = {
    "name": "high_yield_anatomy",
    "schema": {
        "type": "object",
        "properties": {
            "structures": {
                "type": "array",
                "minItems": 5,
                "maxItems": 60,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "why_high_yield": {"type": "string"},
                        "when_in_case": {"type": "string"},
                        "approach_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 0,
                            "maxItems": 3,
                        },
                    },
                    "required": ["name", "type", "why_high_yield", "when_in_case", "approach_ids"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["structures",],
        "additionalProperties": False,
    },
}

def extract_high_yield(
    llm: OpenAIJson,
    *,
    case_prompt: str,
    selected_ids: List[str],
    catalog: List[Dict[str, Any]],
    retrieved_snippets: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    by_id = {a["id"]: a for a in catalog if "id" in a}
    selected = [by_id[i] for i in selected_ids if i in by_id]

    instructions = (
    "You are an orthopaedic anatomy checklist generator.\n"
    "Task: From the given case and selected surgical approaches, list the anatomic structures that are most likely to be asked about, identified, or protected during the case.\n"
    "\n"
    "Guidelines:\n"
    "- Focus on structures that a resident or medical student would be expected to identify intraoperatively or during case questioning.\n"
    "- Prioritize, in order of importance:\n"
    "  1) Critical structures at risk (major nerves, vessels, and organs whose injury causes major morbidity).\n"
    "  2) Key exposure and approach-related structures (intervals, muscles, tendons, capsule).\n"
    "  3) Fixation- or implant-relevant landmarks (bony landmarks, surfaces used for cuts, alignment, or component positioning).\n"
    "- Include structures commonly used for orientation, retraction, protection, or repair.\n"
    "- Do not list obscure anatomy or structures unlikely to be identified or discussed in this case.\n"
    "- Base selections primarily on the provided catalog and case context; avoid adding anatomy not relevant to the approaches used.\n"
    "- Use provided snippets only as supporting context, not as a source of unrelated anatomy.\n"
    "- Output structured JSON only.\n"
)

    payload = {
        "case": case_prompt,
        "selected_approaches": selected,
        "snippets": retrieved_snippets or [],
    }

    user_input = json.dumps(payload, ensure_ascii=False)[:15000]

    return llm.run(
        instructions=instructions,
        user_input=user_input,
        json_schema=HIGH_YIELD_SCHEMA,
    )


# -----------------------------
# Orchestrator
# -----------------------------

def run_pipeline(
    *,
    case_prompt: str,
    catalog: List[Dict[str, Any]],
    model_selector: str = "gpt-4.1-mini",
    model_quiz: str = "gpt-4.1-mini",
    model_high_yield: str = "gpt-4.1",
    snippets: Optional[List[Dict[str, Any]]] = None,
    client: Optional[OpenAI] = None,  # ✅ optional reuse
) -> Dict[str, Any]:
    client = client or OpenAI()

    selector = OpenAIJson(client, model_selector)
    quizzer = OpenAIJson(client, model_quiz)
    anatomist = OpenAIJson(client, model_high_yield)

    sel = select_approaches(selector, case_prompt=case_prompt, catalog=catalog)
    selected_ids = [x["id"] for x in sel.get("selected", [])]

    # ✅ short-circuit if no approaches selected
    if not selected_ids:
        return {
            "approachSelection": sel,
            "anatomyQuiz": {"questions": []},
            "highYieldAnatomy": {"structures": []},
        }

    quiz = build_quiz(quizzer, selected_ids=selected_ids, catalog=catalog)
    high_yield = extract_high_yield(
        anatomist,
        case_prompt=case_prompt,
        selected_ids=selected_ids,
        catalog=catalog,
        retrieved_snippets=snippets,
    )

    return {
        "approachSelection": sel,
        "anatomyQuiz": quiz,
        "highYieldAnatomy": high_yield,
    }
