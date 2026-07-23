"""
CasePrep v2 — curated-first hybrid engine (opt-in).

1. Resolve procedure
2. Return certified curated payload when available (no GPT for core content)
3. Controlled fallback with explicit metadata when not certified
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Optional

from fastapi.concurrency import run_in_threadpool

from caseprep.config import CasePrepConfig
from caseprep.schemas import build_envelope, empty_prompt_response
from caseprep.services import ai_fallback, curated_content_store, procedure_resolver, rag_context
from caseprep.services.demand_events import record_demand_event


def _payload_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _citations_from_snippets(snippets: List[Any]) -> List[Dict[str, Any]]:
    citations: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for index, snippet in enumerate(snippets):
        row = snippet if isinstance(snippet, dict) else {}
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        source_id = str(
            row.get("source_id")
            or metadata.get("source_id")
            or row.get("id")
            or metadata.get("id")
            or f"retrieved-{index + 1}"
        )
        if source_id in seen:
            continue
        seen.add(source_id)
        citations.append(
            {
                "source_id": source_id,
                "title": row.get("title") or metadata.get("title"),
                "url": row.get("url") or metadata.get("url") or metadata.get("source_url"),
                "section": row.get("section") or metadata.get("section"),
                "chunk_id": row.get("chunk_id") or metadata.get("chunk_id") or row.get("id"),
            }
        )
    return citations


def _resolver_contract(resolved: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "raw_query": resolved.get("raw_query"),
        "canonical_slug": resolved.get("procedure_slug"),
        "canonical_name": resolved.get("canonical_display_name") or None,
        "entity_kind": resolved.get("entity_kind"),
        "requested_approach": resolved.get("requested_approach"),
        "resolver_method": resolved.get("match_method") or "unresolved",
        "confidence": resolved.get("confidence"),
        "alternatives": resolved.get("suggested_matches") or [],
        "requires_clarification": bool(resolved.get("requires_clarification")),
        "clarification_reason": resolved.get("clarification_reason"),
    }

_V2_IMPORT_ERROR: Optional[str] = None


def _check_v2_engine_loadable() -> Optional[str]:
    global _V2_IMPORT_ERROR
    if _V2_IMPORT_ERROR is not None:
        return _V2_IMPORT_ERROR
    try:
        import caseprep.engines.v2_curated  # noqa: F401 — self check
        return None
    except Exception as exc:
        _V2_IMPORT_ERROR = str(exc)
        return _V2_IMPORT_ERROR


def is_v2_available(config: Optional[CasePrepConfig] = None) -> bool:
    cfg = config or CasePrepConfig.from_env()
    if not cfg.enable_v2:
        return False
    if _check_v2_engine_loadable():
        return False
    return procedure_resolver.is_resolver_available()


def v2_unavailable_reason(config: Optional[CasePrepConfig] = None) -> str:
    cfg = config or CasePrepConfig.from_env()
    if not cfg.enable_v2:
        return "ENABLE_CASEPREP_V2 is false"
    err = _check_v2_engine_loadable()
    if err:
        return f"v2 engine import error: {err}"
    if not procedure_resolver.is_resolver_available():
        return "procedure_registry not available"
    return ""


def _disabled_response() -> Dict[str, Any]:
    reason = v2_unavailable_reason()
    body = {
        "pimpQuestions": [],
        "otherUsefulFacts": [],
        "anatomy": None,
        "brobot_case_prep": None,
    }
    return build_envelope(
        caseprep_version="v2",
        engine="curated_hybrid",
        procedure_slug=None,
        match_method="none",
        content_status="unsupported",
        body=body,
        ai_used=False,
        rag_used=False,
        warnings=[reason or "CasePrep v2 is disabled"],
        fallback_reason=reason or "v2_disabled",
        user_visible_warning="CasePrep v2 is not enabled on this server.",
        backward_compat=True,
    )


def _certified_response(
    *,
    prompt: str,
    slug: str,
    certified: Dict[str, Any],
    resolved: Dict[str, Any],
) -> Dict[str, Any]:
    pimp_block = ai_fallback.pimp_from_certified_payload(certified)
    ai_used: Any = False
    match_method = resolved.get("match_method") or "none"
    if match_method == "gpt":
        ai_used = ["resolver_classifier"]

    payload_hash = _payload_hash(certified)
    body = {
        **pimp_block,
        "anatomy": {
            "mode": "certified_case_prep_payload",
            "procedure_id": slug,
            "procedure_name": certified.get("procedure_name"),
            "case_prep_status": "certified",
            "payload": certified,
            "resolver": {
                "match_method": match_method,
                "match_score": resolved.get("match_score"),
            },
        },
        "brobot_case_prep": certified,
        "case_prep": {
            "requested_case": prompt,
            **_resolver_contract(resolved),
            "source_type": "curated",
            "content_status": "certified",
            "review_status": "certified",
            "runtime_enabled": True,
            "revision_id": certified.get("revision_id"),
            "payload_hash": payload_hash,
            "fallback_used": False,
            "fallback_reason": None,
            "citations": certified.get("citations") or certified.get("sources") or [],
            "warnings": [],
            "payload": certified,
        },
    }

    print(f"🚀 [v2] Certified payload: {slug} (method={match_method}, ai_used={ai_used})")
    return build_envelope(
        caseprep_version="v2",
        engine="curated_hybrid",
        procedure_slug=slug,
        match_method=match_method,
        content_status="certified",
        body=body,
        ai_used=ai_used,
        rag_used=False,
        backward_compat=True,
    )


async def _fallback_response(
    *,
    prompt: str,
    resolved: Dict[str, Any],
    config: CasePrepConfig,
    catalog: List[Dict[str, Any]],
    openai_client: Any,
) -> Dict[str, Any]:
    slug = resolved.get("procedure_slug")
    match_method = resolved.get("match_method") or "none"
    suggested = resolved.get("suggested_matches") or []
    fallback_msg = curated_content_store.get_fallback_message()

    ai_used: List[str] = []
    rag_used = False
    warnings: List[str] = [fallback_msg]
    citations: List[Dict[str, Any]] = []
    if match_method == "gpt":
        ai_used.append("resolver_classifier")

    if resolved.get("requires_clarification"):
        warning = resolved.get("clarification_reason") or "Please choose a procedure approach."
        body = {
            "pimpQuestions": [],
            "otherUsefulFacts": [],
            "anatomy": None,
            "brobot_case_prep": None,
            "suggestedMatches": suggested,
            "case_prep": {
                "requested_case": prompt,
                **_resolver_contract(resolved),
                "source_type": "unavailable",
                "content_status": None,
                "review_status": None,
                "runtime_enabled": False,
                "revision_id": None,
                "payload_hash": None,
                "fallback_used": False,
                "fallback_reason": "approach_clarification_required",
                "citations": [],
                "warnings": [warning],
                "payload": None,
            },
        }
        return build_envelope(
            caseprep_version="v2",
            engine="curated_hybrid",
            procedure_slug=slug,
            match_method=match_method,
            content_status="unsupported",
            body=body,
            ai_used=ai_used or False,
            rag_used=False,
            warnings=[warning],
            fallback_reason="approach_clarification_required",
            user_visible_warning=warning,
            backward_compat=True,
        )

    if not slug:
        warnings.append(
            "Could not confidently identify a supported procedure from the case description."
        )
        body = {
            "pimpQuestions": [],
            "otherUsefulFacts": [],
            "anatomy": None,
            "brobot_case_prep": None,
            "suggestedMatches": suggested,
            "case_prep": {
                "requested_case": prompt,
                **_resolver_contract(resolved),
                "source_type": "unavailable",
                "content_status": None,
                "review_status": None,
                "runtime_enabled": False,
                "revision_id": None,
                "payload_hash": None,
                "fallback_used": False,
                "fallback_reason": "procedure_unresolved",
                "citations": [],
                "warnings": warnings,
                "payload": None,
            },
        }
        return build_envelope(
            caseprep_version="v2",
            engine="curated_hybrid",
            procedure_slug=None,
            match_method=match_method,
            content_status="unsupported",
            body=body,
            ai_used=ai_used or False,
            rag_used=False,
            warnings=warnings,
            fallback_reason="procedure_unresolved",
            user_visible_warning=warnings[-1],
            backward_compat=True,
        )

    # Resolved but not certified — controlled fallback behind flags
    body: Dict[str, Any] = {
        "pimpQuestions": [],
        "otherUsefulFacts": [],
        "anatomy": None,
        "brobot_case_prep": None,
        "procedure_id": slug,
        "suggestedMatches": suggested,
    }

    if config.enable_v2_rag_fallback and rag_context.is_rag_available():
        try:
            refined = await run_in_threadpool(ai_fallback.refine_prompt, prompt)
            ai_used.append("query_refiner")
            snippets = await run_in_threadpool(rag_context.fetch_snippets, refined)
            rag_used = bool(snippets)
            citations = _citations_from_snippets(snippets)
            if snippets and config.enable_v2_ai_fallback:
                pimp = await run_in_threadpool(
                    ai_fallback.format_pimp_from_snippets, prompt, snippets
                )
                body.update(pimp)
                ai_used.extend(["snippet_filter", "snippet_reformat"])
            elif snippets:
                warnings.append(
                    "RAG snippets retrieved but AI reformat disabled (ENABLE_CASEPREP_V2_AI_FALLBACK=false)."
                )
        except Exception as exc:
            warnings.append(f"RAG fallback failed: {exc}")
    elif config.enable_v2_rag_fallback:
        warnings.append("RAG fallback requested but Pinecone dependencies unavailable.")

    if config.enable_v2_ai_fallback and catalog:
        try:
            anatomy = await run_in_threadpool(
                ai_fallback.run_legacy_anatomy,
                case_prompt=prompt,
                catalog=catalog,
                client=openai_client,
            )
            body["anatomy"] = anatomy
            ai_used.append("anatomy_pipeline")
        except Exception as exc:
            warnings.append(f"Anatomy AI fallback failed: {exc}")
    elif not config.enable_v2_ai_fallback:
        warnings.append("AI anatomy fallback disabled (ENABLE_CASEPREP_V2_AI_FALLBACK=false).")

    source_type = "rag_fallback" if rag_used and citations else "unavailable"
    fallback_reason = (
        "no_certified_payload"
        if source_type == "rag_fallback"
        else "no_certified_payload_and_no_cited_fallback"
    )
    fallback_payload = dict(body) if source_type == "rag_fallback" else None
    body["case_prep"] = {
        "requested_case": prompt,
        **_resolver_contract(resolved),
        "source_type": source_type,
        "content_status": "fallback" if source_type == "rag_fallback" else None,
        "review_status": None,
        "runtime_enabled": False,
        "revision_id": None,
        "payload_hash": None,
        "fallback_used": source_type == "rag_fallback",
        "fallback_reason": fallback_reason,
        "citations": citations,
        "warnings": warnings,
        "payload": fallback_payload,
    }

    print(f"🚀 [v2] Fallback for {slug} (rag={rag_used}, ai={ai_used})")
    return build_envelope(
        caseprep_version="v2",
        engine="curated_hybrid",
        procedure_slug=slug,
        match_method=match_method,
        content_status="fallback",
        body=body,
        ai_used=ai_used or False,
        rag_used=rag_used,
        warnings=warnings,
        fallback_reason=fallback_reason,
        user_visible_warning=fallback_msg,
        backward_compat=True,
    )


async def run_caseprep_v2(
    prompt: str,
    *,
    catalog: List[Dict[str, Any]],
    openai_client: Any,
    config: Optional[CasePrepConfig] = None,
    event_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    started = time.monotonic()
    cfg = config or CasePrepConfig.from_env()

    if not prompt:
        return empty_prompt_response("v2", "curated_hybrid")

    if not cfg.enable_v2:
        return _disabled_response()

    resolved = await run_in_threadpool(
        procedure_resolver.resolve_procedure_safe, prompt, openai_client
    )
    slug = resolved.get("procedure_slug")

    response: Dict[str, Any]
    if slug and not resolved.get("requires_clarification"):
        certified = curated_content_store.get_certified_payload(slug)
        if certified:
            response = _certified_response(
                prompt=prompt,
                slug=slug,
                certified=certified,
                resolved=resolved,
            )
        else:
            response = await _fallback_response(
                prompt=prompt,
                resolved=resolved,
                config=cfg,
                catalog=catalog,
                openai_client=openai_client,
            )
    else:
        response = await _fallback_response(
            prompt=prompt,
            resolved=resolved,
            config=cfg,
            catalog=catalog,
            openai_client=openai_client,
        )

    normalized = response.get("case_prep") or {}
    citations = normalized.get("citations") or []
    record_demand_event(
        raw_request=prompt,
        resolved=resolved,
        curated_hit=normalized.get("source_type") == "curated",
        revision_id=normalized.get("revision_id"),
        payload_hash=normalized.get("payload_hash"),
        fallback_used=bool(normalized.get("fallback_used")),
        fallback_reason=normalized.get("fallback_reason"),
        retrieved_source_ids=[
            str(c.get("source_id")) for c in citations if isinstance(c, dict) and c.get("source_id")
        ],
        response_latency_ms=int((time.monotonic() - started) * 1000),
        context=event_context,
    )
    return response
