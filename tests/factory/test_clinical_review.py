import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from caseprep.factory import clinical_review
from scripts.caseprep.build_ctr_review_package import initial_content


class ClinicalReviewContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patch = patch.object(
            clinical_review,
            "procedure_dir",
            side_effect=lambda slug: self.root / slug,
        )
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def revision(self, content=None):
        return clinical_review.create_revision(
            "carpal_tunnel_release",
            content or initial_content(),
            parent_revision_id=None,
            created_by="test_author",
            change_summary=["test"],
        )

    def test_edit_changes_revision_and_section_hash(self):
        first = self.revision()
        changed = copy.deepcopy(first["content"])
        changed["sections"]["operative_objective"].append("A changed claim.")
        second = clinical_review.create_revision(
            "carpal_tunnel_release",
            changed,
            parent_revision_id=first["revision_id"],
            created_by="test_reconciler",
            change_summary=["changed objective"],
        )
        self.assertNotEqual(first["revision_id"], second["revision_id"])
        self.assertNotEqual(
            first["section_hashes"]["operative_objective"],
            second["section_hashes"]["operative_objective"],
        )

    def test_stale_human_approval_is_invalid_for_changed_revision(self):
        first = self.revision()
        clinical_review.record_human_decision(
            "carpal_tunnel_release",
            first["revision_id"],
            reviewer_id="attending-1",
            decision="approve",
            section_hash_bindings=first["section_hashes"],
        )
        changed = copy.deepcopy(first["content"])
        changed["sections"]["pitfalls"].append("Changed content.")
        second = clinical_review.create_revision(
            "carpal_tunnel_release",
            changed,
            parent_revision_id=first["revision_id"],
            created_by="test_reconciler",
            change_summary=["changed pitfalls"],
        )
        self.assertIsNone(
            clinical_review.current_human_approval(
                "carpal_tunnel_release", second["revision_id"]
            )
        )

    def test_human_decision_rejects_mismatched_section_hashes(self):
        revision = self.revision()
        bindings = dict(revision["section_hashes"])
        bindings["anatomy"] = "stale"
        with self.assertRaises(ValueError):
            clinical_review.record_human_decision(
                "carpal_tunnel_release",
                revision["revision_id"],
                reviewer_id="attending-1",
                decision="approve",
                section_hash_bindings=bindings,
            )

    def test_unresolved_findings_block_qa(self):
        revision = self.revision()
        finding = clinical_review.finding(
            "adversarial_hallucination_reviewer",
            "anatomy",
            "unsafe",
            "critical",
            "A critical anatomy concern remains unresolved and requires adjudication.",
            human=True,
        )
        qa = clinical_review.deterministic_validate(
            revision, findings=[finding], dispositions=[]
        )
        self.assertFalse(qa["passed"])
        self.assertTrue(
            any(row["code"] == "finding_without_disposition" for row in qa["failures"])
        )

    def test_contamination_and_contradictory_postop_are_detected(self):
        content = initial_content()
        content["sections"]["anatomy"].append("ACL tunnel placement.")
        content["sections"]["postoperative_expectations"].extend(
            ["No wrist motion.", "Immediate wrist motion."]
        )
        revision = self.revision(content)
        qa = clinical_review.deterministic_validate(revision)
        codes = {row["code"] for row in qa["failures"]}
        self.assertIn("cross_procedure_contamination:acl", codes)
        self.assertIn("contradictory_postop_motion", codes)

    def test_publication_requires_current_human_approval(self):
        revision = self.revision()
        qa = clinical_review.deterministic_validate(revision)
        readiness = clinical_review.certification_readiness(
            "carpal_tunnel_release",
            revision["revision_id"],
            qa=qa,
            wave_count=2,
        )
        self.assertFalse(readiness["eligible"])
        self.assertIn("no current hash-bound human approval", readiness["reasons"])

    def test_malformed_finding_is_rejected(self):
        with self.assertRaises(ValueError):
            clinical_review.validate_finding(
                {
                    "finding_id": "bad",
                    "reviewer_role": "hand_surgery_content_reviewer",
                    "section_id": "anatomy",
                    "category": "incorrect",
                },
                initial_content()["sections"],
            )

    def test_missing_release_endpoints_and_threshold_are_detected(self):
        content = initial_content()
        content["sections"]["operative_objective"] = ["Decompress the nerve."]
        content["sections"]["postoperative_expectations"].append(
            "Patients must lift 10 kg at 2 weeks."
        )
        qa = clinical_review.deterministic_validate(self.revision(content))
        codes = {row["code"] for row in qa["failures"]}
        self.assertIn("release_endpoints_missing", codes)
        self.assertIn("unsupported_universal_number", codes)

    def test_compile_refuses_without_human_approval(self):
        revision = self.revision()
        qa = clinical_review.deterministic_validate(revision)
        with self.assertRaises(ValueError):
            clinical_review.compile_approved_revision(
                "carpal_tunnel_release",
                revision["revision_id"],
                qa=qa,
                wave_count=2,
            )

    def test_approved_compile_is_deterministic_and_revision_bound(self):
        content = initial_content()
        content["sections"]["postoperative_expectations"] = [
            item for item in content["sections"]["postoperative_expectations"]
            if "must return to work" not in item.lower()
        ]
        revision = self.revision(content)
        qa = clinical_review.deterministic_validate(revision)
        clinical_review.record_human_decision(
            "carpal_tunnel_release",
            revision["revision_id"],
            reviewer_id="attending-1",
            decision="approve",
            section_hash_bindings=revision["section_hashes"],
        )
        first = clinical_review.compile_approved_revision(
            "carpal_tunnel_release",
            revision["revision_id"],
            qa=qa,
            wave_count=2,
        )
        second = clinical_review.compile_approved_revision(
            "carpal_tunnel_release",
            revision["revision_id"],
            qa=qa,
            wave_count=2,
        )
        self.assertEqual(first["payload_hash"], second["payload_hash"])
        self.assertEqual(first["payload"]["revision_id"], revision["revision_id"])


if __name__ == "__main__":
    unittest.main()
