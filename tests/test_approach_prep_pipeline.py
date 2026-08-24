from __future__ import annotations

import json
import unittest
from pathlib import Path

from caseprep.pipelines.approach_prep import build_approach_prep


ROOT = Path(__file__).resolve().parents[1]


class ApproachPrepPipelineTests(unittest.TestCase):
    def _payload(self, slug: str) -> dict:
        path = ROOT / "data/caseprep/procedures" / slug / "certified_payload.json"
        if path.exists():
            return json.loads(path.read_text())
        return {
            "schema_version": "brobot_case_prep_payload_v2",
            "procedure_id": slug,
            "case_prep_status": "unreviewed",
            "procedure_overview": "",
        }

    def test_exact_approach_emits_claim_bound_parallel_sections(self) -> None:
        result = build_approach_prep(
            "modified Henry approach for distal radius ORIF",
            "distal_radius_fracture_orif",
            self._payload("distal_radius_fracture_orif"),
        )
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["decision"]["status"], "selected")
        self.assertEqual(
            result["decision"]["selected_approach_id"], "distal_radius_modified_henry"
        )
        self.assertGreater(result["coverage"]["claim_count"], 10)
        self.assertGreaterEqual(result["coverage"]["source_count"], 2)
        for section_id in (
            "approach_quick_brief",
            "approach_exposure",
            "approach_safety",
            "approach_strategy",
        ):
            self.assertTrue(result["sections"][section_id]["items"], section_id)
        self.assertTrue(result["questions"])
        self.assertTrue(all(q["provenance"] == "approach_library" for q in result["questions"]))

    def test_ambiguous_multi_approach_case_does_not_mix_content(self) -> None:
        result = build_approach_prep(
            "hip hemiarthroplasty",
            "hip_hemiarthroplasty",
            self._payload("hip_hemiarthroplasty"),
        )
        self.assertEqual(result["decision"]["status"], "choice_required")
        self.assertIsNone(result["coverage"]["approach_id"])
        self.assertFalse(result["questions"])

    def test_source_indexed_packet_is_eligible_but_does_not_invent_sections(self) -> None:
        # Source-indexed entries may be offered by the decision layer. If one is
        # selected, the pipeline must expose its coverage/source record without
        # manufacturing clinical items.
        result = build_approach_prep("unknown approach", "not_a_procedure", None)
        self.assertIn(result["status"], {"complete", "unavailable"})
        self.assertEqual(
            sum(len(section["items"]) for section in result["sections"].values()), 0
        )

    def test_common_explicit_approaches_route_to_authored_packets(self) -> None:
        cases = (
            (
                "posterior cervical laminectomy and fusion C2-T1",
                "cervical_laminectomy_fusion",
                "spine_posterior_cervical",
            ),
            (
                "suprapatellar tibial shaft IM nail",
                "tibial_shaft_im_nail",
                "tibia_suprapatellar_nail_entry",
            ),
            (
                "reverse shoulder arthroplasty deltopectoral approach",
                "reverse_total_shoulder_arthroplasty",
                "approach_shoulder_deltopectoral",
            ),
        )
        for prompt, procedure_id, approach_id in cases:
            with self.subTest(prompt=prompt):
                result = build_approach_prep(
                    prompt, procedure_id, self._payload(procedure_id)
                )
                self.assertEqual(result["decision"]["status"], "selected")
                self.assertEqual(
                    result["decision"]["selected_approach_id"], approach_id
                )
                self.assertTrue(result["coverage"]["available_sections"])

    def test_generic_and_ambiguous_common_prompts_do_not_guess(self) -> None:
        cases = (
            ("tibial shaft IM nail", "tibial_shaft_im_nail"),
            ("humeral shaft ORIF", "humeral_shaft_fracture_orif"),
            ("posterior approach humeral shaft ORIF", "humeral_shaft_fracture_orif"),
            ("posterolateral approach trimalleolar ankle ORIF", "trimalleolar_ankle_orif"),
            ("endoscopic carpal tunnel release", "carpal_tunnel_release"),
        )
        for prompt, procedure_id in cases:
            with self.subTest(prompt=prompt):
                result = build_approach_prep(
                    prompt, procedure_id, self._payload(procedure_id)
                )
                self.assertEqual(result["decision"]["status"], "choice_required")
                self.assertIsNone(result["coverage"]["approach_id"])
                self.assertEqual(
                    sum(len(section["items"]) for section in result["sections"].values()),
                    0,
                )

    def test_multiple_named_approaches_are_prepared_in_parallel(self) -> None:
        result = build_approach_prep(
            "Tibial nail. Prepare and compare these approaches: "
            "Semi-extended suprapatellar approach for tibial nailing and "
            "Infrapatellar tibial nail entry approach.",
            "tibial_shaft_im_nail",
            self._payload("tibial_shaft_im_nail"),
        )
        self.assertEqual(result["decision"]["status"], "multiple_selected")
        self.assertEqual(len(result["decision"]["selected_approach_ids"]), 2)
        self.assertEqual(len(result["coverage"]["approach_ids"]), 2)
        self.assertGreaterEqual(len(result["questions"]), 6)
        approach_ids = {
            item.get("approach_id")
            for section in result["sections"].values()
            for item in section["items"]
        }
        self.assertEqual(
            approach_ids,
            {"tibia_suprapatellar_nail_entry", "tibia_infrapatellar_nail_entry"},
        )

    def test_arthroscopic_rotator_cuff_prompt_selects_shoulder_arthroscopy(self) -> None:
        for prompt in (
            "shoulder arthroscopy rotator cuff repair",
            "arthroscopic rotator cuff repair",
        ):
            with self.subTest(prompt=prompt):
                result = build_approach_prep(
                    prompt,
                    "rotator_cuff_repair",
                    self._payload("rotator_cuff_repair"),
                )
                decision = result["decision"]
                self.assertEqual(decision["status"], "selected")
                self.assertEqual(
                    decision["selected_approach_id"],
                    "approach_seed_orthobullets_orthopedics_approaches_shoulder_shoulder_arthroscopy_indications_and_approach",
                )
                self.assertEqual(result["coverage"]["content_status"], "source_indexed")
                self.assertEqual(result["coverage"]["source_count"], 1)
                self.assertEqual(
                    sum(len(section["items"]) for section in result["sections"].values()),
                    0,
                )


if __name__ == "__main__":
    unittest.main()
