"""CasePrep v1.2 safety, provenance, and coverage layer over the v1.1 engine."""

from __future__ import annotations

import json
import re
import time
from typing import Any, AsyncIterator, Dict, Iterable, List, Optional, Tuple

from caseprep.engines.v1_1_web_stream import stream_caseprep_packet
from caseprep.schemas_v1_1_packet import SECTION_IDS, sse_event


VERSION = "v1.2"
ENGINE = "grounded_packet_stream"
EXPECTED_CLINICAL_SECTIONS = tuple(
    section for section in SECTION_IDS if section not in {"related_concepts", "sources"}
)
LEGACY_ESSENTIAL_SECTIONS = {"summary", "key_takeaways", "top_things_to_know"}
APPROACH_DETAIL_SECTIONS = (
    "approach_quick_brief",
    "approach_exposure",
    "approach_safety",
    "approach_strategy",
)
# Themed sections with no curated seed: AI supplementation is allowed through
# the grounding filter here (clearly marked generated). Every other section
# still requires direct source support.
GENERATED_SUPPLEMENT_SECTIONS = {"decision_points", "postop"}
OPERATIVE_WORDS = {
    "orif", "fixation", "arthroplasty", "replacement", "reconstruction", "repair",
    "release", "decompression", "fusion", "osteotomy", "nailing", "pinning",
}


def _decode_event(frame: bytes) -> Tuple[str, Dict[str, Any]]:
    name = "message"
    data_lines: List[str] = []
    for line in frame.decode("utf-8", errors="replace").splitlines():
        if line.startswith("event:"):
            name = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    try:
        return name, json.loads("\n".join(data_lines)) if data_lines else {}
    except json.JSONDecodeError:
        return "error", {"message": "CasePrep emitted an unreadable update."}


def _clean_text(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("Â°", "°").replace("Â", "")
    if isinstance(value, list):
        return [_clean_text(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean_text(item) for key, item in value.items()}
    return value


def _malformed_item(item: Dict[str, Any]) -> bool:
    text = f"{item.get('question', '')} {item.get('answer', '')} {item.get('supporting_detail', '')}"
    return "�" in text or "_Ð" in text or "\x00" in text


def _resolution_problem(prompt: str, case: Dict[str, Any], header: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    lowered = prompt.lower()
    canonical_name = case.get("canonical_name") or header.get("display_name") or prompt
    if "laparoscopic" in lowered:
        cleaned = re.sub(r"\blaparoscopic\b", "", prompt, flags=re.I).strip()
        return {
            "reason": "“Laparoscopic” is incompatible with this orthopaedic procedure. Confirm the intended case.",
            "unresolved_prompt_tokens": ["laparoscopic"],
            "options": [{"label": canonical_name, "prompt": cleaned or canonical_name}],
        }
    from caseprep.services.prompt_understanding import compatible_with_slug, extract_prompt_profile

    profile = extract_prompt_profile(prompt)
    canonical_slug = case.get("canonical_slug")
    has_region = bool(profile.get("regions"))
    has_procedure = bool(canonical_slug or profile.get("has_procedure_intent"))
    has_diagnosis = bool(case.get("diagnosis") or profile.get("has_diagnosis_intent"))
    if not canonical_slug and not has_region and not (has_procedure or has_diagnosis):
        return {
            "reason": "To give you accurate case prep, add the body region and either the planned procedure or diagnosis.",
            "unresolved_prompt_tokens": prompt.split(),
            "options": [],
        }
    if not canonical_slug and not has_region:
        return {
            "reason": "To give you accurate case prep, add the body region involved in this case.",
            "unresolved_prompt_tokens": prompt.split(),
            "options": [],
        }
    if not canonical_slug and not (has_procedure or has_diagnosis):
        return {
            "reason": "To give you accurate case prep, add the planned procedure or the specific diagnosis—not only the body region or symptom.",
            "unresolved_prompt_tokens": prompt.split(),
            "options": [],
        }
    if profile.get("compound") and {"hip", "knee"}.issubset(set(profile.get("regions") or [])):
        return {
            "reason": "This describes more than one major procedure. Choose the hip or knee case so each receives procedure-specific preparation.",
            "unresolved_prompt_tokens": ["hip", "knee"],
            "options": [
                {"label": "Total Hip Arthroplasty", "prompt": "Total Hip Arthroplasty"},
                {"label": "Total Knee Arthroplasty", "prompt": "Total Knee Arthroplasty"},
            ],
        }
    compatible, reasons = compatible_with_slug(profile, case.get("canonical_slug"))
    if not compatible:
        return {
            "reason": "The requested case modifiers do not match the selected packet: " + "; ".join(reasons),
            "unresolved_prompt_tokens": profile.get("modifiers") or [],
            "options": [],
        }
    return None


def _item_provenance(item: Dict[str, Any]) -> Dict[str, Any]:
    output = _clean_text(dict(item))
    generated = bool(output.get("generated"))
    source = str(output.get("source") or ("generated" if generated else "certified"))
    output["provenance"] = (
        "generated"
        if generated
        else (
            "rag"
            if source == "rag"
            else ("approach_library" if source == "approach_library" else "certified")
        )
    )
    output["claim_support"] = output.get("claim_support") or ("unsupported" if generated else "direct")
    output["procedure_relevance"] = output.get("procedure_relevance") or (
        "unknown" if generated or source == "rag" else "direct"
    )
    return output


def _transform_section(
    data: Dict[str, Any], *, allow_generated_supplements: bool = True
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    warnings: List[str] = []
    section_id = str(data.get("section_id") or "")
    raw_items = data.get("items") or []
    items = [_item_provenance(item) for item in raw_items if isinstance(item, dict)]
    malformed_count = sum(1 for item in items if _malformed_item(item))
    if malformed_count:
        warnings.append(f"Removed {malformed_count} malformed source item(s) from {section_id}.")
        items = [item for item in items if not _malformed_item(item)]

    grounded = [item for item in items if not item.get("generated")]
    generated = [item for item in items if item.get("generated")]
    if grounded:
        items = grounded
        generated = []
    if generated:
        if not allow_generated_supplements or section_id not in GENERATED_SUPPLEMENT_SECTIONS:
            warnings.append(f"Omitted {section_id} because it lacked direct source support.")
            return None, warnings
        # AI supplementation is intentional for these themed sections.
        items = generated
    if not items and raw_items:
        return None, warnings

    source_ids = {
        source_id for item in items for source_id in (item.get("source_ids") or []) if source_id
    }
    output = _clean_text(dict(data))
    if "items" in output:
        output["items"] = items
    output.update({
        "coverage": "grounded" if grounded else ("generated_fallback" if generated else "metadata"),
        "grounded_count": len(grounded),
        "generated_count": len(generated),
        "citation_count": len(source_ids),
        "omission_reason": None,
    })
    return output, warnings


def _item_count(section: Optional[Dict[str, Any]]) -> int:
    if not section:
        return 0
    return len(section.get("items") or [])


def has_clinical_body(emitted_sections: Dict[str, Dict[str, Any]]) -> bool:
    """True when the packet has more than a pimp-question list.

    Anatomy, operative flow, or a filled approach guide are the sections a
    resident actually uses to prepare. A quiz-only packet must not look complete.
    """
    if _item_count(emitted_sections.get("anatomy")):
        return True
    if _item_count(emitted_sections.get("operative_flow")):
        return True
    return any(
        _item_count(emitted_sections.get(section_id))
        for section_id in APPROACH_DETAIL_SECTIONS
    )


def evaluate_packet_coverage(
    *,
    canonical_slug: Optional[str],
    certified: bool,
    emitted_sections: Dict[str, Dict[str, Any]],
    expected_sections: Iterable[str],
) -> Dict[str, Any]:
    grounded = sum(
        int(section.get("grounded_count") or 0) for section in emitted_sections.values()
    )
    generated = sum(
        int(section.get("generated_count") or 0) for section in emitted_sections.values()
    )
    total = grounded + generated
    grounded_percentage = round(grounded / total, 3) if total else 0
    pimp_items = (emitted_sections.get("pimp_questions") or {}).get("items") or []
    pimp_count = len(pimp_items)
    citation_count = sum(
        int(section.get("citation_count") or 0) for section in emitted_sections.values()
    )
    direct_pimp_count = sum(
        item.get("procedure_relevance") == "direct" for item in pimp_items
    )
    clinical_body = has_clinical_body(emitted_sections)
    resolved = bool(canonical_slug)
    expected_sections = tuple(expected_sections)
    omitted = [section for section in expected_sections if section not in emitted_sections]
    essentials = emitted_sections.get("essentials") or {}
    essentials_verified = bool(
        essentials.get("source") == "grounded_synthesis"
        and ((essentials.get("payload") or {}).get("verification") or {}).get("passed")
    )
    topic_gaps = ((essentials.get("payload") or {}).get("verification") or {}).get("required_topic_gaps", [])
    # v1.3 promises a brief, not just a quiz. Legacy packets do not require it.
    brief_ready = "essentials" not in expected_sections or essentials_verified
    complete_enough = (
        resolved
        and clinical_body
        and brief_ready
        and not topic_gaps
        and pimp_count >= 5
        and direct_pimp_count >= 5
        and grounded_percentage >= 0.8
        and citation_count > 0
    )
    if certified and complete_enough:
        coverage_status = "certified"
    elif complete_enough and grounded >= 8:
        coverage_status = "grounded_complete"
    elif grounded:
        coverage_status = "grounded_partial"
    elif generated:
        coverage_status = "generated_fallback"
    else:
        coverage_status = "unavailable"
    return {
        "required_topic_gaps": topic_gaps,
        "coverage_status": coverage_status,
        "quality_gate": "passed" if coverage_status in {"certified", "grounded_complete"} else "limited",
        "grounded_percentage": grounded_percentage,
        "grounded_count": grounded,
        "generated_count": generated,
        "omitted_sections": omitted,
        "pimp_question_count": pimp_count,
        "citation_count": citation_count,
        "direct_pimp_question_count": direct_pimp_count,
        "has_clinical_body": clinical_body,
        "essentials_verified": essentials_verified,
    }


async def stream_caseprep_packet_v1_2(
    prompt: str, *, openai_client: Any, config: Any,
    version: str = VERSION, engine: str = ENGINE,
) -> AsyncIterator[bytes]:
    started = time.monotonic()
    header_data: Optional[Dict[str, Any]] = None
    emitted_sections: Dict[str, Dict[str, Any]] = {}
    warnings: List[str] = []

    async for frame in stream_caseprep_packet(
        prompt,
        openai_client=openai_client,
        config=config,
        policy_version=version,
    ):
        name, data = _decode_event(frame)
        if name == "meta":
            data.update({"caseprep_version": version, "engine": engine, "stream_protocol_version": 2})
            yield sse_event(name, data)
            continue
        if name == "header":
            header_data = data
            problem = _resolution_problem(prompt, data.get("case") or {}, data.get("header") or {})
            resolution = {
                "case": data.get("case"),
                "unresolved_prompt_tokens": problem.get("unresolved_prompt_tokens", []) if problem else [],
                "compatibility_status": "needs_clarification" if problem else "valid",
                "modifiers": (data.get("case") or {}).get("modifiers") or [],
                "explicit_question": bool((data.get("case") or {}).get("explicit_question")),
                "compound": bool((data.get("case") or {}).get("compound")),
            }
            yield sse_event("resolution", resolution)
            if problem:
                yield sse_event("clarification", {
                    "case": data.get("case"),
                    "clarification_reason": problem["reason"],
                    "options": problem["options"],
                    "unresolved_prompt_tokens": problem["unresolved_prompt_tokens"],
                })
                yield sse_event("done", {
                    "coverage_status": "clarification_required",
                    "quality_gate": "withheld",
                    "grounded_percentage": 0,
                    "omitted_sections": list(EXPECTED_CLINICAL_SECTIONS),
                    "pipeline_status": {},
                    "timing": {"total_ms": int((time.monotonic() - started) * 1000)},
                    "warnings": [],
                })
                return
            header = dict(data.get("header") or {})
            header["coverage_status"] = "certified" if header.get("certified") else "evaluating"
            yield sse_event("header", {"case": data.get("case"), "header": header})
            continue
        if name == "section":
            transformed, section_warnings = _transform_section(
                data, allow_generated_supplements=version == VERSION
            )
            warnings.extend(section_warnings)
            for warning in section_warnings:
                yield sse_event("warning", {"message": warning})
            if transformed is not None:
                emitted_sections[str(transformed.get("section_id"))] = transformed
                yield sse_event("section", transformed)
            continue
        if name == "done":
            expected_sections = (
                tuple(section for section in EXPECTED_CLINICAL_SECTIONS if section not in LEGACY_ESSENTIAL_SECTIONS)
                if version == "v1.3"
                else tuple(section for section in EXPECTED_CLINICAL_SECTIONS if section != "essentials")
            )
            summary = evaluate_packet_coverage(
                canonical_slug=((header_data or {}).get("case") or {}).get("canonical_slug"),
                certified=bool((header_data or {}).get("header", {}).get("certified")),
                emitted_sections=emitted_sections,
                expected_sections=expected_sections,
            )
            yield sse_event("core_done", summary)
            timing = dict(data.get("timing") or {})
            timing["total_ms"] = int((time.monotonic() - started) * 1000)
            yield sse_event("done", {
                **data,
                **summary,
                "timing": timing,
                "warnings": list(dict.fromkeys([*(data.get("warnings") or []), *warnings])),
                "retrieval_summary": {
                    "accepted_count": summary["grounded_count"],
                    "generated_count": summary["generated_count"],
                    "policy_version": version,
                },
            })
            continue
        yield sse_event(name, _clean_text(data))
