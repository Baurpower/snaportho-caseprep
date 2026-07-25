"""Resolver regression corpus built from real user prompts.

Prompts are taken verbatim from Supabase (`brobot_messages`, `case_prep_logs`)
plus the reported "distal biceps repair -> Elbow Arthroscopy" bug. The whole
point of the corpus is that a *wrong* confident answer is worse than no answer:
a resident who typed one procedure and is shown another one's anatomy, portals
and pimp questions has been actively misled.

Run: python -m unittest tests.test_procedure_resolver_corpus
"""

from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from procedure_registry import REGISTRY, SLUG_TO_DEF, resolve_procedure

CORPUS_PATH = Path(__file__).parent / "data" / "resolver_real_prompts.jsonl"


def load_corpus():
    return [
        json.loads(line)
        for line in CORPUS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def resolve_offline(prompt: str):
    """Resolve without the GPT stage (and without its debug prints)."""
    with redirect_stdout(io.StringIO()):
        # A non-None sentinel client makes stage D fail fast instead of
        # constructing a real OpenAI client, so the corpus exercises only the
        # deterministic stages.
        return resolve_procedure(prompt, openai_client=object())


class ResolverCorpus(unittest.TestCase):
    def test_real_prompts_resolve_to_the_procedure_that_was_typed(self):
        failures = []
        for row in load_corpus():
            result = resolve_offline(row["prompt"])
            actual = result.get("procedure_slug")
            if actual != row["expect"]:
                failures.append(
                    f"{row['prompt']!r}: expected {row['expect']}, got {actual} "
                    f"(method={result.get('match_method')}, {row['note']})"
                )
        self.assertEqual([], failures, "\n" + "\n".join(failures))

    def test_unmatched_prompts_never_claim_confidence(self):
        for row in load_corpus():
            if row["expect"] is not None:
                continue
            result = resolve_offline(row["prompt"])
            self.assertEqual(0.0, result["confidence"], row["prompt"])
            self.assertIn(result["match_method"], {"none", "ambiguous"}, row["prompt"])

    def test_every_expected_slug_exists_in_the_registry(self):
        for row in load_corpus():
            if row["expect"] is not None:
                self.assertIn(row["expect"], SLUG_TO_DEF, row["expect"])

    def test_registry_has_no_prompt_shaped_aliases(self):
        """Aliases must name procedures, not sentences.

        "help me prepare for a tha" only ever matched a whole sentence, and its
        seven filler tokens outranked real anatomy aliases during scoring.
        """
        filler = {"a", "for", "help", "i", "me", "my", "prep", "prepare", "the", "tomorrow", "yo"}
        offenders = [
            (definition.slug, alias)
            for definition in REGISTRY
            for alias in definition.aliases
            if filler & set(alias.lower().split())
        ]
        self.assertEqual([], offenders)

    def test_resolution_is_not_a_coin_flip_between_two_procedures(self):
        """Genuinely ambiguous prompts ask instead of picking a side."""
        result = resolve_offline("acetabulum fracture")
        self.assertIsNone(result["procedure_slug"])


if __name__ == "__main__":
    unittest.main()
