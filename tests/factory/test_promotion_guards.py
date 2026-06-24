from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from caseprep.factory.audit_log import AUDIT_LOG_PATH, record_audit_event
from caseprep.factory.compiler import CompilerError, compile_procedure
from caseprep.services.registry_read_service import ProcedureNotFoundError
from caseprep.services.registry_write_service import approve_procedure, promote_to_runtime


def _write_procedure(
    folder: Path,
    *,
    content_status: str = "draft",
    review_status: str = "unreviewed",
    runtime_enabled: bool = False,
    deprecated: bool = False,
    with_certified_payload: bool = False,
) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {
        "slug": folder.name,
        "display_name": "Test Procedure",
        "specialty": "ortho",
        "body_region": "knee",
        "procedure_family": "test",
        "content_status": content_status,
        "review_status": review_status,
        "coverage_score": 90,
        "runtime_enabled": runtime_enabled,
        "deprecated": deprecated,
    }
    modules = {
        "indications": ["Indication one."],
        "setup_positioning": ["Supine position."],
        "approach_landmarks": ["Landmark."],
        "surgical_layers": [
            {"layer_name": "Skin", "what_user_should_know": "x", "surgical_relevance": "y"}
        ],
        "structures_at_risk": [
            {
                "structure": "Nerve",
                "why_at_risk": "a",
                "how_to_avoid_injury": "b",
                "consequence_of_injury": "c",
            }
        ],
        "pitfalls": ["Pitfall."],
        "attending_pimp_questions": [{"question": "Q", "answer": "A"}],
        "postop_plan": ["Weight-bearing toe-touch for 6 weeks."],
    }
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (folder / "modules.json").write_text(json.dumps(modules), encoding="utf-8")
    (folder / "sources.jsonl").write_text("", encoding="utf-8")
    if with_certified_payload:
        (folder / "certified_payload.json").write_text(
            json.dumps({"procedure_id": folder.name, "schema_version": "brobot_case_prep_payload_v2"}),
            encoding="utf-8",
        )


class CompilerPromotionGuardTests(unittest.TestCase):
    def test_compile_default_does_not_overwrite_live_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "proc"
            _write_procedure(folder, with_certified_payload=True)
            original = (folder / "certified_payload.json").read_text(encoding="utf-8")

            with mock.patch("caseprep.factory.compiler.procedure_dir", return_value=folder):
                result = compile_procedure("proc", promote=False)

            self.assertTrue(result["output_path"].endswith("certified_payload.draft.json"))
            self.assertEqual((folder / "certified_payload.json").read_text(encoding="utf-8"), original)
            self.assertTrue((folder / "certified_payload.draft.json").exists())

    def test_compile_promote_refuses_if_not_approved(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "proc"
            _write_procedure(folder, review_status="needs_review")

            with mock.patch("caseprep.factory.compiler.procedure_dir", return_value=folder):
                with self.assertRaises(CompilerError):
                    compile_procedure("proc", promote=True, actor="dr_smith")

            self.assertFalse((folder / "certified_payload.json").exists())

    def test_compile_promote_refuses_with_blocking_qa_issues(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "proc"
            _write_procedure(folder, review_status="approved")
            (folder / "generation_meta.json").write_text(
                json.dumps(
                    {
                        "procedure_id": "proc",
                        "generated_at": "2026-01-01T00:00:00Z",
                        "blocking_issues": ["placeholder text detected"],
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch("caseprep.factory.compiler.procedure_dir", return_value=folder):
                with self.assertRaises(CompilerError):
                    compile_procedure("proc", promote=True, actor="dr_smith")

    def test_compile_promote_requires_actor(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "proc"
            _write_procedure(folder, review_status="approved")

            with mock.patch("caseprep.factory.compiler.procedure_dir", return_value=folder):
                with self.assertRaises(CompilerError):
                    compile_procedure("proc", promote=True, actor=None)

    def test_compile_promote_succeeds_when_approved_and_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "proc"
            _write_procedure(folder, review_status="approved")

            with mock.patch("caseprep.factory.compiler.procedure_dir", return_value=folder):
                result = compile_procedure("proc", promote=True, actor="dr_smith")

            self.assertTrue((folder / "certified_payload.json").exists())
            self.assertFalse(result["override_used"])

    def test_compile_promote_override_requires_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "proc"
            _write_procedure(folder, review_status="needs_review")

            with mock.patch("caseprep.factory.compiler.procedure_dir", return_value=folder):
                with self.assertRaises(CompilerError):
                    compile_procedure("proc", promote=True, actor="dr_smith", override_reason="")

                result = compile_procedure(
                    "proc", promote=True, actor="dr_smith", override_reason="emergency hotfix, reviewed verbally"
                )
            self.assertTrue(result["override_used"])
            self.assertTrue((folder / "certified_payload.json").exists())


class ApproveProcedureTests(unittest.TestCase):
    def test_approve_refuses_with_blocking_qa_issues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "proc"
            _write_procedure(folder, review_status="needs_review")
            (folder / "generation_meta.json").write_text(
                json.dumps(
                    {
                        "procedure_id": "proc",
                        "generated_at": "2026-01-01T00:00:00Z",
                        "blocking_issues": ["placeholder text detected"],
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch("caseprep.services.registry_write_service.REGISTRY_ROOT", root):
                with self.assertRaises(ValueError):
                    approve_procedure("proc", "dr_smith")


class PromoteToRuntimeTests(unittest.TestCase):
    def test_promote_refuses_uncertified_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "proc"
            _write_procedure(folder, content_status="draft", review_status="needs_review")

            with mock.patch("caseprep.services.registry_write_service.REGISTRY_ROOT", root):
                with self.assertRaises(ValueError):
                    promote_to_runtime("proc", "dr_smith")

    def test_promote_refuses_unknown_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch("caseprep.services.registry_write_service.REGISTRY_ROOT", root):
                with self.assertRaises(ProcedureNotFoundError):
                    promote_to_runtime("does_not_exist", "dr_smith")

    def test_promote_requires_existing_certified_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "proc"
            _write_procedure(
                folder,
                content_status="certified",
                review_status="certified",
                with_certified_payload=False,
            )

            with mock.patch("caseprep.services.registry_write_service.REGISTRY_ROOT", root):
                with self.assertRaises(ValueError):
                    promote_to_runtime("proc", "dr_smith")

    def test_promote_sets_runtime_enabled_after_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "proc"
            _write_procedure(
                folder,
                content_status="certified",
                review_status="certified",
                runtime_enabled=False,
                with_certified_payload=True,
            )

            with mock.patch("caseprep.services.registry_write_service.REGISTRY_ROOT", root), \
                 mock.patch(
                     "caseprep.services.registry_write_service._rebuild_registry_index",
                     return_value=False,
                 ):
                result = promote_to_runtime("proc", "dr_smith")

            self.assertTrue(result["runtime_enabled"])
            self.assertEqual(result["validation_result"], "passed")
            manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["runtime_enabled"])
            self.assertEqual(manifest["promoted_by"], "dr_smith")

    def test_promote_override_requires_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "proc"
            _write_procedure(folder, content_status="draft", review_status="needs_review")

            with mock.patch("caseprep.services.registry_write_service.REGISTRY_ROOT", root):
                with self.assertRaises(ValueError):
                    promote_to_runtime("proc", "dr_smith", override_reason="")


class AuditLogTests(unittest.TestCase):
    def test_record_audit_event_appends_jsonl_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_path = Path(tmp) / "audit_log.jsonl"
            with mock.patch("caseprep.factory.audit_log.AUDIT_LOG_PATH", fake_path):
                entry = record_audit_event(
                    actor="dr_smith",
                    action="approve",
                    slug="proc",
                    previous_status="needs_review",
                    new_status="approved",
                )
            lines = fake_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            logged = json.loads(lines[0])
            self.assertEqual(logged["actor"], "dr_smith")
            self.assertEqual(logged["action"], "approve")
            self.assertEqual(logged["id"], entry["id"])
            self.assertNotIn("api_key", logged)

    def test_record_audit_event_rejects_unknown_action(self):
        with self.assertRaises(ValueError):
            record_audit_event(actor="dr_smith", action="delete_everything", slug="proc")


if __name__ == "__main__":
    unittest.main()
