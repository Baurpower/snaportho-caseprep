from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from caseprep.factory.compiler import (
    CompilerError,
    compile_modules_to_payload,
    is_study_checklist_postop,
)
from caseprep.factory.orchestrator import generate_procedure_draft, list_batch_candidates
from caseprep.factory.qa_agent import score_generated_modules
from caseprep.factory.schemas import ExtractedKnowledge
from caseprep.registry.validation import modules_from_payload, score_modules


class FactoryCompilerTests(unittest.TestCase):
    def test_round_trip_tka_modules_shape(self):
        root = Path(__file__).resolve().parents[2]
        payload_path = root / "data/caseprep/procedures/tka/certified_payload.json"
        manifest_path = root / "data/caseprep/procedures/tka/manifest.json"
        modules_path = root / "data/caseprep/procedures/tka/modules.json"

        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        modules = json.loads(modules_path.read_text(encoding="utf-8"))

        compiled = compile_modules_to_payload(
            modules,
            slug="tka",
            manifest=manifest,
            existing_payload=payload,
            strict=False,
        )

        self.assertEqual(compiled["procedure_id"], "tka")
        self.assertEqual(compiled["schema_version"], "brobot_case_prep_payload_v2")
        self.assertGreaterEqual(len(compiled.get("structures_at_risk") or []), 3)
        self.assertGreaterEqual(len(compiled.get("must_know_anatomy") or []), 1)

        h1 = json.dumps(compiled, sort_keys=True)
        h2 = json.dumps(
            compile_modules_to_payload(
                modules, slug="tka", manifest=manifest, existing_payload=payload, strict=False
            ),
            sort_keys=True,
        )
        self.assertEqual(h1, h2)

    def test_modules_from_payload_inverse_coverage(self):
        root = Path(__file__).resolve().parents[2]
        payload = json.loads(
            (root / "data/caseprep/procedures/tka/certified_payload.json").read_text(encoding="utf-8")
        )
        modules = modules_from_payload(payload)
        score = score_modules(modules)
        self.assertGreaterEqual(score, 70)

    def test_strict_compile_fails_on_empty(self):
        with self.assertRaises(CompilerError):
            compile_modules_to_payload({}, slug="x", manifest={"display_name": "X"}, strict=True)


class FactoryQATests(unittest.TestCase):
    def test_qa_catches_placeholder(self):
        modules = {
            "indications": ["Indication"],
            "setup_positioning": ["See source-backed module or Orthobullets page for this fact."],
            "approach_landmarks": ["Landmark"],
            "surgical_layers": [{"layer_name": "L", "what_user_should_know": "x", "surgical_relevance": "y"}],
            "structures_at_risk": [
                {
                    "structure": "Nerve",
                    "why_at_risk": "a",
                    "how_to_avoid_injury": "b",
                    "consequence_of_injury": "c",
                }
            ],
            "pitfalls": ["Pitfall"],
            "attending_pimp_questions": [{"question": "Q", "answer": "A"}],
            "postop_plan": ["Weight-bearing toe-touch for 6 weeks."],
        }
        knowledge = ExtractedKnowledge(
            procedure_id="test",
            display_name="Test",
            extracted_at="2026-01-01T00:00:00Z",
            source_refs=["https://example.com"],
        )
        meta = score_generated_modules(modules, knowledge, {"slug": "test", "body_region": "knee"})
        self.assertTrue(any("placeholder" in b.lower() for b in meta.blocking_issues))

    def test_study_checklist_detection(self):
        self.assertTrue(
            is_study_checklist_postop(
                [
                    "Review linked modules and source URLs",
                    "Walk through the night-before checklist",
                ]
            )
        )


class FactoryOrchestratorTests(unittest.TestCase):
    def test_generate_refuses_certified_without_force(self):
        with self.assertRaises(RuntimeError):
            generate_procedure_draft("tka", dry_run=True, use_llm=False, force=False)

    def test_generate_dry_run_partial(self):
        result = generate_procedure_draft("tha_lateral", dry_run=True, use_llm=False)
        self.assertEqual(result["slug"], "tha_lateral")
        self.assertIn("coverage_score", result)

    def test_batch_dry_run_lists_candidates(self):
        rows = list_batch_candidates(limit=3, min_coverage=0, max_coverage=0)
        self.assertGreater(len(rows), 0)
        self.assertTrue(all(r["coverage_score"] <= 0 for r in rows))

    def test_manifest_not_certified_after_generate(self):
        with tempfile.TemporaryDirectory() as tmp:
            slug = "test_proc"
            folder = Path(tmp) / slug
            folder.mkdir()
            manifest = {
                "slug": slug,
                "display_name": "Test Proc",
                "body_region": "knee",
                "content_status": "partial",
                "review_status": "unreviewed",
                "coverage_score": 0,
                "runtime_enabled": False,
            }
            (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (folder / "modules.json").write_text("{}", encoding="utf-8")
            (folder / "sources.jsonl").write_text("", encoding="utf-8")

            with mock.patch("caseprep.factory.orchestrator.procedure_dir", return_value=folder):
                from caseprep.factory.orchestrator import update_manifest_for_review
                from caseprep.factory.schemas import GenerationMeta

                meta = GenerationMeta(
                    procedure_id=slug,
                    generated_at="2026-01-01T00:00:00Z",
                    coverage_score=55,
                    overall_quality_score=60.0,
                )
                updated = update_manifest_for_review(slug, meta=meta, dry_run=False)
                self.assertEqual(updated["review_status"], "needs_review")
                self.assertEqual(updated["content_status"], "draft")
                self.assertFalse(updated["runtime_enabled"])


if __name__ == "__main__":
    unittest.main()