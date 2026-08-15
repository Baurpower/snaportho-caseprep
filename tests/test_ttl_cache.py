from __future__ import annotations

import unittest
from unittest import mock

from caseprep.services import procedure_resolver
from caseprep.services.ttl_cache import TtlCache, resolution_cache


class TtlCacheTests(unittest.TestCase):
    def test_get_set_roundtrip(self) -> None:
        cache = TtlCache(max_size=4, ttl_seconds=60)
        cache.set("a", {"value": 1})
        self.assertEqual(cache.get("a"), {"value": 1})
        self.assertIsNone(cache.get("missing"))

    def test_ttl_expiry(self) -> None:
        cache = TtlCache(max_size=4, ttl_seconds=60)
        with mock.patch("caseprep.services.ttl_cache.time.monotonic", side_effect=[0.0, 61.0]):
            cache.set("a", 1)
            self.assertIsNone(cache.get("a"))

    def test_lru_eviction(self) -> None:
        cache = TtlCache(max_size=2, ttl_seconds=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.get("a")  # refresh a
        cache.set("c", 3)  # evicts b
        self.assertEqual(cache.get("a"), 1)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("c"), 3)

    def test_invalidate_and_clear(self) -> None:
        cache = TtlCache(max_size=4, ttl_seconds=60)
        cache.set("a", 1)
        cache.invalidate("a")
        self.assertIsNone(cache.get("a"))
        cache.set("b", 2)
        cache.clear()
        self.assertIsNone(cache.get("b"))


class ResolverCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        resolution_cache.clear()

    def tearDown(self) -> None:
        resolution_cache.clear()

    def test_resolved_prompt_is_cached(self) -> None:
        resolved = {"procedure_slug": "trigger_finger_release", "match_method": "alias"}
        with mock.patch("procedure_registry.resolve_procedure", return_value=dict(resolved)) as fn:
            first = procedure_resolver.resolve_procedure_safe("Trigger Thumb Release")
            second = procedure_resolver.resolve_procedure_safe("  trigger thumb   RELEASE ")
        self.assertEqual(fn.call_count, 1)
        self.assertEqual(first["procedure_slug"], "trigger_finger_release")
        self.assertEqual(second["procedure_slug"], "trigger_finger_release")

    def test_cached_result_is_isolated_copy(self) -> None:
        resolved = {"procedure_slug": "x", "suggested_matches": []}
        with mock.patch("procedure_registry.resolve_procedure", return_value=dict(resolved)):
            first = procedure_resolver.resolve_procedure_safe("prompt")
            first["procedure_slug"] = "mutated"
            second = procedure_resolver.resolve_procedure_safe("prompt")
        self.assertEqual(second["procedure_slug"], "x")

    def test_unresolved_uses_short_ttl(self) -> None:
        resolved = {"procedure_slug": None, "match_method": "none"}
        with mock.patch("procedure_registry.resolve_procedure", return_value=dict(resolved)):
            with mock.patch.object(resolution_cache, "set") as set_mock:
                procedure_resolver.resolve_procedure_safe("mystery case")
        self.assertEqual(
            set_mock.call_args.kwargs.get("ttl_seconds"),
            procedure_resolver.RESOLUTION_MISS_TTL_SECONDS,
        )


class RetrievalCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        from caseprep.services.ttl_cache import retrieval_cache

        retrieval_cache.clear()

    def test_retrieval_cache_hit_skips_pinecone(self) -> None:
        from caseprep.services.rag_retrieval import retrieve_case_qas

        match = {
            "id": "vec-1",
            "score": 0.9,
            "metadata": {
                "question": "What is the A1 pulley?",
                "answer": "The first annular pulley over the MCP joint.",
                "source_collection": "pocket_pimped",
                "content_type": "qa",
                "procedures": ["trigger_finger_release"],
            },
        }
        index = mock.Mock()
        index.query.return_value = {"matches": [match]}
        refined = {"search_text": "trigger finger release", "procedures": ["trigger_finger_release"]}

        diagnostics_first: dict = {}
        first = retrieve_case_qas(
            refined,
            embed_fn=lambda text: [0.0],
            index_obj=index,
            diagnostics=diagnostics_first,
        )
        calls_after_first = index.query.call_count
        self.assertGreater(calls_after_first, 0)
        self.assertFalse(diagnostics_first["cache_hit"])

        diagnostics_second: dict = {}
        second = retrieve_case_qas(
            refined,
            embed_fn=lambda text: [0.0],
            index_obj=index,
            diagnostics=diagnostics_second,
        )
        self.assertEqual(index.query.call_count, calls_after_first)
        self.assertTrue(diagnostics_second["cache_hit"])
        self.assertEqual(
            [item["record_id"] for item in first],
            [item["record_id"] for item in second],
        )


if __name__ == "__main__":
    unittest.main()
