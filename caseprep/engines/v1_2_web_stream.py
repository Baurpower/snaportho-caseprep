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
    if not case.get("canonical_slug") and not profile.get("regions"):
        return {
            "reason": "Add the body region and intended operation so CasePrep can retrieve procedure-relevant questions.",
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
    output["provenance"] = "generated" if generated else ("rag" if source == "rag" else "certified")
    output["claim_support"] = output.get("claim_support") or ("unsupported" if generated else "direct")
    output["procedure_relevance"] = output.get("procedure_relevance") or (
        "unknown" if generated else "direct"
    )
    return output


def _transform_section(data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], List[str]]:
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
        if section_id not in GENERATED_SUPPLEMENT_SECTIONS:
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


async def stream_caseprep_packet_v1_2(
    prompt: str, *, openai_client: Any, config: Any
) -> AsyncIterator[bytes]:
    started = time.monotonic()
    header_data: Optional[Dict[str, Any]] = None
    emitted_sections: Dict[str, Dict[str, Any]] = {}
    warnings: List[str] = []

    async for frame in stream_caseprep_packet(
        prompt,
        openai_client=openai_client,
        config=config,
        policy_version=VERSION,
    ):
        name, data = _decode_event(frame)
        if name == "meta":
            data.update({"caseprep_version": VERSION, "engine": ENGINE, "stream_protocol_version": 2})
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
            transformed, section_warnings = _transform_section(data)
            warnings.extend(section_warnings)
            for warning in section_warnings:
                yield sse_event("warning", {"message": warning})
            if transformed is not None:
                emitted_sections[str(transformed.get("section_id"))] = transformed
                yield sse_event("section", transformed)
            continue
        if name == "done":
            grounded = sum(int(section.get("grounded_count") or 0) for section in emitted_sections.values())
            generated = sum(int(section.get("generated_count") or 0) for section in emitted_sections.values())
            total = grounded + generated
            grounded_percentage = round(grounded / total, 3) if total else 0
            certified = bool((header_data or {}).get("header", {}).get("certified"))
            pimp_count = len((emitted_sections.get("pimp_questions") or {}).get("items") or [])
            citation_count = sum(int(section.get("citation_count") or 0) for section in emitted_sections.values())
            pimp_items = (emitted_sections.get("pimp_questions") or {}).get("items") or []
            direct_pimp_count = sum(item.get("procedure_relevance") == "direct" for item in pimp_items)
            if certified and pimp_count >= 8:
                coverage_status = "certified"
            elif grounded_percentage >= 0.8 and grounded >= 8:
                coverage_status = "grounded_complete"
            elif grounded:
                coverage_status = "grounded_partial"
            elif generated:
                coverage_status = "generated_fallback"
            else:
                coverage_status = "unavailable"
            omitted = [section for section in EXPECTED_CLINICAL_SECTIONS if section not in emitted_sections]
            quality_gate = (
                "passed"
                if coverage_status in {"certified", "grounded_complete"}
                and pimp_count >= 8
                and grounded_percentage >= 0.8
                and citation_count > 0
                and direct_pimp_count >= min(4, pimp_count)
                else "limited"
            )
            summary = {
                "coverage_status": coverage_status,
                "quality_gate": quality_gate,
                "grounded_percentage": grounded_percentage,
                "grounded_count": grounded,
                "generated_count": generated,
                "omitted_sections": omitted,
                "pimp_question_count": pimp_count,
                "citation_count": citation_count,
                "direct_pimp_question_count": direct_pimp_count,
            }
            yield sse_event("core_done", summary)
            timing = dict(data.get("timing") or {})
            timing["total_ms"] = int((time.monotonic() - started) * 1000)
            yield sse_event("done", {
                **data,
                **summary,
                "timing": timing,
                "warnings": list(dict.fromkeys([*(data.get("warnings") or []), *warnings])),
                "retrieval_summary": {
                    "accepted_count": grounded,
                    "generated_count": generated,
                    "policy_version": VERSION,
                },
            })
            continue
        yield sse_event(name, _clean_text(data))
