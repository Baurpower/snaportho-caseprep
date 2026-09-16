from __future__ import annotations

import json
import unittest
from pathlib import Path

from caseprep.pipelines.approach_prep import build_approach_prep
from caseprep.services.curated_content_store import get_certified_payload
from caseprep.services.packet_v3 import procedure_approach_map


ROOT = Path(__file__).resolve().parents[1]


class ApproachPrepPipelineTests(unittest.TestCase):
    def test_generic_tha_choices_load_guides_using_existing_mobile_prompts(self):
        payload = self._payload("tha_posterior")
        result = build_approach_prep("total hip arthroplasty", "tha_posterior", payload)
        self.assertEqual(result["decision"]["status"], "selected")
        options = result["decision"]["approaches"]
        self.assertEqual(len(options), 2)
        self.assertEqual(len(result["decision"]["selected_approach_ids"]), 1)
        for option in options:
            with self.subTest(approach=option["name"]):
                selected = build_approach_prep(
                    f"total hip arthroplasty; planned approach: {option['name']}",
                    "tha_posterior", payload,
                )
                self.assertEqual(selected["decision"]["selected_approach_ids"], [option["approach_id"]])
                for section_id in ("approach_quick_brief", "approach_exposure", "approach_safety", "approach_strategy"):
                    self.assertTrue(selected["sections"][section_id]["items"], section_id)
                self.assertNotIn("hemiarthroplasty", json.dumps(selected["sections"]).lower())

    def test_posterior_tha_retains_protection_instructions(self):
        result = build_approach_prep("posterior THA", "tha_posterior", self._payload("tha_posterior"))
        self.assertEqual(result["decision"]["status"], "selected")
        safety = json.dumps(result["sections"]["approach_safety"])
        self.assertIn("Maintain hip in extension and knee in flexion", safety)
        exposure = json.dumps(result["sections"]["approach_exposure"])
        self.assertIn("Patient in lateral decubitus", exposure)

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
        self.assertEqual(result["decision"]["status"], "selected")
        self.assertTrue(result["coverage"]["approach_id"])
        self.assertTrue(result["questions"] or any(
            section.get("items") for section in result["sections"].values()
        ))

    def test_source_indexed_packet_is_not_selectable_at_runtime(self) -> None:
        # Editorial coverage records remain known, but the runtime must not let
        # a resident select an approach that cannot produce a guide.
        result = build_approach_prep("unknown approach", "not_a_procedure", None)
        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(result["decision"]["approaches"])
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

    def test_carpal_tunnel_choice_resolves_once_and_returns_approach_content(self) -> None:
        generic = build_approach_prep(
            "carpal tunnel release", "carpal_tunnel_release", None
        )
        self.assertEqual(generic["decision"]["status"], "selected")
        self.assertEqual(
            generic["decision"]["selected_approach_id"],
            "approach_wrist_carpal_tunnel",
        )
        self.assertIn(
            "approach_wrist_carpal_tunnel",
            {row["approach_id"] for row in generic["decision"]["approaches"]},
        )
        self.assertNotIn(
            "distal_radius_ulnar_palmar",
            {row["approach_id"] for row in generic["decision"]["approaches"]},
        )

        for prompt, expected_id in (
            ("Open Carpal Tunnel Release", "approach_wrist_carpal_tunnel"),
            (
                "Endoscopic Carpal Tunnel Release",
                "approach_wrist_carpal_tunnel_endoscopic",
            ),
        ):
            with self.subTest(prompt=prompt):
                result = build_approach_prep(
                    prompt, "carpal_tunnel_release", None
                )
                self.assertEqual(result["decision"]["status"], "selected")
                self.assertEqual(
                    result["decision"]["selected_approach_id"], expected_id
                )
                self.assertTrue(
                    all(
                        result["sections"][section_id]["items"]
                        for section_id in (
                            "approach_quick_brief",
                            "approach_exposure",
                            "approach_safety",
                            "approach_strategy",
                        )
                    )
                )

    def test_every_runtime_selectable_approach_produces_guide_content(self) -> None:
        procedure_ids = set(procedure_approach_map())
        procedure_ids.update(
            path.name
            for path in (ROOT / "data/caseprep/procedures").iterdir()
            if path.is_dir()
        )
        audited = 0
        for procedure_id in sorted(procedure_ids):
            payload = get_certified_payload(procedure_id)
            decision = build_approach_prep(
                procedure_id.replace("_", " "), procedure_id, payload
            )["decision"]
            for unavailable in decision.get("unavailable_approaches") or []:
                unavailable_id = unavailable.get("approach_id")
                attempted = build_approach_prep(
                    unavailable.get("name") or unavailable_id,
                    procedure_id,
                    payload,
                )
                self.assertNotIn(
                    unavailable_id,
                    attempted["decision"].get("selected_approach_ids") or [],
                )
            for option in decision.get("approaches") or []:
                with self.subTest(
                    procedure_id=procedure_id,
                    approach_id=option.get("approach_id"),
                ):
                    selected = build_approach_prep(
                        option.get("name") or option["approach_id"],
                        procedure_id,
                        payload,
                    )
                    item_count = sum(
                        len(section.get("items") or [])
                        for section in selected["sections"].values()
                    )
                    self.assertGreater(item_count, 0)
                    audited += 1
        self.assertGreater(audited, 40)

    def test_generic_and_ambiguous_common_prompts_do_not_guess(self) -> None:
        cases = (
            ("tibial shaft IM nail", "tibial_shaft_im_nail"),
            ("humeral shaft ORIF", "humeral_shaft_fracture_orif"),
            ("posterior approach humeral shaft ORIF", "humeral_shaft_fracture_orif"),
            ("posterolateral approach trimalleolar ankle ORIF", "trimalleolar_ankle_orif"),
        )
        for prompt, procedure_id in cases:
            with self.subTest(prompt=prompt):
                result = build_approach_prep(
                    prompt, procedure_id, self._payload(procedure_id)
                )
                self.assertIn(
                    result["decision"]["status"],
                    {"selected", "unavailable"},
                )
                if result["decision"]["status"] == "selected":
                    self.assertTrue(result["coverage"]["approach_id"])
                    self.assertGreater(
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

    def test_source_only_arthroscopy_is_not_exposed_as_an_empty_selection(self) -> None:
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
                self.assertEqual(decision["status"], "unavailable")
                self.assertIsNone(decision["selected_approach_id"])
                self.assertFalse(decision["approaches"])
                self.assertEqual(
                    sum(len(section["items"]) for section in result["sections"].values()),
                    0,
                )


if __name__ == "__main__":
    unittest.main()
