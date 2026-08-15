"""Website-only CasePrep v1.1 packet SSE engine.

Parallel 10-pipeline fan-out streaming sections as they complete. The
non-stream ``run_caseprep_web_v1_1`` engine is untouched; this module reuses
its bounded-threadpool helpers. Nothing here is reachable from the legacy
``/case-prep`` route consumed by iOS.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

from caseprep import schemas_v1_1_packet as protocol
from caseprep.config import CasePrepConfig
from caseprep.engines.v1_1_web import (
    _bounded_thread_call,
    _failed_pipeline,
    _safe_pipeline,
)
from caseprep.pipelines import packet_sections
from caseprep.services import ai_fallback, curated_content_store, procedure_resolver
from caseprep.services.case_identity_v1_1 import build_case_identity, enrich_refined_query
from caseprep.services.caseprep_assembler_v1_1 import collect_sources, high_yield_items
from caseprep.services.rag_retrieval import retrieve_case_qas

# Enrichment decorates a certified payload, but for an uncovered procedure it
# *is* the anatomy / operative flow / pitfalls / postop content. A full gap-fill
# pass (7 sections + pedagogy for 15 questions) measures ~25s, so the tighter
# budget silently emptied seven sections of every uncertified packet. The
# header and pimp questions still stream at ~3s, so the extra budget only
# delays below-the-fold content. Both values are overridable.
ENRICHMENT_TIMEOUT_SECONDS = float(os.getenv("CASEPREP_V1_1_ENRICHMENT_TIMEOUT", "8"))
ENRICHMENT_GAP_FILL_TIMEOUT_SECONDS = float(
    os.getenv("CASEPREP_V1_1_ENRICHMENT_GAP_FILL_TIMEOUT", "30")
)

_PROCEDURE_TYPE_KEYWORDS = (
    ("arthroplasty", ("arthroplasty", "replacement", "tha", "tka")),
    ("arthroscopy", ("arthroscop", "acl", "portal")),
    ("fracture_fixation", ("orif", "fracture", "nail", "pinning", "fixation")),
    ("release_or_decompression", ("release", "decompression", "fasciotomy")),
    ("reconstruction", ("reconstruction", "repair", "transfer", "fusion", "osteotomy")),
)

_DIFFICULTY_BY_TYPE = {
    "arthroplasty": "intermediate",
    "arthroscopy": "intermediate",
    "fracture_fixation": "intermediate",
    "release_or_decompression": "foundational",
    "reconstruction": "advanced",
}

_PGY_BY_TYPE = {
    "release_or_decompression": "MS4-PGY2",
    "arthroscopy": "PGY2-PGY4",
    "fracture_fixation": "PGY1-PGY3",
    "arthroplasty": "PGY2-PGY4",
    "reconstruction": "PGY3-PGY5",
}


def _procedure_type(slug: str, display_name: str) -> str:
    blob = f"{slug} {display_name}".lower()
    for label, keywords in _PROCEDURE_TYPE_KEYWORDS:
        if any(keyword in blob for keyword in keywords):
            return label
    return "general"


def build_packet_header(
    identity: Dict[str, Any], payload: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Deterministic above-the-fold header; enrichment may refine estimates."""
    slug = identity.get("canonical_slug") or ""
    display_name = identity.get("canonical_name") or identity.get("requested_case") or ""
    procedure_type = _procedure_type(slug, display_name)
    certified = bool(payload) and str(payload.get("case_prep_status")).lower() == "certified"

    focus: List[str] = []
    if payload:
        for structure in (payload.get("structures_at_risk") or [])[:3]:
            if isinstance(structure, dict):
                name = str(structure.get("structure") or structure.get("name") or "").strip()
                if name:
                    focus.append(name)
        if not focus:
            focus = [str(z).split(":")[0].strip() for z in (payload.get("danger_zones") or [])[:3]]

    specialty = identity.get("specialty")
    region = identity.get("region")
    try:
        from procedure_registry import SLUG_TO_DEF

        definition = SLUG_TO_DEF.get(slug)
        if definition is not None:
            specialty = specialty or definition.specialty
            region = region or definition.body_region
    except Exception:
        pass

    return {
        "display_name": display_name,
        "certified": certified,
        "procedure_type": procedure_type,
        "difficulty": _DIFFICULTY_BY_TYPE.get(procedure_type, "intermediate"),
        "pgy_level": _PGY_BY_TYPE.get(procedure_type, "PGY1-PGY3"),
        "est_prep_minutes": 25 if certified else 20,
        "common_attending_focus": focus,
        "specialty": specialty,
        "region": region,
    }


def _section_meta(result: Dict[str, Any]) -> Dict[str, Any]:
    items = result.get("items") or []
    sources = {item.get("source") for item in items if item.get("source")}
    source = sources.pop() if len(sources) == 1 else ("mixed" if sources else "curated")
    confidences = [item.get("confidence") for item in items if item.get("confidence")]
    return {
        "source": source,
        "confidence": round(min(confidences), 3) if confidences else None,
        "generated_field_paths": [
            f"items[{index}]" for index, item in enumerate(items) if item.get("generated")
        ],
    }


def _merge_pimp_questions(
    curated: List[Dict[str, Any]], retrieved: List[Dict[str, Any]], limit: int = 15,
    *, prompt: str = "", prioritize_prompt: bool = False,
) -> List[Dict[str, Any]]:
    """Curated attending questions first, then RAG items deduped against them."""
    from caseprep.services.rag_retrieval import _near_duplicate

    merged: List[Dict[str, Any]] = []
    for entry in curated:
        merged.append({**entry, "rank": len(merged) + 1})
    for entry in retrieved:
        if any(_near_duplicate(entry["question"], kept["question"]) for kept in merged):
            continue
        merged.append({**entry, "source": "rag", "rank": len(merged) + 1})
        if len(merged) >= limit:
            break
    if prioritize_prompt:
        from caseprep.services.prompt_understanding import lexical_terms

        prompt_terms = lexical_terms([prompt])
        merged.sort(
            key=lambda item: len(
                prompt_terms & lexical_terms([item.get("question", ""), item.get("answer", "")])
            ),
            reverse=True,
        )
        for index, entry in enumerate(merged):
            entry["rank"] = index + 1
    return merged[:limit]


async def stream_caseprep_packet(
    prompt: str, *, openai_client: Any, config: Optional[CasePrepConfig] = None,
    policy_version: str = "v1.1",
) -> AsyncIterator[bytes]:
    started = time.monotonic()
    cfg = config or CasePrepConfig.from_env()
    packet_id = uuid.uuid4().hex
    yield protocol.meta_event(packet_id)
    yield protocol.progress_event("connecting", "Starting case preparation", 2, 8)

    prompt = (prompt or "").strip()
    if not prompt:
        yield protocol.error_event("Please enter a case description.")
        return

    warnings: List[str] = []
    pipeline_status: Dict[str, Any] = {}

    # ── Preflight: cached resolution + query refinement in parallel ──────────
    async def resolve_case() -> Dict[str, Any]:
        try:
            return await _bounded_thread_call(
                procedure_resolver.resolve_procedure_safe, prompt, openai_client
            )
        except Exception as exc:
            warnings.append(f"Procedure resolution degraded: {exc}")
            return {
                "procedure_slug": None,
                "canonical_display_name": "",
                "match_method": "none",
                "confidence": 0.0,
            }

    async def refine_case() -> Dict[str, Any]:
        try:
            return await _bounded_thread_call(ai_fallback.refine_prompt, prompt)
        except Exception as exc:
            warnings.append(f"Query refinement degraded: {exc}")
            return {"search_text": prompt, "raw_prompt": prompt}

    # Resolution alone gates the header (alias hits are cached and fast). The
    # LLM query refiner runs concurrently with the pipeline fan-out — only the
    # Pocket Pimped retrieval waits on it, so above-the-fold never blocks on a
    # GPT call. Registry-backed enrichment supplies specialty/region for the
    # identity deterministically.
    preflight_started = time.monotonic()
    yield protocol.progress_event("resolving", "Identifying the procedure", 8, 24)
    resolve_task = asyncio.create_task(resolve_case())
    while not resolve_task.done():
        done, _ = await asyncio.wait({resolve_task}, timeout=2.0)
        if done:
            break
        yield protocol.progress_event(
            "resolving",
            "Still identifying the best procedure match",
            8,
            24,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            heartbeat=True,
        )
    resolved = await resolve_task
    refine_task = asyncio.create_task(refine_case())
    refined = enrich_refined_query({"search_text": prompt}, resolved, prompt)
    identity = build_case_identity(prompt, resolved, refined)
    preflight_ms = int((time.monotonic() - preflight_started) * 1000)

    if identity["requires_clarification"] and policy_version != "v1.2":
        refine_task.cancel()
        yield protocol.clarification_event(
            identity,
            identity.get("clarification_reason") or "Choose a surgical approach.",
            [
                {
                    # Resolver suggestions use "name" (e.g. "Open Carpal Tunnel
                    # Release"); registry fuzzy suggestions use "display_name".
                    "label": match.get("name") or match.get("display_name") or match.get("slug"),
                    "prompt": match.get("name") or match.get("display_name"),
                }
                for match in (resolved.get("suggested_matches") or [])
                if isinstance(match, dict)
            ],
        )
        yield protocol.done_event(
            {},
            {"preflight_ms": preflight_ms, "total_ms": int((time.monotonic() - started) * 1000)},
            warnings,
        )
        return

    payload = (
        curated_content_store.get_certified_payload(identity["canonical_slug"])
        if identity["canonical_slug"]
        else None
    )
    yield protocol.header_event(identity, build_packet_header(identity, payload))
    yield protocol.progress_event(
        "assembling", "Loading the case essentials", 24, 38,
        elapsed_ms=int((time.monotonic() - started) * 1000),
    )

    # ── Above-the-fold sections: synchronous curated transforms ──────────────
    for section_id, builder in (
        ("summary", packet_sections.summary_block),
        ("key_takeaways", packet_sections.key_takeaways_block),
        ("top_things_to_know", packet_sections.top_things_to_know_block),
    ):
        result = builder(payload)
        pipeline_status[section_id] = {
            "status": result["status"],
            "item_count": len(result["items"]),
            "duration_ms": result["duration_ms"],
        }
        if result["items"]:
            yield protocol.section_event(
                section_id,
                status="complete",
                items=result["items"],
                duration_ms=result["duration_ms"],
                **_section_meta(result),
            )

    # ── Parallel fan-out ─────────────────────────────────────────────────────
    retrieval_diagnostics: Dict[str, Any] = {}

    async def run_retrieval() -> Dict[str, Any]:
        refined_full: Dict[str, Any] = refined
        try:
            # Merge the (slow, parallel) LLM refinement into the registry-backed
            # scope before querying; degrade to the registry scope on failure.
            try:
                refined_full = enrich_refined_query(await refine_task, resolved, prompt)
            except Exception:
                refined_full = refined
            candidates = await _bounded_thread_call(
                retrieve_case_qas,
                refined_full,
                diagnostics=retrieval_diagnostics,
                policy_version=policy_version,
            )
            return {
                "pipeline_id": "pocket_pimped",
                "status": "complete" if candidates else "unavailable",
                "items": high_yield_items(candidates),
                "source_ids": [],
                "warnings": [],
                "duration_ms": retrieval_diagnostics.get("embedding_ms", 0)
                + retrieval_diagnostics.get("pinecone_query_ms", 0),
            }
        except Exception as exc:
            # Online retrieval is optional. The bundled, source-backed bank is
            # the deterministic outage path and must still return useful Q/A.
            try:
                from caseprep.services.rag_retrieval import bundled_semantic_qas, normalize_query

                candidates = bundled_semantic_qas(normalize_query(refined_full), limit=15)
                warnings.append(f"Online Pocket Pimped retrieval degraded: {type(exc).__name__}.")
                return {
                    "pipeline_id": "pocket_pimped",
                    "status": "complete" if candidates else "unavailable",
                    "items": high_yield_items(candidates),
                    "source_ids": [],
                    "warnings": [],
                    "duration_ms": 0,
                }
            except Exception as fallback_exc:
                return _failed_pipeline(
                    "pocket_pimped",
                    f"Pocket Pimped retrieval failed: {type(fallback_exc).__name__}",
                )

    async def run_enrichment(pimp_questions: List[Dict[str, Any]]) -> Optional[Any]:
        # v1.2 never delays a certified packet for optional prose, and strong
        # grounded question coverage does not need synthetic padding.
        if policy_version == "v1.2" and (payload is not None or len(pimp_questions) >= 8):
            return None
        if not (cfg.enable_v1_1_enrichment and openai_client and identity["canonical_slug"]):
            return None
        from caseprep.services.enrichment_v1_1 import enrich_packet_sections

        budget = (
            ENRICHMENT_TIMEOUT_SECONDS if payload else ENRICHMENT_GAP_FILL_TIMEOUT_SECONDS
        )
        try:
            return await asyncio.wait_for(
                asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: enrich_packet_sections(
                        identity["canonical_slug"],
                        payload,
                        identity=identity,
                        pimp_questions=pimp_questions,
                        openai_client=openai_client,
                        model=cfg.v1_1_model,
                    ),
                ),
                timeout=budget,
            )
        except asyncio.TimeoutError:
            # asyncio.TimeoutError stringifies to "", which produced the
            # useless warning "Enrichment degraded: ".
            warnings.append(f"Enrichment timed out after {budget:.0f}s.")
            return None
        except Exception as exc:
            warnings.append(f"Enrichment degraded: {type(exc).__name__}: {exc}")
            return None

    deterministic_pipelines = {
        "anatomy": packet_sections.important_anatomy_pipeline,
        "operative_flow": packet_sections.operative_flow_pipeline,
        "teaching_topics": packet_sections.teaching_topics_pipeline,
        "pitfalls": packet_sections.pitfalls_pipeline,
        "decision_points": packet_sections.decision_points_pipeline,
        "postop": packet_sections.postop_pipeline,
        "evidence": packet_sections.evidence_pipeline,
        "attending_questions": packet_sections.attending_questions_pipeline,
    }

    retrieval_task = asyncio.create_task(run_retrieval())
    yield protocol.progress_event(
        "retrieving", "Finding high-yield questions", 38, 65,
        elapsed_ms=int((time.monotonic() - started) * 1000),
    )
    section_tasks = {
        asyncio.create_task(_safe_pipeline(section_id, fn, payload)): section_id
        for section_id, fn in deterministic_pipelines.items()
    }

    # Enrichment-backed sections wait for the enrichment result; everything
    # else streams as soon as its pipeline completes. When no curated payload
    # exists, most sections are enrichment gap-fill targets too.
    enrichment_sections = {"decision_points", "teaching_topics", "evidence"}
    if payload is None and cfg.enable_v1_1_enrichment:
        enrichment_sections |= {"anatomy", "operative_flow", "pitfalls", "postop"}
    held_for_enrichment: Dict[str, Dict[str, Any]] = {}
    curated_questions: Optional[Dict[str, Any]] = None

    for task in asyncio.as_completed(list(section_tasks)):
        result = await task
        section_id = result.get("pipeline_id") or "unknown"
        pipeline_status[section_id] = {
            "status": result["status"],
            "item_count": len(result.get("items") or []),
            "duration_ms": result.get("duration_ms", 0),
        }
        for warning in result.get("warnings") or []:
            warnings.append(warning)
        if section_id == "attending_questions":
            curated_questions = result  # merged with retrieval below
            continue
        if section_id in enrichment_sections:
            held_for_enrichment[section_id] = result
            continue
        if result["status"] == "failed":
            yield protocol.section_error_event(section_id, (result.get("warnings") or ["failed"])[0])
        elif result.get("items"):
            yield protocol.section_event(
                section_id,
                status="complete",
                items=result["items"],
                duration_ms=result.get("duration_ms", 0),
                **_section_meta(result),
            )

    # ── Pimp questions: curated first, then Pocket Pimped RAG ────────────────
    while not retrieval_task.done():
        done, _ = await asyncio.wait({retrieval_task}, timeout=2.0)
        if done:
            break
        yield protocol.progress_event(
            "retrieving",
            "Searching grounded questions and teaching points",
            38,
            65,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            heartbeat=True,
        )
    retrieval_result = await retrieval_task
    pipeline_status["pocket_pimped"] = {
        "status": retrieval_result["status"],
        "item_count": len(retrieval_result.get("items") or []),
        "duration_ms": retrieval_result.get("duration_ms", 0),
        "cache_hit": bool(retrieval_diagnostics.get("cache_hit")),
    }
    if retrieval_result["status"] == "failed":
        for warning in retrieval_result.get("warnings") or []:
            warnings.append(warning)

    curated_items = (curated_questions or {}).get("items") or []
    pimp_items = _merge_pimp_questions(
        curated_items,
        retrieval_result.get("items") or [],
        prompt=prompt,
        prioritize_prompt=bool(identity.get("explicit_question")),
    )
    pimp_source = (
        "mixed"
        if curated_items and retrieval_result.get("items")
        else ("certified" if curated_items else "rag")
    )

    def _pimp_event(items: List[Dict[str, Any]], status: str, generated_paths: List[str]) -> bytes:
        confidences = [entry.get("confidence") for entry in items if entry.get("confidence")]
        return protocol.section_event(
            "pimp_questions",
            status=status,
            items=items,
            source=pimp_source,
            confidence=round(min(confidences), 3) if confidences else None,
            generated_field_paths=generated_paths,
            duration_ms=retrieval_result.get("duration_ms", 0),
        )

    # Stream the merged questions immediately; pedagogy fields (pearl / why /
    # difficulty) arrive with a follow-up "complete" emission once enrichment
    # resolves. The client replaces the slot content in place.
    enrichment_pending = bool(
        cfg.enable_v1_1_enrichment and openai_client and identity["canonical_slug"]
        and not (policy_version == "v1.2" and (payload is not None or len(pimp_items) >= 8))
    )
    if pimp_items and enrichment_pending:
        yield _pimp_event(pimp_items, "partial", [])
    elif pimp_items:
        yield _pimp_event(pimp_items, "complete", [])
    elif retrieval_result["status"] == "failed":
        yield protocol.section_error_event("pimp_questions", "Pimp question retrieval failed.")

    enrichment = None
    if enrichment_pending:
        yield protocol.progress_event(
            "enhancing", "Enhancing the remaining case details", 65, 92,
            elapsed_ms=int((time.monotonic() - started) * 1000),
        )
        enrichment_task = asyncio.create_task(run_enrichment(pimp_items))
        while not enrichment_task.done():
            done, _ = await asyncio.wait({enrichment_task}, timeout=2.0)
            if done:
                break
            yield protocol.progress_event(
                "enhancing",
                "Still building anatomy and operative details",
                65,
                92,
                elapsed_ms=int((time.monotonic() - started) * 1000),
                heartbeat=True,
            )
        enrichment = await enrichment_task
    if enrichment_pending:
        generated_paths: List[str] = []
        if enrichment:
            pimp_items, generated_paths = enrichment.apply_to_pimp_questions(pimp_items)
        # Emit even when curated+RAG were empty — generated questions may be
        # the only pimp content for uncovered procedures (clearly marked).
        if pimp_items:
            yield _pimp_event(pimp_items, "complete", generated_paths)

    # ── Enrichment-backed sections (D/H/J + gap-fill) ────────────────────────
    ordered_enrichment_sections = (
        "anatomy",
        "operative_flow",
        "teaching_topics",
        "decision_points",
        "pitfalls",
        "postop",
        "evidence",
    )
    for section_id in ordered_enrichment_sections:
        if section_id not in enrichment_sections:
            continue
        base = held_for_enrichment.get(section_id) or _failed_pipeline(section_id, "missing")
        items = list(base.get("items") or [])
        generated_paths = []
        if enrichment:
            items, generated_paths = enrichment.apply_to_section(section_id, items)
        if items:
            meta = _section_meta({"items": items})
            meta["generated_field_paths"] = generated_paths or meta["generated_field_paths"]
            yield protocol.section_event(
                section_id,
                status="complete",
                items=items,
                duration_ms=base.get("duration_ms", 0),
                **meta,
            )
            status_row = pipeline_status.setdefault(section_id, {"duration_ms": 0})
            status_row["item_count"] = len(items)
            status_row["status"] = "complete"
        elif base.get("status") == "failed":
            yield protocol.section_error_event(section_id, (base.get("warnings") or ["failed"])[0])

    # ── Sources + done ───────────────────────────────────────────────────────
    all_results = list(held_for_enrichment.values())
    if curated_questions:
        all_results.append(curated_questions)
    sources = collect_sources(retrieval_result.get("items") or [], all_results)
    if sources:
        yield protocol.section_event(
            "sources", status="complete", payload={"sources": sources}, source="mixed"
        )

    yield protocol.progress_event(
        "finalizing", "Finishing your case prep packet", 92, 99,
        elapsed_ms=int((time.monotonic() - started) * 1000),
    )
    yield protocol.done_event(
        pipeline_status,
        {
            "preflight_ms": preflight_ms,
            "retrieval_cache_hit": bool(retrieval_diagnostics.get("cache_hit")),
            "total_ms": int((time.monotonic() - started) * 1000),
        },
        list(dict.fromkeys(warnings)),
    )
