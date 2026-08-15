from __future__ import annotations

import unittest

from caseprep.services.rag_retrieval import bundled_semantic_qas, normalize_query
from caseprep.engines.v1_1_web_stream import _merge_pimp_questions
from caseprep.services.prompt_understanding import extract_prompt_profile
from procedure_registry import resolve_procedure


class V12RealCaseRegressionTests(unittest.TestCase):
    def test_implicit_question_without_question_mark_is_detected(self):
        profile = extract_prompt_profile(
            "Cutting more proximal tibia and more distal femur affect which gaps respectively during TKA"
        )
        self.assertTrue(profile["explicit_question"])

    def test_high_risk_modifiers_route_before_broad_aliases(self):
        cases = {
            "Anterior total hip arthroplasty": "tha_anterior",
            "cement spacer for infected TKA": "revision_tka",
            "Subtrochanteric fracture IM NAIL": "subtrochanteric_femur_fracture_im_nail",
            "Triceps tendon repair": "triceps_tendon_repair",
            "Menisectomy": "partial_meniscectomy",
            "Posterior fusion for scoliosis": "posterior_spinal_fusion_scoliosis",
            "volar ganglion cyst removal": "wrist_ganglion_excision",
            "Minimally invasive partial plantar fasciotomy, left side": "plantar_fasciitis_release",
            "IMN left tibia": "tibial_shaft_im_nail",
            "ORIF proximal tibia": "tibial_plateau_fracture_orif",
        }
        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                self.assertEqual(resolve_procedure(prompt, openai_client=False)["procedure_slug"], expected)

    def test_explicit_question_ranks_direct_answer_first(self):
        query = normalize_query({
            "search_text": "Cutting more proximal tibia and more distal femur affect which gaps respectively during total knee arthroplasty",
            "procedures": ["tka"],
            "region": "knee",
            "explicit_question": True,
        })
        rows = bundled_semantic_qas(query, limit=8)
        self.assertGreaterEqual(len(rows), 2)
        first_two = " ".join(row["question"].lower() for row in rows[:2])
        self.assertIn("proximal tibia", first_two)
        self.assertIn("distal femur", first_two)

    def test_explicit_question_outranks_generic_curated_questions(self):
        prompt = "Cutting more proximal tibia and more distal femur affect which gaps respectively during TKA"
        generic = [{"question": "What is the most common TKA approach?", "answer": "Medial parapatellar"}]
        direct = [
            {"question": "Cutting more bone from the distal femur increases which gap?", "answer": "Extension gap"},
            {"question": "Cutting more bone from the proximal tibia increases which gaps?", "answer": "Flexion and extension"},
        ]
        merged = _merge_pimp_questions(generic, direct, prompt=prompt, prioritize_prompt=True)
        first_two = " ".join(item["question"].lower() for item in merged[:2])
        self.assertIn("distal femur", first_two)
        self.assertIn("proximal tibia", first_two)

    def test_infection_modifier_excludes_generic_primary_tka_backfill(self):
        query = normalize_query({
            "search_text": "cement spacer for infected TKA",
            "procedures": ["revision_tka"],
            "region": "knee",
            "modifiers": ["infection", "revision", "operative"],
        })
        rows = bundled_semantic_qas(query, limit=15)
        self.assertTrue(rows)
        combined = " ".join(f"{row['question']} {row['answer']}" for row in rows).lower()
        self.assertRegex(combined, r"infect|aspirat|wbc|spacer|septic|pji")
        self.assertNotIn("most common approach for a tka", combined)

    def test_sparse_procedure_gets_grounded_regional_backfill(self):
        query = normalize_query({
            "search_text": "Subtrochanteric fracture IM NAIL",
            "procedures": ["subtrochanteric_femur_fracture_im_nail"],
            "region": "hip",
            "modifiers": ["operative"],
        })
        rows = bundled_semantic_qas(query, limit=8)
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(row["record_id"].startswith("bundled-pp-") for row in rows))
        self.assertTrue(any("subtrochanteric" in row["question"].lower() for row in rows))

    def test_sparse_recognized_procedure_without_name_overlap_gets_regional_backfill(self):
        query = normalize_query({
            "search_text": "Hip disarticulation",
            "procedures": ["hip_disarticulation"],
            "region": "hip",
            "modifiers": ["operative"],
        })
        rows = bundled_semantic_qas(query, limit=8)
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(row["record_id"].startswith("bundled-pp-") for row in rows))


if __name__ == "__main__":
    unittest.main()
