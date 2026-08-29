from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock

from caseprep.services.essentials_v1_3 import (
    build_evidence,
    generate_essentials,
    verify_essentials,
)


VALID_RESPONSE = {
    "indications": {
        "summary": "Operate for end-stage arthritis after nonoperative treatment fails.",
        "key_points": ["Progressive functional limitation", "Failure of nonoperative treatment"],
        "case_specific_note": None,
    },
    "critical_portion": {
        "name": "Safe exposure",
        "summary": "Obtain exposure while protecting the principal structure at risk.",
        "why_it_matters": "Injury here produces the most consequential avoidable complication.",
        "execution_points": ["Identify the safe interval", "Confirm the structure is protected"],
        "failure_mode": "Unrecognized injury during exposure.",
    },
    "postop_protocol": {
        "summary": "Protect the reconstruction while beginning staged rehabilitation.",
        "immediate_priorities": ["Repeat and document the neurovascular examination"],
        "immobilization": "Use procedure-appropriate protection.",
        "weight_bearing": "Follow fixation- and surgeon-specific restrictions.",
        "motion": "Begin motion according to construct stability.",
        "follow_up": "Early wound and radiographic review.",
        "red_flags": ["New neurovascular deficit"],
        "variability_note": "Confirm the operating surgeon's protocol.",
    },
    "citations": {
        "indications.summary": ["E1"],
        "indications.key_points": ["E1"],
        "critical_portion.name": ["E1"],
        "critical_portion.summary": ["E1"],
        "critical_portion.why_it_matters": ["E1"],
        "critical_portion.execution_points": ["E1"],
        "critical_portion.failure_mode": ["E1"],
        "postop_protocol.summary": ["E1"],
        "postop_protocol.immediate_priorities": ["E1"],
        "postop_protocol.red_flags": ["E1"],
        "postop_protocol.immobilization": ["E1"],
        "postop_protocol.weight_bearing": ["E1"],
        "postop_protocol.motion": ["E1"],
        "postop_protocol.follow_up": ["E1"],
    },
}


class EssentialsV13Tests(unittest.TestCase):
    def test_generates_without_question_bank_or_pinecone_context(self) -> None:
        client = MagicMock()
        client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content=json.dumps(VALID_RESPONSE)))
        ]

        result = generate_essentials(
            identity={"canonical_name": "Total Knee Arthroplasty", "diagnosis": "Osteoarthritis"},
            payload={
                "procedure_overview": "Knee replacement for end-stage arthritis.",
                "source_urls": ["https://example.org/source"],
                "attending_pimp_questions": ["Q: This must not enter the prompt? A: Correct."],
            },
            approach_prep={"sections": {}},
            openai_client=client,
            model="test-model",
        )

        self.assertIsNotNone(result)
        prompt = client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
        self.assertNotIn("This must not enter the prompt", prompt)
        self.assertNotIn("pinecone", prompt.lower())
        self.assertEqual(result["payload"]["critical_portion"]["name"], "Safe exposure")
        self.assertEqual(result["confidence"], 0.89)
        self.assertTrue(result["payload"]["verification"]["passed"])

    def test_no_client_degrades_without_error(self) -> None:
        result = generate_essentials(
            identity={"canonical_name": "Total Knee Arthroplasty"},
            payload=None,
            approach_prep={"sections": {}},
            openai_client=None,
            model="test-model",
        )
        self.assertIsNone(result)

    def test_rejects_retrograde_case_with_antegrade_entry(self) -> None:
        output = json.loads(json.dumps(VALID_RESPONSE))
        output["critical_portion"]["summary"] = (
            "Place the retrograde nail through an intertrochanteric entry point."
        )
        evidence = [{
            "evidence_id": "E1",
            "text": "Use an intercondylar entry for retrograde nailing.",
            "source_ids": ["ao"],
            "kind": "approach",
        }]
        verification = verify_essentials(
            output, evidence, {"requested_case": "Retrograde femoral nail"}
        )
        self.assertFalse(verification["passed"])
        self.assertIn("antegrade proximal entry", " ".join(verification["errors"]))

    def test_build_evidence_prioritizes_approach_and_requires_sources(self) -> None:
        evidence = build_evidence(
            {"procedure_overview": "Uncited overview is excluded."},
            {"sections": {"approach_exposure": {"items": [{
                "answer": "Enter through the intercondylar notch.",
                "source_ids": ["orthobullets_12457"],
            }]}}},
        )
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["source_ids"], ["orthobullets_12457"])

    def test_selected_approach_excludes_legacy_wrong_corridor_context(self) -> None:
        evidence = build_evidence(
            {
                "surgical_approach_anatomy": ["Split vastus lateralis for lateral plating."],
                "source_urls": ["https://example.org/legacy"],
            },
            {
                "coverage": {"approach_id": "femur_retrograde_nailing_entry"},
                "sections": {"approach_exposure": {"items": [{
                    "answer": "Enter through the intercondylar notch.",
                    "source_ids": ["orthobullets_12457"],
                }]}},
            },
        )
        body = " ".join(row["text"] for row in evidence).lower()
        self.assertIn("intercondylar notch", body)
        self.assertNotIn("vastus lateralis", body)

    def test_rejects_uncited_core_claim(self) -> None:
        output = json.loads(json.dumps(VALID_RESPONSE))
        del output["citations"]["critical_portion.failure_mode"]
        verification = verify_essentials(
            output,
            [{"evidence_id": "E1", "text": "Evidence", "source_ids": ["s1"]}],
            {"canonical_name": "Test operation"},
        )
        self.assertFalse(verification["passed"])
        self.assertIn("critical_portion.failure_mode", " ".join(verification["errors"]))

    def test_rejects_generic_femoral_nailing_boilerplate(self) -> None:
        output = json.loads(json.dumps(VALID_RESPONSE))
        output["critical_portion"]["summary"] = (
            "Proper reaming and nail insertion provide adequate stabilization."
        )
        verification = verify_essentials(
            output,
            [{"evidence_id": "E1", "text": "Specific sourced fact", "source_ids": ["s1"]}],
            {"requested_case": "Retrograde femoral nail"},
        )
        self.assertFalse(verification["passed"])
        self.assertIn("generic essentials language", " ".join(verification["errors"]))

    def test_rejects_incomplete_model_response(self) -> None:
        client = MagicMock()
        client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content='{"indications": {}}'))
        ]
        result = generate_essentials(
            identity={"canonical_name": "Total Knee Arthroplasty"},
            payload=None,
            approach_prep={"sections": {}},
            openai_client=client,
            model="test-model",
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
