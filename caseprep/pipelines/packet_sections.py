"""Deterministic CasePrep v1.1 packet pipelines (spec pipelines D-J + operative flow).

All content here is transformed from the certified/curated payload — no LLM
calls and no fabrication. Sections the curated payload cannot support return
``status: "unavailable"`` and are filled (marked ``generated: true``) by the
enrichment layer, never by these pipelines.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from caseprep.pipelines.shared import (
    clean,
    item,
    norm_key,
    parse_qa,
    pipeline_result,
    source_ids,
)

def _payload_source(payload: Dict[str, Any]) -> str:
    status = clean(payload.get("case_prep_status")).lower()
    return "certified" if status == "certified" else "curated_uncertified"


def _mark(items: List[Dict[str, Any]], payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    source = _payload_source(payload)
    for entry in items:
        entry["source"] = source
    return items


def important_anatomy_pipeline(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Pipeline E — must-know anatomy, structures at risk, danger zones, landmarks.

    Blood supply / innervation buckets are enrichment gap-fill targets.
    """
    started = time.monotonic()
    if not payload:
        return pipeline_result("anatomy", started, [], status="unavailable")
    refs = source_ids(payload)
    items: List[Dict[str, Any]] = []
    for fact in (payload.get("must_know_anatomy") or [])[:6]:
        result = item(
            prefix="mustknow",
            question="Must-know anatomy",
            answer=fact,
            category="must_know_anatomy",
            sources=refs,
            confidence=0.95,
            dedup_key=f"anatomy:{norm_key(fact)}",
        )
        if result:
            items.append(result)
    for structure in (payload.get("structures_at_risk") or [])[:6]:
        if not isinstance(structure, dict):
            continue
        name = structure.get("structure") or structure.get("name")
        result = item(
            prefix="risk",
            question=clean(name) or "Structure at risk",
            answer=structure.get("why_at_risk"),
            supporting_detail=structure.get("how_to_avoid_injury"),
            category="structure_at_risk",
            sources=structure.get("source_refs") or refs,
            confidence=0.95,
            dedup_key=f"structure:{norm_key(name)}",
        )
        if result:
            items.append(result)
    for zone in (payload.get("danger_zones") or [])[:5]:
        result = item(
            prefix="danger",
            question="Danger zone",
            answer=zone,
            category="danger_zone",
            sources=refs,
            confidence=0.95,
            dedup_key=f"danger:{norm_key(zone)}",
        )
        if result:
            items.append(result)
    for landmark in (payload.get("key_landmarks") or [])[:5]:
        result = item(
            prefix="landmark",
            question="Surface landmark",
            answer=landmark,
            category="surface_landmark",
            sources=refs,
            confidence=0.9,
        )
        if result:
            items.append(result)
    # pipeline_id doubles as the stream section_id — must stay "anatomy".
    return pipeline_result(
        "anatomy", started, _mark(items[:16], payload), sources=refs
    )


def attending_questions_pipeline(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Pipeline F — curated attending questions; ranked ahead of RAG by the engine."""
    started = time.monotonic()
    if not payload:
        return pipeline_result("attending_questions", started, [], status="unavailable")
    refs = source_ids(payload)
    items: List[Dict[str, Any]] = []
    for raw in payload.get("attending_pimp_questions") or []:
        question, answer = parse_qa(raw)
        result = item(
            prefix="attending",
            question=question,
            answer=answer,
            category="attending_question",
            sources=refs,
            confidence=0.95,
        )
        if result:
            items.append(result)
    return pipeline_result(
        "attending_questions", started, _mark(items[:12], payload), sources=refs
    )


def decision_points_pipeline(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Pipeline H — operate / who-not / convert / stop / alternatives.

    The curated seed was a keyword-filtered slice of ``attending_pimp_questions``
    — every item was a verbatim copy of a card already shown in ``pimp_questions``.
    That slice is dropped; the section now carries only enrichment-generated
    decision points (marked generated).
    """
    started = time.monotonic()
    return pipeline_result("decision_points", started, [], status="unavailable")


def postop_pipeline(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Pipeline I — postoperative protocol.

    Formerly a keyword slice of ``attending_pimp_questions`` (duplicated
    ``pimp_questions``); dropped in favor of enrichment-generated postop content.
    """
    started = time.monotonic()
    return pipeline_result("postop", started, [], status="unavailable")


def evidence_pipeline(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Pipeline J — reference stubs from curated source URLs; enrichment adds
    landmark evidence summaries."""
    started = time.monotonic()
    if not payload:
        return pipeline_result("evidence", started, [], status="unavailable")
    refs = source_ids(payload)
    items: List[Dict[str, Any]] = []
    for url in refs[:6]:
        result = item(
            prefix="reference",
            question="High-yield reference",
            answer=url,
            category="reference",
            sources=[url],
            confidence=1.0,
        )
        if result:
            items.append(result)
    return pipeline_result("evidence", started, _mark(items, payload), sources=refs)


def operative_flow_pipeline(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Operative flow — exposure, layers, implant strategy, fluoro checkpoints.

    Category doubles as the flow phase so the UI can group steps. Positioning
    and equipment are enrichment gap-fill targets (curated payloads lack them).
    """
    started = time.monotonic()
    if not payload:
        return pipeline_result("operative_flow", started, [], status="unavailable")
    refs = source_ids(payload)
    items: List[Dict[str, Any]] = []
    for index, description in enumerate((payload.get("surgical_approach_anatomy") or [])[:4]):
        result = item(
            prefix="exposure",
            question="Exposure" if index == 0 else f"Exposure (step {index + 1})",
            answer=description,
            category="exposure",
            sources=refs,
            confidence=0.9,
        )
        if result:
            items.append(result)
    for portal in (payload.get("arthroscopy_or_portal_anatomy") or [])[:4]:
        result = item(
            prefix="portal",
            question="Portal placement",
            answer=portal,
            category="exposure",
            sources=refs,
            confidence=0.9,
        )
        if result:
            items.append(result)
    for layer in (payload.get("surgical_layers") or [])[:8]:
        if not isinstance(layer, dict):
            continue
        result = item(
            prefix="step",
            question=clean(layer.get("layer_name")) or "Operative layer",
            answer=layer.get("what_user_should_know") or layer.get("surgical_relevance"),
            supporting_detail=layer.get("surgical_relevance"),
            category="critical_step",
            sources=layer.get("source_refs") or refs,
            confidence=0.9,
        )
        if result:
            items.append(result)
    for strategy in (payload.get("reduction_or_implant_anatomy") or [])[:4]:
        result = item(
            prefix="implant",
            question="Reduction / implant strategy",
            answer=strategy,
            category="critical_step",
            sources=refs,
            confidence=0.9,
        )
        if result:
            items.append(result)
    for checkpoint in (payload.get("fluoroscopy_checkpoints") or [])[:4]:
        result = item(
            prefix="fluoro",
            question="Fluoroscopy checkpoint",
            answer=checkpoint,
            category="checkpoint",
            sources=refs,
            confidence=0.9,
            dedup_key=f"fluoro:{norm_key(checkpoint)}",
        )
        if result:
            items.append(result)
    notes = clean(payload.get("approach_specific_notes"))
    if notes:
        result = item(
            prefix="notes",
            question="Approach-specific notes",
            answer=notes,
            category="pearl",
            sources=refs,
            confidence=0.85,
        )
        if result:
            items.append(result)
    return pipeline_result(
        "operative_flow", started, _mark(items[:18], payload), sources=refs
    )


# ── Above-the-fold builders (synchronous; emitted immediately after header) ──


def summary_block(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    started = time.monotonic()
    if not payload:
        return pipeline_result("summary", started, [], status="unavailable")
    refs = source_ids(payload)
    items: List[Dict[str, Any]] = []
    overview = clean(payload.get("procedure_overview"))
    if overview:
        result = item(
            prefix="summary",
            question="Procedure overview",
            answer=overview,
            category="summary",
            sources=refs,
            confidence=0.95,
        )
        if result:
            items.append(result)
    return pipeline_result("summary", started, _mark(items, payload), sources=refs)


def key_takeaways_block(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Highest-yield takeaways: top structure-at-risk avoidance + top mistakes."""
    started = time.monotonic()
    if not payload:
        return pipeline_result("key_takeaways", started, [], status="unavailable")
    refs = source_ids(payload)
    items: List[Dict[str, Any]] = []
    for structure in (payload.get("structures_at_risk") or [])[:2]:
        if not isinstance(structure, dict):
            continue
        name = clean(structure.get("structure") or structure.get("name"))
        avoidance = clean(structure.get("how_to_avoid_injury"))
        if name and avoidance:
            result = item(
                prefix="takeaway",
                question=f"Protect the {name}",
                answer=avoidance,
                category="key_takeaway",
                sources=structure.get("source_refs") or refs,
                confidence=0.95,
                dedup_key=f"structure:{norm_key(name)}",
            )
            if result:
                items.append(result)
    for mistake in (payload.get("common_mistakes") or [])[:2]:
        result = item(
            prefix="takeaway",
            question="Avoid this mistake",
            answer=mistake,
            category="key_takeaway",
            sources=refs,
            confidence=0.9,
            dedup_key=f"mistake:{norm_key(mistake)}",
        )
        if result:
            items.append(result)
    for zone in (payload.get("danger_zones") or [])[:1]:
        result = item(
            prefix="takeaway",
            question="Danger zone",
            answer=zone,
            category="key_takeaway",
            sources=refs,
            confidence=0.95,
            dedup_key=f"danger:{norm_key(zone)}",
        )
        if result:
            items.append(result)
    return pipeline_result(
        "key_takeaways", started, _mark(items[:5], payload), sources=refs
    )


def top_things_to_know_block(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Top-10 list drawn across curated modules in priority order."""
    started = time.monotonic()
    if not payload:
        return pipeline_result("top_things_to_know", started, [], status="unavailable")
    refs = source_ids(payload)
    items: List[Dict[str, Any]] = []

    def _add(
        question: str,
        answer: Any,
        category: str,
        confidence: float,
        dedup_key: Optional[str] = None,
    ) -> None:
        if len(items) >= 10:
            return
        result = item(
            prefix="top",
            question=question,
            answer=answer,
            category=category,
            sources=refs,
            confidence=confidence,
            dedup_key=dedup_key,
        )
        if result:
            items.append(result)

    for fact in (payload.get("must_know_anatomy") or [])[:3]:
        _add("Must-know anatomy", fact, "anatomy", 0.95, dedup_key=f"anatomy:{norm_key(fact)}")
    for structure in (payload.get("structures_at_risk") or [])[:3]:
        if isinstance(structure, dict):
            name = clean(structure.get("structure") or structure.get("name"))
            _add(
                name or "Structure at risk",
                structure.get("why_at_risk"),
                "risk",
                0.95,
                dedup_key=f"structure:{norm_key(name)}" if name else None,
            )
    for raw in (payload.get("attending_pimp_questions") or [])[:3]:
        question, answer = parse_qa(raw)
        if question:
            _add(question, answer, "pimp", 0.9, dedup_key=f"pimpq:{norm_key(question)}")
    for mistake in (payload.get("common_mistakes") or [])[:2]:
        _add("Common mistake", mistake, "pitfall", 0.9, dedup_key=f"mistake:{norm_key(mistake)}")
    for checkpoint in (payload.get("fluoroscopy_checkpoints") or [])[:1]:
        _add(
            "Fluoroscopy checkpoint",
            checkpoint,
            "checkpoint",
            0.9,
            dedup_key=f"fluoro:{norm_key(checkpoint)}",
        )
    return pipeline_result(
        "top_things_to_know", started, _mark(items[:10], payload), sources=refs
    )
