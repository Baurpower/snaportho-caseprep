import json
import os
import re
import hashlib
from functools import lru_cache
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI

# ── Setup ─────────────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")

client = OpenAI(api_key=OPENAI_API_KEY, project=OPENAI_PROJECT_ID, timeout=20.0)

# Tunables
SNIP_CHAR_BUDGET = 9000
QUESTION_MAX_TOKENS = 1000
FACTS_MAX_TOKENS = 400
RANK_MAX_TOKENS = 400
MAX_FACTS_OUT = 12

# ── Helpers ───────────────────────────────────────────────────
def _normalize_q(s: str) -> str:
    s = s.strip()
    return re.sub(r"\s+", " ", s).lower()

def _looks_like_qa(s: str) -> bool:
    s = (s or "").strip()
    return s.startswith("Q:") and " A:" in s

def _enforce_qa_format(s: str) -> str:
    s = (s or "").strip()
    if _looks_like_qa(s):
        return s
    if "?" in s:
        q, a = s.split("?", 1)
        return f"Q: {q.strip()}? A:{a.strip() or ' (answer not provided)'}"
    return f"Q: {s} A: (answer not provided)"

def _strip_noise(s: str) -> str:
    s = re.sub(r"`{3}.*?`{3}", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"#|[*_>-]{2,}", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _chunk_snippets(snips: List[str], char_budget: int = 6000) -> List[List[str]]:
    cleaned = [_strip_noise(s or "") for s in snips if isinstance(s, str) and s]
    cleaned = [s[:4000] for s in cleaned if len(s) > 10]
    batches, cur, cur_len = [], [], 0
    for s in cleaned:
        L = len(s) + 1
        if cur and cur_len + L > char_budget:
            batches.append(cur)
            cur, cur_len = [], 0
        cur.append(s)
        cur_len += L
    if cur:
        batches.append(cur)
    return batches

# ── Schemas ───────────────────────────────────────────────────
QUESTION_ONLY_SCHEMA = {
    "type": "object",
    "properties": {"pimpQuestions": {"type": "array", "items": {"type": "string"}}},
    "required": ["pimpQuestions"],
    "additionalProperties": False
}
FACTS_ONLY_SCHEMA = {
    "type": "object",
    "properties": {"otherUsefulFacts": {"type": "array", "items": {"type": "string"}}},
    "required": ["otherUsefulFacts"],
    "additionalProperties": False
}
RANK_SCHEMA = {
    "type": "object",
    "properties": {"scores": {"type": "array", "items": {"type": "number"}}},
    "required": ["scores"],
    "additionalProperties": False
}

TOOLS_QUESTIONS = [{"type": "function", "function": {"name": "emit_questions", "parameters": QUESTION_ONLY_SCHEMA}}]
TOOLS_FACTS = [{"type": "function", "function": {"name": "emit_facts", "parameters": FACTS_ONLY_SCHEMA}}]
RANK_TOOL = [{"type": "function", "function": {"name": "emit_scores", "parameters": RANK_SCHEMA}}]

# ── Core extraction calls ─────────────────────────────────────
def _extract_questions_for_batch(user_query: str, batch_snips: List[str]) -> List[str]:
    system_prompt = (
        "You are a senior orthopaedic surgeon. Input: (1) case, (2) vetted notes subset.\n"
        "Return ONLY 'Common Pimp Questions' relevant to THIS case, formatted exactly 'Q: … A: …'."
    )
    payload = {"case": user_query, "snippets": batch_snips}
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        max_tokens=QUESTION_MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
        ],
        tools=TOOLS_QUESTIONS,
        tool_choice={"type": "function", "function": {"name": "emit_questions"}},
        parallel_tool_calls=False
    )
    msg = resp.choices[0].message
    tc = getattr(msg, "tool_calls", None)
    if tc:
        data = json.loads(tc[0].function.arguments)
        items = data.get("pimpQuestions", []) or []
    else:
        content = (msg.content or "").strip()
        items = json.loads(content).get("pimpQuestions", []) if content else []
    return [_enforce_qa_format(s) for s in items if isinstance(s, str)]

def _extract_facts(user_query: str, trimmed_snips: List[str], max_facts: int = MAX_FACTS_OUT) -> List[str]:
    system_prompt = (
        "You are a senior orthopaedic surgeon. Input: (1) case, (2) vetted notes subset.\n"
        f"Return ONLY the top {max_facts} concise, high-yield 'Other Useful Facts' directly relevant to THIS case."
    )
    payload = {"case": user_query, "snippets": trimmed_snips}
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        max_tokens=FACTS_MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
        ],
        tools=TOOLS_FACTS,
        tool_choice={"type": "function", "function": {"name": "emit_facts"}},
        parallel_tool_calls=False
    )
    msg = resp.choices[0].message
    tc = getattr(msg, "tool_calls", None)
    if tc:
        data = json.loads(tc[0].function.arguments)
        items = data.get("otherUsefulFacts", []) or []
    else:
        content = (msg.content or "").strip()
        items = json.loads(content).get("otherUsefulFacts", []) if content else []
    facts = [re.sub(r"\s+", " ", f.strip()) for f in items if isinstance(f, str) and f.strip()]
    return facts[:max_facts]

# ── Ranking (LLM-only) ────────────────────────────────────────
def _rank_batch_with_llm(case: str, items: List[str], label: str, max_tokens: int = RANK_MAX_TOKENS) -> List[float]:
    if not items:
        return []
    system = (
        "You are an orthopaedic attending prepping a junior for the OR.\n"
        "Score each item for THIS case by OR utility (0–100). "
        f"Items are {label}. Consider safety, approach, reduction/fixation, and complications."
    )
    user = {"case": case, "items": items}
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user)}],
        tools=RANK_TOOL,
        tool_choice={"type": "function", "function": {"name": "emit_scores"}},
        parallel_tool_calls=False,
        temperature=0.2,
        max_tokens=max_tokens,
    )
    tc = resp.choices[0].message.tool_calls
    if tc:
        scores = json.loads(tc[0].function.arguments).get("scores", [])
        scores = [float(x) for x in scores][:len(items)]
        if len(scores) < len(items):
            scores += [50.0] * (len(items) - len(scores))
        return scores
    return [50.0] * len(items)

@lru_cache(maxsize=256)
def _rank_scores_cached(case_key: str, label: str, items_json: str) -> List[float]:
    """
    Caches scores using only hashable args.
    case_key: md5 of the case string
    items_json: JSON-encoded list[str] in canonical order
    """
    items = json.loads(items_json)
    return _rank_batch_with_llm(case_key, items, label)

def _rank_items_for_case(case: str, items: List[str], label: str) -> List[str]:
    if not items:
        return []
    case_key = hashlib.md5(case.encode("utf-8")).hexdigest()
    items_json = json.dumps(items, ensure_ascii=False)
    scores = _rank_scores_cached(case_key, label, items_json)
    order = sorted(range(len(items)), key=lambda i: scores[i], reverse=True)
    return [items[i] for i in order]

# ── Public API ────────────────────────────────────────────────
def refine_case_snippets(user_query: str, snippets: List[str]) -> Dict[str, Any]:
    """
    1) Chunk snippets and extract questions per chunk.
    2) Merge & dedupe locally.
    3) Separate facts pass.
    4) Rank both lists (LLM importance only).
    """
    batches = _chunk_snippets(snippets, char_budget=SNIP_CHAR_BUDGET)

    all_questions: List[str] = []
    seen_keys = set()
    for batch in batches:
        qs = _extract_questions_for_batch(user_query, batch)
        for q in qs:
            key = _normalize_q(q)
            if key not in seen_keys:
                seen_keys.add(key)
                all_questions.append(q)

    # Facts: use first two batches for context (capped)
    facts_input = batches[0] if batches else []
    if len(batches) > 1:
        combined = (batches[0] + batches[1])[:6000]
        facts_input = combined
    facts = _extract_facts(user_query, facts_input, max_facts=MAX_FACTS_OUT)

    ranked_questions = _rank_items_for_case(user_query, all_questions, label="questions")
    ranked_facts = _rank_items_for_case(user_query, facts, label="facts")

    return {"pimpQuestions": ranked_questions, "otherUsefulFacts": ranked_facts}