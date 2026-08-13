from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from caseprep.engines.v1_2_web_stream import stream_caseprep_packet_v1_2
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


if __name__ == "__main__":
    unittest.main()
