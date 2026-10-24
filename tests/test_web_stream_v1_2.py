from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from caseprep.engines.v1_2_web_stream import (
    evaluate_packet_coverage,
    stream_caseprep_packet_v1_2,
)
from caseprep.schemas_v1_1_packet import sse_event


def decode(frame: bytes):
    lines = frame.decode().splitlines()
    name = next(line[6:].strip() for line in lines if line.startswith("event:"))
    data = json.loads(next(line[5:].strip() for line in lines if line.startswith("data:")))
    return name, data


async def upstream(*_args, **_kwargs):
    yield sse_event("meta", {"packet_id": "p1", "caseprep_version": "v1.1", "engine": "old", "stream_protocol_version": 1})
    yield sse_event("header", {
        "case": {"requested_case": "distal radius ORIF", "canonical_slug": "distal_radius_orif", "canonical_name": "Distal Radius ORIF"},
        "header": {"display_name": "Distal Radius ORIF", "certified": False, "procedure_type": "fracture_fixation"},
    })
    yield sse_event("section", {"section_id": "pimp_questions", "status": "complete", "source": "mixed", "items": [
        {"id": "rag", "question": "What is at risk?", "answer": "Median nerve", "source": "rag", "source_ids": ["source-1"], "generated": False},
        {"id": "ai", "question": "Generic question?", "answer": "Generic answer", "source": "generated", "source_ids": [], "generated": True},
    ]})
    yield sse_event("section", {"section_id": "operative_flow", "status": "complete", "source": "generated", "items": [
        {"id": "unsafe", "question": "Step", "answer": "Invented step", "generated": True}
    ]})
    yield sse_event("done", {"pipeline_status": {}, "timing": {}, "warnings": []})


class WebStreamV12Tests(unittest.IsolatedAsyncioTestCase):
    async def test_emits_v12_contract_and_removes_generated_competitors(self):
        with patch("caseprep.engines.v1_2_web_stream.stream_caseprep_packet", upstream):
            events = [decode(frame) async for frame in stream_caseprep_packet_v1_2(
                "distal radius ORIF", openai_client=None, config=None
            )]

        self.assertEqual(events[0][1]["caseprep_version"], "v1.2")
        self.assertEqual(events[1][0], "resolution")
        sections = [data for name, data in events if name == "section"]
        self.assertEqual([item["id"] for item in sections[0]["items"]], ["rag"])
        self.assertEqual(sections[0]["items"][0]["provenance"], "rag")
        self.assertNotIn("operative_flow", [section["section_id"] for section in sections])
        done = [data for name, data in events if name == "done"][0]
        self.assertEqual(done["coverage_status"], "grounded_partial")
        self.assertEqual(done["generated_count"], 0)

    async def test_contradictory_modifier_requires_clarification(self):
        with patch("caseprep.engines.v1_2_web_stream.stream_caseprep_packet", upstream):
            events = [decode(frame) async for frame in stream_caseprep_packet_v1_2(
                "laparoscopic distal radius ORIF", openai_client=None, config=None
            )]
        self.assertIn("clarification", [name for name, _ in events])
        self.assertFalse(any(name == "section" for name, _ in events))
        self.assertEqual(events[-1][1]["quality_gate"], "withheld")

    async def test_fracture_prompt_is_useful_without_terminal_clarification(self):
        with patch("caseprep.engines.v1_2_web_stream.stream_caseprep_packet", upstream):
            events = [decode(frame) async for frame in stream_caseprep_packet_v1_2(
                "distal radius fracture", openai_client=None, config=None
            )]
        self.assertNotIn("clarification", [name for name, _ in events])
        self.assertIn("section", [name for name, _ in events])


def _pimp_item(index: int) -> dict:
    return {
        "id": f"pimp-{index}",
        "question": f"Question {index}?",
        "answer": f"Answer {index}",
        "source": "rag",
        "source_ids": [f"src-{index}"],
        "generated": False,
        "procedure_relevance": "direct",
        "grounded_count": 1,
    }


class PacketCoverageGateTests(unittest.TestCase):
    def test_v13_requires_verified_brief_even_with_full_quiz_and_anatomy(self):
        sections = {
            "pimp_questions": {"items": [_pimp_item(i) for i in range(8)], "grounded_count": 8, "citation_count": 8},
            "anatomy": {"items": [{"answer": "Sourced anatomy"}], "grounded_count": 1, "citation_count": 1},
        }
        def coverage():
            return evaluate_packet_coverage(canonical_slug="tka", certified=False,
                emitted_sections=sections, expected_sections=("essentials", "anatomy", "pimp_questions"))
        self.assertEqual(coverage()["quality_gate"], "limited")
        sections["essentials"] = {"source": "grounded_fallback", "payload": {"verification": {"passed": True}}}
        self.assertEqual(coverage()["quality_gate"], "limited")
        sections["essentials"] = {"source": "grounded_synthesis", "payload": {"verification": {"passed": True}}}
        self.assertEqual(coverage()["quality_gate"], "passed")

    def test_pimp_only_packet_is_limited_even_with_eight_direct_questions(self):
        pimp_items = [_pimp_item(index) for index in range(11)]
        summary = evaluate_packet_coverage(
            canonical_slug="intertrochanteric_hip_fracture_orif",
            certified=False,
            emitted_sections={
                "pimp_questions": {
                    "items": pimp_items,
                    "grounded_count": 11,
                    "generated_count": 0,
                    "citation_count": 11,
                }
            },
            expected_sections=("anatomy", "operative_flow", "pimp_questions"),
        )
        self.assertEqual(summary["coverage_status"], "grounded_partial")
        self.assertEqual(summary["quality_gate"], "limited")
        self.assertFalse(summary["has_clinical_body"])

    def test_unresolved_slug_cannot_pass(self):
        pimp_items = [_pimp_item(index) for index in range(15)]
        summary = evaluate_packet_coverage(
            canonical_slug=None,
            certified=False,
            emitted_sections={
                "pimp_questions": {
                    "items": pimp_items,
                    "grounded_count": 15,
                    "generated_count": 0,
                    "citation_count": 15,
                },
                "anatomy": {
                    "items": [{"id": "a1", "question": "Nerve?", "answer": "Radial"}],
                    "grounded_count": 1,
                    "generated_count": 0,
                    "citation_count": 1,
                },
            },
            expected_sections=("anatomy", "pimp_questions"),
        )
        self.assertEqual(summary["coverage_status"], "grounded_partial")
        self.assertEqual(summary["quality_gate"], "limited")

    def test_grounded_packet_with_anatomy_and_direct_pimp_passes(self):
        pimp_items = [_pimp_item(index) for index in range(8)]
        summary = evaluate_packet_coverage(
            canonical_slug="humeral_shaft_fracture_orif",
            certified=False,
            emitted_sections={
                "pimp_questions": {
                    "items": pimp_items,
                    "grounded_count": 8,
                    "generated_count": 0,
                    "citation_count": 8,
                },
                "anatomy": {
                    "items": [{"id": "a1", "question": "Nerve?", "answer": "Radial nerve"}],
                    "grounded_count": 1,
                    "generated_count": 0,
                    "citation_count": 1,
                },
            },
            expected_sections=("anatomy", "pimp_questions"),
        )
        self.assertEqual(summary["coverage_status"], "grounded_complete")
        self.assertEqual(summary["quality_gate"], "passed")
        self.assertTrue(summary["has_clinical_body"])

    def test_approach_detail_counts_as_clinical_body(self):
        pimp_items = [_pimp_item(index) for index in range(8)]
        summary = evaluate_packet_coverage(
            canonical_slug="clavicle_fracture_orif",
            certified=False,
            emitted_sections={
                "pimp_questions": {
                    "items": pimp_items,
                    "grounded_count": 8,
                    "generated_count": 0,
                    "citation_count": 8,
                },
                "approach_safety": {
                    "items": [{"id": "s1", "question": "At risk", "answer": "Supraclavicular nerves"}],
                    "grounded_count": 1,
                    "generated_count": 0,
                    "citation_count": 1,
                },
            },
            expected_sections=("approach_safety", "pimp_questions"),
        )
        self.assertEqual(summary["quality_gate"], "passed")


if __name__ == "__main__":
    unittest.main()
