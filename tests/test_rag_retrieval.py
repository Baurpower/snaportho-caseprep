from __future__ import annotations

import threading
import time
import unittest
from unittest.mock import patch

from caseprep.services.rag_retrieval import (
    apply_v1_2_relevance_gate,
    bundled_case_qas,
    build_query_branches,
    normalize_match,
    normalize_query,
    retrieve_case_qas,
    rerank_and_dedupe,
)


class FakeIndex:
    def __init__(self, matches_by_call):
        self.matches_by_call = list(matches_by_call)
        self.calls = []
        self.lock = threading.Lock()

    def query(self, **kwargs):
        time.sleep(0.01)
        with self.lock:
            index = len(self.calls)
            self.calls.append(kwargs)
        return {"matches": self.matches_by_call[index]}


def match(record_id, score, question, answer, **metadata):
    return {
        "id": record_id,
        "score": score,
        "metadata": {"question": question, "answer": answer, **metadata},
    }


class RagRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.refined = {
            "search_text": "Open carpal tunnel release",
            "specialties": ["hand"],
            "region": "hand",
            "subregion": "carpal_tunnel",
            "diagnoses": ["carpal_tunnel_syndrome"],
            "procedures": ["carpal_tunnel_release"],
        }

    def test_normalizes_singular_legacy_metadata(self):
        candidate = normalize_match(
            match(
                "pp-1",
                0.8,
                "What nerve is decompressed?",
                "Median nerve",
                procedure="Carpal Tunnel Release",
                diagnosis="Carpal Tunnel Syndrome",
                specialty="Hand",
            ),
            "exact_scope",
        )
        self.assertEqual(candidate["procedures"], ["carpal_tunnel_release"])
        self.assertEqual(candidate["diagnoses"], ["carpal_tunnel_syndrome"])
        self.assertEqual(candidate["specialties"], ["hand"])

    def test_bundled_bank_maps_legacy_ankle_orif_to_canonical_slug(self):
        query = normalize_query({
            "search_text": "Ankle fracture ORIF",
            "procedures": ["ankle_fracture_orif"],
            "region": "ankle",
            "specialties": ["trauma"],
        })

        results = bundled_case_qas(query)

        self.assertGreaterEqual(len(results), 5)
        self.assertTrue(all(row["retrieval_branch"] == "bundled_fallback" for row in results))
        joined = " ".join(row["question"].lower() for row in results)
        self.assertTrue("ankle" in joined or "syndesm" in joined or "fibula" in joined)

    def test_bundled_bank_survives_vector_service_failure(self):
        diagnostics = {}

        results = retrieve_case_qas(
            {
                "search_text": "Ankle fracture ORIF",
                "procedures": ["ankle_fracture_orif"],
                "region": "ankle",
            },
            embed_fn=lambda _: (_ for _ in ()).throw(RuntimeError("offline")),
            index_obj=FakeIndex([]),
            diagnostics=diagnostics,
            use_cache=False,
        )

        self.assertGreaterEqual(len(results), 5)
        self.assertEqual(diagnostics["failed_branches"], ["vector_setup"])
        self.assertEqual(diagnostics["bundled_fallback_count"], len(results))

    def test_pocket_pimped_branch_is_source_filtered(self):
        branches = build_query_branches(normalize_query(self.refined))
        pocket_filter = dict(branches)["pocket_pimped"]
        self.assertIn("source_collection", repr(pocket_filter))
        self.assertIn("content_type", repr(pocket_filter))

    def test_strict_mode_source_filters_every_branch(self):
        with patch.dict("os.environ", {"CASEPREP_POCKET_PIMP_METADATA_READY": "true"}):
            branches = build_query_branches(normalize_query(self.refined))
        self.assertTrue(branches)
        self.assertTrue(all("source_collection" in repr(filter_value) for _, filter_value in branches))

    def test_extracts_qa_from_embedded_text_when_fields_are_missing(self):
        candidate = normalize_match(
            {
                "id": "pp-text",
                "score": 0.8,
                "metadata": {"text": "Q: What is released? A: Transverse carpal ligament Note: Protect the median nerve"},
            },
            "procedure_focus",
        )
        self.assertEqual(candidate["question"], "What is released?")
        self.assertEqual(candidate["answer"], "Transverse carpal ligament")
        self.assertEqual(candidate["additional_info"], "Protect the median nerve")

    def test_uses_one_embedding_parallel_scoped_queries_and_dedupes(self):
        query = normalize_query(self.refined)
        branch_count = len(build_query_branches(query))
        exact = match(
            "pp-exact",
            0.78,
            "What nerve is decompressed?",
            "Median nerve",
            procedures=["carpal_tunnel_release"],
            diagnoses=["carpal_tunnel_syndrome"],
            region="hand",
        )
        duplicate = match(
            "pp-duplicate",
            0.92,
            "Which nerve is decompressed?",
            "The median nerve",
            region="hand",
        )
        incomplete = {"id": "fact", "score": 0.99, "metadata": {"text": "not a Q/A"}}
        index = FakeIndex([[exact, incomplete], [duplicate], []][:branch_count])
        embedding_calls = []

        results = retrieve_case_qas(
            self.refined,
            embed_fn=lambda text: embedding_calls.append(text) or [0.1, 0.2],
            index_obj=index,
        )

        self.assertEqual(len(embedding_calls), 1)
        self.assertEqual(len(index.calls), branch_count)
        self.assertTrue(all(call["top_k"] == 24 for call in index.calls))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["record_id"], "pp-exact")

    def test_one_failed_branch_does_not_discard_other_results(self):
        class PartiallyFailingIndex(FakeIndex):
            def query(self, **kwargs):
                with self.lock:
                    index = len(self.calls)
                    self.calls.append(kwargs)
                if index == 0:
                    raise RuntimeError("branch unavailable")
                return {"matches": [match(f"ok-{index}", 0.8, f"Question {index}?", "Answer", region="hand")]}

        results = retrieve_case_qas(
            self.refined,
            embed_fn=lambda _: [0.1],
            index_obj=PartiallyFailingIndex([]),
        )
        self.assertGreaterEqual(len(results), 1)

    def test_rejects_explicit_cross_procedure_and_opposite_approach_results(self):
        query = normalize_query({**self.refined, "approaches": ["posterior"]})
        wrong = normalize_match(match("wrong", .9, "What is at risk?", "Lateral femoral cutaneous nerve", procedure="tha_anterior"), "regional_backup")
        right = normalize_match(match("right", .8, "What is at risk?", "Median nerve", procedure="carpal_tunnel_release"), "exact_scope")
        self.assertEqual([row["record_id"] for row in rerank_and_dedupe([wrong, right], query)], ["right"])

    def test_v12_relevance_gate_rejects_unrelated_and_caps_regional_backfill(self):
        query = normalize_query(self.refined)
        candidates = [
            {
                "record_id": "direct",
                "question": "What is released?",
                "answer": "Transverse carpal ligament",
                "additional_info": "",
                "procedures": ["carpal_tunnel_release"],
                "retrieval_branch": "procedure_focus",
                "retrieval_score": 0.9,
            },
            {
                "record_id": "regional-1",
                "question": "What hand structure is nearby?",
                "answer": "Median nerve",
                "additional_info": "",
                "procedures": [],
                "retrieval_branch": "semantic_fallback",
                "retrieval_score": 0.82,
            },
            {
                "record_id": "regional-2",
                "question": "What hand tendon is nearby?",
                "answer": "FPL",
                "additional_info": "",
                "procedures": [],
                "retrieval_branch": "semantic_fallback",
                "retrieval_score": 0.81,
            },
            {
                "record_id": "drift",
                "question": "What is the Lisfranc interval?",
                "answer": "Medial cuneiform to second metatarsal",
                "additional_info": "",
                "procedures": ["lisfranc_orif"],
                "retrieval_branch": "semantic_fallback",
                "retrieval_score": 0.99,
            },
        ]

        accepted, rejected = apply_v1_2_relevance_gate(candidates, query, limit=5)

        self.assertEqual([row["record_id"] for row in accepted], ["direct", "regional-1"])
        self.assertEqual(accepted[0]["procedure_relevance"], "direct")
        self.assertEqual(rejected, {"regional_cap": 1, "unrelated": 1})


if __name__ == "__main__":
    unittest.main()
