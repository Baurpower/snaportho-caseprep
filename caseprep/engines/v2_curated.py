"""
CasePrep v2 — curated-first hybrid engine (opt-in).

1. Resolve procedure
2. Return certified curated payload when available (no GPT for core content)
3. Controlled fallback with explicit metadata when not certified
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi.concurrency import run_in_threadpool

from caseprep.config import CasePrepConfig
from caseprep.schemas import build_envelope, empty_prompt_response
from caseprep.services import ai_fallback, curated_content_store, procedure_resolver, rag_context

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
    if match_method == "gpt":
        ai_used.append("resolver_classifier")

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
        fallback_reason="no_certified_payload",
        user_visible_warning=fallback_msg,
        backward_compat=True,
    )


async def run_caseprep_v2(
    prompt: str,
    *,
    catalog: List[Dict[str, Any]],
    openai_client: Any,
    config: Optional[CasePrepConfig] = None,
) -> Dict[str, Any]:
    cfg = config or CasePrepConfig.from_env()

    if not prompt:
        return empty_prompt_response("v2", "curated_hybrid")

    if not cfg.enable_v2:
        return _disabled_response()

    resolved = await run_in_threadpool(
        procedure_resolver.resolve_procedure_safe, prompt, openai_client
    )
    slug = resolved.get("procedure_slug")

    if slug:
        certified = curated_content_store.get_certified_payload(slug)
        if certified:
            return _certified_response(
                prompt=prompt,
                slug=slug,
                certified=certified,
                resolved=resolved,
            )

    return await _fallback_response(
        prompt=prompt,
        resolved=resolved,
        config=cfg,
        catalog=catalog,
        openai_client=openai_client,
    )