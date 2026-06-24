"""
CasePrep version flags and runtime configuration.

v1 remains the production default. v2 is opt-in via route or env.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")


BASE_DIR = Path(__file__).resolve().parents[1]
ANATOMY_ROOT = BASE_DIR / "data" / "anatomy"
CERTIFIED_PAYLOADS_PATH = ANATOMY_ROOT / "case_prep" / "certified_case_prep_payloads.jsonl"
CASE_PREP_ROUTER_PATH = ANATOMY_ROOT / "case_prep" / "case_prep_router.json"

APPROACH_CATALOG_PATHS: List[str] = [
    os.getenv(
        "UPPER_APPROACH_CATALOG_PATH",
        str(BASE_DIR / "data" / "upper_extremity" / "approaches" / "upper_extremity_approaches.jsonl"),
    ),
    os.getenv(
        "LOWER_APPROACH_CATALOG_PATH",
        str(BASE_DIR / "data" / "lower_extremity" / "approaches" / "lower_extremity_approaches.jsonl"),
    ),
]


@dataclass(frozen=True)
class CasePrepConfig:
    default_version: str
    enable_v2: bool
    enable_v2_ai_fallback: bool
    enable_v2_rag_fallback: bool

    @classmethod
    def from_env(cls) -> "CasePrepConfig":
        default = (os.getenv("CASEPREP_DEFAULT_VERSION", "v1") or "v1").lower().strip()
        if default not in ("v1", "v2"):
            default = "v1"
        return cls(
            default_version=default,
            enable_v2=_env_bool("ENABLE_CASEPREP_V2", False),
            enable_v2_ai_fallback=_env_bool("ENABLE_CASEPREP_V2_AI_FALLBACK", False),
            enable_v2_rag_fallback=_env_bool("ENABLE_CASEPREP_V2_RAG_FALLBACK", True),
        )


def rag_dependencies_available() -> bool:
    """Pinecone RAG path requires API keys and index name at import/runtime."""
    return bool(
        os.getenv("OPENAI_API_KEY")
        and os.getenv("PINECONE_API_KEY")
        and os.getenv("PINECONE_INDEX")
    )