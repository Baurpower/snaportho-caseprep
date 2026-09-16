from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from caseprep.engines.v1_3_web_stream import stream_caseprep_packet_v1_3


def decode(frame: bytes):
    lines = frame.decode().splitlines()
    name = next(line[6:].strip() for line in lines if line.startswith("event:"))
    data = json.loads(next(line[5:].strip() for line in lines if line.startswith("data:")))
    return name, data


class WebStreamV13Tests(unittest.IsolatedAsyncioTestCase):
    async def test_tha_mobile_choice_round_trip(self):
        async def stream(prompt):
            with patch("caseprep.engines.v1_1_web_stream.retrieve_case_qas", return_value=[]):
                return [decode(frame) async for frame in stream_caseprep_packet_v1_3(
                    prompt, openai_client=None, config=None,
                )]

        events = await stream("total hip arthroplasty")
        header = next(data for name, data in events if name == "header")
        self.assertIn("Total Hip Arthroplasty", header["header"]["display_name"])
        decision = next(data["payload"] for name, data in events
                        if name == "section" and data.get("section_id") == "approach_decision")
        self.assertEqual(decision["status"], "selected")
        self.assertEqual(len(decision["approaches"]), 2)
        self.assertEqual(len(decision["selected_approach_ids"]), 1)
        for option in decision["approaches"]:
            with self.subTest(approach=option["name"]):
                selected = await stream(f"total hip arthroplasty; planned approach: {option['name']}")
                sections = {data["section_id"]: data for name, data in selected if name == "section"}
                self.assertEqual(sections["approach_decision"]["payload"]["selected_approach_ids"], [option["approach_id"]])
                for section_id in ("approach_quick_brief", "approach_exposure", "approach_safety", "approach_strategy"):
                    self.assertTrue(sections[section_id]["items"], section_id)
                    self.assertNotIn("hemiarthroplasty", json.dumps(sections[section_id]).lower())

    async def test_v13_combines_grounded_packet_rag_and_approach_content(self) -> None:
        resolved = {
            "procedure_slug": "tka",
            "canonical_display_name": "Total Knee Arthroplasty",
            "match_method": "exact",
            "confidence": 1.0,
            "requires_clarification": False,
        }
        rag_items = [
            {
                "record_id": f"rag-{index}",
                "question": f"Grounded question {index}?",
                "answer": f"Grounded answer {index}.",
                "source": "rag",
                "source_ids": [f"source-{index}"],
                "retrieval_score": 0.9,
                "vector_score": 0.9,
                "procedure_relevance": "direct",
                "claim_support": "direct",
            }
            for index in range(8)
        ]
        grounded_packet = {
            "case_prep_status": "certified",
            "review": {"status": "agent_reviewed", "label": "Agent reviewed"},
            "procedure_overview": "Grounded TKA overview.",
            "must_know_anatomy": ["Protect the relevant neurovascular structures."],
            "common_mistakes": ["Avoid unsupported component positioning."],
            "attending_pimp_questions": [],
            "source_urls": ["https://example.test/tka"],
        }
        essentials = {
            "payload": {
                "indications": {"summary": "End-stage symptomatic arthritis.", "key_points": [], "case_specific_note": None},
                "critical_portion": {
                    "name": "Balanced reconstruction", "summary": "Restore alignment and balance.",
                    "why_it_matters": "It drives stability.", "execution_points": [],
                    "failure_mode": "Instability.",
                },
                "postop_protocol": {
                    "summary": "Mobilize with appropriate prophylaxis.", "immediate_priorities": [],
                    "immobilization": None, "weight_bearing": "As tolerated", "motion": "Early motion",
                    "follow_up": "Routine wound review", "red_flags": [],
                    "variability_note": "Confirm surgeon preference.",
                },
            },
            "duration_ms": 10,
        }

        with patch(
            "caseprep.engines.v1_1_web_stream.procedure_resolver.resolve_procedure_safe",
            return_value=resolved,
        ), patch(
            "caseprep.engines.v1_1_web_stream.ai_fallback.refine_prompt",
            return_value={"search_text": "TKA", "procedures": ["tka"]},
        ), patch(
            "caseprep.engines.v1_1_web_stream.retrieve_case_qas",
            return_value=rag_items,
        ), patch(
            "caseprep.engines.v1_1_web_stream.curated_content_store.get_certified_payload",
            return_value=grounded_packet,
        ) as packet_loader, patch(
            "caseprep.services.essentials_v1_3.generate_essentials",
            return_value=essentials,
        ):
            events = [
                decode(frame)
                async for frame in stream_caseprep_packet_v1_3(
                    "TKA", openai_client=None, config=None
                )
            ]

        packet_loader.assert_called_once_with("tka")
        meta = events[0][1]
        self.assertEqual(meta["caseprep_version"], "v1.3")
        self.assertEqual(meta["engine"], "rag_approach_packet_stream")
        header = next(data for name, data in events if name == "header")
        self.assertTrue(header["header"]["certified"])
        section_ids = [data.get("section_id") for name, data in events if name == "section"]
        self.assertIn("essentials", section_ids)
        self.assertNotIn("summary", section_ids)
        self.assertNotIn("key_takeaways", section_ids)
        self.assertNotIn("top_things_to_know", section_ids)
        questions = next(
            data for name, data in events
            if name == "section" and data.get("section_id") == "pimp_questions"
        )
        self.assertTrue(questions["items"])
        self.assertTrue(all(item["provenance"] == "rag" for item in questions["items"]))

    async def test_rag_policy_does_not_run_ai_enrichment(self) -> None:
        resolved = {
            "procedure_slug": "tka",
            "canonical_display_name": "Total Knee Arthroplasty",
            "match_method": "exact",
            "confidence": 1.0,
            "requires_clarification": False,
        }
        config = SimpleNamespace(
            enable_v1_1_dedup=False,
            enable_v1_1_enrichment=True,
            v1_1_model="unused",
        )
        with patch(
            "caseprep.engines.v1_1_web_stream.procedure_resolver.resolve_procedure_safe",
            return_value=resolved,
        ), patch(
            "caseprep.engines.v1_1_web_stream.ai_fallback.refine_prompt",
            return_value={"search_text": "TKA", "procedures": ["tka"]},
        ), patch(
            "caseprep.engines.v1_1_web_stream.retrieve_case_qas",
            return_value=[],
        ), patch(
            "caseprep.engines.v1_1_web_stream.curated_content_store.get_certified_payload",
            return_value=None,
        ) as packet_loader, patch(
            "caseprep.services.enrichment_v1_1.enrich_packet_sections"
        ) as enrichment:
            events = [
                decode(frame)
                async for frame in stream_caseprep_packet_v1_3(
                    "TKA", openai_client=object(), config=config
                )
            ]

        packet_loader.assert_called_once_with("tka")
        enrichment.assert_not_called()
        self.assertFalse(
            any(
                item.get("generated")
                for name, data in events
                if name == "section"
                for item in data.get("items", [])
            )
        )


if __name__ == "__main__":
    unittest.main()
