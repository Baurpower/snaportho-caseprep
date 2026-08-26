"""Focused AI synthesis for the CasePrep v1.3 Essentials section.

This is intentionally independent of Pocket Pimped retrieval.  Curated and
approach-library context improve the brief when present; the model may use its
general orthopaedic knowledge when those sources are incomplete.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from caseprep.pipelines.shared import clean


SYSTEM_PROMPT = """\
You are an orthopaedic attending preparing a trainee for tomorrow's operation.
Create a concise, procedure-specific Case Essentials brief. You may use
established general orthopaedic knowledge in addition to the supplied context.

Cover only:
1. The indications for surgery.
2. The single most critical portion of the operation.
3. The expected postoperative protocol.

Hard rules:
- Write declarative teaching content, never quiz questions or Q/A.
- Do not reproduce or anticipate attending pimp questions.
- Select one critical operative portion, explain why it matters, and identify
  its most consequential failure mode.
- Never contradict supplied context. When practice varies, say so explicitly.
- Do not invent implant brands, unsupported measurements, or false precision.
- Keep the complete brief scannable in about one minute.
- Return only valid JSON matching the requested schema.
"""

RESPONSE_SCHEMA = {
    "indications": {
        "summary": "string",
        "key_points": ["string"],
        "case_specific_note": "string or null",
    },
    "critical_portion": {
        "name": "string",
        "summary": "string",
        "why_it_matters": "string",
        "execution_points": ["string"],
        "failure_mode": "string",
    },
    "postop_protocol": {
        "summary": "string",
        "immediate_priorities": ["string"],
        "immobilization": "string or null",
        "weight_bearing": "string or null",
        "motion": "string or null",
        "follow_up": "string or null",
        "red_flags": ["string"],
        "variability_note": "string",
    },
}

CONTEXT_FIELDS = (
    "procedure_overview",
    "indications",
    "must_know_anatomy",
    "structures_at_risk",
    "surgical_approach_anatomy",
    "surgical_layers",
    "reduction_or_implant_anatomy",
    "fluoroscopy_checkpoints",
    "common_mistakes",
    "danger_zones",
    "postop_plan",
    "limitations",
    "approach_specific_notes",
)


def _texts(value: Any, limit: int) -> List[str]:
    if not isinstance(value, list):
        return []
    return [text for entry in value[:limit] if (text := clean(entry))]


def _nullable_text(value: Any) -> Optional[str]:
    text = clean(value)
    return text or None


def _sanitize(raw: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    indications = raw.get("indications")
    critical = raw.get("critical_portion")
    postop = raw.get("postop_protocol")
    if not all(isinstance(section, dict) for section in (indications, critical, postop)):
        return None

    output = {
        "indications": {
            "summary": clean(indications.get("summary")),
            "key_points": _texts(indications.get("key_points"), 4),
            "case_specific_note": _nullable_text(indications.get("case_specific_note")),
        },
        "critical_portion": {
            "name": clean(critical.get("name")),
            "summary": clean(critical.get("summary")),
            "why_it_matters": clean(critical.get("why_it_matters")),
            "execution_points": _texts(critical.get("execution_points"), 4),
            "failure_mode": clean(critical.get("failure_mode")),
        },
        "postop_protocol": {
            "summary": clean(postop.get("summary")),
            "immediate_priorities": _texts(postop.get("immediate_priorities"), 4),
            "immobilization": _nullable_text(postop.get("immobilization")),
            "weight_bearing": _nullable_text(postop.get("weight_bearing")),
            "motion": _nullable_text(postop.get("motion")),
            "follow_up": _nullable_text(postop.get("follow_up")),
            "red_flags": _texts(postop.get("red_flags"), 4),
            "variability_note": clean(postop.get("variability_note")),
        },
    }
    required = (
        output["indications"]["summary"],
        output["critical_portion"]["name"],
        output["critical_portion"]["summary"],
        output["postop_protocol"]["summary"],
    )
    return output if all(required) else None


def _context(
    identity: Dict[str, Any],
    payload: Optional[Dict[str, Any]],
    approach_prep: Dict[str, Any],
) -> Dict[str, Any]:
    curated = {
        key: payload.get(key)
        for key in CONTEXT_FIELDS
        if payload and payload.get(key)
    }
    approach = {
        section_id: section.get("items") or []
        for section_id, section in (approach_prep.get("sections") or {}).items()
        if section.get("items")
    }
    return {
        "case": {
            key: identity.get(key)
            for key in (
                "requested_case",
                "canonical_name",
                "diagnosis",
                "approach",
                "laterality",
                "patient_age",
                "specialty",
                "region",
                "modifiers",
            )
            if identity.get(key) not in (None, "", [])
        },
        "curated_content": curated,
        "approach_content": approach,
    }


def generate_essentials(
    *,
    identity: Dict[str, Any],
    payload: Optional[Dict[str, Any]],
    approach_prep: Dict[str, Any],
    openai_client: Any,
    model: str,
) -> Optional[Dict[str, Any]]:
    """Return a sanitized Essentials section result, or ``None`` on failure."""
    if openai_client is None:
        return None
    started = time.monotonic()
    context = json.dumps(_context(identity, payload, approach_prep), ensure_ascii=False)[:12000]
    prompt = (
        f"Case context and optional reviewed material:\n{context}\n\n"
        "Use this material when useful and supplement it with established general "
        "orthopaedic knowledge. No question-bank content is included.\n\n"
        f"Return JSON with this schema:\n{json.dumps(RESPONSE_SCHEMA)}"
    )
    try:
        response = openai_client.chat.completions.create(
            model=model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        raw = json.loads(response.choices[0].message.content or "{}")
        result = _sanitize(raw)
    except Exception:
        return None
    if result is None:
        return None
    return {
        "payload": result,
        "duration_ms": int((time.monotonic() - started) * 1000),
    }
