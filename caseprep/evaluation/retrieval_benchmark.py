from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Sequence


def normalize(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def candidate_text(candidate: Dict[str, Any]) -> str:
    return normalize(
        " ".join(
            str(candidate.get(key) or "")
            for key in ("question", "answer", "additional_info", "supporting_detail")
        )
    )


def contains_term(text: str, term: str) -> bool:
    return normalize(term) in text


def duplicate_rate(candidates: Sequence[Dict[str, Any]]) -> float:
    questions = [normalize(candidate.get("question")) for candidate in candidates]
    questions = [question for question in questions if question]
    return 0.0 if not questions else 1.0 - (len(set(questions)) / len(questions))


def evaluate_case(case: Dict[str, Any], candidates: Sequence[Dict[str, Any]], top_k: int = 10) -> Dict[str, Any]:
    selected = list(candidates[:top_k])
    texts = [candidate_text(candidate) for candidate in selected]
    combined = " ".join(texts)
    required = case.get("must_include_terms") or []
    acceptable = [*required, *(case.get("acceptable_terms") or [])]
    prohibited = case.get("prohibited_terms") or []
    required_hits = [term for term in required if contains_term(combined, term)]
    prohibited_hits = [term for term in prohibited if contains_term(combined, term)]
    relevant = sum(
        any(contains_term(text, term) for term in acceptable)
        for text in texts
    )
    return {
        "case_id": case["case_id"],
        "result_count": len(selected),
        "must_include_recall": len(required_hits) / len(required) if required else 1.0,
        "top_k_relevance": relevant / len(selected) if selected else 0.0,
        "contamination": len(prohibited_hits) / len(prohibited) if prohibited else 0.0,
        "duplicate_rate": duplicate_rate(selected),
        "missing_terms": [term for term in required if term not in required_hits],
        "prohibited_hits": prohibited_hits,
    }


def summarize(results: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(results)
    if not rows:
        return {"case_count": 0}

    def average(key: str) -> float:
        return round(sum(float(row[key]) for row in rows) / len(rows), 4)

    return {
        "case_count": len(rows),
        "must_include_recall": average("must_include_recall"),
        "top_k_relevance": average("top_k_relevance"),
        "contamination": average("contamination"),
        "duplicate_rate": average("duplicate_rate"),
        "empty_result_rate": round(sum(row["result_count"] == 0 for row in rows) / len(rows), 4),
    }
