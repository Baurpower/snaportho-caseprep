from __future__ import annotations

import unittest
from pathlib import Path

from caseprep.approach_library import ApproachLibrary
from caseprep.approach_library.schema import content_hash, empty_packet, validate_packet
from caseprep.services.packet_v3 import approach_decision_payload
from scripts.compile_curated_approaches import CURATED_DIR, _definitions, compile_definition


class ApproachLibraryTests(unittest.TestCase):
    def setUp(self) -> None:
        ApproachLibrary.reset()

    def test_source_inventory_contains_both_requested_providers(self):
        rows = list(ApproachLibrary.source_pages().values())
        providers = {row["provider"] for row in rows}
        self.assertGreaterEqual(len(rows), 600)
        self.assertEqual(providers, {"ao_surgery_reference", "orthobullets"})
        self.assertEqual(len(rows), len({row["url"] for row in rows}))

    def test_source_index_seed_cannot_publish_as_clinical_guidance(self):
        packet = empty_packet("approach_test", "Test approach", region="test")
        result = validate_packet(packet)
        self.assertFalse(result["passed"])
        self.assertIn("Missing required field: corridor", result["failures"])

    def test_review_hash_excludes_review_metadata(self):
        packet = empty_packet("approach_test", "Test approach", region="test")
        before = content_hash(packet)
        packet["review"]["status"] = "agent_reviewed"
        self.assertEqual(before, content_hash(packet))

    def test_unresolved_contradictory_claim_values_fail(self):
        packet = empty_packet("approach_test", "Test approach", region="test")
        packet["corridor"] = "Test corridor"
        packet["claims"] = [
            {
                "claim_id": "c1",
                "claim_key": "patient_position",
                "normalized_value": "supine",
                "source_ids": ["s1"],
                "risk_level": "low",
            },
            {
                "claim_id": "c2",
                "claim_key": "patient_position",
                "normalized_value": "prone",
                "source_ids": ["s2"],
                "risk_level": "low",
            },
        ]
        packet["sources"] = [
            {"source_id": "s1", "url": "https://surgeryreference.aofoundation.org/a"},
            {"source_id": "s2", "url": "https://pubmed.ncbi.nlm.nih.gov/1"},
        ]
        result = validate_packet(packet, require_reviews=False)
        self.assertIn("Unresolved contradictory claim values: patient_position", result["failures"])

    def test_authored_library_packets_drive_runtime_approach_choice(self):
        decision = approach_decision_payload(
            "posterior hip hemiarthroplasty",
            {
                "schema_version": "brobot_case_prep_payload_v2",
                "procedure_id": "hip_hemiarthroplasty",
                "case_prep_status": "certified",
                "procedure_overview": "Hip hemiarthroplasty.",
            },
        )
        self.assertEqual(decision["status"], "selected")
        ids = {row["approach_id"] for row in decision["approaches"]}
        self.assertGreaterEqual(len(ids), 4)
        self.assertIn("hip_anterior_smith_petersen", ids)
        self.assertIn("hip_anterolateral_watson_jones", ids)

    def test_local_curated_definitions_compile_without_api(self):
        paths = sorted(Path(CURATED_DIR).glob("*.json"))
        packets = [compile_definition(row) for row in _definitions(paths)]
        self.assertGreaterEqual(len(packets), 2)
        for packet in packets:
            self.assertEqual(packet["authoring_provenance"]["method"], "local_codex_curated")
            self.assertFalse(packet["authoring_provenance"]["api_used"])
            self.assertTrue(validate_packet(packet, require_reviews=False)["passed"])


if __name__ == "__main__":
    unittest.main()
