"""
Request/response helpers for versioned CasePrep engines.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class CasePrepRequest(BaseModel):
    prompt: str
    version: Optional[str] = Field(
        default=None,
        description="Optional engine version override: v1 | v2 (route /case-prep/v2 is preferred).",
    )


AiUsed = Union[bool, List[str]]


def build_envelope(
    *,
    caseprep_version: str,
    engine: str,
    content_status: str,
    body: Dict[str, Any],
    procedure_slug: Optional[str] = None,
    match_method: Optional[str] = None,
    ai_used: AiUsed = False,
    rag_used: bool = False,
    warnings: Optional[List[str]] = None,
    fallback_reason: Optional[str] = None,
    user_visible_warning: Optional[str] = None,
    backward_compat: bool = True,
) -> Dict[str, Any]:
    """
    Stable envelope + optional top-level legacy fields for v1 consumers.
    """
    envelope: Dict[str, Any] = {
        "caseprep_version": caseprep_version,
        "engine": engine,
        "procedure_slug": procedure_slug,
        "content_status": content_status,
        "match_method": match_method if match_method is not None else "none",
        "ai_used": ai_used,
        "rag_used": rag_used,
        "warnings": warnings or [],
        "payload": body,
    }
    if fallback_reason:
        envelope["fallback_reason"] = fallback_reason
    if user_visible_warning:
        envelope["user_visible_warning"] = user_visible_warning

    if backward_compat:
        # Spread legacy body keys at top level (pimpQuestions, otherUsefulFacts, anatomy, etc.)
        out = {**body, **envelope}
        return out

    return envelope


def empty_prompt_response(version: str, engine: str) -> Dict[str, Any]:
    body = {
        "pimpQuestions": [],
        "otherUsefulFacts": ["❌ No prompt provided"],
        "anatomy": None,
    }
    return build_envelope(
        caseprep_version=version,
        engine=engine,
        content_status="unsupported",
        body=body,
        match_method="none",
        warnings=["No prompt provided"],
        user_visible_warning="No prompt provided",
        fallback_reason="empty_prompt",
        backward_compat=True,
    )


V2_REQUIRED_ENVELOPE_KEYS = (
    "caseprep_version",
    "engine",
    "procedure_slug",
    "content_status",
    "match_method",
    "ai_used",
    "rag_used",
    "warnings",
    "payload",
)


def assert_v2_envelope(data: Dict[str, Any]) -> List[str]:
    """Return list of missing/invalid envelope fields for v2 contract checks."""
    errors: List[str] = []
    for key in V2_REQUIRED_ENVELOPE_KEYS:
        if key not in data:
            errors.append(f"missing key: {key}")
    if data.get("caseprep_version") != "v2":
        errors.append("caseprep_version must be v2")
    status = data.get("content_status")
    if status in ("fallback", "unsupported") and not data.get("user_visible_warning"):
        if status == "unsupported" and data.get("fallback_reason") == "v2_disabled":
            pass  # disabled responses always set user_visible_warning in engine
        elif not data.get("fallback_reason"):
            errors.append("fallback/unsupported should include fallback_reason or user_visible_warning")
    if status == "fallback" and not data.get("fallback_reason"):
        errors.append("fallback content_status requires fallback_reason")
    return errors