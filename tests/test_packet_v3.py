from __future__ import annotations

import json
import unittest
from pathlib import Path

from caseprep.services.packet_v3 import (
    AGENT_REVIEW_ROLES,
    approach_decision_payload,
    normalize_packet,
    validate_review_gate,
)


ROOT = Path(__file__).resolve().parents[1]


class PacketV3Tests(unittest.TestCase):
    def test_single_usable_common_option_is_selected_for_older_mobile_clients(self):
        packet = {
            "schema_version": "brobot_case_prep_payload_v3",
            "procedure_id": "test",
            "approaches": [{
                "approach_id": "only_corridor", "name": "Available corridor",
                "role": "common_option", "content_status": "curated",
            }],
        }
        decision = approach_decision_payload("prepare my case", packet)
        self.assertEqual(decision["status"], "selected")
        self.assertEqual(decision["selected_approach_ids"], ["only_corridor"])
        packet["approaches"][0]["content_status"] = "coverage_gap"
        decision = approach_decision_payload("prepare my case", packet)
        self.assertFalse(decision["selected_approach_ids"])
        self.assertFalse(decision["approaches"])

    def _payload(self, slug: str):
        return json.loads(
            (ROOT / f"data/caseprep/procedures/{slug}/certified_payload.json").read_text()
        )

    def test_all_live_legacy_packets_normalize_without_claiming_agent_review(self):
        live = []
        for folder in (ROOT / "data/caseprep/procedures").iterdir():
            manifest_path = folder / "manifest.json"
            payload_path = folder / "certified_payload.json"
            if not manifest_path.exists() or not payload_path.exists():
                continue
            manifest = json.loads(manifest_path.read_text())
            if not manifest.get("runtime_enabled"):
                continue
            packet = normalize_packet(json.loads(payload_path.read_text()))
            self.assertEqual(packet["schema_version"], "brobot_case_prep_payload_v3")
            self.assertTrue(packet["approaches"], manifest["slug"])
            self.assertNotEqual(packet["review"]["status"], "agent_reviewed")
            self.assertTrue(packet["review"]["legacy_certification_migrated"])
            live.append(manifest["slug"])
        self.assertEqual(len(live), 24)

    def test_generic_hemi_exposes_all_curated_approaches_and_requires_choice(self):
        packet = self._payload("hip_hemiarthroplasty")
        decision = approach_decision_payload("hip hemiarthroplasty", packet)
        self.assertEqual(decision["status"], "selected")
        self.assertTrue(decision["selected_approach_id"])
        self.assertLessEqual(len(decision["approaches"]), 3)
        self.assertEqual(decision["coverage"]["gap_count"], 0)
        self.assertIn(
            "approach_lower_ext_hip_posterior_moore_southern",
            {row["approach_id"] for row in decision["approaches"]},
        )

    def test_intertrochanteric_defaults_to_nail_entry_not_hardinge(self):
        seed = {
            "schema_version": "brobot_case_prep_payload_v2",
            "procedure_id": "intertrochanteric_hip_fracture_orif",
            "procedure_name": "Intertrochanteric Hip Fracture ORIF",
            "case_prep_status": "unreviewed",
            "procedure_overview": "",
        }
        decision = approach_decision_payload("Intertrochanteric fracture", seed)
        ids = [row["approach_id"] for row in decision["approaches"]]
        self.assertEqual(decision["status"], "selected")
        self.assertEqual(decision["selected_approach_id"], "femur_antegrade_trochanteric_entry")
        self.assertIn("femur_antegrade_trochanteric_entry", ids)
        self.assertNotIn("approach_lower_ext_hip_lateral_hardinge", ids)
        self.assertLessEqual(len(ids), 3)

    def test_live_demand_missing_approaches_now_resolve(self):
        cases = {
            "wrist arthroscopy tfcc": (
                "wrist_arthroscopy_tfcc",
                "wrist_dorsal_arthroscopy_portals",
            ),
            "trigger finger release": (
                "trigger_finger_release",
                "hand_a1_pulley_open",
            ),
            "acdf": ("acdf", "spine_anterior_cervical_c3_c7"),
            "olecranon orif": (
                "olecranon_fracture_orif",
                "proximal_forearm_posterior_ulna",
            ),
            "ankle fracture orif": (
                "ankle_fracture_orif",
                "malleolus_lateral_fibula",
            ),
        }
        for prompt, (slug, expected) in cases.items():
            with self.subTest(prompt=prompt):
                seed = {
                    "schema_version": "brobot_case_prep_payload_v2",
                    "procedure_id": slug,
                    "procedure_name": slug,
                    "case_prep_status": "unreviewed",
                    "procedure_overview": "",
                }
                decision = approach_decision_payload(prompt, seed)
                ids = [row["approach_id"] for row in decision["approaches"]]
                self.assertEqual(decision["status"], "selected")
                self.assertEqual(decision["selected_approach_id"], expected)
                self.assertIn(expected, ids)
                self.assertNotIn("distal_tibia_posterolateral", ids)

    def test_humeral_shaft_orif_does_not_offer_pin_safe_zones(self):
        packet = self._payload("humeral_shaft_fracture_orif")
        decision = approach_decision_payload("Humeral shaft fracture displaced", packet)
        ids = {row["approach_id"] for row in decision["approaches"]}
        self.assertEqual(decision["status"], "selected")
        self.assertLessEqual(len(ids), 3)
        self.assertTrue(ids & {
            "approach_humerus_anterolateral_distal",
            "approach_humerus_posterior_triceps_split",
        })
        self.assertNotIn("humerus_percutaneous_pin_safe_zones", ids)
        self.assertNotIn("humeral_shaft_pin_safe_zones", ids)

    def test_explicit_hemi_approach_is_selected(self):
        packet = self._payload("hip_hemiarthroplasty")
        decision = approach_decision_payload("posterior hip hemiarthroplasty", packet)
        self.assertEqual(decision["status"], "selected")
        self.assertEqual(
            decision["selected_approach_id"],
            "approach_lower_ext_hip_posterior_moore_southern",
        )

    def test_imn_filters_femoral_shaft_packet_to_nailing_approaches(self):
        packet = self._payload("femoral_shaft_fracture_orif")
        decision = approach_decision_payload("femoral shaft IMN", packet)
        self.assertEqual(decision["status"], "selected")
        self.assertTrue(decision["selected_approach_id"])
        self.assertTrue(decision["approaches"])
        identities = [
            " ".join(
                [option["approach_id"], option["name"], *option.get("aliases", [])]
            ).lower()
            for option in decision["approaches"]
        ]
        self.assertTrue(
            all(
                any(term in identity for term in ("nail", "imn", "esin"))
                for identity in identities
            )
        )
        self.assertFalse(
            any(
                option["approach_id"] == "femoral_shaft_lateral_open"
                for option in decision["approaches"]
            )
        )
        self.assertFalse(
            any("pediatric" in identity or "esin" in identity for identity in identities)
        )

    def test_retrograde_femoral_imn_selects_the_adult_retrograde_entry(self):
        packet = self._payload("femoral_shaft_fracture_orif")
        decision = approach_decision_payload(
            "retrograde femoral shaft IMN", packet
        )
        self.assertEqual(decision["status"], "selected")
        self.assertEqual(
            decision["selected_approach_id"], "femur_retrograde_nailing_entry"
        )

    def test_im_nail_compatibility_slug_has_retrograde_approach_content(self):
        seed = {
            "schema_version": "brobot_case_prep_payload_v2",
            "procedure_id": "femoral_shaft_im_nail",
            "procedure_name": "Femoral Shaft IM Nailing",
            "case_prep_status": "unreviewed",
            "procedure_overview": "",
        }
        decision = approach_decision_payload(
            "distal femoral shaft orif retrograde imn nail", seed
        )
        self.assertEqual(decision["status"], "selected")
        self.assertEqual(
            decision["selected_approach_id"], "femur_retrograde_nailing_entry"
        )
        self.assertTrue(decision["approaches"])

        generic = approach_decision_payload("femoral IMN", seed)
        self.assertEqual(generic["status"], "selected")
        self.assertIn(
            "femur_retrograde_nailing_entry",
            {option["approach_id"] for option in generic["approaches"]},
        )

    def test_named_nailing_corridor_is_selected(self):
        packet = self._payload("tibial_shaft_fracture_orif")
        decision = approach_decision_payload("suprapatellar tibial nailing", packet)
        self.assertEqual(decision["status"], "selected")
        self.assertEqual(
            decision["selected_approach_id"], "tibia_suprapatellar_nail_entry"
        )

    def test_plating_filters_out_nails_and_external_fixation(self):
        packet = self._payload("femoral_shaft_fracture_orif")
        decision = approach_decision_payload("femoral shaft plating", packet)
        self.assertEqual(decision["status"], "selected")
        self.assertEqual(
            {option["approach_id"] for option in decision["approaches"]},
            {"femoral_shaft_lateral_mipo", "femoral_shaft_lateral_open"},
        )

    def test_external_fixation_selects_pin_corridor_not_an_open_exposure(self):
        packet = self._payload("femoral_shaft_fracture_orif")
        decision = approach_decision_payload(
            "external fixation femoral shaft", packet
        )
        self.assertEqual(decision["status"], "selected")
        self.assertEqual(
            decision["selected_approach_id"],
            "femoral_shaft_external_fixator_pin_locations",
        )

    def test_arthroscopy_never_substitutes_medial_parapatellar_arthrotomy(self):
        for prompt, slug in (
            ("arthroscopic ACL reconstruction", "acl_reconstruction"),
            ("knee arthroscopy meniscus repair", "meniscus_repair"),
        ):
            with self.subTest(prompt=prompt):
                decision = approach_decision_payload(prompt, self._payload(slug))
                self.assertEqual(decision["status"], "unavailable")
                self.assertFalse(decision["approaches"])

    def test_femoral_neck_percutaneous_pinning_does_not_select_an_open_approach(self):
        seed = {
            "schema_version": "brobot_case_prep_payload_v2",
            "procedure_id": "femoral_neck_fracture_orif_young",
            "case_prep_status": "unreviewed",
            "procedure_overview": "",
        }
        decision = approach_decision_payload(
            "perc pinning for fem neck fracture", seed
        )
        self.assertEqual(decision["status"], "unavailable")
        self.assertIsNone(decision["selected_approach_id"])
        self.assertFalse(decision["approaches"])
        names = {option["name"] for option in decision["approaches"]}
        self.assertFalse(any("Pediatric" in name for name in names))
        self.assertFalse(any("ESIN" in name for name in names))

    def test_migrated_packet_cannot_pass_review_gate_by_manifest_flag(self):
        result = validate_review_gate(self._payload("hip_hemiarthroplasty"))
        self.assertFalse(result["passed"])
        self.assertEqual(set(result["missing_agent_roles"]), set(AGENT_REVIEW_ROLES))

    def test_native_v3_packet_still_recomputes_hash_bound_review_state(self):
        packet = normalize_packet(self._payload("hip_hemiarthroplasty"))
        packet["review"]["status"] = "agent_reviewed"
        packet["review"]["completed_agent_reviews"] = sorted(AGENT_REVIEW_ROLES)
        normalized = normalize_packet(packet)
        self.assertEqual(normalized["review"]["status"], "agent_review_pending")
        self.assertEqual(normalized["review"]["completed_agent_reviews"], [])
        self.assertTrue(normalized["review"]["content_hash"])


if __name__ == "__main__":
    unittest.main()
