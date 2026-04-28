"""
cpt_suggester.py
================
Standalone CPT suggestion engine.

Pipeline:
  Stage 1 — GPT case parsing
  Stage 2 — SQLite candidate retrieval using parsed anatomy/procedure terms
  Stage 3 — GPT reranking + clarifying questions
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_SCRIPT_DIR = Path(__file__).parent.resolve()
DB_PATH: str = os.getenv("CPT_DB_PATH", str(_SCRIPT_DIR / "cpt_codes.db"))

MAX_CANDIDATES: int = 60
TOP_N: int = 5
GPT_MODEL: str = "gpt-4o-mini"

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        project = os.getenv("OPENAI_API_PROJECT_ID") or os.getenv("OPENAI_PROJECT_ID")
        _client = OpenAI(api_key=api_key, project=project, timeout=60.0)
    return _client


# ── Text cleanup ───────────────────────────────────────────────────────────────

def _normalize_query(query: str) -> str:
    q = query.strip()

    replacements = {
        "ORIIF": "ORIF",
        "oriif": "orif",
        "fx": "fracture",
        "Fx": "fracture",
        "CRPP": "closed reduction percutaneous pinning",
        "ORIF": "open reduction internal fixation",
        "I&D": "irrigation and debridement",
        "I and D": "irrigation and debridement",
    }

    for old, new in replacements.items():
        q = q.replace(old, new)

    return q


def _extract_keywords(query: str) -> list[str]:
    stopwords = {
        "a", "an", "the", "for", "of", "in", "on", "at", "to", "with",
        "and", "or", "is", "was", "are", "were", "be", "been", "by",
        "this", "that", "it", "i", "my", "we", "he", "she", "they",
        "year", "old", "patient", "female", "male", "yo", "right", "left",
        "using", "performed", "procedure", "surgery",
    }
    tokens = re.findall(r"[A-Za-z]{3,}", query.lower())
    return list(dict.fromkeys([t for t in tokens if t not in stopwords]))


# ── Stage 1: GPT case parsing ─────────────────────────────────────────────────

_PARSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "anatomic_region": {"type": "string"},
        "specific_bone_or_joint": {"type": "string"},
        "bone_segment": {"type": "string"},
        "procedure": {"type": "string"},
        "approach": {"type": "string"},
        "fixation_or_implant": {"type": "string"},
        "fracture_pattern": {"type": "string"},
        "laterality": {"type": "string"},
        "coding_intent": {"type": "string"},
        "positive_keywords": {
            "type": "array",
            "items": {"type": "string"},
        },
        "negative_keywords": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "anatomic_region",
        "specific_bone_or_joint",
        "procedure",
        "approach",
        "fixation_or_implant",
        "fracture_pattern",
        "laterality",
        "coding_intent",
        "positive_keywords",
        "negative_keywords",
    ],
    "additionalProperties": False,
}

_PARSE_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "emit_case_parse",
            "description": "Extract structured coding-relevant anatomy and procedure terms.",
            "parameters": _PARSE_SCHEMA,
        },
    }
]

_PARSE_PROMPT = """\
You are an orthopaedic surgery coding parser.

Extract the coding-relevant anatomy and procedure from the case description.

Rules:
- Normalize misspellings and orthopaedic abbreviations.
- ORIF means open reduction internal fixation.
- fx means fracture.
- Prefer the most specific anatomy.
- Separate anatomy from generic procedural words.
- For long bones, identify the bone segment when possible:
  proximal, shaft/diaphysis, distal, intra-articular, periarticular.
- Examples:
  intertrochanteric hip fracture = proximal femur / intertrochanteric region
  femoral shaft fracture = femoral shaft
  distal femur fracture = distal femur
  tibial plafond or pilon fracture = distal tibia
  tibial shaft fracture = tibial shaft
  proximal humerus fracture = proximal humerus
  distal radius fracture = distal radius
- If the bone segment is not stated, use "unspecified".
- positive_keywords should help retrieve the correct CPT code.
- negative_keywords should include anatomy/procedures that would be wrong if clearly not part of the case.
- Return only via the function tool.
"""


def _parse_case_with_gpt(case_description: str) -> dict[str, Any]:
    client = _get_client()

    resp = client.chat.completions.create(
        model=GPT_MODEL,
        temperature=0.0,
        max_tokens=700,
        messages=[
            {"role": "system", "content": _PARSE_PROMPT},
            {"role": "user", "content": case_description},
        ],
        tools=_PARSE_TOOL,
        tool_choice={"type": "function", "function": {"name": "emit_case_parse"}},
        parallel_tool_calls=False,
    )

    msg = resp.choices[0].message
    tool_calls = getattr(msg, "tool_calls", None) or []

    for tc in tool_calls:
        if tc.function.name == "emit_case_parse":
            return json.loads(tc.function.arguments or "{}")

    return {}


# ── Stage 2: SQL candidate retrieval ──────────────────────────────────────────

def _row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "code": row["code"],
        "description": row["description"],
        "fellowship": row["fellowship"],
        "category": row["category"],
    }


def _base_candidate_sql(where_clause: str) -> str:
    return f"""
        SELECT DISTINCT
            p.code AS code,
            p.description AS description,
            f.name AS fellowship,
            c.name AS category
        FROM cpt_codes p
        JOIN category_cpt cc ON cc.cpt_id = p.id
        JOIN case_categories c ON c.id = cc.category_id
        JOIN fellowships f ON f.id = c.fellowship_id
        WHERE {where_clause}
        LIMIT ?
    """


def _phrase_like_search(conn: sqlite3.Connection, phrases: list[str], limit: int) -> list[dict]:
    phrases = [p.strip().lower() for p in phrases if p and p.strip()]
    phrases = list(dict.fromkeys(phrases))

    if not phrases:
        return []

    clauses = []
    params: list[Any] = []

    for phrase in phrases:
        clauses.append("LOWER(p.description) LIKE ?")
        params.append(f"%{phrase}%")

        clauses.append("LOWER(c.name) LIKE ?")
        params.append(f"%{phrase}%")

        clauses.append("LOWER(f.name) LIKE ?")
        params.append(f"%{phrase}%")

    params.append(limit)

    sql = _base_candidate_sql(" OR ".join(clauses))
    cur = conn.execute(sql, params)

    return [_row_dict(r) for r in cur.fetchall()]


def _fts_search(conn: sqlite3.Connection, keywords: list[str], limit: int) -> list[dict]:
    if not keywords:
        return []

    def _run(match_expr: str) -> list[dict]:
        try:
            cur = conn.execute(
                """
                SELECT DISTINCT
                    p.code AS code,
                    p.description AS description,
                    f.name AS fellowship,
                    c.name AS category
                FROM cpt_fts fts
                JOIN cpt_codes p ON p.code = fts.code
                JOIN category_cpt cc ON cc.cpt_id = p.id
                JOIN case_categories c ON c.id = cc.category_id
                JOIN fellowships f ON f.id = c.fellowship_id
                WHERE cpt_fts MATCH ?
                LIMIT ?
                """,
                (match_expr, limit),
            )
            return [_row_dict(r) for r in cur.fetchall()]
        except sqlite3.OperationalError:
            return []

    and_expr = " AND ".join(keywords)
    rows = _run(and_expr)
    if rows:
        return rows

    or_expr = " OR ".join(f"{kw}*" for kw in keywords)
    return _run(or_expr)


def _generic_like_search(conn: sqlite3.Connection, keywords: list[str], limit: int) -> list[dict]:
    if not keywords:
        return []

    clauses = []
    params: list[Any] = []

    for kw in keywords:
        clauses.append("LOWER(p.description) LIKE ?")
        params.append(f"%{kw.lower()}%")

        clauses.append("LOWER(c.name) LIKE ?")
        params.append(f"%{kw.lower()}%")

    params.append(limit)

    sql = _base_candidate_sql(" OR ".join(clauses))
    cur = conn.execute(sql, params)

    return [_row_dict(r) for r in cur.fetchall()]


def _build_search_terms(parsed: dict[str, Any], original_query: str) -> dict[str, list[str]]:
    anatomy_terms: list[str] = []
    procedure_terms: list[str] = []
    phrase_terms: list[str] = []

    for key in ["specific_bone_or_joint", "bone_segment", "anatomic_region"]:
        value = str(parsed.get(key, "")).strip()
        if value:
            anatomy_terms.append(value)
            phrase_terms.append(value)

    for key in ["procedure", "approach", "fixation_or_implant", "fracture_pattern", "coding_intent"]:
        value = str(parsed.get(key, "")).strip()
        if value:
            procedure_terms.append(value)
            phrase_terms.append(value)

    for kw in parsed.get("positive_keywords", []) or []:
        if isinstance(kw, str) and kw.strip():
            phrase_terms.append(kw.strip())

    raw_keywords = _extract_keywords(" ".join(phrase_terms + [original_query]))

    return {
        "anatomy_terms": list(dict.fromkeys(anatomy_terms)),
        "procedure_terms": list(dict.fromkeys(procedure_terms)),
        "phrase_terms": list(dict.fromkeys(phrase_terms)),
        "keywords": raw_keywords,
    }


def _score_candidate(row: dict[str, Any], parsed: dict[str, Any], terms: dict[str, list[str]]) -> int:
    description = str(row.get("description", "")).lower()
    category = str(row.get("category", "")).lower()
    fellowship = str(row.get("fellowship", "")).lower()

    haystack = " ".join([description, category, fellowship])

    score = 0

    for term in terms["anatomy_terms"]:
        t = term.lower()
        if t and t in haystack:
            score += 25

    for term in terms["procedure_terms"]:
        t = term.lower()
        if t and t in haystack:
            score += 8

    for term in terms["keywords"]:
        t = term.lower()
        if t and t in haystack:
            score += 2

    for neg in parsed.get("negative_keywords", []) or []:
        if isinstance(neg, str) and neg.lower() in haystack:
            score -= 25

    bone_segment = str(parsed.get("bone_segment", "")).lower()
    fracture_pattern = str(parsed.get("fracture_pattern", "")).lower()
    specific = str(parsed.get("specific_bone_or_joint", "")).lower()

    segment_context = " ".join([bone_segment, fracture_pattern, specific])

    # Femur segment logic
    if "femur" in segment_context or "femoral" in segment_context or "hip" in segment_context:
        if (
            "intertrochanteric" in segment_context
            or "peritrochanteric" in segment_context
            or "subtrochanteric" in segment_context
            or "proximal femur" in segment_context
            or "hip" in segment_context
        ):
            if (
                "intertrochanteric" in description
                or "peritrochanteric" in description
                or "subtrochanteric" in description
                or "proximal femur" in description
                or "hip" in description
            ):
                score += 60

            if (
                "shaft" in description
                or "supracondylar" in description
                or "transcondylar" in description
                or "distal femur" in description
                or "condyle" in description
            ):
                score -= 60

        elif "shaft" in segment_context or "diaphysis" in segment_context:
            if "shaft" in description:
                score += 50

            if (
                "intertrochanteric" in description
                or "peritrochanteric" in description
                or "subtrochanteric" in description
                or "supracondylar" in description
                or "distal femur" in description
            ):
                score -= 50

        elif (
            "distal femur" in segment_context
            or "supracondylar" in segment_context
            or "condyle" in segment_context
        ):
            if (
                "distal femur" in description
                or "supracondylar" in description
                or "transcondylar" in description
                or "condyle" in description
            ):
                score += 50

            if (
                "shaft" in description
                or "intertrochanteric" in description
                or "peritrochanteric" in description
                or "subtrochanteric" in description
            ):
                score -= 50

    # Tibia segment logic
    if "tibia" in segment_context or "tibial" in segment_context:
        if "pilon" in segment_context or "plafond" in segment_context or "distal tibia" in segment_context:
            if "pilon" in description or "plafond" in description or "distal tibia" in description:
                score += 50
            if "shaft" in description or "plateau" in description:
                score -= 50

        elif "shaft" in segment_context or "diaphysis" in segment_context:
            if "shaft" in description:
                score += 50
            if "pilon" in description or "plafond" in description or "plateau" in description:
                score -= 50

        elif "plateau" in segment_context or "proximal tibia" in segment_context:
            if "plateau" in description or "proximal tibia" in description:
                score += 50
            if "shaft" in description or "pilon" in description or "plafond" in description:
                score -= 50

    # Humerus segment logic
    if "humerus" in segment_context or "humeral" in segment_context:
        if "proximal humerus" in segment_context:
            if "proximal humerus" in description:
                score += 50
            if "shaft" in description or "distal humerus" in description:
                score -= 50

        elif "shaft" in segment_context:
            if "shaft" in description:
                score += 50
            if "proximal humerus" in description or "distal humerus" in description:
                score -= 50

        elif "distal humerus" in segment_context or "supracondylar" in segment_context:
            if "distal humerus" in description or "supracondylar" in description or "condyle" in description:
                score += 50
            if "shaft" in description or "proximal humerus" in description:
                score -= 50

    return score

def _get_candidates_from_parse(parsed: dict[str, Any], original_query: str) -> list[dict]:
    terms = _build_search_terms(parsed, original_query)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        anatomy_rows = _phrase_like_search(conn, terms["anatomy_terms"], MAX_CANDIDATES)
        phrase_rows = _phrase_like_search(conn, terms["phrase_terms"], MAX_CANDIDATES)
        fts_rows = _fts_search(conn, terms["keywords"], MAX_CANDIDATES)
        like_rows = _generic_like_search(conn, terms["keywords"], MAX_CANDIDATES)
    finally:
        conn.close()

    seen: set[str] = set()
    merged: list[dict] = []

    for row in anatomy_rows + phrase_rows + fts_rows + like_rows:
        code = row.get("code")
        if code and code not in seen:
            seen.add(code)
            row["retrieval_score"] = _score_candidate(row, parsed, terms)
            merged.append(row)

    merged.sort(key=lambda r: r.get("retrieval_score", 0), reverse=True)

    return merged[:MAX_CANDIDATES]


# ── Stage 3: GPT reranking + clarifying questions ─────────────────────────────

_RERANK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "description": "Top 3–5 CPT codes ranked most-to-least appropriate.",
            "items": {
                "type": "object",
                "properties": {
                    "rank": {"type": "integer"},
                    "cpt_code": {"type": "string"},
                    "description": {"type": "string"},
                    "fellowship": {"type": "string"},
                    "category": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": [
                    "rank",
                    "cpt_code",
                    "description",
                    "fellowship",
                    "category",
                    "reason",
                ],
                "additionalProperties": False,
            },
            "minItems": 1,
            "maxItems": 5,
        },
        "clarifying_questions": {
            "type": "array",
            "description": "Questions that would help distinguish between close CPT codes.",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "why_it_matters": {"type": "string"},
                    "codes_affected": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["question", "why_it_matters", "codes_affected"],
                "additionalProperties": False,
            },
            "maxItems": 3,
        },
    },
    "required": ["suggestions", "clarifying_questions"],
    "additionalProperties": False,
}

_RERANK_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "emit_cpt_suggestions",
            "description": "Output ranked CPT code suggestions and clarifying questions.",
            "parameters": _RERANK_SCHEMA,
        },
    }
]

_RERANK_PROMPT = """\
You are a board-certified orthopaedic surgeon and expert medical coder.

You will receive:
1) The original case description.
2) A parsed anatomy/procedure summary.
3) Candidate CPT codes retrieved from a local orthopaedic CPT database.

Your job:
- Select the TOP 3 to 5 CPT codes that best match the case.
- Use the parsed anatomy heavily.
- Do not choose a code from the wrong anatomic region unless no better option exists.
- Do not invent codes that are not in the candidate list.
- Prefer specific codes over generic ones.

CRITICAL RULE:

If multiple high-ranking candidate codes differ by a clinically meaningful modifier

AND that modifier is NOT specified in the case description,

you MUST generate a clarifying question.

These modifiers include:

- intra-articular vs extra-articular, only when relevant to the candidate code descriptions

- number of fragments

- number of levels or segments

- spinal region (cervical, thoracic, lumbar)

- open vs percutaneous vs arthroscopic approach

- superficial vs deep vs bone debridement

- implant type: intramedullary implant vs plate/screw implant, only if not already specified

- presence of fixation, grafting, instrumentation, or hardware removal

Do NOT ask a clarifying question when the case description already specifies the detail that distinguishes the codes.

Examples:

- If the case says IMN, intramedullary nail, cephalomedullary nail, or short nail, do NOT ask implant type when comparing intramedullary implant vs plate/screw implant.

- For intertrochanteric, peritrochanteric, or subtrochanteric femur fractures, do NOT ask intra-articular vs extra-articular; that distinction is not relevant to these CPT codes.

- Only ask about implant type if the case says vague fixation without specifying nail versus plate/screw.

Do NOT assume a default.

Do NOT assume “most common.”

If it is not explicitly stated, treat it as unknown.

Clarifying questions:
- Return 1–3 questions when ambiguity affects CPT selection.
- Each question must directly distinguish between specific candidate codes.
- Include which codes are affected.
- If no ambiguity exists, return an empty array.

Example:
Case: "Distal radius ORIF"
→ MUST ask:
"Intra-articular vs extra-articular fracture?"

Output only via the function tool.
"""

def _rerank_with_gpt(
    case_description: str,
    parsed_case: dict[str, Any],
    candidates: list[dict],
) -> dict[str, Any]:
    client = _get_client()

    payload = {
        "case": case_description,
        "parsed_case": parsed_case,
        "candidates": candidates,
    }

    resp = client.chat.completions.create(
        model=GPT_MODEL,
        temperature=0.0,
        max_tokens=1400,
        messages=[
            {"role": "system", "content": _RERANK_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        tools=_RERANK_TOOL,
        tool_choice={"type": "function", "function": {"name": "emit_cpt_suggestions"}},
        parallel_tool_calls=False,
    )

    msg = resp.choices[0].message
    tool_calls = getattr(msg, "tool_calls", None) or []

    for tc in tool_calls:
        try:
            if tc.function.name == "emit_cpt_suggestions":
                return json.loads(tc.function.arguments or "{}")
        except Exception:
            continue

    return {
        "suggestions": [],
        "clarifying_questions": [],
    }


# ── Public API ────────────────────────────────────────────────────────────────

def suggest_cpt_codes(case_description: str) -> dict[str, Any]:
    if not case_description or not case_description.strip():
        raise ValueError("case_description must be a non-empty string.")

    normalized_case = _normalize_query(case_description)
    parsed_case = _parse_case_with_gpt(normalized_case)
    candidates = _get_candidates_from_parse(parsed_case, normalized_case)

    if not candidates:
        raise ValueError(
            "No candidate CPT codes found in the database for that query. "
            "Try different keywords."
        )

    result = _rerank_with_gpt(normalized_case, parsed_case, candidates)

    suggestions = result.get("suggestions", [])
    clarifying_questions = result.get("clarifying_questions", [])

    if not suggestions:
        raise RuntimeError("GPT returned no suggestions. Check your API key and try again.")

    return {
        "suggestions": sorted(suggestions, key=lambda x: x.get("rank", 99))[:TOP_N],
        "clarifying_questions": clarifying_questions[:3],
        "parsed_case": parsed_case,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def _pretty_print(result: dict[str, Any]) -> None:
    suggestions = result.get("suggestions", [])
    questions = result.get("clarifying_questions", [])

    print(f"\n{'=' * 60}")
    print(f"  TOP {len(suggestions)} SUGGESTED CPT CODE(S)")
    print(f"{'=' * 60}\n")

    for s in suggestions:
        print(f"  #{s['rank']}  CPT {s['cpt_code']} — {s['description']}")
        print(f"      Fellowship : {s['fellowship']}")
        print(f"      Category   : {s['category']}")
        print(f"      Why        : {s['reason']}")
        print()

    if questions:
        print(f"{'=' * 60}")
        print("  CLARIFYING QUESTIONS")
        print(f"{'=' * 60}\n")

        for i, q in enumerate(questions, start=1):
            print(f"  {i}. {q['question']}")
            print(f"     Why: {q['why_it_matters']}")
            print(f"     Codes affected: {', '.join(q.get('codes_affected', []))}")
            print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python cpt_suggester.py "<case description>"')
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"\nCase: {query}")

    try:
        result = suggest_cpt_codes(query)
        _pretty_print(result)
    except (ValueError, RuntimeError) as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)