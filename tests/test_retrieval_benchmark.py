from __future__ import annotations

import unittest

from caseprep.evaluation.retrieval_benchmark import evaluate_case, summarize


class RetrievalBenchmarkTests(unittest.TestCase):
    def test_scores_recall_relevance_contamination_and_duplicates(self):
        case = {
            "case_id": "ctr",
            "must_include_terms": ["median nerve", "transverse carpal ligament"],
            "acceptable_terms": ["recurrent motor branch"],
            "prohibited_terms": ["ulnar nerve"],
        }
        candidates = [
            {"question": "What nerve?", "answer": "Median nerve"},
            {"question": "What is released?", "answer": "Transverse carpal ligament"},
            {"question": "What nerve?", "answer": "Median nerve"},
            {"question": "Wrong structure?", "answer": "Ulnar nerve"},
        ]
        result = evaluate_case(case, candidates)
        self.assertEqual(result["must_include_recall"], 1.0)
        self.assertEqual(result["contamination"], 1.0)
        self.assertGreater(result["duplicate_rate"], 0)
        self.assertEqual(result["top_k_relevance"], 0.75)

    def test_summary_includes_empty_result_rate(self):
        summary = summarize(
            [
                {"result_count": 0, "must_include_recall": 0, "top_k_relevance": 0, "contamination": 0, "duplicate_rate": 0},
                {"result_count": 2, "must_include_recall": 1, "top_k_relevance": 1, "contamination": 0, "duplicate_rate": 0},
            ]
        )
        self.assertEqual(summary["empty_result_rate"], 0.5)
        self.assertEqual(summary["must_include_recall"], 0.5)


if __name__ == "__main__":
    unittest.main()
