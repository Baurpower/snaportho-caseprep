from __future__ import annotations
import unittest

from caseprep.services.rock_grounding import (
    resolve_rock_context_by_text,
    format_grounding_block,
    MAX_PASSAGE_CHARS,
)


class FakeResp:
    def __init__(self, matches):
        self.matches = matches


def _m(score, cid, title, text, chunk_index=0):
    return {
        "score": score,
        "metadata": {
            "chapter_id": cid, "canonical_id": cid, "title": title,
            "url": f"https://rock.aaos.org/coursecontent.aspx?id={cid}",
            "text": text, "chunk_index": chunk_index, "source_collection": "rock",
        },
    }


class FakeIndex:
    def __init__(self, matches):
        self._matches = matches
        self.last_kwargs = None

    def query(self, **kwargs):
        self.last_kwargs = kwargs
        return FakeResp(self._matches)


class RockGroundingTests(unittest.TestCase):
    def test_dedupes_to_chapters_and_caps_passages(self):
        idx = FakeIndex([
            _m(0.80, "111", "Distal Femur Fractures", "passage A", 0),
            _m(0.78, "111", "Distal Femur Fractures", "passage B", 1),
            _m(0.77, "111", "Distal Femur Fractures", "passage C", 2),  # beyond max_passages
            _m(0.70, "222", "Periprosthetic Fractures", "passage D", 0),
        ])
        ctx = resolve_rock_context_by_text("distal femur", index_obj=idx, embed_fn=lambda t: [0.1],
                                           max_chapters=3, max_passages=2)
        self.assertEqual(ctx["retrieval"], "vector")
        self.assertEqual(len(ctx["chapters"]), 2)
        self.assertEqual(ctx["chapters"][0]["chapter_id"], "111")
        self.assertEqual(len(ctx["chapters"][0]["passages"]), 2)  # capped
        # scoped filter applied
        self.assertEqual(idx.last_kwargs["namespace"], "rock-v1")
        self.assertEqual(idx.last_kwargs["filter"], {"source_collection": {"$eq": "rock"}})

    def test_drops_low_score_matches(self):
        idx = FakeIndex([_m(0.20, "111", "T", "weak")])
        ctx = resolve_rock_context_by_text("x", index_obj=idx, embed_fn=lambda t: [0.1])
        self.assertEqual(ctx["chapters"], [])

    def test_passage_length_capped(self):
        long_text = "word " * 400
        idx = FakeIndex([_m(0.9, "111", "T", long_text)])
        ctx = resolve_rock_context_by_text("x", index_obj=idx, embed_fn=lambda t: [0.1])
        self.assertLessEqual(len(ctx["chapters"][0]["passages"][0]), MAX_PASSAGE_CHARS + 1)

    def test_empty_query(self):
        ctx = resolve_rock_context_by_text("   ", index_obj=FakeIndex([]), embed_fn=lambda t: [0.1])
        self.assertEqual(ctx["retrieval"], "empty_query")

    def test_error_is_swallowed(self):
        class Boom:
            def query(self, **k): raise RuntimeError("pinecone down")
        ctx = resolve_rock_context_by_text("x", index_obj=Boom(), embed_fn=lambda t: [0.1])
        self.assertEqual(ctx["retrieval"], "error")
        self.assertEqual(ctx["chapters"], [])

    def test_format_block(self):
        ctx = {"chapters": [{"title": "Distal Femur Fractures",
                             "url": "https://rock.aaos.org/coursecontent.aspx?id=111",
                             "passages": ["fix with a lateral locking plate"]}]}
        block = format_grounding_block(ctx)
        self.assertIn("AAOS ROCK", block)
        self.assertIn("Distal Femur Fractures", block)
        self.assertIn("do not copy verbatim", block)
        self.assertEqual(format_grounding_block({"chapters": []}), "")


class RockReferenceBranchTests(unittest.TestCase):
    def test_disabled_returns_empty(self):
        import os
        from caseprep.services import rag_retrieval
        old = os.environ.get("CASEPREP_ROCK_GROUNDING_ENABLED")
        os.environ["CASEPREP_ROCK_GROUNDING_ENABLED"] = "false"
        try:
            self.assertEqual(rag_retrieval.retrieve_rock_references({"search_text": "x"}), [])
        finally:
            if old is None:
                os.environ.pop("CASEPREP_ROCK_GROUNDING_ENABLED", None)
            else:
                os.environ["CASEPREP_ROCK_GROUNDING_ENABLED"] = old

    def test_normalizes_shape(self):
        import os
        from caseprep.services import rag_retrieval, rock_grounding
        os.environ["CASEPREP_ROCK_GROUNDING_ENABLED"] = "true"
        orig = rock_grounding.resolve_rock_context_by_text
        rock_grounding.resolve_rock_context_by_text = lambda *a, **k: {
            "chapters": [{"chapter_id": "111", "title": "Distal Femur Fractures",
                          "url": "u", "passages": ["p1", "p2"]}]}
        try:
            refs = rag_retrieval.retrieve_rock_references({"search_text": "distal femur"})
            self.assertEqual(len(refs), 1)
            self.assertEqual(refs[0]["content_type"], "rock_reference")
            self.assertEqual(refs[0]["source_collection"], "rock")
            self.assertEqual(refs[0]["record_id"], "rock-111")
        finally:
            rock_grounding.resolve_rock_context_by_text = orig


if __name__ == "__main__":
    unittest.main()
