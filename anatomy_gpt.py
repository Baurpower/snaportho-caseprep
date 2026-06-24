import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

# Deterministic router (optional pre-filter) + validator + supported case gate
try:
    from approach_router import get_allowed_and_blocked, validate_selected_approaches, get_supported_case
except Exception:
    get_allowed_and_blocked = None
    validate_selected_approaches = None
    get_supported_case = None


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
    allowed_approach_ids: Optional[List[str]] = None,
    blocked_approach_ids: Optional[List[str]] = None,
    router_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Fast pass: select 1-3 approach IDs from a compacted catalog.

    If allowed_approach_ids is provided (from deterministic router), the prompt
    is heavily constrained to only those IDs. GPT is not allowed to pick
    blocked ones. This prevents clinically wrong choices for obvious procedures.
    """
    catalog_compact = compact_catalog_for_prompt(catalog, max_chars=catalog_max_chars)

    # Build constrained instructions if router data is present
    constraint_text = ""
    if allowed_approach_ids:
        allowed_str = ", ".join(allowed_approach_ids)
        constraint_text = (
            f"\nDETERMINISTIC ROUTER RESULT (high confidence):\n"
            f"You MUST choose ONLY from these allowed approach IDs: [{allowed_str}]\n"
        )
        if blocked_approach_ids:
            blocked_str = ", ".join(blocked_approach_ids)
            constraint_text += f"DO NOT choose any of these blocked IDs: [{blocked_str}]\n"
        if router_info:
            constraint_text += f"Router rationale: {router_info.get('rationale', '')}\n"

    instructions = (
        "You are an orthopaedic surgical approach selector.\n"
        "Task: Given a case scenario and a catalog of predefined approaches, choose the best 1–3 approach IDs.\n"
        "Hard rules:\n"
        "- Only output IDs that exist in the provided catalog.\n"
        "- Prefer the most anatomically appropriate approach(es) given the case.\n"
        "- Keep rationales short and practical.\n"
        + constraint_text
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

    # --- Router pre-filter (deterministic safety layer) + supported case gate ---
    router_info = None
    allowed = None
    blocked = None
    supported = True
    enforce_supported_gate = os.getenv("ENABLE_LOCAL_ANATOMY_RAG", "").lower() in ("1", "true", "yes", "on")
    if get_allowed_and_blocked or get_supported_case:
        try:
            if get_supported_case:
                sc = get_supported_case(case_prompt)
                supported = bool(sc.get("supported", True))
                router_info = sc  # richer shape
                if supported or not enforce_supported_gate:
                    allowed = sc.get("recommended_approach_ids") or sc.get("allowed_approach_ids") or None
                    blocked = sc.get("blocked_approach_ids") or None
                else:
                    # Gate (only when ENABLE_LOCAL=true): do not allow free-form GPT guessing for unsupported
                    allowed = []
                    blocked = sc.get("blocked_approach_ids", [])
                    if router_info:
                        router_info["selectionMode"] = "unsupported_case_no_approach_guessing"
            elif get_allowed_and_blocked:
                router_info = get_allowed_and_blocked(case_prompt)
                if router_info.get("confidence") in ("high", "medium"):
                    allowed = router_info.get("allowed_approach_ids") or None
                    blocked = router_info.get("blocked_approach_ids") or None
        except Exception:
            router_info = None
            supported = True  # fail open

    if not supported and enforce_supported_gate:
        # Short-circuit: return limited without running full GPT select/quiz (only under ENABLE=true)
        limited_sel = {
            "selected": [],
            "notes": (router_info or {}).get("reason", "Case not supported by curated approach playbook; no approach guessing performed."),
            "router": router_info or {"case_family": "unknown", "selectionMode": "unsupported_case_no_approach_guessing"},
        }
        return {
            "approachSelection": limited_sel,
            "anatomyQuiz": {"questions": []},
            "router": router_info,
        }

    sel = select_approaches(
        selector,
        case_prompt=case_prompt,
        catalog=catalog,
        n_min=n_min,
        n_max=n_max,
        catalog_max_chars=catalog_max_chars,
        allowed_approach_ids=allowed,
        blocked_approach_ids=blocked,
        router_info=router_info,
    )
    selected_ids = [x["id"] for x in sel.get("selected", [])]

    # Attach router metadata to the selection result for downstream transparency
    if router_info:
        sel["router"] = {
            "case_family": router_info.get("case_family"),
            "selectionMode": "deterministic_router" if allowed else "legacy_gpt_selector",
            "allowedApproachIds": allowed or [],
            "blockedApproachIds": blocked or [],
            "routerRationale": router_info.get("rationale", ""),
        }

    # --- Safety validation (post-GPT) ---
    valid_catalog_ids = {a.get("id") for a in catalog if a.get("id")}
    if validate_selected_approaches is not None:
        validation = validate_selected_approaches(selected_ids, valid_catalog_ids, router_info)
    else:
        # Guard: router/validator import was skipped (defensive try/except at module top).
        # Preserve selection; mark as unvalidated so downstream (hybrid) still gets approachSelection.
        validation = {
            "valid_selected": selected_ids,
            "removed": [],
            "reason": "validator unavailable (approach_router import skipped or None)",
        }
    sel["validation"] = validation
    # Overwrite selected with only the validated ones
    if validation.get("valid_selected"):
        # Rebuild the selected list from original sel to preserve confidence/rationale
        orig_by_id = {x["id"]: x for x in sel.get("selected", [])}
        sel["selected"] = [orig_by_id[i] for i in validation["valid_selected"] if i in orig_by_id]
        selected_ids = validation["valid_selected"]
    else:
        sel["selected"] = []
        selected_ids = []

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

    result = {
        "approachSelection": sel,
        "anatomyQuiz": quiz,
    }
    # If router provided metadata, surface it at top level of the legacy anatomy result
    # so hybrid builder / callers can expose selectionMode etc.
    if router_info:
        result["router"] = sel.get("router")
    return result