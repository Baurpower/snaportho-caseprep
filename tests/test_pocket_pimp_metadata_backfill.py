from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "caseprep" / "backfill_pocket_pimp_metadata.py"
SPEC = importlib.util.spec_from_file_location("backfill_pocket_pimp_metadata", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class PocketPimpMetadataBackfillTests(unittest.TestCase):
    def test_patch_adds_filterable_source_and_qa_metadata(self):
        patch = MODULE.metadata_patch(
            {
                "question": "What is released?",
                "answer": "Transverse carpal ligament",
                "additional_info": "Protect the median nerve.",
                "metadata": {
                    "specialty": "Hand",
                    "region": "Hand",
                    "diagnosis_raw": "Carpal tunnel syndrome",
                    "procedure": "Carpal tunnel release",
                },
            }
        )
        self.assertEqual(patch["source_collection"], "pocket_pimped")
        self.assertEqual(patch["content_type"], "qa")
        self.assertEqual(patch["diagnoses"], ["carpal_tunnel_syndrome"])
        self.assertEqual(patch["procedures"], ["carpal_tunnel_release"])

    def test_stable_id_matches_existing_upload_convention(self):
        self.assertEqual(
            MODULE.stable_id("Question", "Answer"),
            MODULE.stable_id("Question", "Answer"),
        )
        self.assertTrue(MODULE.stable_id("Question", "Answer").startswith("pp-"))


if __name__ == "__main__":
    unittest.main()
