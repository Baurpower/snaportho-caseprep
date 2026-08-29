"""Deterministic parallel approach-preparation pipeline.

The approach library is already procedure-mapped and claim-bound, so the
primary runtime path is an exact local lookup rather than semantic search.  All
library packets are eligible: authored packets emit their clinical content;
source-indexed packets emit identity/source coverage without manufacturing
missing operative guidance.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from caseprep.approach_library import ApproachLibrary
from caseprep.pipelines.shared import clean, item, pipeline_result
from caseprep.services.packet_v3 import approach_decision_payload


SECTION_FIELDS = {
    "approach_quick_brief": (
        ("corridor", "Corridor", "corridor"),
        ("positioning", "Positioning", "position"),
        ("setup", "Setup", "equipment"),
        ("surface_landmarks", "Surface landmark", "landmark"),
    ),
    "approach_exposure": (
        ("incision", "Incision", "incision"),
        ("superficial_interval", "Superficial interval", "superficial_interval"),
        ("deep_interval", "Deep interval", "deep_interval"),
        ("layers", "Layer", "layer"),
        ("structures_encountered", "Structure encountered", "structure_encountered"),
        ("exposure", "Exposure", "exposure"),
    ),
    "approach_safety": (
        ("structures_at_risk", "Structure at risk", "structure_at_risk"),
        ("danger_zones", "Danger zone", "danger_zone"),
        ("retraction_hazards", "Retraction hazard", "retraction_hazard"),
        ("complications", "Approach complication", "complication"),
    ),
    "approach_strategy": (
        ("indications", "Use this approach when", "indication"),
        ("relative_contraindications", "Consider another approach when", "contraindication"),
        ("limitations", "Limitation", "limitation"),
        ("extensions", "Extension", "extension"),
        ("implant_implications", "Implant implication", "implant"),
        ("fluoroscopy_implications", "Fluoroscopy implication", "fluoroscopy"),
        ("closure", "Closure", "closure"),
        ("bailouts", "Bailout", "bailout"),
    ),
}


def further_reading_resources(approach_prep: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Turn selected-approach sources into user-facing reading recommendations."""
    resources: List[Dict[str, Any]] = []
    seen: set[str] = set()
    approach_name = clean((approach_prep.get("coverage") or {}).get("approach_name"))
    for source in approach_prep.get("sources") or []:
        if not isinstance(source, dict):
            continue
        url = clean(source.get("url"))
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc or url in seen:
            continue
        seen.add(url)
        publisher = clean(source.get("provider") or source.get("publisher"))
        title = clean(source.get("title")) or parsed.netloc
        provider_key = publisher.lower()
        if "ao surgery" in provider_key:
            resource_type = "operative_technique"
            best_for = "Step-by-step approach, positioning, and operative technique"
        elif "orthobullets" in provider_key:
            resource_type = "clinical_review"
            best_for = "High-yield indications, technique, complications, and review"
        else:
            resource_type = "case_reference"
            best_for = "Deeper review of the selected operative approach"
        resources.append(
            {
                "source_id": clean(source.get("source_id")) or url,
                "title": title,
                "source_name": publisher or parsed.netloc,
                "url": url,
                "resource_type": resource_type,
                "best_for": best_for,
                "badges": [value for value in ("Selected approach", approach_name) if value],
            }
        )
    return resources


def _source_map(packet: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(source.get("source_id")): source
        for source in packet.get("sources") or []
        if isinstance(source, dict) and source.get("source_id")
    }


def _claim_map(packet: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(claim.get("claim_id")): claim
        for claim in packet.get("claims") or []
        if isinstance(claim, dict) and claim.get("claim_id")
    }


def _values(packet: Dict[str, Any], field: str) -> Iterable[Any]:
    value = packet.get(field)
    if field == "corridor":
        return [value] if clean(value) else []
    return value if isinstance(value, list) else []


def _clinical_item(
    packet: Dict[str, Any], field: str, label: str, category: str, raw: Any
) -> Optional[Dict[str, Any]]:
    row = raw if isinstance(raw, dict) else {"text": raw}
    answer = clean(row.get("text") or row.get("answer"))
    if not answer:
        return None
    claim_ids = [clean(value) for value in row.get("claim_ids") or [] if clean(value)]
    claims = _claim_map(packet)
    source_ids: List[str] = []
    risk_levels: List[str] = []
    for claim_id in claim_ids:
        claim = claims.get(claim_id) or {}
        source_ids.extend(clean(value) for value in claim.get("source_ids") or [] if clean(value))
        if clean(claim.get("risk_level")):
            risk_levels.append(clean(claim.get("risk_level")))
    if not source_ids:
        source_ids = list(_source_map(packet))
    result = item(
        prefix=f"approach-{field}",
        question=label,
        answer=answer,
        category=category,
        sources=source_ids,
        confidence=0.92 if claim_ids else 0.75,
    )
    if result:
        result.update(
            {
                "source": "approach_library",
                "provenance": "approach_library",
                "approach_id": packet.get("approach_id"),
                "claim_ids": claim_ids,
                "risk_level": "critical" if "critical" in risk_levels else (
                    "high" if "high" in risk_levels else (risk_levels[0] if risk_levels else None)
                ),
                "review_status": (packet.get("review") or {}).get("status") or "not_started",
                "content_status": packet.get("content_status") or "unknown",
            }
        )
    return result


def _selected_packet(procedure_id: str, selected_approach_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not selected_approach_id:
        return None
    library = ApproachLibrary()
    for packet in library.for_procedure(procedure_id):
        if packet.get("approach_id") == selected_approach_id:
            return packet
    # The decision layer may select a catalog/legacy approach. Return a direct
    # library match when one exists, even if its procedure mapping is sparse.
    return library.get(selected_approach_id)


def _packet_from_decision_option(option: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt a curated inline/legacy option into the native pipeline shape."""
    def rows(field: str) -> List[Dict[str, Any]]:
        values = option.get(field) or []
        if field == "corridor":
            values = [values] if clean(values) else []
        result: List[Dict[str, Any]] = []
        for value in values if isinstance(values, list) else []:
            if isinstance(value, dict):
                text = clean(
                    value.get("text")
                    or value.get("answer")
                    or value.get("structure")
                    or value.get("landmark")
                    or value.get("name")
                    or value.get("layer_name")
                )
            else:
                text = clean(value)
            if text:
                result.append({"text": text})
        return result

    sources = [
        {
            "source_id": f"inline-{index}",
            "title": str(url),
            "url": str(url),
        }
        for index, url in enumerate(option.get("source_urls") or [])
        if clean(url)
    ]
    return {
        "approach_id": option.get("approach_id"),
        "name": option.get("name"),
        "content_status": option.get("content_status") or "curated",
        "review": {"status": option.get("review_status") or "agent_review_pending"},
        "sources": sources,
        "claims": [],
        "corridor": clean(option.get("corridor")),
        "positioning": rows("positioning"),
        "setup": [],
        "surface_landmarks": rows("landmarks"),
        "incision": [],
        "superficial_interval": [],
        "deep_interval": [],
        "layers": rows("layers"),
        "structures_encountered": [],
        "structures_at_risk": rows("structures_at_risk"),
        "danger_zones": [],
        "retraction_hazards": [],
        "exposure": rows("exposure"),
        "limitations": rows("selection_limitations"),
        "extensions": [],
        "indications": rows("selection_indications"),
        "relative_contraindications": [],
        "implant_implications": [],
        "fluoroscopy_implications": [],
        "closure": [],
        "complications": rows("pitfalls"),
        "bailouts": [],
        "questions": option.get("questions") or [],
    }


def build_approach_prep(
    prompt: str,
    procedure_id: str,
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    started = time.monotonic()
    seed = payload or {
        "schema_version": "brobot_case_prep_payload_v2",
        "procedure_id": procedure_id,
        "case_prep_status": "unreviewed",
        "procedure_overview": "",
    }
    decision = approach_decision_payload(prompt, seed)
    selected_ids = decision.get("selected_approach_ids") or (
        [decision.get("selected_approach_id")]
        if decision.get("selected_approach_id")
        else []
    )
    options_by_id = {
        str(option.get("approach_id")): option
        for option in decision.get("approaches") or []
        if option.get("approach_id")
    }
    packets = []
    for approach_id in selected_ids:
        packet = _selected_packet(procedure_id, approach_id)
        if not packet and approach_id in options_by_id:
            packet = _packet_from_decision_option(options_by_id[approach_id])
        if packet:
            packets.append(packet)
    packet = packets[0] if packets else None
    sections: Dict[str, Dict[str, Any]] = {}
    questions: List[Dict[str, Any]] = []

    if packets:
        for section_id, fields in SECTION_FIELDS.items():
            section_started = time.monotonic()
            entries: List[Dict[str, Any]] = []
            for selected_packet in packets:
                for field, label, category in fields:
                    for raw in _values(selected_packet, field):
                        result = _clinical_item(selected_packet, field, label, category, raw)
                        if result:
                            if len(packets) > 1:
                                result["approach_name"] = selected_packet.get("name")
                            entries.append(result)
            sections[section_id] = pipeline_result(
                section_id,
                section_started,
                entries,
                sources={
                    source_id: source
                    for selected_packet in packets
                    for source_id, source in _source_map(selected_packet).items()
                },
            )
        for selected_packet in packets:
            for raw in selected_packet.get("questions") or []:
                if not isinstance(raw, dict):
                    continue
                result = _clinical_item(
                    selected_packet,
                    "questions",
                    raw.get("question") or "Approach question",
                    "approach_question",
                    raw,
                )
                if not result:
                    continue
                result["question"] = clean(raw.get("question"))
                result["answer"] = clean(raw.get("answer"))
                result["procedure_relevance"] = "direct"
                result["approach_relevance"] = "exact"
                result["claim_support"] = (
                    "direct" if result.get("claim_ids") else "indirect"
                )
                questions.append(result)

    sources_by_id = {}
    for selected_packet in packets:
        sources_by_id.update(_source_map(selected_packet))
    sources = list(sources_by_id.values())
    coverage = {
        "approach_id": decision.get("selected_approach_id"),
        "approach_ids": selected_ids,
        "approach_name": (packet or {}).get("name"),
        "selection_status": decision.get("status"),
        "content_status": (packet or {}).get("content_status") or "unavailable",
        "review_status": ((packet or {}).get("review") or {}).get("status") or "not_started",
        "claim_count": sum(len(value.get("claims") or []) for value in packets),
        "source_count": len(sources),
        "question_count": len(questions),
        "available_sections": [key for key, value in sections.items() if value.get("items")],
        "missing_sections": [key for key, value in sections.items() if not value.get("items")],
    }
    return {
        "pipeline_id": "approach_prep",
        "status": "complete" if decision.get("approaches") else "unavailable",
        "decision": decision,
        "sections": sections,
        "questions": questions,
        "sources": sources,
        "coverage": coverage,
        "duration_ms": int((time.monotonic() - started) * 1000),
    }
