"""
Load and serve certified curated CasePrep payloads.

Priority:
  1. Per-procedure registry folders (data/caseprep/procedures/<slug>/certified_payload.json)
  2. Registry export JSONL (data/caseprep/certified_payloads_export.jsonl)
  3. Legacy flat JSONL (data/anatomy/case_prep/certified_case_prep_payloads.jsonl)

Missing registry never raises — v1 and disabled v2 remain safe.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from caseprep.config import (
    CASE_PREP_ROUTER_PATH,
    CERTIFIED_PAYLOADS_PATH,
)

BASE_DIR = Path(__file__).resolve().parents[2]
REGISTRY_PROCEDURES_ROOT = BASE_DIR / "data" / "caseprep" / "procedures"
REGISTRY_INDEX_PATH = BASE_DIR / "data" / "caseprep" / "registry_index.json"
REGISTRY_EXPORT_PATH = BASE_DIR / "data" / "caseprep" / "certified_payloads_export.jsonl"

_STORE: Optional[Dict[str, Dict[str, Any]]] = None
_SOURCE: str = "none"
_ROUTER: Optional[Dict[str, Any]] = None
_LOAD_ERROR: Optional[str] = None


def _manifest_allows_runtime(manifest: Dict[str, Any]) -> bool:
    return bool(
        manifest.get("runtime_enabled")
        and manifest.get("content_status") == "certified"
        and manifest.get("review_status") == "certified"
        and not manifest.get("deprecated")
    )


def _load_from_registry_folders() -> Dict[str, Dict[str, Any]]:
    store: Dict[str, Dict[str, Any]] = {}
    if not REGISTRY_PROCEDURES_ROOT.exists():
        return store

    for folder in sorted(REGISTRY_PROCEDURES_ROOT.iterdir()):
        if not folder.is_dir():
            continue
        manifest_path = folder / "manifest.json"
        payload_path = folder / "certified_payload.json"
        if not manifest_path.exists() or not payload_path.exists():
            continue
        try:
            with manifest_path.open("r", encoding="utf-8") as f:
                manifest = json.load(f)
            if not _manifest_allows_runtime(manifest):
                continue
            with payload_path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            slug = manifest.get("slug") or payload.get("procedure_id") or folder.name
            if slug:
                store[slug] = payload
        except Exception:
            continue
    return store


def _load_from_export_jsonl() -> Dict[str, Dict[str, Any]]:
    store: Dict[str, Dict[str, Any]] = {}
    if not REGISTRY_EXPORT_PATH.exists():
        return store
    try:
        with REGISTRY_EXPORT_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    pid = obj.get("procedure_id")
                    if pid:
                        store[pid] = obj
    except Exception:
        return {}
    return store


def _load_from_flat_jsonl() -> Dict[str, Dict[str, Any]]:
    store: Dict[str, Dict[str, Any]] = {}
    if not CERTIFIED_PAYLOADS_PATH.exists():
        return store
    with CERTIFIED_PAYLOADS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                pid = obj.get("procedure_id")
                if pid:
                    store[pid] = obj
    return store


def _load_store() -> Dict[str, Dict[str, Any]]:
    global _STORE, _SOURCE, _LOAD_ERROR
    if _STORE is not None:
        return _STORE

    _STORE = {}
    _LOAD_ERROR = None

    try:
        registry_store = _load_from_registry_folders()
        if registry_store:
            _STORE = registry_store
            _SOURCE = "registry"
            print(
                f"✅ curated_content_store: loaded {len(_STORE)} from registry folders"
            )
            return _STORE

        export_store = _load_from_export_jsonl()
        if export_store:
            _STORE = export_store
            _SOURCE = "registry_export"
            print(
                f"✅ curated_content_store: loaded {len(_STORE)} from certified_payloads_export.jsonl"
            )
            return _STORE

        if CERTIFIED_PAYLOADS_PATH.exists():
            _STORE = _load_from_flat_jsonl()
            _SOURCE = "flat_jsonl"
            print(
                f"✅ curated_content_store: loaded {len(_STORE)} from flat JSONL (fallback)"
            )
            return _STORE

        _LOAD_ERROR = "no certified payloads found (registry, export, or flat JSONL)"
        print(f"ℹ️ curated_content_store: {_LOAD_ERROR}")
    except Exception as exc:
        _LOAD_ERROR = str(exc)
        print(f"⚠️ curated_content_store load failed: {exc}")
        _STORE = {}

    return _STORE


def get_certified_payload(procedure_slug: str) -> Optional[Dict[str, Any]]:
    store = _load_store()
    return store.get(procedure_slug)


def certified_count() -> int:
    return len(_load_store())


def get_fallback_message() -> str:
    global _ROUTER
    if _ROUTER is None:
        if CASE_PREP_ROUTER_PATH.exists():
            try:
                with CASE_PREP_ROUTER_PATH.open("r", encoding="utf-8") as f:
                    _ROUTER = json.load(f)
            except Exception:
                _ROUTER = {}
        else:
            _ROUTER = {}
    return (
        _ROUTER.get("fallback_message")
        or "Anatomy case prep is still being improved for this procedure."
    )


def is_store_available() -> bool:
    _load_store()
    return _LOAD_ERROR is None and certified_count() > 0


def registry_available() -> bool:
    return REGISTRY_PROCEDURES_ROOT.exists() and any(
        p.is_dir() for p in REGISTRY_PROCEDURES_ROOT.iterdir()
    )


def store_status() -> Dict[str, Any]:
    _load_store()
    return {
        "available": is_store_available(),
        "certified_count": certified_count(),
        "source": _SOURCE,
        "registry_available": registry_available(),
        "registry_index_available": REGISTRY_INDEX_PATH.exists(),
        "registry_root": str(REGISTRY_PROCEDURES_ROOT),
        "flat_jsonl_path": str(CERTIFIED_PAYLOADS_PATH),
        "error": _LOAD_ERROR,
    }


def reset_store_cache() -> None:
    """Clear in-memory cache (for tests or hot-reload). Next access re-reads from disk."""
    global _STORE, _LOAD_ERROR, _ROUTER, _SOURCE
    _STORE = None
    _LOAD_ERROR = None
    _ROUTER = None
    _SOURCE = "none"