from __future__ import annotations

import unittest

from caseprep.pipelines.clinical_sections import (
    anatomy_pipeline,
    approach_pipeline,
    complications_pipeline,
    indications_pipeline,
)
from caseprep.services.case_identity_v1_1 import build_case_identity, enrich_refined_query
from caseprep.services.caseprep_assembler_v1_1 import (
    assemble_sections,
    collect_sources,
    high_yield_items,
    validate_response,
)


PAYLOAD = {
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
    "surgical_approach_anatomy": ["Use a palmar incision aligned with the radial border of the ring finger."],
    "surgical_layers": [
        {
            "layer_name": "transverse carpal ligament",
            "what_user_should_know": "Divide the ligament while protecting the median nerve.",
            "source_refs": ["https://example.test/carpal-tunnel"],
        }
    ],
    "common_mistakes": ["Incomplete distal release can cause persistent symptoms."],
    "attending_pimp_questions": [
        "Q: What are the indications for carpal tunnel release? A: Persistent symptoms despite appropriate nonoperative care or denervation.",
        "Q: What postoperative complication can occur? A: Persistent symptoms from incomplete release.",
    ],
}


class Phase2ParallelResponseTests(unittest.TestCase):
    def test_shared_identity_enriches_query_once(self):
        resolved = {
            "procedure_slug": "carpal_tunnel_release",
            "canonical_display_name": "Carpal Tunnel Release",
            "requested_approach": "open",
            "match_method": "exact",
            "confidence": 0.98,
        }
        refined = enrich_refined_query(
            {"region": "hand", "specialties": ["hand"]}, resolved, "Right open CTR in a 52 year-old"
        )
        identity = build_case_identity("Right open CTR in a 52 year-old", resolved, refined)
        self.assertEqual(refined["procedures"], ["carpal_tunnel_release"])
        self.assertEqual(identity["laterality"], "right")
        self.assertEqual(identity["patient_age"], 52)
        self.assertEqual(identity["approach"], "open")

    def test_supporting_pipelines_are_structured_and_source_backed(self):
        pipelines = [
            indications_pipeline(PAYLOAD),
            anatomy_pipeline(PAYLOAD),
            approach_pipeline(PAYLOAD),
            complications_pipeline(PAYLOAD),
        ]
        self.assertTrue(all(result["status"] == "complete" for result in pipelines))
        self.assertTrue(all(result["source_ids"] for result in pipelines))
        sections = assemble_sections(pipelines)
        self.assertTrue(sections["indications"])
        self.assertTrue(sections["anatomy"])
        self.assertTrue(sections["approach"])
        self.assertTrue(sections["operative_steps"])
        self.assertTrue(sections["complications"])
        self.assertTrue(sections["postoperative_care"])

    def test_assembler_preserves_pocket_pimped_first_and_provenance(self):
        high_yield = high_yield_items(
            [
                {
                    "record_id": "pp-1",
                    "question": "What nerve is decompressed?",
                    "answer": "Median nerve",
                    "additional_info": "Protect the recurrent motor branch.",
                    "retrieval_score": 0.91,
                }
            ]
        )
        supporting = [anatomy_pipeline(PAYLOAD)]
        response = {
            "case": {"canonical_slug": "carpal_tunnel_release"},
            "high_yield_questions": high_yield,
            "sections": assemble_sections(supporting),
        }
        self.assertEqual(high_yield[0]["source_ids"], ["pp-1"])
        self.assertEqual(validate_response(response), [])
        sources = collect_sources(high_yield, supporting)
        self.assertEqual(sources[0]["source_id"], "pp-1")
        self.assertTrue(any(source["url"] for source in sources))

    def test_missing_curated_payload_degrades_without_failure(self):
        for pipeline in (
            indications_pipeline,
            anatomy_pipeline,
            approach_pipeline,
            complications_pipeline,
        ):
            self.assertEqual(pipeline(None)["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
