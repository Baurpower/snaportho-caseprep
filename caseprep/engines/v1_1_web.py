"""Website-only CasePrep v1.1 parallel, source-preserving engine."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List

from fastapi.concurrency import run_in_threadpool

from caseprep.pipelines.clinical_sections import (
    anatomy_pipeline,
    approach_pipeline,
    complications_pipeline,
    indications_pipeline,
)
from caseprep.schemas import build_envelope, empty_prompt_response
from caseprep.services import ai_fallback, curated_content_store, procedure_resolver
from caseprep.services.case_identity_v1_1 import build_case_identity, enrich_refined_query
from caseprep.services.caseprep_assembler_v1_1 import (
    assemble_sections,
    collect_sources,
    high_yield_items,
    validate_response,
)
from caseprep.services.rag_retrieval import retrieve_case_qas

PIPELINE_TIMEOUT_SECONDS = 4.0
EMPTY_SECTIONS = {
    "indications": [],
    "anatomy": [],
    "approach": [],
    "operative_steps": [],
    "complications": [],
    "postoperative_care": [],
}


def _retrieval_contract(diagnostics: Dict[str, Any], candidate_count: int) -> Dict[str, Any]:
    return {
        "strategy": "single_embedding_parallel_scoped_queries",
        "candidate_count": candidate_count,
        "embedding_count": diagnostics.get("embedding_count", 0),
        "embedding_ms": diagnostics.get("embedding_ms", 0),
        "pinecone_query_ms": diagnostics.get("pinecone_query_ms", 0),
        "branch_count": diagnostics.get("branch_count", 0),
        "branch_candidate_counts": diagnostics.get("branch_candidate_counts", {}),
        "failed_branches": diagnostics.get("failed_branches", []),
        "raw_candidate_count": diagnostics.get("raw_candidate_count", 0),
        "selected_count": diagnostics.get("selected_count", 0),
    }


async def _bounded_thread_call(function, *args, **kwargs):
    return await asyncio.wait_for(
        run_in_threadpool(function, *args, **kwargs),
        timeout=PIPELINE_TIMEOUT_SECONDS,
    )


def _failed_pipeline(pipeline_id: str, reason: str) -> Dict[str, Any]:
    return {
        "pipeline_id": pipeline_id,
        "status": "failed",
        "items": [],
        "source_ids": [],
        "warnings": [reason],
        "duration_ms": int(PIPELINE_TIMEOUT_SECONDS * 1000),
    }


async def _safe_pipeline(pipeline_id: str, function, payload):
    try:
        return await _bounded_thread_call(function, payload)
    except asyncio.TimeoutError:
        return _failed_pipeline(pipeline_id, f"{pipeline_id} pipeline timed out.")
    except Exception as exc:
        return _failed_pipeline(pipeline_id, f"{pipeline_id} pipeline failed: {exc}")


async def run_caseprep_web_v1_1(
    prompt: str, *, catalog: List[Dict[str, Any]], openai_client: Any
) -> Dict[str, Any]:
    del catalog  # v1.1 uses published modules instead of the legacy anatomy generator.
    started = time.monotonic()
    if not prompt:
        return empty_prompt_response("v1.1", "web_parallel_rag")

    preflight_warnings: List[str] = []
    async def resolve_case():
        try:
            return await _bounded_thread_call(
                procedure_resolver.resolve_procedure_safe, prompt, openai_client
            )
        except Exception as exc:
            preflight_warnings.append(f"Procedure resolution degraded: {exc}")
            return {
                "procedure_slug": None,
                "canonical_display_name": "",
                "match_method": "none",
                "confidence": 0.0,
            }

    async def refine_case():
        try:
            return await _bounded_thread_call(ai_fallback.refine_prompt, prompt)
        except Exception as exc:
            preflight_warnings.append(f"Query refinement degraded: {exc}")
            return {"search_text": prompt, "raw_prompt": prompt}

    preflight_started = time.monotonic()
    resolved, refined_raw = await asyncio.gather(resolve_case(), refine_case())
    preflight_ms = int((time.monotonic() - preflight_started) * 1000)
    refined = enrich_refined_query(refined_raw, resolved, prompt)
    identity = build_case_identity(prompt, resolved, refined)

    if identity["requires_clarification"]:
        body = {
            "pimpQuestions": [],
            "otherUsefulFacts": [],
            "anatomy": None,
            "case": identity,
            "high_yield_questions": [],
            "highYieldQuestions": [],
            "sections": dict(EMPTY_SECTIONS),
            "case_specific_pearls": [],
            "sources": [],
            "pipeline_status": {},
            "timing": {
                "preflight_ms": preflight_ms,
                "total_ms": int((time.monotonic() - started) * 1000),
            },
            "retrieval": _retrieval_contract({}, 0),
        }
        return build_envelope(
            caseprep_version="v1.1",
            engine="web_parallel_rag",
            content_status="clarification",
            body=body,
            ai_used=["resolver_classifier"] if resolved.get("match_method") == "gpt" else False,
            rag_used=False,
            warnings=[
                identity.get("clarification_reason") or "Choose a surgical approach.",
                *preflight_warnings,
            ],
            backward_compat=True,
        )

    payload = (
        curated_content_store.get_certified_payload(identity["canonical_slug"])
        if identity["canonical_slug"]
        else None
    )
    retrieval_diagnostics: Dict[str, Any] = {}

    async def retrieve_high_yield():
        return await _bounded_thread_call(
            retrieve_case_qas, refined, diagnostics=retrieval_diagnostics
        )

    tasks = [
        retrieve_high_yield(),
        _safe_pipeline("indications", indications_pipeline, payload),
        _safe_pipeline("anatomy", anatomy_pipeline, payload),
        _safe_pipeline("approach", approach_pipeline, payload),
        _safe_pipeline("complications", complications_pipeline, payload),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    retrieval_result = results[0]
    retrieval_failed = isinstance(retrieval_result, BaseException)
    retrieved = [] if retrieval_failed else retrieval_result
    supporting = [
        result
        if isinstance(result, dict)
        else _failed_pipeline(pipeline_id, f"{pipeline_id} pipeline failed: {result}")
        for pipeline_id, result in zip(
            ("indications", "anatomy", "approach", "complications"), results[1:]
        )
    ]

    high_yield = high_yield_items(retrieved)
    sections = assemble_sections(supporting)
    pipeline_status = {
        "pocket_pimped": {
            "status": "failed" if retrieval_failed else ("complete" if high_yield else "unavailable"),
            "item_count": len(high_yield),
            "duration_ms": retrieval_diagnostics.get("pinecone_query_ms", 0)
            + retrieval_diagnostics.get("embedding_ms", 0),
        },
        **{
            result["pipeline_id"]: {
                "status": result["status"],
                "item_count": len(result["items"]),
                "duration_ms": result["duration_ms"],
            }
            for result in supporting
        },
    }
    response = {
        "case": identity,
        "high_yield_questions": high_yield,
        "sections": sections,
        "case_specific_pearls": [
            item["supporting_detail"]
            for item in high_yield
            if item.get("supporting_detail")
        ][:3],
        "sources": collect_sources(high_yield, supporting),
        "pipeline_status": pipeline_status,
        "timing": {
            "preflight_ms": preflight_ms,
            "total_ms": int((time.monotonic() - started) * 1000),
        },
    }
    validation_warnings = validate_response(response)
    pipeline_warnings = [
        warning for result in supporting for warning in result.get("warnings") or []
    ]
    if retrieval_failed:
        pipeline_warnings.insert(0, f"Pocket Pimped retrieval failed: {retrieval_result}")
    warnings = list(
        dict.fromkeys([*preflight_warnings, *pipeline_warnings, *validation_warnings])
    )

    anatomy_compat = {
        "highYieldAnatomy": {
            "structures": [
                {
                    "name": item["answer"],
                    "type": item["category"],
                    "why_high_yield": item["supporting_detail"],
                }
                for item in sections["anatomy"]
            ]
        }
    } if sections["anatomy"] else None

    body = {
        **response,
        "pimpQuestions": [f"Q: {item['question']} A: {item['answer']}" for item in high_yield],
        "otherUsefulFacts": response["case_specific_pearls"],
        "anatomy": anatomy_compat,
        "highYieldQuestions": retrieved,
        "retrieval": _retrieval_contract(retrieval_diagnostics, len(high_yield)),
    }
    return build_envelope(
        caseprep_version="v1.1",
        engine="web_parallel_rag",
        procedure_slug=identity["canonical_slug"],
        match_method=identity["resolver_method"],
        content_status="preview",
        body=body,
        ai_used=["query_refiner"]
        + (["resolver_classifier"] if resolved.get("match_method") == "gpt" else []),
        rag_used=bool(high_yield),
        warnings=warnings,
        backward_compat=True,
    )
