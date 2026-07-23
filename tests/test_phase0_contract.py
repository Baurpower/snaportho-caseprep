from __future__ import annotations

import ast
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from caseprep.config import CasePrepConfig


ROOT = Path(__file__).resolve().parents[1]


class Phase0ContractTests(unittest.TestCase):
    def test_caseprep_request_owns_version_override(self):
        tree = ast.parse((ROOT / "caseprep" / "schemas.py").read_text(encoding="utf-8"))
        classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}

        def annotated_fields(class_name):
            return {
                node.target.id
                for node in classes[class_name].body
                if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
            }

        self.assertIn("version", annotated_fields("CasePrepRequest"))
        self.assertNotIn("version", annotated_fields("PinnedCasePrepFollowupRequest"))

    def test_defaults_keep_legacy_route_and_web_preview_off(self):
        env_names = (
            "CASEPREP_DEFAULT_VERSION",
            "ENABLE_CASEPREP_V2",
            "ENABLE_CASEPREP_V2_AI_FALLBACK",
            "ENABLE_CASEPREP_V2_RAG_FALLBACK",
            "ENABLE_CASEPREP_WEB_V1_1",
        )
        with patch.dict(os.environ, {}, clear=False):
            for name in env_names:
                os.environ.pop(name, None)
            config = CasePrepConfig.from_env()
        self.assertEqual(config.default_version, "v1")
        self.assertFalse(config.enable_web_v1_1)

    def test_versioned_routes_are_additive_and_v2_returns(self):
        tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
        functions = {
            node.name: node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        legacy_source = ast.unparse(functions["case_prep"])
        self.assertNotIn("v1_1_web", legacy_source)
        self.assertTrue(any(isinstance(node, ast.Return) for node in ast.walk(functions["case_prep_v2"])))
        self.assertIn("case_prep_web_v1_1", functions)


if __name__ == "__main__":
    unittest.main()
