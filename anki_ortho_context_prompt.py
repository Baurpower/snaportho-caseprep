import json
from typing import Any, Dict, List, Optional

from openai import OpenAI


ALLOWED_LEVELS = [
    "MS4",
    "Junior Resident",
    "Senior Resident",
    "Boards",
]

ALLOWED_YIELD = ["Low", "Medium", "High"]


def _card_level_tool_schema() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "emit_anki_card_level",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "card_level": {
                            "type": "object",
                            "properties": {
                                "level": {
                                    "type": "string",
                                    "enum": ALLOWED_LEVELS,
                                },
                                "oite_yield": {
                                    "type": "string",
                                    "enum": ALLOWED_YIELD,
                                },
                                "why": {"type": "string"},
                            },
                            "required": ["level", "oite_yield", "why"],
                            "additionalProperties": False,
                        },
                        "related_pimp_questions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "question": {"type": "string"},
                                    "answer": {"type": "string"},
                                    "source_id": {"type": "string"},
                                },
                                "required": ["question", "answer", "source_id"],
                                "additionalProperties": False,
                            },
                        },
                        "confidence": {"type": "number"},
                    },
                    "required": ["card_level", "related_pimp_questions", "confidence"],
                    "additionalProperties": False,
                },
            },
        }
    ]


def _fast_system_prompt() -> str:
    return (
        "You are a senior orthopaedic resident teaching a medical student.\n"
        "Return one flat list of the best related pimp questions and one card-level classification.\n"
        "Classify the overall card, not each question.\n"
        "Use only the card and the provided retrieved Q/A.\n"
        "Usually return 4 to 8 questions.\n"
        "Preserve the original question and answer as much as possible, with only light cleanup.\n"
        "Do not include unsupported facts.\n"
        "Do not mention AI, retrieval, or sources.\n"
        "No markdown.\n"
        "Return JSON only through the function tool."
    )


def _enhanced_system_prompt() -> str:
    return (
        "You are a senior orthopaedic resident teaching a medical student during review.\n"
        "Return one flat list of the best related pimp questions and one card-level classification.\n"
        "Sound crisp, clinical, and high-yield. Do not sound like generic chatbot output.\n"
        "Use ONLY the provided card text and retrieved source matches.\n"
        "Do NOT invent unsupported facts, diagnoses, classifications, indications, complications, or procedures.\n"
        "Prefer the diagnosis, subregion, and treatment decision that are explicitly present in the card.\n"
        "If the card is about femoral neck fracture treatment, keep THA/hemiarthroplasty decision-making if supported,"
        " but omit THA component-positioning or unrelated dislocation questions.\n"
        "Related pimp questions must come only from the provided source matches.\n"
        "Choose only the visible questions that best fit the card topic.\n"
        "Do not force a question for every level.\n"
        "Classify the overall card as MS4, Junior Resident, Senior Resident, or Boards.\n"
        "Stay concise and high-yield.\n"
        "Return output only through the function tool."
    )


def _compact_match_for_fast(match: Dict[str, Any]) -> Dict[str, Any]:
    metadata = match.get("metadata") or {}
    return {
        "question": match.get("question"),
        "answer": match.get("answer"),
        "diagnosis": metadata.get("diagnoses") or metadata.get("diagnosis") or [],
        "procedure": metadata.get("procedures") or metadata.get("procedure") or [],
        "region": metadata.get("region"),
        "subregion": metadata.get("subregion"),
        "source": metadata.get("source"),
    }


def _compact_match_for_enhanced(match: Dict[str, Any]) -> Dict[str, Any]:
    metadata = match.get("metadata") or {}
    return {
        "question": match.get("question"),
        "answer": match.get("answer"),
        "specialty": metadata.get("specialty"),
        "region": metadata.get("region"),
        "subregion": metadata.get("subregion"),
        "diagnoses": metadata.get("diagnoses") or [],
        "procedures": metadata.get("procedures") or [],
        "source": metadata.get("source"),
        "score": match.get("score"),
        "rerank_score": match.get("rerank_score"),
    }


def _extract_tool_args(message: Any, tool_name: str) -> Dict[str, Any]:
    tool_calls = getattr(message, "tool_calls", None) or []
    for tool_call in tool_calls:
        try:
            fn = tool_call.function
            if fn and fn.name == tool_name:
                return json.loads(fn.arguments or "{}")
        except Exception:
            continue
    return {}


def format_fast_article_with_gpt(
    *,
    client: OpenAI,
    model: str,
    card: Dict[str, Any],
    source_matches: List[Dict[str, Any]],
    fallback_article: Dict[str, Any],
    timeout_seconds: float,
) -> Optional[Dict[str, Any]]:
    payload = {
        "card": card,
        "fallback_article": fallback_article,
        "source_matches": [_compact_match_for_fast(match) for match in source_matches[:6]],
    }

    completion = client.with_options(timeout=timeout_seconds).chat.completions.create(
        model=model,
        temperature=0.0,
        max_tokens=220,
        messages=[
            {"role": "system", "content": _fast_system_prompt()},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        tools=_card_level_tool_schema(),
        tool_choice={"type": "function", "function": {"name": "emit_anki_card_level"}},
        parallel_tool_calls=False,
    )

    message = completion.choices[0].message
    data = _extract_tool_args(message, "emit_anki_card_level")
    return data if isinstance(data, dict) and data else None


def format_enhanced_anki_ortho_context_with_gpt(
    *,
    client: OpenAI,
    model: str,
    card: Dict[str, Any],
    source_matches: List[Dict[str, Any]],
    badge_hints: Dict[str, Any],
    fallback_article: Dict[str, Any],
    fallback_related_topics: List[str],
    fallback_confidence: float,
    timeout_seconds: float,
) -> Optional[Dict[str, Any]]:
    payload = {
        "card": card,
        "badge_hints": badge_hints,
        "fallback_article": fallback_article,
        "fallback_related_topics": fallback_related_topics,
        "fallback_confidence": fallback_confidence,
        "source_matches": [_compact_match_for_enhanced(match) for match in source_matches[:10]],
        "instructions": {
            "question_selection": "Prefer directly aligned questions; omit procedure-adjacent but off-topic questions.",
            "card_level_policy": "Assign one overall card level and OITE yield with a short explanation.",
        },
    }

    completion = client.with_options(timeout=timeout_seconds).chat.completions.create(
        model=model,
        temperature=0.15,
        max_tokens=520,
        messages=[
            {"role": "system", "content": _enhanced_system_prompt()},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        tools=_card_level_tool_schema(),
        tool_choice={"type": "function", "function": {"name": "emit_anki_card_level"}},
        parallel_tool_calls=False,
    )

    message = completion.choices[0].message
    data = _extract_tool_args(message, "emit_anki_card_level")
    return data if isinstance(data, dict) and data else None
