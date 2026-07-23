"""Published-revision-only Case Prep follow-up retrieval."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from caseprep.factory.clinical_review import (
    PUBLISHED_POINTER,
    load_revision,
    review_dir,
)


class PinnedCasePrepError(ValueError):
    pass


def _tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in {
            "what", "when", "where", "which", "does", "from", "should", "could",
            "would", "give", "tell", "about",
        }
    }


def _section_score(section_id: str, value: Any, query: str) -> int:
    haystack = _tokens(f"{section_id} {json.dumps(value, ensure_ascii=False)}")
    return len(haystack & _tokens(query))


def load_pinned_packet(
    *,
    slug: str,
    revision_id: str,
    payload_hash: str,
) -> Dict[str, Any]:
    pointer_path = review_dir(slug) / PUBLISHED_POINTER
    if not pointer_path.exists():
        raise PinnedCasePrepError("No published Case Prep revision exists for this case.")
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    if pointer.get("revision_id") != revision_id:
        raise PinnedCasePrepError("The pinned revision is no longer the published revision.")
    if pointer.get("payload_hash") != payload_hash:
        raise PinnedCasePrepError("The pinned payload hash does not match publication.")
    revision = load_revision(slug, revision_id)
    if pointer.get("content_hash") != revision["content_hash"]:
        raise PinnedCasePrepError("Published content hash mismatch.")
    return {"pointer": pointer, "revision": revision}


def answer_from_pinned_revision(
    *,
    slug: str,
    revision_id: str,
    payload_hash: str,
    question: str,
    current_section: str | None = None,
) -> Dict[str, Any]:
    packet = load_pinned_packet(
        slug=slug, revision_id=revision_id, payload_hash=payload_hash
    )
    sections = packet["revision"]["content"]["sections"]
    ranked: List[tuple[int, str, Any]] = []
    for section_id, value in sections.items():
        score = _section_score(section_id, value, question)
        if current_section == section_id:
            score += 2
        ranked.append((score, section_id, value))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    relevant = [row for row in ranked if row[0] > 0][:3]
    if not relevant:
        return {
            "answer_status": "not_in_curated_packet",
            "message": "The pinned curated document does not contain a clear answer to that question.",
            "sections": [],
            "supplemental_retrieval_used": False,
            "citations": [],
        }
    return {
        "answer_status": "curated",
        "message": "Answer from the pinned curated Case Prep revision.",
        "sections": [
            {"section_id": section_id, "content": value}
            for _, section_id, value in relevant
        ],
        "supplemental_retrieval_used": False,
        "citations": [],
    }
