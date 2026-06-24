from __future__ import annotations

import json
import unittest

from caseprep.services.registry_read_service import (
    ProcedureNotFoundError,
    compute_is_live,
    get_health,
    get_index,
    get_procedure_detail,
)


class RegistryReadServiceTests(unittest.TestCase):
    def test_health_reports_registry_available(self):
        health = get_health()
        self.assertTrue(health.registry_available)
        self.assertGreater(health.procedure_count, 0)
        self.assertEqual(health.schema_version, "caseprep_registry_read_v1")

    def test_index_does_not_expose_certified_payload(self):
        index = get_index()
        payload = json.dumps(index.model_dump())
        self.assertNotIn("certified_payload", payload)
        self.assertNotIn("data/caseprep", payload)
        self.assertGreater(len(index.procedures), 0)

    def test_tka_detail_has_clinical_sections_without_payload_blob(self):
        detail = get_procedure_detail("tka", include_validation=True)
        serialized = json.dumps(detail.model_dump())

        self.assertNotIn("certified_payload", serialized)
        self.assertNotIn("source_payload_hash", serialized)
        self.assertEqual(detail.slug, "tka")
        self.assertTrue(detail.is_live)
        self.assertEqual(len(detail.sections), 11)
        self.assertEqual(detail.sections[0].key, "indications")
        self.assertEqual(detail.sections[0].label, "Indications")
        self.assertEqual(detail.sections[-1].key, "sources")
        postop = next(s for s in detail.sections if s.key == "postop_plan")
        self.assertEqual(postop.label, "Post-op Protocol")

    def test_partial_procedure_is_not_live(self):
        detail = get_procedure_detail("acdf", include_validation=True)
        self.assertFalse(detail.is_live)
        self.assertEqual(detail.content_status, "draft")

    def test_unknown_slug_raises_not_found(self):
        with self.assertRaises(ProcedureNotFoundError):
            get_procedure_detail("not_real_slug")

    def test_compute_is_live_requires_certified_payload_file(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            manifest = {
                "runtime_enabled": True,
                "content_status": "certified",
                "review_status": "certified",
                "deprecated": False,
            }
            self.assertFalse(compute_is_live(manifest, folder))
            (folder / "certified_payload.json").write_text("{}", encoding="utf-8")
            self.assertTrue(compute_is_live(manifest, folder))


if __name__ == "__main__":
    unittest.main()