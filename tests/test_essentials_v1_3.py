from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock

from caseprep.services.essentials_v1_3 import generate_essentials


VALID_RESPONSE = {
    "indications": {
        "summary": "Operate for symptomatic disease that has failed appropriate nonoperative care.",
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
        "summary": "Protect the reconstruction while beginning appropriate rehabilitation.",
        "immediate_priorities": ["Repeat and document the neurovascular examination"],
        "immobilization": "Use procedure-appropriate protection.",
        "weight_bearing": "Follow fixation- and surgeon-specific restrictions.",
        "motion": "Begin motion according to construct stability.",
        "follow_up": "Early wound and radiographic review.",
        "red_flags": ["New neurovascular deficit"],
        "variability_note": "Confirm the operating surgeon's protocol.",
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

    def test_no_client_degrades_without_error(self) -> None:
        result = generate_essentials(
            identity={"canonical_name": "Total Knee Arthroplasty"},
            payload=None,
            approach_prep={"sections": {}},
            openai_client=None,
            model="test-model",
        )
        self.assertIsNone(result)

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
