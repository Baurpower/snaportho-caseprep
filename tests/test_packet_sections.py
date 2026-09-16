from __future__ import annotations

import unittest

from caseprep.pipelines.packet_sections import (
    attending_questions_pipeline,
    decision_points_pipeline,
    evidence_pipeline,
    important_anatomy_pipeline,
    key_takeaways_block,
    operative_flow_pipeline,
    payload_from_approach_prep,
    postop_pipeline,
    summary_block,
    top_things_to_know_block,
)

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
            "source_refs": ["https://example.test/carpal-tunnel"],
        }
    ],
    "surgical_approach_anatomy": [
        "Use a palmar incision aligned with the radial border of the ring finger."
    ],
    "surgical_layers": [
        {
            "layer_name": "transverse carpal ligament",
            "what_user_should_know": "Divide the ligament while protecting the median nerve.",
            "source_refs": ["https://example.test/carpal-tunnel"],
        }
    ],
    "reduction_or_implant_anatomy": [],
    "fluoroscopy_checkpoints": ["Confirm no retained instrument before closure."],
    "danger_zones": ["Kaplan's cardinal line marks the recurrent motor branch."],
    "key_landmarks": ["Radial border of the ring finger."],
    "common_mistakes": ["Incomplete distal release can cause persistent symptoms."],
    "attending_pimp_questions": [
        "Q: What are the indications for surgical release? A: Failed conservative care or thenar weakness.",
        "Q: What is the postoperative plan? A: Early digital motion, wound care at two weeks.",
        "Q: Where is the recurrent motor branch? A: Distal to the transverse carpal ligament.",
    ],
    "night_before_review_checklist": [
        "Review linked modules and source URLs",
        "Trace the median nerve course through the carpal tunnel.",
    ],
    "approach_specific_notes": "Mini-open technique differs distally.",
}

ALL_PIPELINES = (
    important_anatomy_pipeline,
    attending_questions_pipeline,
    decision_points_pipeline,
    postop_pipeline,
    evidence_pipeline,
    operative_flow_pipeline,
    summary_block,
    key_takeaways_block,
    top_things_to_know_block,
)


class CrossSectionDedupTests(unittest.TestCase):
    """The 'recurrent motor branch' structure appears in both a highlight block
    (key_takeaways) and the fuller body section (anatomy). Highlight and body
    must produce the SAME framing-independent _dedup_key so the engine can
    suppress the repeat."""

    def _keys(self, items):
        return {i["_dedup_key"] for i in items if i.get("_dedup_key")}

    def test_structure_key_shared_between_highlight_and_body(self) -> None:
        anatomy_keys = self._keys(important_anatomy_pipeline(PAYLOAD)["items"])
        highlight_keys = self._keys(key_takeaways_block(PAYLOAD)["items"])
        shared = anatomy_keys & highlight_keys
        self.assertIn("structure:recurrent motor branch", shared)

    def test_anatomy_and_fluoro_keys_reach_top_things(self) -> None:
        top_keys = self._keys(top_things_to_know_block(PAYLOAD)["items"])
        anatomy_keys = self._keys(important_anatomy_pipeline(PAYLOAD)["items"])
        flow_keys = self._keys(operative_flow_pipeline(PAYLOAD)["items"])
        # must_know_anatomy fact is claimable from top over anatomy
        self.assertTrue(anatomy_keys & top_keys)
        # fluoroscopy checkpoint is claimable from top over operative_flow
        self.assertTrue(flow_keys & top_keys)


class PacketSectionContractTests(unittest.TestCase):
    def test_empty_payload_is_unavailable_not_crash(self) -> None:
        for pipeline in ALL_PIPELINES:
            result = pipeline(None)
            self.assertEqual(result["status"], "unavailable", pipeline.__name__)
            self.assertEqual(result["items"], [])

    def test_all_pipelines_return_contract_shape(self) -> None:
        for pipeline in ALL_PIPELINES:
            result = pipeline(PAYLOAD)
            for key in ("pipeline_id", "status", "items", "source_ids", "warnings", "duration_ms"):
                self.assertIn(key, result, pipeline.__name__)
            for entry in result["items"]:
                for key in ("id", "question", "answer", "category", "source_ids", "confidence", "generated"):
                    self.assertIn(key, entry, pipeline.__name__)
                self.assertFalse(entry["generated"], "deterministic pipelines never generate")
                self.assertEqual(entry["source"], "certified")

    def test_approach_prep_fills_anatomy_when_payload_is_missing(self) -> None:
        overlay = payload_from_approach_prep(
            None,
            {
                "sections": {
                    "approach_safety": {
                        "items": [{
                            "question": "Structure at risk",
                            "answer": "Protect the radial nerve in the spiral groove.",
                            "source_ids": ["ao-1"],
                        }]
                    },
                    "approach_quick_brief": {
                        "items": [{
                            "question": "Surface landmark",
                            "answer": "Lateral intermuscular septum",
                            "category": "landmark",
                        }]
                    },
                },
                "sources": [{"url": "https://example.test/humerus"}],
            },
        )
        self.assertTrue(overlay)
        anatomy = important_anatomy_pipeline(overlay)
        self.assertEqual(anatomy["status"], "complete")
        self.assertGreaterEqual(len(anatomy["items"]), 1)
        self.assertFalse(anatomy["items"][0]["generated"])

    def test_never_fabricates_content(self) -> None:
        # Every answer must be traceable to a payload value.
        payload_blob = str(PAYLOAD)
        for pipeline in ALL_PIPELINES:
            for entry in pipeline(PAYLOAD)["items"]:
                self.assertIn(entry["answer"], payload_blob, pipeline.__name__)

    def test_uncertified_payload_marks_source(self) -> None:
        uncertified = {**PAYLOAD, "case_prep_status": "draft"}
        result = important_anatomy_pipeline(uncertified)
        self.assertTrue(result["items"])
        self.assertTrue(all(i["source"] == "curated_uncertified" for i in result["items"]))


class PacketSectionContentTests(unittest.TestCase):
    def test_anatomy_buckets(self) -> None:
        categories = {i["category"] for i in important_anatomy_pipeline(PAYLOAD)["items"]}
        self.assertEqual(
            categories,
            {"must_know_anatomy", "structure_at_risk", "danger_zone", "surface_landmark"},
        )

    def test_operative_flow_phases(self) -> None:
        categories = {i["category"] for i in operative_flow_pipeline(PAYLOAD)["items"]}
        self.assertIn("exposure", categories)
        self.assertIn("critical_step", categories)
        self.assertIn("checkpoint", categories)
        self.assertIn("pearl", categories)

    def test_decision_points_no_longer_slices_pimp_questions(self) -> None:
        # The curated seed was a keyword slice of attending_pimp_questions —
        # every item duplicated a card already shown in pimp_questions. It is
        # dropped; the section is now enrichment-only.
        result = decision_points_pipeline(PAYLOAD)
        self.assertEqual(result["items"], [])
        self.assertEqual(result["status"], "unavailable")

    def test_postop_no_longer_slices_pimp_questions(self) -> None:
        result = postop_pipeline(PAYLOAD)
        self.assertEqual(result["items"], [])
        self.assertEqual(result["status"], "unavailable")

    def test_top_things_capped_at_ten(self) -> None:
        self.assertLessEqual(len(top_things_to_know_block(PAYLOAD)["items"]), 10)

    def test_key_takeaways_lead_with_structure_protection(self) -> None:
        items = key_takeaways_block(PAYLOAD)["items"]
        self.assertTrue(items)
        self.assertIn("recurrent motor branch", items[0]["question"])

    def test_summary_is_case_frame_plus_must_knows(self) -> None:
        payload = {
            **PAYLOAD,
            "procedure_overview": (
                "Displaced or unstable femoral-neck fracture in an older adult. "
                "Performed via the Lateral (Hardinge) approach; protect the superior gluteal nerve."
            ),
            "must_know_anatomy": [
                "Limit the gluteus medius split to 3-5 cm above the greater trochanter.",
                "Repair the anterior abductors to the greater trochanter.",
            ],
        }
        items = summary_block(payload)["items"]
        frame = next(row for row in items if row["category"] == "summary")
        self.assertIn("Displaced or unstable femoral-neck fracture", frame["answer"])
        self.assertNotIn("Performed via", frame["answer"])
        self.assertNotIn("Hardinge", frame["answer"])
        knows = [row for row in items if row["category"] == "must_know"]
        self.assertEqual(len(knows), 2)
        self.assertTrue(all(row["_dedup_key"].startswith("anatomy:") for row in knows))
        anatomy_keys = {
            row["_dedup_key"]
            for row in important_anatomy_pipeline(payload)["items"]
            if row.get("_dedup_key")
        }
        self.assertTrue({row["_dedup_key"] for row in knows} <= anatomy_keys)


if __name__ == "__main__":
    unittest.main()
