import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI


# -----------------------------
# IO helpers
# -----------------------------

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
    """
    Compact the approach catalog so you're not shipping huge payloads to the model.
    Keep the fields most useful for selection and quiz generation.
    """
    rows = []
    for a in catalog:
        aliases = a.get("aliases") or []
        meta = a.get("meta") or {}
        rows.append(
            {
                "id": a.get("id"),
                "name": a.get("name"),
                "aliases": aliases[:5],
                "region": meta.get("region"),
                "anatomic_area": meta.get("anatomic_area"),
                "joint": meta.get("joint"),
                "summary": (a.get("text", "") or "")[:280],
            }
        )
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
    catalog_max_chars: int = 12000,
) -> Dict[str, Any]:
    """
    Fast pass: select 1-3 approach IDs from a compacted catalog.
    """
    catalog_compact = compact_catalog_for_prompt(catalog, max_chars=catalog_max_chars)

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

    # Safety filter: keep only IDs that exist in the full catalog
    valid_ids = {a.get("id") for a in catalog if a.get("id")}
    result["selected"] = [x for x in result.get("selected", []) if x.get("id") in valid_ids]

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
    max_selected_chars: int = 12000,
) -> Dict[str, Any]:
    """
    Generates anatomy questions for the selected approaches.
    Speed-focused:
      - Only ships the *selected* approach entries (not full catalog).
      - Truncates payload to a reasonable char limit.
    """
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
        "- Always set approach_id to one of the provided selected approach IDs.\n"
    )

    selected_json = json.dumps(selected, ensure_ascii=False)
    user_input = (
        f"SELECTED APPROACHES (JSON):\n{selected_json[:max_selected_chars]}\n\n"
        f"Create ~{num_questions} questions total, spread across the approaches."
    )

    out = llm.run(
        instructions=instructions,
        user_input=user_input,
        json_schema=ANATOMY_QUIZ_SCHEMA,
    )

    # Safety filter: drop any questions that reference an approach_id we didn't pick
    allowed = set(selected_ids)
    out["questions"] = [q for q in out.get("questions", []) if q.get("approach_id") in allowed]

    return out


# -----------------------------
# Orchestrator (Stages 1 + 2 only)
# -----------------------------

def run_pipeline_fast(
    *,
    case_prompt: str,
    catalog: List[Dict[str, Any]],
    model_selector: str = "gpt-4.1-mini",
    model_quiz: str = "gpt-4.1-mini",
    client: Optional[OpenAI] = None,
    # Speed knobs
    n_min: int = 1,
    n_max: int = 3,
    num_questions: int = 8,
    catalog_max_chars: int = 12000,
    max_selected_chars: int = 12000,
) -> Dict[str, Any]:
    """
    Fast pipeline:
      1) approach selection
      2) anatomy quiz
    (Stage 3 removed.)
    """
    client = client or OpenAI()

    selector = OpenAIJson(client, model_selector)
    quizzer = OpenAIJson(client, model_quiz)

    sel = select_approaches(
        selector,
        case_prompt=case_prompt,
        catalog=catalog,
        n_min=n_min,
        n_max=n_max,
        catalog_max_chars=catalog_max_chars,
    )
    selected_ids = [x["id"] for x in sel.get("selected", [])]

    if not selected_ids:
        return {
            "approachSelection": sel,
            "anatomyQuiz": {"questions": []},
        }

    quiz = build_quiz(
        quizzer,
        selected_ids=selected_ids,
        catalog=catalog,
        num_questions=num_questions,
        max_selected_chars=max_selected_chars,
    )

    return {
        "approachSelection": sel,
        "anatomyQuiz": quiz,
    }