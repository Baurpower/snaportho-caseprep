import json
import os
import re
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI

# ── Setup ─────────────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.getenv("OPENAI_API_PROJECT_ID") or os.getenv("OPENAI_PROJECT_ID")

client = OpenAI(api_key=OPENAI_API_KEY, project=OPENAI_PROJECT_ID, timeout=60.0)

# Tunables
SNIP_CHAR_BUDGET = 8000
PER_SNIP_LIMIT = 800
QUESTION_MAX_TOKENS = 2000   # can tune down more later if needed
FACTS_MAX_TOKENS = 1000      # can tune down more later if needed
MAX_SNIPPETS_FOR_REFORMAT = 45
MAX_FACTS_OUT = 20

# ── Lightweight helpers ───────────────────────────────────────
def _normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _strip_noise(s: str) -> str:
    # remove code blocks, html, heavy markdown bullets/rules
    s = re.sub(r"`{3}.*?`{3}", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"^[-*•]+\s*", "", s, flags=re.M)
    s = re.sub(r"[_>#]{2,}", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _ensure_question_mark(q: str) -> str:
    q = _normalize_space(q)
    if q and not q.endswith("?"):
        if re.search(
            r"^(what|how|why|when|where|which|list|name|define|describe|explain|"
            r"indications|contraindications|steps|complications)\b",
            q,
            re.I,
        ):
            q += "?"
    return q


def _format_qa(q: str, a: str) -> str:
    q = _ensure_question_mark(q)
    a = _normalize_space(a)
    return f"Q: {q} A: {a if a else '(answer not provided)'}"


def _prepare_snippets(snips: List[Any], char_budget: int) -> List[str]:
    """
    Clean, truncate, and enforce overall character budget.
    Accepts either:
      - plain strings, or
      - dicts with at least a 'text' field and optional 'source'.

    Returns a list of snippet strings ready to send to the model.
    """
    cleaned: List[str] = []
    total = 0

    for raw in snips:
        # Handle dicts from vector search: {"text": ..., "source": ...}
        if isinstance(raw, dict):
            base = (raw.get("text") or "").strip()
            src = (raw.get("source") or "").strip()
            if src:
                s = f"{base} [Source: {src}]"
            else:
                s = base
        elif isinstance(raw, str):
            s = raw
        else:
            # Unknown type → skip
            continue

        s = _strip_noise(s)
        if len(s) < 10:
            continue

        # Per-snippet limit
        s = s[:PER_SNIP_LIMIT]
        L = len(s) + 1

        # Enforce global character budget
        if cleaned and total + L > char_budget:
            break

        cleaned.append(s)
        total += L

    return cleaned


# ── Schema for relevance mask only ────────────────────────────
SNIPPET_FILTER_SCHEMA = {
    "type": "object",
    "properties": {
        "keepMask": {
            "description": (
                "Boolean mask indicating which snippets are clearly relevant "
                "to THIS specific case. Length MUST equal the number of input snippets."
            ),
            "type": "array",
            "items": {"type": "boolean"},
        },
    },
    "required": ["keepMask"],
    "additionalProperties": False,
}

FILTER_SNIPPETS_TOOL = [
    {"type": "function", "function": {"name": "filter_snippets", "parameters": SNIPPET_FILTER_SCHEMA}}
]


def _filter_irrelevant_snippets(case: str, snippets: List[str]) -> List[str]:
    """
    Ask GPT for a keepMask and drop snippets that are clearly unrelated.
    No scoring / ranking. We rely on Pinecone for order.
    """
    if not snippets:
        return []

    system_prompt = (
        "You are an orthopaedic attending preparing a trainee for a specific case.\n"
        "You will receive:\n"
        "  • A case description (e.g., 'ankle ORIF for bimalleolar fracture in a diabetic', "
        "    'total knee arthroplasty for OA', 'above-knee amputation for mangled extremity').\n"
        "  • A list of teaching snippets from orthopaedic resources.\n\n"
        "Your job:\n"
        "  - For each snippet, decide if it is clearly relevant to THIS case.\n"
        "  - Output a boolean keepMask array of the same length as the snippet list.\n\n"
        "CLINICALLY / TEST-TAKING RELEVANT (keepMask = true):\n"
        "  • Same region and same general topic (e.g., ankle fractures, pilon fractures,\n"
        "    syndesmosis, ankle external fixation) for an 'ankle ORIF' case.\n"
        "  • Closely related anatomy, biomechanics, classifications, approaches, complications, or postop care.\n"
        "  • Classic exam/pimp questions that would reasonably come up during THIS case.\n\n"
        "MARK AS NOT RELEVANT (keepMask = false) ONLY when:\n"
        "  • The content is clearly about a different region (femoral shaft vs knee; forefoot vs ankle; spine vs hip).\n"
        "  • Or a completely different topic (e.g., calcaneus surgery for an adult ankle ORIF).\n"
        "  • Or a completely different specialty (e.g., shoulder replacement for an glenoid labrum repair in an athlete).\n"
        "IF YOU ARE UNSURE:\n"
        "  • Prefer keepMask = true instead of false.\n\n"
        "Output requirements:\n"
        "  • keepMask MUST have the same length as the input snippet list.\n"
        "  • Do NOT rewrite snippets. Only decide keepMask.\n"
        "  • Use the function tool ONLY; no free-text."
    )

    payload = {"case": case, "snippets": snippets}

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.0,
        max_tokens=200,  # small, it's just booleans
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        tools=FILTER_SNIPPETS_TOOL,
        tool_choice={"type": "function", "function": {"name": "filter_snippets"}},
        parallel_tool_calls=False,
    )

    msg = resp.choices[0].message
    if getattr(msg, "tool_calls", None):
        try:
            data = json.loads(msg.tool_calls[0].function.arguments)
        except Exception:
            data = {}
        keep_mask: List[bool] = data.get("keepMask", []) or []
    else:
        # Worst-case: model ignored tools. Keep everything.
        keep_mask = [True] * len(snippets)

    # Safety: if lengths don't match, keep everything.
    if len(keep_mask) != len(snippets):
        keep_mask = [True] * len(snippets)

    kept = [s for s, keep in zip(snippets, keep_mask) if keep]

    # Fallback: if somehow everything was dropped, keep all
    if not kept:
        return snippets

    return kept


# ── Final reformatter schema ──────────────────────────────────
QUESTIONS_OBJ_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "answer": {"type": "string"},
    },
    "required": ["question", "answer"],
    "additionalProperties": False,
}

CASEPREP_SCHEMA = {
    "type": "object",
    "properties": {
        "pimpQuestions": {
            "type": "array",
            "items": QUESTIONS_OBJ_SCHEMA,
        },
        "otherUsefulFacts": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["pimpQuestions", "otherUsefulFacts"],
    "additionalProperties": False,
}

CASEPREP_TOOL = [
    {"type": "function", "function": {"name": "emit_caseprep", "parameters": CASEPREP_SCHEMA}}
]

def _looks_like_question(q: str) -> bool:
    q = (q or "").strip().lower()
    if not q:
        return False
    if q.endswith("?"):
        return True
    return bool(re.match(r"^(what|how|why|when|where|which|who|list|name|define|describe|explain|indications|contraindications|steps|complications)\b", q))


# ── Single-stage reformatter (after masking) ──────────────────
def _extract_tool_args(msg, tool_name: str) -> Dict[str, Any]:
    """Find tool call by name and parse JSON args safely."""
    tool_calls = getattr(msg, "tool_calls", None) or []
    for tc in tool_calls:
        try:
            fn = tc.function
            if fn and fn.name == tool_name:
                return json.loads(fn.arguments or "{}")
        except Exception:
            continue
    return {}


def _reformat_snippets(user_query: str, snippets: List[str]) -> Dict[str, Any]:
    """
    Take pre-cleaned, relevance-filtered snippets and produce:
      - pimpQuestions: list of 'Q: ... A: ...' strings (ONLY when Q/A is obvious)
      - otherUsefulFacts: list of short facts, close to original
    """
    if not snippets:
        return {"pimpQuestions": [], "otherUsefulFacts": []}

    snippets = snippets[:MAX_SNIPPETS_FOR_REFORMAT]

    system_prompt = (
        "You are an orthopaedic attending preparing a trainee for ONE specific case.\n"
        "You will be given:\n"
        "  1) A case prompt\n"
        "  2) A list of teaching snippets (already filtered for relevance)\n\n"
        "Your job is to output TWO lists:\n"
        "  - pimpQuestions: high-yield intraop/pimp-style Q&A pairs drawn DIRECTLY from snippets.\n"
        "    Only create a question if the snippet clearly supports an answer.\n"
        "    Keep questions short and surgical.\n"
        "  - otherUsefulFacts: short standalone facts that help with the case.\n\n"
        "Rules:\n"
        "  - Do NOT invent facts.\n"
        "  - Prefer being faithful to the snippet wording.\n"
        "  - Avoid duplicates.\n"
        "  - If a snippet is already formatted like 'Q: ... A: ...', preserve it.\n\n"
        "Output requirements:\n"
        "  - Use the function tool ONLY.\n"
        "  - pimpQuestions must be an array of objects: {question: string, answer: string}\n"
        "  - otherUsefulFacts must be an array of short strings.\n"
    )

    payload = {"case": user_query, "snippets": snippets}

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.1,       # tighter for extractive behavior
        max_tokens=900,        # plenty for ~20 Qs + facts
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        tools=CASEPREP_TOOL,
        tool_choice={"type": "function", "function": {"name": "emit_caseprep"}},
        parallel_tool_calls=False,
    )

    msg = resp.choices[0].message
    data = _extract_tool_args(msg, "emit_caseprep")

    raw_qs = data.get("pimpQuestions", []) or []
    raw_facts = data.get("otherUsefulFacts", []) or []

    pimp_questions: List[str] = []
    other_facts: List[str] = []

    seen_q = set()
    for obj in raw_qs:
        if not isinstance(obj, dict):
            continue
        q = (obj.get("question") or "").strip()
        a = (obj.get("answer") or "").strip()
        if not q:
            continue

        if not _looks_like_question(q):
            s = _normalize_space(q)
            if s:
                other_facts.append(s)
            continue

        formatted = _format_qa(q, a)
        key = _normalize_space(formatted).lower()
        if key in seen_q:
            continue
        seen_q.add(key)
        pimp_questions.append(formatted)

    seen_f = set()
    for f in raw_facts:
        if not isinstance(f, str):
            continue
        s = _normalize_space(f)
        if not s:
            continue
        k = s.lower()
        if k in seen_f:
            continue
        seen_f.add(k)
        other_facts.append(s)
        if len(other_facts) >= MAX_FACTS_OUT:
            break

    return {"pimpQuestions": pimp_questions, "otherUsefulFacts": other_facts}

# ── Public API ────────────────────────────────────────────────
def refine_case_snippets(user_query: str, snippets: List[Any]) -> Dict[str, Any]:
    """
    Pipeline:
      1) Clean + truncate raw snippets (strings or metadata dicts).
      2) Use GPT to:
           - mask out clearly irrelevant snippets for this specific case.
      3) Use a second GPT call to:
           - lightly reformat remaining snippets into 'pimpQuestions' and 'otherUsefulFacts'
             WITHOUT aggressively summarizing away content.
    """
    prepped = _prepare_snippets(snippets, SNIP_CHAR_BUDGET)
    if not prepped:
        return {"pimpQuestions": [], "otherUsefulFacts": []}

    kept = _filter_irrelevant_snippets(user_query, prepped)

    result = _reformat_snippets(user_query, kept)
    return result
