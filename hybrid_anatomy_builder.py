"""
Hybrid Anatomy Builder (Phase 4 / hybrid fix).

Combines:
- Legacy approach catalog output (approachSelection + anatomyQuiz from anatomy_gpt.py)
- Miller Gold RAG output (source-backed facts from context_builder / retrievers)

Goal:
- Never drop useful approach logic when Miller is enabled.
- Keep strict separation: GPT approach content stays in legacy fields; Miller facts stay source-backed.
- Provide clear provenance via anatomySystem.
- Graceful degradation on partial failures.

Public function:
    build_hybrid_anatomy(legacy_anatomy: dict | None, miller_anatomy: dict | None) -> dict

The returned dict is the new stable hybrid anatomy payload for /case-prep and /anatomy.
"""

from typing import Any, Dict, Optional
import os

def _get_strict_mode() -> bool:
    val = os.getenv("ANATOMY_STRICT_SOURCE_MODE", "true").lower()
    return val in ("1", "true", "yes", "on")

def _safe_dict(d: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return d or {}

def _extract_miller_core(miller: Dict[str, Any]) -> Dict[str, Any]:
    """Pull the source-backed Miller parts, tolerant of current builder shapes."""
    if not miller:
        return {
            "relevantAnatomy": [],
            "structuresAtRisk": [],
            "approachLandmarks": [],
            "highYieldFacts": [],
            "sources": [],
            "retrievalSummary": {
                "chunksUsed": 0,
                "mode": "unavailable",
                "limited": True,
                "regions": [],
                "warning": "Miller retrieval unavailable",
            },
        }

    # Support both flat (old builder) and grouped forms
    core = {
        "relevantAnatomy": miller.get("relevantAnatomy") or miller.get("sourceBackedAnatomy", {}).get("relevantAnatomy", []),
        "structuresAtRisk": miller.get("structuresAtRisk") or miller.get("sourceBackedAnatomy", {}).get("structuresAtRisk", []),
        "approachLandmarks": miller.get("approachLandmarks") or miller.get("sourceBackedAnatomy", {}).get("approachLandmarks", []),
        "highYieldFacts": miller.get("highYieldFacts") or miller.get("sourceBackedAnatomy", {}).get("highYieldFacts", []),
        "sources": miller.get("sources") or miller.get("sourceBackedAnatomy", {}).get("sources", []),
        "retrievalSummary": miller.get("retrievalSummary") or miller.get("sourceBackedAnatomy", {}).get("retrievalSummary", {}),
    }

    # Ensure retrievalSummary has basics
    rs = core["retrievalSummary"] or {}
    core["retrievalSummary"] = {
        "chunksUsed": rs.get("chunksUsed", 0),
        "mode": rs.get("mode") or miller.get("retrievalMode", "miller_gold_local"),
        "limited": rs.get("limited", miller.get("limitedAnatomyContext", True)),
        "regions": rs.get("regions", []),
        "warning": rs.get("warning"),
    }

    return core

def build_hybrid_anatomy(
    legacy_anatomy: Optional[Dict[str, Any]],
    miller_anatomy: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Merge legacy approach system + Miller source-backed system into hybrid payload.

    Rules:
    - Legacy fields (approachSelection, anatomyQuiz, highYieldAnatomy) come only from legacy_anatomy.
    - Miller fields come only from miller_anatomy and stay source-backed.
    - If one subsystem fails, the other is still returned.
    - limitedAnatomyContext specifically refers to Miller source-backed context.
    - anatomySystem explains provenance.
    """
    legacy = _safe_dict(legacy_anatomy)
    miller = _safe_dict(miller_anatomy)

    miller_core = _extract_miller_core(miller)

    limited_miller = miller.get("limitedAnatomyContext", True) if miller else True
    retrieval_mode = miller.get("retrievalMode", "miller_gold_local") if miller else "unavailable"

    if retrieval_mode == "not_run_unsupported_case":
        approach_logic = "unsupported_case_no_approach_guessing"
        warning = (miller.get("anatomySystem", {}) or {}).get("warning") or (
            "This procedure is not yet mapped to a curated approach, so BroBot did not "
            "guess approach anatomy or run specific Miller retrieval."
        )
    else:
        approach_logic = "legacy_catalog_gpt" if legacy.get("approachSelection") else "unavailable"
        warning = (
            "Approach quiz/selection generated from curated approach catalog + GPT. "
            "Miller facts are strictly source-backed to the gold corpus and include page citations. "
            "The two systems are complementary."
        )
        if not legacy.get("approachSelection") and limited_miller:
            warning += " Both approach logic and Miller retrieval were limited for this case."

    hybrid: Dict[str, Any] = {
        "approachSelection": legacy.get("approachSelection"),
        "anatomyQuiz": legacy.get("anatomyQuiz"),
        "highYieldAnatomy": legacy.get("highYieldAnatomy"),
        "retrievalMode": retrieval_mode,
        "limitedAnatomyContext": limited_miller,
        "sourceBackedAnatomy": {
            "relevantAnatomy": miller_core["relevantAnatomy"],
            "structuresAtRisk": miller_core["structuresAtRisk"],
            "approachLandmarks": miller_core["approachLandmarks"],
            "highYieldFacts": miller_core["highYieldFacts"],
            "sources": miller_core["sources"],
            "retrievalSummary": miller_core["retrievalSummary"],
        },
        "relevantAnatomy": miller_core["relevantAnatomy"],
        "structuresAtRisk": miller_core["structuresAtRisk"],
        "approachLandmarks": miller_core["approachLandmarks"],
        "highYieldFacts": miller_core["highYieldFacts"],
        "sources": miller_core["sources"],
        "retrievalSummary": miller_core["retrievalSummary"],
        "anatomySystem": {
            "approachLogic": approach_logic,
            "sourceBackedFacts": retrieval_mode,
            "strictSourceMode": _get_strict_mode(),
            "warning": warning,
        },
    }

    # If Miller was weak but we have good approach data, do not poison the whole anatomy object.
    # limitedAnatomyContext already reflects Miller only (via miller_core).
    # We can add a top-level note only if both systems are degraded.
    if not legacy.get("approachSelection") and limited_miller and retrieval_mode != "not_run_unsupported_case":
        hybrid["anatomySystem"]["warning"] = (
            hybrid["anatomySystem"]["warning"]
            + " Both approach logic and Miller retrieval were limited for this case."
        )

    return hybrid

def build_limited_hybrid(reason: str) -> Dict[str, Any]:
    """Safe fallback when both systems are unavailable."""
    return {
        "approachSelection": None,
        "anatomyQuiz": None,
        "highYieldAnatomy": None,
        "retrievalMode": "error",
        "limitedAnatomyContext": True,
        "sourceBackedAnatomy": {
            "relevantAnatomy": [],
            "structuresAtRisk": [],
            "approachLandmarks": [],
            "highYieldFacts": [],
            "sources": [],
            "retrievalSummary": {
                "chunksUsed": 0,
                "mode": "error",
                "limited": True,
                "regions": [],
                "warning": reason,
            },
        },
        "relevantAnatomy": [],
        "structuresAtRisk": [],
        "approachLandmarks": [],
        "highYieldFacts": [],
        "sources": [],
        "retrievalSummary": {
            "chunksUsed": 0,
            "mode": "error",
            "limited": True,
            "regions": [],
            "warning": reason,
        },
        "anatomySystem": {
            "approachLogic": "error",
            "sourceBackedFacts": "error",
            "strictSourceMode": _get_strict_mode(),
            "warning": reason,
        },
    }
