"""
Lazy wrapper around procedure_registry.resolve_procedure.
Safe to import even when procedure_registry is unavailable.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, Optional

from caseprep.services.ttl_cache import (
    RESOLUTION_MISS_TTL_SECONDS,
    normalize_cache_key,
    resolution_cache,
)


def resolve_procedure_safe(prompt: str, openai_client: Optional[Any] = None) -> Dict[str, Any]:
    default = {
        "procedure_slug": None,
        "canonical_display_name": "",
        "match_method": "none",
        "match_score": 0.0,
        "confidence": 0.0,
        "suggested_matches": [],
    }
    cache_key = normalize_cache_key(prompt)
    if cache_key:
        cached = resolution_cache.get(cache_key)
        if cached is not None:
            return copy.deepcopy(cached)
    try:
        from procedure_registry import resolve_procedure

        resolved = resolve_procedure(prompt, openai_client) or default
    except Exception as exc:
        print(f"⚠️ procedure_resolver unavailable: {exc}")
        return {**default, "resolver_error": str(exc)}
    if cache_key:
        # Unresolved prompts get a short TTL so registry fixes surface quickly.
        ttl = None if resolved.get("procedure_slug") else RESOLUTION_MISS_TTL_SECONDS
        resolution_cache.set(cache_key, copy.deepcopy(resolved), ttl_seconds=ttl)
    return resolved


def is_resolver_available() -> bool:
    try:
        import procedure_registry  # noqa: F401

        return True
    except Exception:
        return False