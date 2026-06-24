#!/usr/bin/env python3
"""
Integration tests for versioned CasePrep (v1 isolation + v2 contract).

Run: python3 scripts/anatomy/test_caseprep_v2_integration.py
"""

from __future__ import annotations

import asyncio
import importlib
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

V1_FORBIDDEN_MODULES = (
    "procedure_registry",
    "approach_router",
    "hybrid_anatomy_builder",
    "anatomy_context_builder",
    "playbook_anatomy_builder",
    "anatomy_curator",
)

V2_ENVELOPE_KEYS = (
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


def _ok(name: str, cond: bool, detail: str = "") -> bool:
    if cond:
        print(f"PASS: {name}")
        return True
    print(f"FAIL: {name} {detail}")
    return False


def _assert_v2_envelope(data: Dict[str, Any], *, expect_fallback_reason: Optional[str] = None) -> List[str]:
    errors: List[str] = []
    for key in V2_ENVELOPE_KEYS:
        if key not in data:
            errors.append(f"missing {key}")
    if data.get("caseprep_version") != "v2":
        errors.append("caseprep_version != v2")
    if expect_fallback_reason and data.get("fallback_reason") != expect_fallback_reason:
        errors.append(f"fallback_reason expected {expect_fallback_reason}, got {data.get('fallback_reason')}")
    status = data.get("content_status")
    if status in ("fallback", "unsupported") and not data.get("user_visible_warning"):
        if data.get("fallback_reason") != "v2_disabled":
            errors.append("missing user_visible_warning on fallback/unsupported")
    return errors


def test_v1_module_import_isolation() -> bool:
    """v1 engine package must not statically depend on v2-only modules."""
    files = [
        ROOT / "caseprep" / "engines" / "v1_legacy.py",
        ROOT / "caseprep" / "services" / "ai_fallback.py",
        ROOT / "caseprep" / "services" / "rag_context.py",
        ROOT / "caseprep" / "schemas.py",
    ]
    combined = ""
    for f in files:
        combined += f.read_text(encoding="utf-8") + "\n"
    ok = True
    for mod in V1_FORBIDDEN_MODULES:
        if f"import {mod}" in combined or f"from {mod}" in combined:
            ok = False
            print(f"  found forbidden import: {mod}")
    return _ok("v1 module import isolation (static)", ok)


def test_v1_legacy_top_level_fields() -> bool:
    from caseprep.config import CasePrepConfig
    from caseprep.engines import v1_legacy

    async def _run():
        return await v1_legacy.run_caseprep_v1(
            "THA tomorrow",
            catalog=[],
            openai_client=None,
        )

    try:
        result = asyncio.run(_run())
    except Exception as exc:
        # RAG/GPT may fail without keys; still check envelope if partial
        return _ok("v1 legacy top-level fields", False, str(exc))

    has_fields = all(k in result for k in ("pimpQuestions", "otherUsefulFacts", "anatomy"))
    is_v1 = result.get("caseprep_version") == "v1"
    return _ok("v1 legacy top-level fields", has_fields and is_v1, str(list(result.keys())[:12]))


def test_v1_survives_missing_curated_store() -> bool:
    """v1 must not require data/anatomy."""
    import caseprep.services.curated_content_store as store

    fake_path = ROOT / "data" / "anatomy" / "__nonexistent_test_path__" / "payloads.jsonl"
    with patch.object(store, "CERTIFIED_PAYLOADS_PATH", fake_path):
        store.reset_store_cache()
        store._load_store()
        from caseprep.engines import v1_legacy

        async def _run():
            return await v1_legacy.run_caseprep_v1("test case", catalog=[], openai_client=None)

        try:
            result = asyncio.run(_run())
            ok = result.get("caseprep_version") == "v1"
        except Exception as exc:
            ok = False
            print(f"  exception: {exc}")
    store.reset_store_cache()
    return _ok("v1 survives missing curated store", ok)


def test_route_v1_default() -> bool:
    os.environ.pop("CASEPREP_DEFAULT_VERSION", None)
    os.environ["ENABLE_CASEPREP_V2"] = "true"  # v1 route must still be v1
    importlib.reload(importlib.import_module("caseprep.config"))

    from fastapi.testclient import TestClient
    import main

    client = TestClient(main.app)
    resp = client.post("/case-prep", json={"prompt": "THA"})
    data = resp.json()
    return _ok(
        "/case-prep defaults to v1 even when v2 enabled",
        data.get("caseprep_version") == "v1" and data.get("engine") == "legacy_rag_gpt",
        str(data.get("caseprep_version")),
    )


def test_v2_disabled_route() -> bool:
    os.environ["ENABLE_CASEPREP_V2"] = "false"
    from fastapi.testclient import TestClient
    import main

    client = TestClient(main.app)
    resp = client.post("/case-prep/v2", json={"prompt": "posterior THA tomorrow"})
    data = resp.json()
    errs = _assert_v2_envelope(data, expect_fallback_reason="ENABLE_CASEPREP_V2 is false")
    ok = (
        not errs
        and data.get("content_status") == "unsupported"
        and data.get("user_visible_warning")
        and data.get("ai_used") is False
    )
    if errs:
        print("  envelope errors:", errs)
    return _ok("v2 disabled controlled response", ok)


def test_v2_certified_tha() -> bool:
    os.environ["ENABLE_CASEPREP_V2"] = "true"
    os.environ["ENABLE_CASEPREP_V2_AI_FALLBACK"] = "false"
    os.environ["ENABLE_CASEPREP_V2_RAG_FALLBACK"] = "false"

    from caseprep.config import CasePrepConfig
    from caseprep.engines import v2_curated
    from caseprep.services import curated_content_store

    curated_content_store.reset_store_cache()
    import main

    cfg = CasePrepConfig.from_env()

    async def _run():
        return await v2_curated.run_caseprep_v2(
            "posterior THA tomorrow",
            catalog=main.CATALOG,
            openai_client=main.OPENAI_CLIENT,
            config=cfg,
        )

    data = asyncio.run(_run())
    errs = _assert_v2_envelope(data)
    certified = data.get("brobot_case_prep") or {}
    pimp = data.get("pimpQuestions") or []
    attending = certified.get("attending_pimp_questions") or []
    ok = (
        not errs
        and data.get("procedure_slug") == "tha_posterior"
        and data.get("content_status") == "certified"
        and data.get("ai_used") is False
        and data.get("rag_used") is False
        and len(pimp) > 0
        and len(attending) > 0
        and pimp[0] == attending[0]
    )
    if errs:
        print("  envelope errors:", errs)
    return _ok("v2 certified posterior THA", ok, f"slug={data.get('procedure_slug')} ai={data.get('ai_used')}")


def test_v2_unsupported_no_ai_fallback() -> bool:
    os.environ["ENABLE_CASEPREP_V2"] = "true"
    os.environ["ENABLE_CASEPREP_V2_AI_FALLBACK"] = "false"
    os.environ["ENABLE_CASEPREP_V2_RAG_FALLBACK"] = "false"

    from caseprep.config import CasePrepConfig
    from caseprep.engines import v2_curated
    import main

    cfg = CasePrepConfig.from_env()
    prompt = "prep me for trigger finger release"

    async def _run():
        return await v2_curated.run_caseprep_v2(
            prompt,
            catalog=main.CATALOG,
            openai_client=main.OPENAI_CLIENT,
            config=cfg,
        )

    data = asyncio.run(_run())
    errs = _assert_v2_envelope(data)
    ai = data.get("ai_used")
    ai_list = ai if isinstance(ai, list) else []
    gpt_steps = [s for s in ai_list if s in ("snippet_filter", "snippet_reformat", "anatomy_pipeline")]
    ok = (
        not errs
        and data.get("content_status") == "fallback"
        and data.get("fallback_reason") == "no_certified_payload"
        and not gpt_steps
        and data.get("user_visible_warning")
    )
    if errs:
        print("  envelope errors:", errs)
    return _ok("v2 non-certified fallback without AI", ok, f"ai_used={ai}")


def test_v2_unresolved_unsupported() -> bool:
    os.environ["ENABLE_CASEPREP_V2"] = "true"
    os.environ["ENABLE_CASEPREP_V2_AI_FALLBACK"] = "false"
    os.environ["ENABLE_CASEPREP_V2_RAG_FALLBACK"] = "false"

    from caseprep.config import CasePrepConfig
    from caseprep.engines import v2_curated
    import main

    cfg = CasePrepConfig.from_env()
    prompt = "prep me for something weird with no matching procedure name xyz"

    async def _run():
        return await v2_curated.run_caseprep_v2(
            prompt,
            catalog=main.CATALOG,
            openai_client=None,
            config=cfg,
        )

    data = asyncio.run(_run())
    errs = _assert_v2_envelope(data)
    ok = (
        not errs
        and data.get("content_status") == "unsupported"
        and data.get("procedure_slug") is None
        and data.get("fallback_reason") == "procedure_unresolved"
    )
    return _ok("v2 unresolved unsupported metadata", ok)


def main() -> int:
    print("=== CasePrep v1/v2 Integration Tests ===\n")
    tests = [
        test_v1_module_import_isolation,
        test_v1_survives_missing_curated_store,
        test_v1_legacy_top_level_fields,
        test_route_v1_default,
        test_v2_disabled_route,
        test_v2_certified_tha,
        test_v2_unsupported_no_ai_fallback,
        test_v2_unresolved_unsupported,
    ]
    passed = sum(1 for t in tests if t())
    failed = len(tests) - passed
    print(f"\n=== RESULTS: {passed} passed, {failed} failed ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())