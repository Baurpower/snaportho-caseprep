from __future__ import annotations

import json
import os
import unittest
from typing import Dict, List, Tuple
from unittest import mock

from fastapi.testclient import TestClient

from caseprep.services.ttl_cache import invalidate_resolution_caches

PAYLOAD = {
    "case_prep_status": "certified",
    "procedure_overview": "Open carpal tunnel release for median nerve decompression.",
    "source_urls": ["https://example.test/carpal-tunnel"],
    "must_know_anatomy": ["The median nerve lies deep to the transverse carpal ligament."],
    "structures_at_risk": [
        {
            "structure": "recurrent motor branch",
            "why_at_risk": "Its course is variable.",
            "how_to_avoid_injury": "Release under direct visualization.",
        }
    ],
    "surgical_approach_anatomy": ["Palmar incision aligned with the ring finger."],
    "surgical_layers": [
        {
            "layer_name": "transverse carpal ligament",
            "what_user_should_know": "Divide while protecting the median nerve.",
        }
    ],
    "common_mistakes": ["Incomplete distal release."],
    "attending_pimp_questions": [
        "Q: What are the indications for release? A: Failed conservative care.",
    ],
    "night_before_review_checklist": ["Trace the median nerve course."],
}


def parse_sse(raw: bytes) -> List[Tuple[str, Dict]]:
    events: List[Tuple[str, Dict]] = []
    for block in raw.decode("utf-8").split("\n\n"):
        if not block.strip():
            continue
        event_name, data = "", {}
        for line in block.splitlines():
            if line.startswith("event: "):
                event_name = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        events.append((event_name, data))
    return events


class WebStreamE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        invalidate_resolution_caches()
        self._env = mock.patch.dict(
            os.environ, {"ENABLE_CASEPREP_WEB_V1_1_STREAM": "true"}
        )
        self._env.start()
        import main

        self.client = TestClient(main.app)

    def tearDown(self) -> None:
        self._env.stop()
        invalidate_resolution_caches()

    def _stream(self, prompt: str) -> List[Tuple[str, Dict]]:
        with mock.patch(
            "caseprep.engines.v1_1_web_stream.curated_content_store.get_certified_payload",
            return_value=PAYLOAD,
        ), mock.patch(
            "caseprep.engines.v1_1_web_stream.ai_fallback.refine_prompt",
            return_value={"search_text": prompt, "procedures": []},
        ), mock.patch(
            "caseprep.engines.v1_1_web_stream.retrieve_case_qas",
            return_value=[
                {
                    "record_id": "vec-1",
                    "question": "What tendon is affected in trigger finger?",
                    "answer": "Flexor tendon at the A1 pulley.",
                    "additional_info": "",
                    "retrieval_score": 0.8,
                    "vector_score": 0.8,
                }
            ],
        ):
            response = self.client.post(
                "/case-prep/web/v1.1/stream", json={"prompt": prompt}
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        return parse_sse(response.content)

    def test_flag_off_returns_404(self) -> None:
        with mock.patch.dict(os.environ, {"ENABLE_CASEPREP_WEB_V1_1_STREAM": "false"}):
            response = self.client.post(
                "/case-prep/web/v1.1/stream", json={"prompt": "trigger finger release"}
            )
        self.assertEqual(response.status_code, 404)

    def test_meta_first_done_last_header_before_sections(self) -> None:
        events = self._stream("trigger thumb release")
        names = [name for name, _ in events]
        self.assertEqual(names[0], "meta")
        self.assertEqual(names[-1], "done")
        self.assertIn("header", names)
        first_section = names.index("section")
        self.assertLess(names.index("header"), first_section)
        meta = events[0][1]
        self.assertEqual(meta["caseprep_version"], "v1.1")
        self.assertEqual(meta["engine"], "web_packet_stream")
        self.assertTrue(meta["packet_id"])
        progress = [data for name, data in events if name == "progress"]
        self.assertTrue(progress)
        self.assertEqual(progress[0]["phase"], "connecting")
        self.assertTrue(any(item["phase"] == "retrieving" for item in progress))
        self.assertLessEqual(progress[0]["progress_min"], progress[0]["progress_max"])

    def test_above_the_fold_sections_stream_before_done(self) -> None:
        events = self._stream("trigger thumb release")
        section_ids = [data["section_id"] for name, data in events if name == "section"]
        for expected in ("summary", "key_takeaways", "top_things_to_know", "pimp_questions"):
            self.assertIn(expected, section_ids)
        # Above-the-fold sections must precede the fan-out sections.
        self.assertLess(
            section_ids.index("summary"), section_ids.index("pimp_questions")
        )

    def test_pimp_questions_curated_before_rag(self) -> None:
        events = self._stream("trigger thumb release")
        pimp = next(
            data for name, data in events
            if name == "section" and data["section_id"] == "pimp_questions"
        )
        self.assertEqual(pimp["items"][0]["category"], "attending_question")
        self.assertEqual(pimp["items"][0]["rank"], 1)
        rag_items = [item for item in pimp["items"] if item.get("source") == "rag"]
        self.assertEqual(len(rag_items), 1)

    def test_header_has_above_the_fold_fields(self) -> None:
        events = self._stream("trigger thumb release")
        header = next(data for name, data in events if name == "header")
        for key in (
            "display_name",
            "est_prep_minutes",
            "difficulty",
            "pgy_level",
            "procedure_type",
            "common_attending_focus",
            "certified",
        ):
            self.assertIn(key, header["header"])
        self.assertEqual(header["case"]["canonical_slug"], "trigger_finger_release")
        self.assertEqual(header["header"]["procedure_type"], "release_or_decompression")

    def test_clarification_path_is_terminal(self) -> None:
        with mock.patch(
            "caseprep.engines.v1_1_web_stream.ai_fallback.refine_prompt",
            return_value={"search_text": "carpal tunnel release"},
        ):
            response = self.client.post(
                "/case-prep/web/v1.1/stream", json={"prompt": "carpal tunnel release"}
            )
        events = parse_sse(response.content)
        names = [name for name, _ in events]
        self.assertIn("clarification", names)
        self.assertEqual(names[-1], "done")
        self.assertNotIn("section", names)
        clarification = next(data for name, data in events if name == "clarification")
        self.assertTrue(clarification["clarification_reason"])

    def test_retrieval_failure_degrades_not_fatal(self) -> None:
        with mock.patch(
            "caseprep.engines.v1_1_web_stream.curated_content_store.get_certified_payload",
            return_value=None,
        ), mock.patch(
            "caseprep.engines.v1_1_web_stream.ai_fallback.refine_prompt",
            return_value={"search_text": "trigger thumb release"},
        ), mock.patch(
            "caseprep.engines.v1_1_web_stream.retrieve_case_qas",
            side_effect=RuntimeError("pinecone down"),
        ):
            response = self.client.post(
                "/case-prep/web/v1.1/stream", json={"prompt": "trigger thumb release"}
            )
        events = parse_sse(response.content)
        names = [name for name, _ in events]
        self.assertEqual(names[-1], "done")
        self.assertIn("section", names)
        self.assertNotIn("error", names)
        done = events[-1][1]
        self.assertEqual(done["pipeline_status"]["pocket_pimped"]["status"], "complete")

    def test_empty_prompt_is_fatal_error(self) -> None:
        response = self.client.post("/case-prep/web/v1.1/stream", json={"prompt": "  "})
        events = parse_sse(response.content)
        self.assertEqual(events[-1][0], "error")

    def test_enrichment_emits_partial_then_complete_pimp_questions(self) -> None:
        from caseprep.services.enrichment_v1_1 import EnrichmentResult, _sanitize

        enrichment = EnrichmentResult(
            _sanitize(
                {
                    "generated_pimp_questions": [
                        {
                            "question": "Which pulley must be preserved?",
                            "answer": "The A2 pulley.",
                            "teaching_pearl": "A2 and A4 are critical.",
                            "why_attendings_ask": "Anatomy trap.",
                            "common_mistake": "Confusing A1 with A2.",
                            "difficulty": "easy",
                        }
                    ],
                    "decision_points": [
                        {
                            "category": "when_to_operate",
                            "question": "When do we operate?",
                            "answer": "Failed conservative care.",
                        }
                    ],
                }
            ),
            certified=False,
        )
        import main

        with mock.patch.dict(
            os.environ, {"CASEPREP_V1_1_ENRICHMENT_ENABLED": "true"}
        ), mock.patch.object(main, "OPENAI_CLIENT", mock.Mock()), mock.patch(
            "caseprep.services.enrichment_v1_1.enrich_packet_sections",
            return_value=enrichment,
        ):
            events = self._stream("trigger thumb release")

        pimp_events = [
            data for name, data in events
            if name == "section" and data["section_id"] == "pimp_questions"
        ]
        self.assertEqual([e["status"] for e in pimp_events], ["partial", "complete"])
        final_items = pimp_events[-1]["items"]
        # This fixture has fewer than the minimum grounded questions, so the
        # generated question is retained strictly as gap-fill.
        self.assertTrue(any(item.get("generated") for item in final_items))
        self.assertTrue(pimp_events[-1]["generated_field_paths"])

        decision = next(
            data for name, data in events
            if name == "section" and data["section_id"] == "decision_points"
        )
        # decision_points no longer slices pimp_questions; with no curated seed
        # it is filled by enrichment gap-fill (clearly marked generated).
        generated = [item for item in decision["items"] if item.get("generated")]
        self.assertTrue(generated)
        self.assertEqual(generated[0]["question"], "When do we operate?")

    def test_certified_v1_2_fills_themed_sections_but_keeps_body_grounded(self) -> None:
        """Certified v1.2: enrichment fills decision_points/postop only; pimp and
        the descriptive body stay grounded-only (no partial pass, no padding)."""
        from caseprep.services.enrichment_v1_1 import EnrichmentResult, _sanitize

        enrichment = EnrichmentResult(
            _sanitize(
                {
                    # Would gap-fill pimp/anatomy if allowed — must be ignored for
                    # a certified packet (those stay grounded-only).
                    "generated_pimp_questions": [
                        {"question": "AI pimp?", "answer": "AI answer."}
                    ],
                    "anatomy_gap_fill": [
                        {"question": "AI anatomy?", "answer": "AI anatomy fact.",
                         "category": "must_know_anatomy"}
                    ],
                    "decision_points": [
                        {"category": "when_to_operate",
                         "question": "When do we operate?",
                         "answer": "Failed conservative care."}
                    ],
                    "postop": ["Early digital motion; wound check at two weeks."],
                }
            ),
            certified=True,
        )
        import main

        with mock.patch.dict(
            os.environ,
            {"ENABLE_CASEPREP_WEB_V1_2_STREAM": "true",
             "CASEPREP_V1_1_ENRICHMENT_ENABLED": "true"},
        ), mock.patch.object(main, "OPENAI_CLIENT", mock.Mock()), mock.patch(
            "caseprep.engines.v1_1_web_stream.curated_content_store.get_certified_payload",
            return_value=PAYLOAD,
        ), mock.patch(
            "caseprep.engines.v1_1_web_stream.ai_fallback.refine_prompt",
            return_value={"search_text": "trigger thumb release", "procedures": []},
        ), mock.patch(
            "caseprep.engines.v1_1_web_stream.retrieve_case_qas",
            return_value=[],
        ), mock.patch(
            "caseprep.services.enrichment_v1_1.enrich_packet_sections",
            return_value=enrichment,
        ):
            response = self.client.post(
                "/case-prep/web/v1.2/stream", json={"prompt": "trigger thumb release"}
            )
        self.assertEqual(response.status_code, 200)
        events = parse_sse(response.content)
        sections = {
            data["section_id"]: data
            for name, data in events
            if name == "section" and "section_id" in data
        }

        # Themed gap-fill sections are AI-filled on a certified packet.
        self.assertIn("decision_points", sections)
        self.assertTrue(
            any(i.get("generated") for i in sections["decision_points"]["items"])
        )

        # Pimp questions never went "partial" and carry no AI-generated card.
        pimp_events = [
            data for name, data in events
            if name == "section" and data.get("section_id") == "pimp_questions"
        ]
        self.assertNotIn("partial", [e["status"] for e in pimp_events])
        if pimp_events:
            self.assertFalse(
                any(i.get("generated") for i in pimp_events[-1]["items"])
            )

        # Anatomy stays grounded-only — the AI anatomy fact must not appear.
        if "anatomy" in sections:
            self.assertFalse(
                any(i.get("generated") for i in sections["anatomy"]["items"])
            )


class NonStreamRegressionTests(unittest.TestCase):
    """Regression lock for the existing non-stream preview consumed by the web."""

    def test_non_stream_route_flag_off_404(self) -> None:
        import main

        client = TestClient(main.app)
        with mock.patch.dict(os.environ, {"ENABLE_CASEPREP_WEB_V1_1": "false"}):
            response = client.post(
                "/case-prep/web/v1.1", json={"prompt": "trigger finger release"}
            )
        self.assertEqual(response.status_code, 404)

    def test_non_stream_envelope_shape_unchanged(self) -> None:
        import main

        client = TestClient(main.app)
        invalidate_resolution_caches()
        with mock.patch.dict(os.environ, {"ENABLE_CASEPREP_WEB_V1_1": "true"}), mock.patch(
            "caseprep.engines.v1_1_web.curated_content_store.get_certified_payload",
            return_value=PAYLOAD,
        ), mock.patch(
            "caseprep.engines.v1_1_web.ai_fallback.refine_prompt",
            return_value={"search_text": "trigger finger release"},
        ), mock.patch(
            "caseprep.services.rag_retrieval.retrieve_case_qas",
            return_value=[],
        ), mock.patch(
            "caseprep.engines.v1_1_web.retrieve_case_qas", return_value=[]
        ):
            response = client.post(
                "/case-prep/web/v1.1", json={"prompt": "trigger finger release"}
            )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        for key in (
            "caseprep_version",
            "engine",
            "case",
            "high_yield_questions",
            "sections",
            "pimpQuestions",
            "otherUsefulFacts",
            "pipeline_status",
            "timing",
            "retrieval",
        ):
            self.assertIn(key, body)
        self.assertEqual(body["caseprep_version"], "v1.1")
        self.assertEqual(body["engine"], "web_parallel_rag")


if __name__ == "__main__":
    unittest.main()
