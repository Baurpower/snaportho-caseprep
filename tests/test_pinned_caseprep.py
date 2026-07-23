import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from caseprep.factory import clinical_review
from caseprep.services import pinned_caseprep
from scripts.caseprep.build_ctr_review_package import initial_content


class PinnedCasePrepTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patch_review = patch.object(
            clinical_review, "procedure_dir", side_effect=lambda slug: self.root / slug
        )
        self.patch_pinned = patch.object(
            pinned_caseprep, "review_dir", side_effect=lambda slug: self.root / slug / "clinical_review"
        )
        self.patch_review.start()
        self.patch_pinned.start()
        self.revision = clinical_review.create_revision(
            "carpal_tunnel_release",
            initial_content(),
            parent_revision_id=None,
            created_by="test",
            change_summary=["test"],
        )
        pointer = {
            "revision_id": self.revision["revision_id"],
            "content_hash": self.revision["content_hash"],
            "payload_hash": "payload-123",
        }
        path = self.root / "carpal_tunnel_release" / "clinical_review" / "published_revision.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(pointer), encoding="utf-8")

    def tearDown(self):
        self.patch_pinned.stop()
        self.patch_review.stop()
        self.temp.cleanup()

    def test_anatomy_question_uses_pinned_content(self):
        result = pinned_caseprep.answer_from_pinned_revision(
            slug="carpal_tunnel_release",
            revision_id=self.revision["revision_id"],
            payload_hash="payload-123",
            question="What is the recurrent motor branch anatomy?",
        )
        self.assertEqual(result["answer_status"], "curated")
        self.assertTrue(result["sections"])

    def test_stale_revision_is_rejected(self):
        with self.assertRaises(pinned_caseprep.PinnedCasePrepError):
            pinned_caseprep.answer_from_pinned_revision(
                slug="carpal_tunnel_release",
                revision_id="stale",
                payload_hash="payload-123",
                question="anatomy",
            )

    def test_missing_answer_does_not_invent(self):
        result = pinned_caseprep.answer_from_pinned_revision(
            slug="carpal_tunnel_release",
            revision_id=self.revision["revision_id"],
            payload_hash="payload-123",
            question="What antibiotic dose should I give?",
        )
        self.assertEqual(result["answer_status"], "not_in_curated_packet")
        self.assertFalse(result["supplemental_retrieval_used"])


if __name__ == "__main__":
    unittest.main()
