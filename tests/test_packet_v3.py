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
        self.assertEqual(decision["status"], "choice_required")
        self.assertEqual(len(decision["approaches"]), 4)
        self.assertEqual(decision["coverage"]["gap_count"], 0)
        self.assertEqual(
            {row["approach_id"] for row in decision["approaches"]},
            {
                "lateral_hardinge_hip",
                "approach_lower_ext_hip_posterior_moore_southern",
                "hip_anterior_smith_petersen",
                "hip_anterolateral_watson_jones",
            },
        )

    def test_explicit_hemi_approach_is_selected(self):
        packet = self._payload("hip_hemiarthroplasty")
        decision = approach_decision_payload("posterior hip hemiarthroplasty", packet)
        self.assertEqual(decision["status"], "selected")
        self.assertEqual(
            decision["selected_approach_id"],
            "approach_lower_ext_hip_posterior_moore_southern",
        )

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
