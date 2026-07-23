from __future__ import annotations

import json
import unittest
from unittest import mock

from caseprep.services.enrichment_v1_1 import (
    EnrichmentResult,
    _sanitize,
    enrich_packet_sections,
)
from caseprep.services.ttl_cache import enrichment_cache

RAW_LLM_OUTPUT = {
    "pimp_pedagogy": [
        {
            "id": "attending:abc",
            "teaching_pearl": "Release the A1 pulley completely under direct vision.",
            "why_attendings_ask": "Tests understanding of the pulley system.",
            "common_mistake": "Stopping short of complete release.",
            "difficulty": "medium",
        }
    ],
    "generated_pimp_questions": [
        {
            "question": "Which pulley must be preserved to prevent bowstringing?",
            "answer": "The A2 pulley.",
            "teaching_pearl": "A2 and A4 are the critical pulleys.",
            "why_attendings_ask": "Classic anatomy trap.",
            "common_mistake": "Confusing A1 with A2.",
            "difficulty": "easy",
        }
    ],
    "teaching_topics": ["Pulley system anatomy"],
    "decision_points": [
        {"category": "when_to_operate", "question": "When do we operate?", "answer": "Failed conservative care."},
        {"category": "bogus_category", "question": "x", "answer": "y"},
    ],
    "evidence": [{"title": "Landmark RCT", "finding": "Splinting works early.", "why_it_matters": "Changes first-line care."}],
    "anatomy_gap_fill": [
        {"category": "sensory_innervation", "question": "Digital nerve position?", "answer": "Radial digital nerve crosses A1 in the thumb."}
    ],
    "operative_flow": [{"phase": "position", "step": "Supine, hand table, tourniquet."}],
    "pitfalls": ["Injury to the radial digital nerve."],
    "postop": ["Immediate motion; sutures out at 10-14 days."],
}


def make_client(payload_dict=None, content=None):
    message = mock.Mock()
    message.content = content if content is not None else json.dumps(payload_dict)
    choice = mock.Mock(message=message)
    response = mock.Mock(choices=[choice])
    client = mock.Mock()
    client.chat.completions.create.return_value = response
    return client


IDENTITY = {"canonical_name": "Trigger Finger Release", "canonical_slug": "trigger_finger_release"}


class SanitizeTests(unittest.TestCase):
    def test_invalid_rows_dropped(self) -> None:
        data = _sanitize(RAW_LLM_OUTPUT)
        self.assertEqual(len(data["decision_points"]), 1)
        self.assertEqual(data["decision_points"][0]["category"], "when_to_operate")

    def test_malformed_input_yields_empty_structures(self) -> None:
        data = _sanitize("not a dict")
        self.assertEqual(data["pimp_pedagogy"], {})
        self.assertEqual(data["generated_pimp_questions"], [])


class MergeRuleTests(unittest.TestCase):
    def _result(self, certified: bool) -> EnrichmentResult:
        return EnrichmentResult(_sanitize(RAW_LLM_OUTPUT), certified=certified)

    def test_pedagogy_annotates_only_empty_fields(self) -> None:
        curated_item = {
            "id": "attending:abc",
            "question": "How much of the A1 pulley do you release?",
            "answer": "The entire pulley.",
            "teaching_pearl": "CURATED PEARL — must not be replaced.",
            "confidence": 0.95,
            "generated": False,
        }
        items, paths = self._result(certified=True).apply_to_pimp_questions([curated_item])
        self.assertEqual(items[0]["teaching_pearl"], "CURATED PEARL — must not be replaced.")
        self.assertEqual(items[0]["why_attendings_ask"], "Tests understanding of the pulley system.")
        self.assertIn("items[0].why_attendings_ask", paths)
        self.assertNotIn("items[0].teaching_pearl", paths)

    def test_generated_questions_appended_and_marked(self) -> None:
        items, paths = self._result(certified=True).apply_to_pimp_questions([])
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["generated"])
        self.assertEqual(items[0]["source"], "generated")
        self.assertEqual(paths, ["items[0]"])

    def test_curated_section_items_never_removed(self) -> None:
        curated = [{"id": "x", "question": "Curated Q", "answer": "Curated A", "generated": False}]
        items, _ = self._result(certified=True).apply_to_section("decision_points", curated)
        self.assertEqual(items[0], curated[0])
        self.assertEqual(len(items), 2)
        self.assertTrue(items[1]["generated"])

    def test_certified_blocks_operative_flow_generation(self) -> None:
        items, paths = self._result(certified=True).apply_to_section("operative_flow", [])
        self.assertEqual(items, [])
        self.assertEqual(paths, [])

    def test_uncertified_allows_operative_flow_generation(self) -> None:
        items, _ = self._result(certified=False).apply_to_section("operative_flow", [])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["category"], "position")
        self.assertTrue(items[0]["generated"])


class CacheAndDegradationTests(unittest.TestCase):
    def setUp(self) -> None:
        enrichment_cache.clear()

    def tearDown(self) -> None:
        enrichment_cache.clear()

    def test_cache_hit_skips_openai(self) -> None:
        client = make_client(RAW_LLM_OUTPUT)
        first = enrich_packet_sections(
            "trigger_finger_release", None, identity=IDENTITY, openai_client=client
        )
        second = enrich_packet_sections(
            "trigger_finger_release", None, identity=IDENTITY, openai_client=client
        )
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(client.chat.completions.create.call_count, 1)

    def test_malformed_llm_json_degrades_to_none_and_not_cached(self) -> None:
        client = make_client(content="{not json")
        result = enrich_packet_sections(
            "trigger_finger_release", None, identity=IDENTITY, openai_client=client
        )
        self.assertIsNone(result)
        # A later good response must not be shadowed by a cached failure.
        good = enrich_packet_sections(
            "trigger_finger_release", None, identity=IDENTITY,
            openai_client=make_client(RAW_LLM_OUTPUT),
        )
        self.assertIsNotNone(good)

    def test_no_client_returns_none(self) -> None:
        self.assertIsNone(
            enrich_packet_sections(
                "trigger_finger_release", None, identity=IDENTITY, openai_client=None
            )
        )


if __name__ == "__main__":
    unittest.main()
