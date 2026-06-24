"""
Pinecone RAG retrieval for CasePrep (v1 primary, v2 optional fallback).
"""

from __future__ import annotations

from typing import Any, List

from caseprep.config import rag_dependencies_available


def is_rag_available() -> bool:
    if not rag_dependencies_available():
        return False
    try:
        import vector_search  # noqa: F401

        return True
    except Exception:
        return False


def fetch_snippets(refined_prompt: Any) -> List[Any]:
    """
    Retrieve case snippets from Pinecone. Caller should run refine_query first.
    Raises if RAG is not configured — callers must guard with is_rag_available().
    """
    from vector_search import get_case_snippets

    return get_case_snippets(refined_prompt)