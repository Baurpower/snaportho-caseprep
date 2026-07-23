"""Deterministic supporting pipelines backed by published CasePrep payloads."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from caseprep.pipelines.shared import item, parse_qa, pipeline_result, source_ids


def _question_items(
    payload: Dict[str, Any], keywords: tuple[str, ...], category: str, limit: int
) -> List[Dict[str, Any]]:
    refs = source_ids(payload)
    output: List[Dict[str, Any]] = []
    for raw in payload.get("attending_pimp_questions") or []:
        question, answer = parse_qa(raw)
        if not question or not any(word in question.lower() for word in keywords):
            continue
        result = item(
            prefix=category,
            question=question,
            answer=answer,
            category=category,
            sources=refs,
            confidence=0.9,
        )
        if result:
            output.append(result)
        if len(output) >= limit:
            break
    return output


def indications_pipeline(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    started = time.monotonic()
    if not payload:
        return pipeline_result("indications", started, [], status="unavailable")
    items = _question_items(
        payload,
        ("indication", "contraindication", "nonoperative treatment", "when do", "who should"),
        "indications",
        6,
    )
    return pipeline_result("indications", started, items, sources=source_ids(payload))


def anatomy_pipeline(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    started = time.monotonic()
    if not payload:
        return pipeline_result("anatomy", started, [], status="unavailable")
    refs = source_ids(payload)
    items: List[Dict[str, Any]] = []
    for fact in (payload.get("must_know_anatomy") or [])[:4]:
        result = item(
            prefix="anatomy",
            question="What anatomy is important for this case?",
            answer=fact,
            category="important_anatomy",
            sources=refs,
            confidence=0.9,
        )
        if result:
            items.append(result)
    for structure in (payload.get("structures_at_risk") or [])[:5]:
        if not isinstance(structure, dict):
            continue
        name = structure.get("structure") or structure.get("name")
        result = item(
            prefix="risk",
            question=f"Why is the {name} at risk?" if name else "What structure is at risk?",
            answer=structure.get("why_at_risk"),
            supporting_detail=structure.get("how_to_avoid_injury"),
            category="structure_at_risk",
            sources=structure.get("source_refs") or refs,
            confidence=0.95,
        )
        if result:
            items.append(result)
    return pipeline_result("anatomy", started, items[:8], sources=refs)


def approach_pipeline(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    started = time.monotonic()
    if not payload:
        return pipeline_result("approach", started, [], status="unavailable")
    refs = source_ids(payload)
    items: List[Dict[str, Any]] = []
    for index, description in enumerate(payload.get("surgical_approach_anatomy") or []):
        result = item(
            prefix="approach",
            question="What is the key surgical exposure?" if index == 0 else "What is the next important part of the exposure?",
            answer=description,
            category="approach",
            sources=refs,
            confidence=0.9,
        )
        if result:
            items.append(result)
    for layer in (payload.get("surgical_layers") or [])[:6]:
        if not isinstance(layer, dict):
            continue
        result = item(
            prefix="step",
            question=f"What should you know at {layer.get('layer_name', 'this operative layer')}?",
            answer=layer.get("what_user_should_know") or layer.get("surgical_relevance"),
            supporting_detail=layer.get("surgical_relevance"),
            category="operative_steps",
            sources=layer.get("source_refs") or refs,
            confidence=0.9,
        )
        if result:
            items.append(result)
    return pipeline_result("approach", started, items[:10], sources=refs)


def complications_pipeline(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    started = time.monotonic()
    if not payload:
        return pipeline_result("complications", started, [], status="unavailable")
    refs = source_ids(payload)
    items: List[Dict[str, Any]] = []
    for mistake in (payload.get("common_mistakes") or [])[:6]:
        result = item(
            prefix="complication",
            question="What common mistake or complication should be avoided?",
            answer=mistake,
            category="complications",
            sources=refs,
            confidence=0.9,
        )
        if result:
            items.append(result)
    items.extend(
        _question_items(
            payload,
            ("complication", "postop", "postoperative", "weight bearing", "immobil"),
            "postoperative_care",
            4,
        )
    )
    return pipeline_result("complications", started, items[:8], sources=refs)
