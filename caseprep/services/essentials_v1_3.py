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
- Put those IDs in `citations`, keyed by the exact JSON field path.
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
    "indications.summary", "critical_portion.summary",
    "critical_portion.why_it_matters", "critical_portion.failure_mode",
)
VARIABILITY_TERMS = (
    "case-specific", "construct-specific", "surgeon-specific", "depends on",
    "based on fixation", "based on construct", "confirm with",
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
    for field in CONTEXT_FIELDS:
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
    if "antegrade" in case_text and any(term in body for term in ("intercondylar notch", "blumensaat")):
        errors.append("antegrade femoral case contains a retrograde distal entry point")
    return errors


def verify_essentials(output: Dict[str, Any], evidence: List[Dict[str, Any]], identity: Dict[str, Any]) -> Dict[str, Any]:
    valid_ids = {row["evidence_id"] for row in evidence}
    citations = output.get("citations") or {}
    errors = _approach_contradictions(identity, output)
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
    cited_ids = {ref for refs in citations.values() if isinstance(refs, list) for ref in refs if ref in valid_ids}
    source_ids = sorted({source_id for row in evidence if row["evidence_id"] in cited_ids
                         for source_id in row.get("source_ids") or []})
    coverage = supported_paths / len(CORE_CITATION_PATHS)
    confidence = round(min(0.98, 0.45 + 0.4 * coverage + 0.04 * min(2, len(source_ids))), 2)
    return {"passed": not errors, "errors": errors, "core_claim_coverage": round(coverage, 2),
            "cited_evidence_count": len(cited_ids), "source_ids": source_ids,
            "confidence": confidence if not errors else min(confidence, 0.49)}


def generate_essentials(*, identity: Dict[str, Any], payload: Optional[Dict[str, Any]],
                        approach_prep: Dict[str, Any], openai_client: Any, model: str) -> Optional[Dict[str, Any]]:
    if openai_client is None:
        return None
    started = time.monotonic()
    evidence = build_evidence(payload, approach_prep)
    if not evidence:
        return None
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
        return None
    if result is None:
        return None
    verification = verify_essentials(result, evidence, identity)
    if not verification["passed"]:
        return None
    result["verification"] = verification
    return {"payload": result, "confidence": verification["confidence"],
            "source_ids": verification["source_ids"],
            "duration_ms": int((time.monotonic() - started) * 1000)}
