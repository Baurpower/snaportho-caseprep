"""
Map registry files to clinical DTOs for surgeon-facing read APIs.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional

from caseprep.registry.constants import (
    CLINICAL_SECTION_ORDER,
    COVERAGE_WEIGHTS,
    REQUIRED_SECTIONS,
    SECTION_CONTENT_TYPES,
    SECTION_LABELS,
)
from caseprep.registry.dto import (
    BulletItemDTO,
    ClinicalSectionDTO,
    PimpQuestionItemDTO,
    SourceDTO,
    SourceItemDTO,
    StructureAtRiskItemDTO,
    SurgicalLayerItemDTO,
)
from caseprep.registry.validation import section_has_content

_PIMP_PATTERN = re.compile(
    r"^\s*Q:\s*(?P<question>.+?)\s*A:\s*(?P<answer>.+?)\s*$",
    re.IGNORECASE | re.DOTALL,
)


def _source_urls(value: Any) -> List[str]:
    if not isinstance(value, dict):
        return []
    refs = value.get("source_refs") or value.get("source_urls") or []
    if not isinstance(refs, list):
        return []
    return [str(url).strip() for url in refs if isinstance(url, str) and url.strip()]


def parse_pimp_question(raw: str) -> Optional[PimpQuestionItemDTO]:
    text = (raw or "").strip()
    if not text:
        return None
    match = _PIMP_PATTERN.match(text)
    if match:
        question = match.group("question").strip()
        answer = match.group("answer").strip()
        if question and answer:
            return PimpQuestionItemDTO(question=question, answer=answer)
    return None


def map_structure_at_risk(item: Dict[str, Any]) -> Optional[StructureAtRiskItemDTO]:
    structure = str(item.get("structure") or "").strip()
    if not structure:
        return None
    return StructureAtRiskItemDTO(
        structure=structure,
        why_at_risk=str(item.get("why_at_risk") or "").strip(),
        how_to_avoid_injury=str(item.get("how_to_avoid_injury") or "").strip(),
        consequence_of_injury=str(item.get("consequence_of_injury") or "").strip(),
        approach_context=str(item.get("approach_context") or "").strip() or None,
        source_urls=_source_urls(item),
    )


def map_surgical_layer(item: Dict[str, Any]) -> Optional[SurgicalLayerItemDTO]:
    layer_name = str(item.get("layer_name") or "").strip()
    if not layer_name:
        return None
    key_structures = item.get("key_structures") or []
    structures_at_risk = item.get("structures_at_risk") or []
    return SurgicalLayerItemDTO(
        layer_name=layer_name,
        what_user_should_know=str(item.get("what_user_should_know") or "").strip(),
        key_structures=[str(v).strip() for v in key_structures if str(v).strip()],
        structures_at_risk=[str(v).strip() for v in structures_at_risk if str(v).strip()],
        surgical_relevance=str(item.get("surgical_relevance") or "").strip(),
        source_urls=_source_urls(item),
    )


def map_section_items(section_key: str, raw_items: Any) -> List[Dict[str, Any]]:
    if raw_items is None:
        return []

    items: List[Dict[str, Any]] = []

    if section_key in {
        "indications",
        "setup_positioning",
        "approach_landmarks",
        "pitfalls",
        "postop_plan",
        "implant_strategy",
        "reduction_or_fluoro_checkpoints",
    }:
        values = raw_items if isinstance(raw_items, list) else [raw_items]
        for value in values:
            if isinstance(value, str) and value.strip():
                items.append(BulletItemDTO(text=value.strip()).model_dump())
        return items

    if section_key == "attending_pimp_questions":
        values = raw_items if isinstance(raw_items, list) else [raw_items]
        for value in values:
            if isinstance(value, str):
                parsed = parse_pimp_question(value)
                if parsed:
                    items.append(parsed.model_dump())
            elif isinstance(value, dict):
                question = str(value.get("question") or "").strip()
                answer = str(value.get("answer") or "").strip()
                if question:
                    items.append(
                        PimpQuestionItemDTO(question=question, answer=answer).model_dump()
                    )
        return items

    if section_key == "structures_at_risk":
        values = raw_items if isinstance(raw_items, list) else [raw_items]
        for value in values:
            if isinstance(value, dict):
                mapped = map_structure_at_risk(value)
                if mapped:
                    items.append(mapped.model_dump())
        return items

    if section_key == "surgical_layers":
        values = raw_items if isinstance(raw_items, list) else [raw_items]
        for value in values:
            if isinstance(value, dict):
                mapped = map_surgical_layer(value)
                if mapped:
                    items.append(mapped.model_dump())
        return items

    if section_key == "sources":
        values = raw_items if isinstance(raw_items, list) else [raw_items]
        for value in values:
            if isinstance(value, dict):
                url = str(value.get("url") or "").strip()
                if not url:
                    continue
                items.append(
                    SourceItemDTO(
                        source_type=str(value.get("source_type") or "unknown"),
                        title=(str(value.get("title")).strip() if value.get("title") else None),
                        url=url,
                        consumed=bool(value.get("consumed")),
                    ).model_dump()
                )
        return items

    return items


def build_clinical_sections(
    modules: Dict[str, Any],
    sources: List[Dict[str, Any]],
) -> List[ClinicalSectionDTO]:
    sections: List[ClinicalSectionDTO] = []

    for section_key in CLINICAL_SECTION_ORDER:
        if section_key == "sources":
            raw_items = sources
        else:
            raw_items = modules.get(section_key)

        items = map_section_items(section_key, raw_items)
        is_empty = len(items) == 0
        if section_key != "sources":
            is_empty = not section_has_content(raw_items)

        sections.append(
            ClinicalSectionDTO(
                key=section_key,
                label=SECTION_LABELS[section_key],
                content_type=SECTION_CONTENT_TYPES[section_key],
                is_required=section_key in REQUIRED_SECTIONS,
                is_empty=is_empty,
                coverage_weight=COVERAGE_WEIGHTS.get(section_key, 0),
                items=items,
            )
        )

    return sections


def stable_source_id(url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return digest[:16]


def build_source_dtos(
    sources: List[Dict[str, Any]],
    modules: Dict[str, Any],
) -> List[SourceDTO]:
    linked_by_url: Dict[str, set[str]] = {}

    for section_key, raw_items in modules.items():
        if section_key == "sources":
            continue
        values = raw_items if isinstance(raw_items, list) else [raw_items]
        for value in values:
            urls: List[str] = []
            if isinstance(value, dict):
                urls = _source_urls(value)
            if not urls:
                continue
            for url in urls:
                linked_by_url.setdefault(url, set()).add(section_key)

    rows: List[SourceDTO] = []
    seen: set[str] = set()
    for row in sources:
        url = str(row.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        rows.append(
            SourceDTO(
                id=stable_source_id(url),
                source_type=str(row.get("source_type") or "unknown"),
                title=(str(row.get("title")).strip() if row.get("title") else None),
                url=url,
                consumed=bool(row.get("consumed")),
                linked_section_keys=sorted(linked_by_url.get(url, set())),
            )
        )
    return rows


def load_aliases(aliases_obj: Optional[Dict[str, Any]]) -> List[str]:
    if not aliases_obj:
        return []
    aliases = aliases_obj.get("aliases") or []
    if not isinstance(aliases, list):
        return []
    return [str(alias).strip() for alias in aliases if str(alias).strip()]


def excerpt_review_notes(text: Optional[str], limit: int = 500) -> Optional[str]:
    if not text:
        return None
    cleaned = re.sub(r"[#*_>`\[\]()]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return None
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."