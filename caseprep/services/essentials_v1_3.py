"""Evidence-grounded synthesis for the CasePrep v1.3 Essentials section."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from caseprep.pipelines.shared import clean


SYSTEM_PROMPT = """\
You are an orthopaedic attending preparing a trainee for tomorrow's operation.
Create a concise, procedure-specific Case Essentials brief using ONLY the
numbered evidence claims supplied by the user. Do not use memory or outside
medical knowledge.

Cover only the indications, the single most critical operative portion, and
the expected postoperative protocol.

Hard rules:
- Write declarative teaching content, never quiz questions or Q/A.
- Every factual output field must be supported by one or more evidence IDs.
- Put those IDs in `citations`, keyed by the exact JSON field path. Cite list
  fields at their list path (for example `critical_portion.execution_points`).
- Prefer concrete anatomy, reduction, imaging, and construct facts from the
  selected approach over generic surgical advice.
- Do not write empty phrases such as "proper technique," "adequate
  stabilization," "appropriate size," "ensure alignment," or "monitor for
  complications." State the evidenced action, landmark, check, or failure.
- When evidence is absent, say that the detail is case-, construct-, or
  surgeon-specific. Never fill an evidence gap from memory.
- Never mix antegrade and retrograde entry anatomy.
- Do not invent implant brands, unsupported measurements, or false precision.
- Keep the complete brief scannable in about one minute.
- Return only valid JSON matching the requested schema.
"""

RESPONSE_SCHEMA = {
    "indications": {"summary": "string", "key_points": ["string"], "case_specific_note": "string or null"},
    "critical_portion": {
        "name": "string", "summary": "string", "why_it_matters": "string",
        "execution_points": ["string"], "failure_mode": "string",
    },
    "postop_protocol": {
        "summary": "string", "immediate_priorities": ["string"],
        "immobilization": "string or null", "weight_bearing": "string or null",
        "motion": "string or null", "follow_up": "string or null",
        "red_flags": ["string"], "variability_note": "string",
    },
    "citations": {"exact.field.path": ["evidence_id"]},
}

CONTEXT_FIELDS = (
    "procedure_overview", "indications", "must_know_anatomy", "structures_at_risk",
    "surgical_approach_anatomy", "surgical_layers", "reduction_or_implant_anatomy",
    "fluoroscopy_checkpoints", "common_mistakes", "danger_zones", "postop_plan",
    "limitations", "approach_specific_notes",
)
CORE_CITATION_PATHS = (
    "indications.summary", "indications.key_points",
    "critical_portion.name", "critical_portion.summary",
    "critical_portion.why_it_matters", "critical_portion.execution_points",
    "critical_portion.failure_mode", "postop_protocol.summary",
    "postop_protocol.immediate_priorities", "postop_protocol.red_flags",
)
VARIABILITY_TERMS = (
    "case-specific", "construct-specific", "surgeon-specific", "depends on",
    "based on fixation", "based on construct", "confirm with",
)
GENERIC_ESSENTIALS_PHRASES = (
    "proper reaming", "proper alignment", "adequate stabilization",
    "appropriate reamer", "appropriate size", "ensure proper",
    "optimal alignment", "monitor for any signs", "appropriate rehabilitation",
    "proper technique",
)


def _texts(value: Any, limit: int) -> List[str]:
    if not isinstance(value, list):
        return []
    return [text for entry in value[:limit] if (text := clean(entry))]


def _nullable_text(value: Any) -> Optional[str]:
    text = clean(value)
    return text or None


def _flatten_text(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        if clean(value):
            yield clean(value)
    elif isinstance(value, list):
        for entry in value:
            yield from _flatten_text(entry)
    elif isinstance(value, dict):
        preferred = value.get("text") or value.get("answer")
        if preferred:
            yield from _flatten_text(preferred)
        else:
            for entry in value.values():
                yield from _flatten_text(entry)


def _payload_source_ids(payload: Optional[Dict[str, Any]]) -> List[str]:
    if not payload:
        return []
    refs = payload.get("source_ids") or payload.get("source_urls") or []
    return [clean(ref) for ref in refs if clean(ref)] if isinstance(refs, list) else []


def build_evidence(payload: Optional[Dict[str, Any]], approach_prep: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Select compact, source-addressable evidence with exact approach facts first."""
    if approach_prep.get("graph_mode"):
        from caseprep.services.approach_graph_evidence import packet_evidence
        return packet_evidence(approach_prep.get("selected_packets", []))
    evidence: List[Dict[str, Any]] = []
    seen: set[Tuple[str, Tuple[str, ...]]] = set()

    def add(text: Any, source_ids: Any, kind: str) -> None:
        statement = clean(text)
        refs = tuple(dict.fromkeys(clean(ref) for ref in (source_ids or []) if clean(ref)))
        if not statement or not refs or (statement.lower(), refs) in seen:
            return
        seen.add((statement.lower(), refs))
        evidence.append({"evidence_id": f"E{len(evidence) + 1}", "text": statement,
                         "source_ids": list(refs), "kind": kind})

    for section_id, section in (approach_prep.get("sections") or {}).items():
        for entry in section.get("items") or []:
            if isinstance(entry, dict):
                add(entry.get("answer"), entry.get("source_ids"), section_id)

    payload_refs = _payload_source_ids(payload)
    # Once an exact approach has been selected, legacy aggregate anatomy is
    # unsafe evidence: older packets commonly describe a different corridor
    # (for example lateral plating inside a retrograde femoral-nail case).
    # Approach-library claims own the operative and indication content. The
    # legacy payload may only supplement a genuinely explicit postop plan.
    selected_approach = clean((approach_prep.get("coverage") or {}).get("approach_id"))
    payload_fields = ("postop_plan",) if selected_approach else CONTEXT_FIELDS
    for field in payload_fields:
        if payload and payload.get(field):
            for statement in _flatten_text(payload[field]):
                add(statement, payload_refs, field)
    return evidence[:60]


def _sanitize(raw: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    indications, critical, postop, citations = (
        raw.get("indications"), raw.get("critical_portion"),
        raw.get("postop_protocol"), raw.get("citations"),
    )
    if not all(isinstance(section, dict) for section in (indications, critical, postop)) or not isinstance(citations, dict):
        return None
    output = {
        "indications": {"summary": clean(indications.get("summary")),
                        "key_points": _texts(indications.get("key_points"), 4),
                        "case_specific_note": _nullable_text(indications.get("case_specific_note"))},
        "critical_portion": {"name": clean(critical.get("name")),
                             "summary": clean(critical.get("summary")),
                             "why_it_matters": clean(critical.get("why_it_matters")),
                             "execution_points": _texts(critical.get("execution_points"), 4),
                             "failure_mode": clean(critical.get("failure_mode"))},
        "postop_protocol": {"summary": clean(postop.get("summary")),
                            "immediate_priorities": _texts(postop.get("immediate_priorities"), 4),
                            "immobilization": _nullable_text(postop.get("immobilization")),
                            "weight_bearing": _nullable_text(postop.get("weight_bearing")),
                            "motion": _nullable_text(postop.get("motion")),
                            "follow_up": _nullable_text(postop.get("follow_up")),
                            "red_flags": _texts(postop.get("red_flags"), 4),
                            "variability_note": clean(postop.get("variability_note"))},
        "citations": {clean(path): list(dict.fromkeys(clean(ref) for ref in refs if clean(ref)))
                      for path, refs in citations.items() if clean(path) and isinstance(refs, list)},
    }
    required = (output["indications"]["summary"], output["critical_portion"]["name"],
                output["critical_portion"]["summary"], output["critical_portion"]["why_it_matters"],
                output["critical_portion"]["failure_mode"], output["postop_protocol"]["summary"],
                output["postop_protocol"]["variability_note"])
    return output if all(required) else None


def _all_output_text(payload: Dict[str, Any]) -> str:
    return " ".join(_flatten_text({k: v for k, v in payload.items() if k != "citations"})).lower()


def _approach_contradictions(identity: Dict[str, Any], output: Dict[str, Any]) -> List[str]:
    case_text = " ".join(clean(identity.get(key)) for key in
                         ("requested_case", "canonical_name", "diagnosis", "approach")
                         if clean(identity.get(key))).lower()
    body = _all_output_text(output)
    errors: List[str] = []
    if "retrograde" in case_text and any(term in body for term in ("intertrochanteric", "greater trochanter", "piriformis")):
        errors.append("retrograde femoral case contains an antegrade proximal entry point")
    critical = " ".join(_flatten_text(output.get("critical_portion") or {})).lower()
    if "retrograde" in case_text and not any(
        term in critical
        for term in ("retrograde", "intercondylar", "blumensaat", "patellar tendon", "pcl")
    ):
        errors.append("retrograde femoral critical portion is not anchored to the selected corridor")
    if "antegrade" in case_text and any(term in body for term in ("intercondylar notch", "blumensaat")):
        errors.append("antegrade femoral case contains a retrograde distal entry point")
    return errors


def _specificity_errors(output: Dict[str, Any]) -> List[str]:
    """Reject boilerplate that conveys no case-specific operative decision."""
    body = _all_output_text(output)
    return [
        f"generic essentials language: {phrase}"
        for phrase in GENERIC_ESSENTIALS_PHRASES
        if phrase in body
    ]


def verify_essentials(output: Dict[str, Any], evidence: List[Dict[str, Any]], identity: Dict[str, Any]) -> Dict[str, Any]:
    valid_ids = {row["evidence_id"] for row in evidence}
    citations = output.get("citations") or {}
    errors = _approach_contradictions(identity, output) + _specificity_errors(output)
    graph_evidence = any(row.get("packet_hash") for row in evidence)
    if graph_evidence:
        from caseprep.services.approach_graph_evidence import support_errors
        errors.extend(support_errors(output, evidence))
    supported_paths = 0
    for path in CORE_CITATION_PATHS:
        refs = citations.get(path) or []
        if refs and all(ref in valid_ids for ref in refs):
            supported_paths += 1
        else:
            errors.append(f"missing or invalid evidence citation for {path}")
    for field in ("immobilization", "weight_bearing", "motion", "follow_up"):
        value = clean((output.get("postop_protocol") or {}).get(field)).lower()
        refs = citations.get(f"postop_protocol.{field}") or []
        if value and not (refs and all(ref in valid_ids for ref in refs)) and not any(term in value for term in VARIABILITY_TERMS):
            errors.append(f"unsupported postoperative directive at postop_protocol.{field}")
    # Citations may not point at empty evidence or at claims without a source.
    evidence_by_id = {row["evidence_id"]: row for row in evidence}
    for path, refs in citations.items():
        if not isinstance(refs, list):
            continue
        for ref in refs:
            row = evidence_by_id.get(ref)
            if row is not None and not row.get("source_ids"):
                errors.append(f"citation {ref} for {path} has no source")
    cited_ids = {ref for refs in citations.values() if isinstance(refs, list) for ref in refs if ref in valid_ids}
    source_ids = sorted({source_id for row in evidence if row["evidence_id"] in cited_ids
                         for source_id in row.get("source_ids") or []})
    coverage = supported_paths / len(CORE_CITATION_PATHS)
    confidence = round(min(0.98, 0.45 + 0.4 * coverage + 0.04 * min(2, len(source_ids))), 2)
    return {"support_method": "exact_source_excerpt" if graph_evidence else "citation_validation",
            "used_claim_ids": sorted({c for row in evidence if row["evidence_id"] in cited_ids for c in row.get("source_claim_ids", [])}),
            "passed": not errors, "errors": errors, "core_claim_coverage": round(coverage, 2),
            "cited_evidence_count": len(cited_ids), "source_ids": source_ids,
            "confidence": confidence if not errors else min(confidence, 0.49)}


def grounded_essentials_fallback(
    evidence: List[Dict[str, Any]],
    identity: Dict[str, Any],
    *,
    duration_ms: int = 0,
    reason: str = "synthesis_unavailable",
) -> Optional[Dict[str, Any]]:
    if not evidence:
        return None
    name = clean(identity.get("canonical_name")) or "this procedure"
    indication = next(
        (row for row in evidence if row.get("kind") in {"indications"}),
        None,
    )
    critical = next(
        (row for row in evidence if row.get("kind") in {"approach_safety", "approach_exposure"}),
        evidence[0],
    )
    postop = next(
        (row for row in evidence if row.get("kind") in {"postop_plan", "postop"}),
        None,
    )
    evidence_id = indication["evidence_id"] if indication else None
    critical_id = critical["evidence_id"]
    postop_id = postop["evidence_id"] if postop else None
    payload = {
        "indications": {
            "summary": indication["text"] if indication else "Indications are unavailable in this brief.",
            "key_points": [],
            "case_specific_note": None,
        },
        "critical_portion": {
            "name": f"Available operative evidence for {name}",
            "summary": critical["text"],
            "why_it_matters": "The available sources do not establish why this is the critical step.",
            "execution_points": [critical["text"]],
            "failure_mode": "A procedure-specific failure mode is not available in this brief.",
        },
        "postop_protocol": {
            "summary": (postop or {}).get("text")
            or "Postoperative details are unavailable in this brief.",
            "immediate_priorities": [],
            "immobilization": None,
            "weight_bearing": None,
            "motion": None,
            "follow_up": None,
            "red_flags": [],
            "variability_note": "Confirm the operating surgeon's protocol.",
        },
        "citations": {
            "indications.summary": [evidence_id] if evidence_id else [],
            "critical_portion.summary": [critical_id],
            "critical_portion.execution_points": [critical_id],
            "postop_protocol.summary": [postop_id] if postop else [],
        },
        "verification": {
            "passed": False,
            "errors": ["Evidence excerpts only; complete brief has not been verified."],
            "core_claim_coverage": 0.0,
            "cited_evidence_count": len({value for value in (evidence_id, critical_id, postop_id) if value}),
            "source_ids": list(dict.fromkeys(
                source_id
                for row in (indication, critical, postop) if row
                for source_id in row.get("source_ids") or []
            )),
            "confidence": 0.62,
        },
    }
    return {
        "payload": payload,
        "confidence": 0.62,
        "source_ids": payload["verification"]["source_ids"],
        "duration_ms": duration_ms,
        "fallback": True,
        "fallback_reason": reason,
    }


def generate_essentials(*, identity: Dict[str, Any], payload: Optional[Dict[str, Any]],
                        approach_prep: Dict[str, Any], openai_client: Any, model: str) -> Optional[Dict[str, Any]]:
    started = time.monotonic()
    evidence = build_evidence(payload, approach_prep)
    if approach_prep.get("graph_mode"):
        from caseprep.services.approach_graph_evidence import REQUIRED_TOPICS
        topics = sorted({r["semantic_topic"] for r in evidence})
        gaps = [t for t in REQUIRED_TOPICS if t not in topics]
        if gaps:
            fallback = grounded_essentials_fallback(evidence, identity, duration_ms=int((time.monotonic()-started)*1000), reason="required_topic_gaps")
            if fallback:
                fallback["payload"]["verification"].update({"required_topic_gaps": gaps, "available_topics": topics, "support_method": "source_excerpts_only"})
                cited = {v for values in fallback["payload"].get("citations", {}).values() for v in values}
                used = [r for r in evidence if r["evidence_id"] in cited]
                fallback["payload"]["evidence_provenance"] = used
                fallback["payload"]["verification"]["used_claim_ids"] = sorted({c for r in used for c in r["source_claim_ids"]})
            return fallback
    if not evidence:
        return None
    if openai_client is None:
        return grounded_essentials_fallback(
            evidence, identity, duration_ms=int((time.monotonic() - started) * 1000), reason="no_model_client"
        )
    case = {key: identity.get(key) for key in
            ("requested_case", "canonical_name", "diagnosis", "approach", "laterality",
             "patient_age", "specialty", "region", "modifiers")
            if identity.get(key) not in (None, "", [])}
    prompt = (f"Case identity:\n{json.dumps(case, ensure_ascii=False)}\n\n"
              f"Numbered evidence claims:\n{json.dumps(evidence, ensure_ascii=False)}\n\n"
              f"Return JSON with this schema:\n{json.dumps(RESPONSE_SCHEMA)}")
    try:
        response = openai_client.chat.completions.create(
            model=model, temperature=0.1, response_format={"type": "json_object"},
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        )
        result = _sanitize(json.loads(response.choices[0].message.content or "{}"))
    except Exception:
        return grounded_essentials_fallback(
            evidence, identity, duration_ms=int((time.monotonic() - started) * 1000), reason="model_or_json_error"
        )
    if result is None:
        return grounded_essentials_fallback(
            evidence, identity, duration_ms=int((time.monotonic() - started) * 1000), reason="invalid_response"
        )
    verification = verify_essentials(result, evidence, identity)
    if not verification["passed"]:
        return grounded_essentials_fallback(
            evidence, identity, duration_ms=int((time.monotonic() - started) * 1000), reason="verification_failed"
        )
    result["verification"] = verification
    return {"payload": result, "confidence": verification["confidence"],
            "source_ids": verification["source_ids"],
            "duration_ms": int((time.monotonic() - started) * 1000)}
