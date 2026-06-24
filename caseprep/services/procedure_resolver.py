"""
Lazy wrapper around procedure_registry.resolve_procedure.
Safe to import even when procedure_registry is unavailable.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def resolve_procedure_safe(prompt: str, openai_client: Optional[Any] = None) -> Dict[str, Any]:
    default = {
        "procedure_slug": None,
        "canonical_display_name": "",
        "match_method": "none",
        "match_score": 0.0,
        "confidence": 0.0,
        "suggested_matches": [],
    }
    try:
        from procedure_registry import resolve_procedure

        return resolve_procedure(prompt, openai_client) or default
    except Exception as exc:
        print(f"⚠️ procedure_resolver unavailable: {exc}")
        return {**default, "resolver_error": str(exc)}


def is_resolver_available() -> bool:
    try:
        import procedure_registry  # noqa: F401

        return True
    except Exception:
        return False