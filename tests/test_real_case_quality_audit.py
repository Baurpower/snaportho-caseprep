from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_v12_supabase_cases import load_cases, summarize


class RealCaseQualityAuditTests(unittest.TestCase):
    def test_load_cases_reuses_prior_audit_without_historical_answers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cohort.json"
            path.write_text(json.dumps({"results": [
                {
                    "response_id": 7,
                    "created_at": "2026-01-01T00:00:00Z",
                    "question": "Distal radius ORIF",
                    "pimp_questions": [{"answer": "must not be copied"}],
                }
            ]}))

            self.assertEqual(load_cases(path, 100), [{
                "response_id": 7,
                "created_at": "2026-01-01T00:00:00Z",
                "question": "Distal radius ORIF",
            }])

    def test_summary_enforces_expected_version_and_counts_region_mismatch(self):
        results = [{
            "response_id": 1,
            "question": "Distal radius ORIF",
            "elapsed_ms": 100,
            "caseprep_version": "v1.1",
            "compatibility_status": "valid",
            "region_consistent": False,
            "quality_gate": "limited",
            "coverage_status": "grounded_partial",
            "pimp_count": 1,
            "citation_count": 1,
            "utility_score": 50,
        }]

        summary = summarize(results, "http://local", "v1.2", "frozen.json")

        self.assertEqual(summary["version_confirmed"], 0)
        self.assertEqual(summary["version_counts"], {"v1.1": 1})
        self.assertEqual(summary["region_mismatches"], 1)
        self.assertEqual(summary["cohort_source"], "frozen.json")


if __name__ == "__main__":
    unittest.main()
