from __future__ import annotations

import json
import unittest
from pathlib import Path

from caseprep.approach_library import ApproachLibrary
from caseprep.approach_library.schema import content_hash, empty_packet, validate_packet
from caseprep.services.packet_v3 import approach_decision_payload, normalize_packet
from scripts.compile_curated_approaches import CURATED_DIR, _definitions, compile_definition

ROOT = Path(__file__).resolve().parents[1]
LIVE_PROCEDURES_DIR = ROOT / "data/caseprep/procedures"


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

    def _live_runtime_slugs(self) -> list[str]:
        slugs = []
        for folder in LIVE_PROCEDURES_DIR.iterdir():
            manifest_path = folder / "manifest.json"
            if not manifest_path.exists():
                continue
            manifest = json.loads(manifest_path.read_text())
            if manifest.get("runtime_enabled"):
                slugs.append(str(manifest.get("slug") or folder.name))
        return sorted(slugs)

    def _certified_payload(self, slug: str) -> dict:
        return json.loads(
            (LIVE_PROCEDURES_DIR / slug / "certified_payload.json").read_text()
        )

    def test_procedure_id_aliases_point_at_real_targets(self):
        lib = ApproachLibrary()
        authored_ids = {
            (application.get("procedure_id") if isinstance(application, dict) else application)
            for packet in lib.packets().values()
            for application in packet.get("procedure_applications") or []
        }
        authored_ids.update(
            str(row.get("procedure_id") or "")
            for row in lib.mappings()
            if row.get("procedure_id")
        )
        for live_id, dests in lib.procedure_id_alias_map().items():
            self.assertTrue(live_id)
            for dest in dests:
                self.assertIn(dest, authored_ids, f"{live_id} → {dest}")
        for live_id, approach_ids in lib.procedure_approach_alias_map().items():
            self.assertTrue(live_id)
            for approach_id in approach_ids:
                self.assertIn(approach_id, lib.packets(), f"{live_id} → {approach_id}")

    def test_aliased_live_slugs_attach_library_drafts(self):
        lib = ApproachLibrary()
        expected = {
            "pelvis_ring_fracture_orif": "pelvic_ring_pubic_symphysis",
            "supracondylar_humerus_fracture_pediatric": "pediatric_distal_humerus_medial",
            "posterior_lumbar_decompression_fusion": "spine_posterior_midline_thoracolumbar",
        }
        for slug, sentinel in expected.items():
            ids = {row["approach_id"] for row in lib.for_procedure(slug)}
            self.assertIn(sentinel, ids, slug)
            for packet in lib.for_procedure(slug):
                self.assertNotEqual(packet.get("content_status"), "source_indexed", packet.get("approach_id"))
                self.assertNotEqual((packet.get("review") or {}).get("status"), "agent_reviewed")
                self.assertEqual((packet.get("review") or {}).get("status"), "agent_review_pending")

        lumbar_ids = {row["approach_id"] for row in lib.for_procedure("posterior_lumbar_decompression_fusion")}
        self.assertIn("spine_wiltse", lumbar_ids)
        self.assertNotIn("spine_retroperitoneal_l4_s1", lumbar_ids)
        self.assertNotIn("spine_transpsoas_l2_l4", lumbar_ids)

    def test_live_runtime_packets_never_claim_agent_reviewed(self):
        slugs = self._live_runtime_slugs()
        self.assertEqual(len(slugs), 24)
        aliased = set(ApproachLibrary.procedure_id_alias_map()) | set(
            ApproachLibrary.procedure_approach_alias_map()
        )
        for slug in slugs:
            packet = normalize_packet(self._certified_payload(slug))
            self.assertIsNotNone(packet)
            self.assertEqual(packet["schema_version"], "brobot_case_prep_payload_v3")
            self.assertNotEqual(packet["review"]["status"], "agent_reviewed")
            for option in packet.get("approaches") or []:
                self.assertNotEqual(option.get("review_status"), "agent_reviewed", option.get("approach_id"))
            library_rows = ApproachLibrary().for_procedure(slug)
            if slug in aliased or library_rows:
                library_ids = {row["approach_id"] for row in library_rows}
                rendered_ids = {row["approach_id"] for row in packet.get("approaches") or []}
                self.assertTrue(library_ids & rendered_ids, slug)
                for option in packet.get("approaches") or []:
                    if option.get("approach_id") in library_ids:
                        self.assertEqual(option.get("review_status"), "agent_review_pending")
                        self.assertEqual(option.get("content_status"), "curated")

    def test_hip_hemi_choice_is_unchanged_by_aliases(self):
        decision = approach_decision_payload(
            "hip hemiarthroplasty",
            self._certified_payload("hip_hemiarthroplasty"),
        )
        self.assertEqual(decision["status"], "choice_required")
        ids = {row["approach_id"] for row in decision["approaches"]}
        self.assertGreaterEqual(len(ids), 4)
        self.assertIn("hip_anterior_smith_petersen", ids)
        self.assertIn("hip_anterolateral_watson_jones", ids)
        selected = approach_decision_payload(
            "posterior hip hemiarthroplasty",
            self._certified_payload("hip_hemiarthroplasty"),
        )
        self.assertEqual(selected["status"], "selected")
        self.assertEqual(
            selected["selected_approach_id"],
            "approach_lower_ext_hip_posterior_moore_southern",
        )

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
