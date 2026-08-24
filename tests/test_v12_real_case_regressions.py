from __future__ import annotations

import unittest

from caseprep.services.rag_retrieval import bundled_semantic_qas, normalize_query
from caseprep.engines.v1_1_web_stream import _merge_pimp_questions
from caseprep.engines.v1_2_web_stream import _resolution_problem
from caseprep.services.prompt_understanding import extract_prompt_profile
from procedure_registry import REGISTRY, resolve_procedure


class V12RealCaseRegressionTests(unittest.TestCase):
    def test_every_registered_procedure_name_maps_to_its_canonical_region(self):
        for definition in REGISTRY:
            with self.subTest(procedure=definition.slug):
                profile = extract_prompt_profile(definition.display_name)
                self.assertEqual(profile["region"], definition.body_region)

    def test_region_disambiguation_prefers_specific_anatomy(self):
        cases = {
            "proximal humerus ORIF": "shoulder",
            "humeral shaft IM nail": "humerus",
            "distal radius ORIF": "wrist",
            "radial shaft ORIF": "forearm",
            "acetabulum posterior wall ORIF": "pelvis",
            "femoral neck ORIF": "hip",
            "distal femur ORIF": "femur",
            "proximal tibia ORIF": "knee",
            "tibial shaft IMN": "leg",
            "pilon ORIF": "ankle",
            "MTP 5th digit amputation": "foot",
        }
        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                self.assertEqual(extract_prompt_profile(prompt)["region"], expected)

    def test_generic_operation_words_do_not_invent_anatomy(self):
        for prompt in ("fusion", "repair", "ORIF", "revision surgery"):
            with self.subTest(prompt=prompt):
                self.assertEqual(extract_prompt_profile(prompt)["regions"], [])

    def test_common_operative_terms_are_detected(self):
        for prompt in (
            "SCFE pinning", "ankle arthrodesis", "high tibial osteotomy",
            "leg fasciotomy", "Dupuytren fasciectomy", "partial meniscectomy",
            "lumbar laminectomy", "closed reduction and percutaneous pinning",
        ):
            with self.subTest(prompt=prompt):
                self.assertIn("operative", extract_prompt_profile(prompt)["modifiers"])

    def test_case_sufficiency_recognizes_diagnoses_and_procedures(self):
        cases = {
            "infected total shoulder": (True, True),
            "undifferentiated pleomorphic sarcoma": (False, True),
            "MTP 5th digit amputation": (True, False),
            "right shoulder bone graft with distal tibia allograft": (True, False),
            "knee pain": (False, False),
        }
        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                profile = extract_prompt_profile(prompt)
                self.assertEqual(
                    (profile["has_procedure_intent"], profile["has_diagnosis_intent"]),
                    expected,
                )

    def test_vague_cases_receive_targeted_clarification(self):
        scenarios = {
            "Right shoulder": "planned procedure or the specific diagnosis",
            "knee pain": "planned procedure or the specific diagnosis",
            "undifferentiated pleomorphic sarcoma": "body region",
            "Tia": "body region and either the planned procedure or diagnosis",
        }
        for prompt, expected_message in scenarios.items():
            with self.subTest(prompt=prompt):
                problem = _resolution_problem(prompt, {}, {})
                self.assertIsNotNone(problem)
                self.assertIn(expected_message, problem["reason"])

    def test_useful_unresolved_cases_can_continue_with_regional_retrieval(self):
        for prompt in (
            "infected total shoulder",
            "lateral interbody fusion",
            "MTP 5th digit amputation",
            "osteochondral defect with ankle impingement",
        ):
            with self.subTest(prompt=prompt):
                self.assertIsNone(_resolution_problem(prompt, {}, {}))

    def test_mtp_digit_amputation_is_understood_without_clarification(self):
        prompt = "MTP 5th digit amputation"
        profile = extract_prompt_profile(prompt)

        self.assertEqual(profile["region"], "foot")
        self.assertIn("operative", profile["modifiers"])
        self.assertIsNone(_resolution_problem(prompt, {}, {}))

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
