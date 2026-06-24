"""
GPT-backed CasePrep helpers (v1 primary; v2 only when explicitly enabled).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def refine_prompt(user_prompt: str) -> Any:
    from query_refiner import refine_query

    return refine_query(user_prompt)


def format_pimp_from_snippets(user_query: str, snippets: List[Any]) -> Dict[str, Any]:
    from gpt_refiner import refine_case_snippets

    return refine_case_snippets(user_query, snippets)


def run_legacy_anatomy(
    *,
    case_prompt: str,
    catalog: List[Dict[str, Any]],
    client: Any,
) -> Dict[str, Any]:
    from anatomy_gpt import run_pipeline_fast

    return run_pipeline_fast(case_prompt=case_prompt, catalog=catalog, client=client)


def pimp_from_certified_payload(certified: Dict[str, Any]) -> Dict[str, Any]:
    """Extract attending pimp Qs from curated payload — no GPT."""
    questions = (
        certified.get("attending_pimp_questions")
        or certified.get("common_pimp_questions")
        or []
    )
    facts = certified.get("must_know_anatomy") or certified.get("otherUsefulFacts") or []
    if isinstance(facts, list):
        other = [str(f) for f in facts[:10] if f]
    else:
        other = []
    return {
        "pimpQuestions": list(questions),
        "otherUsefulFacts": other,
    }