import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from caseprep.config import CasePrepConfig
from caseprep.engines.v2_curated import run_caseprep_v2
from procedure_registry import resolve_procedure


class CarpalTunnelResolverTests(unittest.TestCase):
    def test_requested_phrases_preserve_approach_semantics(self):
        generic = resolve_procedure("carpal tunnel release")
        self.assertEqual(generic["procedure_slug"], "carpal_tunnel_release")
        self.assertTrue(generic["requires_clarification"])
        self.assertEqual(len(generic["suggested_matches"]), 2)

        for query in ("CTR", "carpal tunnel surgery"):
            result = resolve_procedure(query)
            self.assertEqual(result["procedure_slug"], "carpal_tunnel_release")
            self.assertTrue(result["requires_clarification"])

        opened = resolve_procedure("open carpal tunnel release")
        self.assertEqual(opened["entity_kind"], "approach")
        self.assertEqual(opened["requested_approach"], "open")
        self.assertFalse(opened["requires_clarification"])

        endoscopic = resolve_procedure("endoscopic carpal tunnel release")
        self.assertEqual(endoscopic["requested_approach"], "endoscopic")
        self.assertFalse(endoscopic["requires_clarification"])


class CarpalTunnelV2MissTests(unittest.TestCase):
    def test_partial_registry_record_is_never_curated(self):
        config = CasePrepConfig(
            default_version="v1",
            enable_v2=True,
            enable_v2_ai_fallback=False,
            enable_v2_rag_fallback=False,
        )
        with patch(
            "caseprep.engines.v2_curated.curated_content_store.get_certified_payload",
            return_value=None,
        ):
            response = asyncio.run(
                run_caseprep_v2(
                    "open carpal tunnel release",
                    catalog=[],
                    openai_client=None,
                    config=config,
                    event_context={"anonymous_session_id": "test-session"},
                )
            )
        normalized = response["case_prep"]
        self.assertEqual(normalized["canonical_slug"], "carpal_tunnel_release")
        self.assertEqual(normalized["source_type"], "unavailable")
        self.assertFalse(normalized["runtime_enabled"])
        self.assertIsNone(normalized["payload"])
        self.assertNotEqual(response["content_status"], "certified")

    def test_generic_request_requires_approach_clarification(self):
        config = CasePrepConfig("v1", True, False, False)
        response = asyncio.run(
            run_caseprep_v2(
                "carpal tunnel release",
                catalog=[],
                openai_client=None,
                config=config,
            )
        )
        self.assertEqual(
            response["fallback_reason"], "approach_clarification_required"
        )
        self.assertTrue(response["case_prep"]["requires_clarification"])


if __name__ == "__main__":
    unittest.main()
