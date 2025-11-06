import json
import os
import re
import hashlib
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv
from openai import OpenAI

# ── Setup ─────────────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")

client = OpenAI(api_key=OPENAI_API_KEY, project=OPENAI_PROJECT_ID, timeout=60.0)

# Tunables
SNIP_CHAR_BUDGET = 9000
QUESTION_MAX_TOKENS = 1200
FACTS_MAX_TOKENS = 500
RANK_MAX_TOKENS = 400
MAX_FACTS_OUT = 12

# ── Helpers ───────────────────────────────────────────────────
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

def _ensure_question_mark(q: str) -> str:
    q = _normalize_space(q)
    # add '?' if it looks like a question without punctuation
    if q and not re.search(r"[?]$", q):
        if re.search(r"^(what|how|why|when|where|which|list|name|define|describe|explain|indications|contraindications|steps|complications)\b", q, re.I):
            q += "?"
    return q

def _format_qa(q: str, a: str) -> str:
    q = _ensure_question_mark(q)
    a = _normalize_space(a)
    return f"Q: {q} A: {a if a else '(answer not provided)'}"

# ── Schemas ───────────────────────────────────────────────────
QUESTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "pimpQuestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"}
                },
                "required": ["question", "answer"],
                "additionalProperties": False
            }
        }
    },
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

TOOLS_QUESTIONS = [{"type": "function", "function": {"name": "emit_questions", "parameters": QUESTIONS_SCHEMA}}]
TOOLS_FACTS = [{"type": "function", "function": {"name": "emit_facts", "parameters": FACTS_ONLY_SCHEMA}}]
RANK_TOOL = [{"type": "function", "function": {"name": "emit_scores", "parameters": RANK_SCHEMA}}]

# ── Core extraction calls ─────────────────────────────────────
def _extract_questions_for_batch(user_query: str, batch_snips: List[str]) -> List[str]:
    """
    Ask for structured Q/A pairs via tool call, then normalize to 'Q: … A: …' strings.
    """
    system_prompt = (
        "You are a senior orthopaedic surgeon.\n"
        "You will receive: (1) a surgical case, (2) a subset of vetted notes.\n"
        "Return ONLY 'Common Pimp Questions' that are directly relevant to THIS case.\n"
        "Rules:\n"
        " - Use the tool function ONLY (no prose, no markdown).\n"
        " - Provide 6–14 high-yield Q/A pairs.\n"
        " - Questions must be precise (e.g., 'What structures are at risk during the volar Henry approach?').\n"
        " - Answers must be concise, factual, and derived from the notes or standard teaching.\n"
        " - No duplicate or near-duplicate items.\n"
        " - No references, no citations, no lists inside answers.\n"
        "Few-shot schema example (not content):\n"
        "  {\"pimpQuestions\": [{\"question\": \"Indications for distal radius ORIF?\", \"answer\": \"...\"}]}\n"
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
    items: List[str] = []
    if getattr(msg, "tool_calls", None):
        data = json.loads(msg.tool_calls[0].function.arguments)
        raw = data.get("pimpQuestions", []) or []
        for obj in raw:
            if isinstance(obj, dict):
                q = obj.get("question", "").strip()
                a = obj.get("answer", "").strip()
                if q:
                    items.append(_format_qa(q, a))
    else:
        # Fallback if tool call fails (rare)
        content = (msg.content or "").strip()
        if content:
            try:
                data = json.loads(content)
                raw = data.get("pimpQuestions", []) or []
                for obj in raw:
                    if isinstance(obj, dict):
                        items.append(_format_qa(obj.get("question",""), obj.get("answer","")))
            except Exception:
                pass
    # De-dupe
    seen, out = set(), []
    for s in items:
        key = _normalize_space(s).lower()
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out

def _extract_facts(user_query: str, trimmed_snips: List[str], max_facts: int = MAX_FACTS_OUT) -> List[str]:
    system_prompt = (
        "You are a senior orthopaedic surgeon. Input: (1) case, (2) vetted notes subset.\n"
        f"Return ONLY the top {max_facts} concise, high-yield 'Other Useful Facts' directly relevant to THIS case.\n"
        "Rules: tool function ONLY; 1 sentence per fact; no markdown, no lists, no references; no duplicates."
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
    items: List[str] = []
    if getattr(msg, "tool_calls", None):
        data = json.loads(msg.tool_calls[0].function.arguments)
        raw = data.get("otherUsefulFacts", []) or []
        items = [ _normalize_space(f) for f in raw if isinstance(f, str) and f.strip() ]
    else:
        content = (msg.content or "").strip()
        if content:
            try:
                data = json.loads(content)
                raw = data.get("otherUsefulFacts", []) or []
                items = [ _normalize_space(f) for f in raw if isinstance(f, str) and f.strip() ]
            except Exception:
                items = []
    # De-dupe + cap
    seen, out = set(), []
    for s in items:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out[:max_facts]

# ── Ranking (LLM-only) with correct case text ────────────────
_RANK_CACHE: Dict[Tuple[str, str, str], List[float]] = {}

def _rank_batch_with_llm(case_text: str, items: List[str], label: str, max_tokens: int = RANK_MAX_TOKENS) -> List[float]:
    if not items:
        return []
    system = (
        "You are an orthopaedic attending prepping a junior for the OR.\n"
        "Score each item for THIS case by OR utility (0–100). "
        f"Items are {label}. Consider safety, approach, reduction/fixation, complications."
    )
    user = {"case": case_text, "items": items}
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user)}],
        tools=RANK_TOOL,
        tool_choice={"type": "function", "function": {"name": "emit_scores"}},
        parallel_tool_calls=False,
        temperature=0.2,
        max_tokens=max_tokens,
    )
    tc = getattr(resp.choices[0].message, "tool_calls", None)
    if tc:
        scores = json.loads(tc[0].function.arguments).get("scores", [])
        scores = [float(x) for x in scores][:len(items)]
        if len(scores) < len(items):
            scores += [50.0] * (len(items) - len(scores))
        return scores
    return [50.0] * len(items)

def _rank_items_for_case(case_text: str, items: List[str], label: str) -> List[str]:
    if not items:
        return []
    case_hash = hashlib.md5(case_text.encode("utf-8")).hexdigest()
    items_hash = hashlib.sha1(json.dumps(items, ensure_ascii=False).encode("utf-8")).hexdigest()
    key = (case_hash, label, items_hash)
    if key not in _RANK_CACHE:
        _RANK_CACHE[key] = _rank_batch_with_llm(case_text, items, label)
    scores = _RANK_CACHE[key]
    order = sorted(range(len(items)), key=lambda i: scores[i], reverse=True)
    return [items[i] for i in order]

# ── Public API ────────────────────────────────────────────────
def refine_case_snippets(user_query: str, snippets: List[str]) -> Dict[str, Any]:
    """
    1) Chunk snippets and extract questions per chunk.
    2) Merge & dedupe locally.
    3) Separate facts pass over first two batches.
    4) Rank both lists (LLM importance only).
    """
    batches = _chunk_snippets(snippets, char_budget=SNIP_CHAR_BUDGET)

    all_questions: List[str] = []
    seen_keys = set()
    for batch in batches:
        qs = _extract_questions_for_batch(user_query, batch)
        for q in qs:
            key = _normalize_space(q).lower()
            if key not in seen_keys:
                seen_keys.add(key)
                all_questions.append(q)

    # Facts: combine first two batches if available
    facts_input = []
    if batches:
        facts_input = (batches[0] + (batches[1] if len(batches) > 1 else []))[:6000]
    facts = _extract_facts(user_query, facts_input, max_facts=MAX_FACTS_OUT)

    ranked_questions = _rank_items_for_case(user_query, all_questions, label="questions")
    ranked_facts = _rank_items_for_case(user_query, facts, label="facts")

    return {"pimpQuestions": ranked_questions, "otherUsefulFacts": ranked_facts}
