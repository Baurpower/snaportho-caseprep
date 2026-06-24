"""
CasePrep v1 — legacy production pipeline.

Flow: refine_query → Pinecone RAG → GPT pimp reformat → legacy anatomy_gpt catalog.
Does not import v2-only modules (procedure_registry, hybrid_anatomy_builder, etc.).
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi.concurrency import run_in_threadpool

from caseprep.schemas import build_envelope, empty_prompt_response
from caseprep.services import ai_fallback, rag_context

V1_AI_STEPS = [
    "query_refiner",
    "snippet_filter",
    "snippet_reformat",
    "anatomy_pipeline",
]


async def run_caseprep_v1(
    prompt: str,
    *,
    catalog: List[Dict[str, Any]],
    openai_client: Any,
) -> Dict[str, Any]:
    if not prompt:
        return empty_prompt_response("v1", "legacy_rag_gpt")

    refined_prompt = await run_in_threadpool(ai_fallback.refine_prompt, prompt)
    print(f"🧠 [v1] Refined Prompt: {refined_prompt}")

    if not rag_context.is_rag_available():
        body = {
            "pimpQuestions": [],
            "otherUsefulFacts": ["❌ RAG not configured (missing Pinecone/OpenAI env)."],
            "anatomy": None,
        }
        return build_envelope(
            caseprep_version="v1",
            engine="legacy_rag_gpt",
            content_status="legacy",
            body=body,
            ai_used=False,
            rag_used=False,
            warnings=["RAG dependencies not available"],
            backward_compat=True,
        )

    snippets = await run_in_threadpool(rag_context.fetch_snippets, refined_prompt)
    if not snippets:
        body = {
            "pimpQuestions": [],
            "otherUsefulFacts": ["❌ No relevant content found."],
            "anatomy": None,
        }
        return build_envelope(
            caseprep_version="v1",
            engine="legacy_rag_gpt",
            content_status="legacy",
            body=body,
            ai_used=["query_refiner"],
            rag_used=True,
            warnings=["No Pinecone snippets returned"],
            backward_compat=True,
        )

    async def run_pimp():
        result = await run_in_threadpool(ai_fallback.format_pimp_from_snippets, prompt, snippets)
        print("✅ [v1] CasePrep pimp pipeline finished")
        return result

    async def run_anatomy():
        result = await run_in_threadpool(
            ai_fallback.run_legacy_anatomy,
            case_prompt=prompt,
            catalog=catalog,
            client=openai_client,
        )
        print("🦴 [v1] Legacy anatomy pipeline finished")
        return result

    pimp_result, anatomy_result = await asyncio.gather(run_pimp(), run_anatomy())

    body = {
        **pimp_result,
        "anatomy": anatomy_result,
    }

    print("🚀 [v1] CasePrep completed — legacy_rag_gpt")
    return build_envelope(
        caseprep_version="v1",
        engine="legacy_rag_gpt",
        content_status="legacy",
        body=body,
        ai_used=V1_AI_STEPS,
        rag_used=True,
        backward_compat=True,
    )


def is_v1_available() -> bool:
    """v1 needs approach catalog paths and RAG for full behavior; engine itself always loadable."""
    return True