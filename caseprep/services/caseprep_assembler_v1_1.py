from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List


SECTION_ORDER = (
    "indications",
    "anatomy",
    "approach",
    "operative_steps",
    "complications",
    "postoperative_care",
)
SECTION_LIMITS = {
    "indications": 6,
    "anatomy": 8,
    "approach": 6,
    "operative_steps": 8,
    "complications": 6,
    "postoperative_care": 5,
}


def _key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def high_yield_items(candidates: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for row in candidates:
        question, answer = str(row.get("question") or "").strip(), str(row.get("answer") or "").strip()
        if not question or not answer:
            continue
        output.append(
            {
                "id": row.get("record_id"),
                "question": question,
                "answer": answer,
                "supporting_detail": row.get("additional_info") or "",
                "category": "high_yield",
                "source_ids": [row.get("record_id")],
                "confidence": row.get("retrieval_score") or row.get("vector_score") or 0.0,
                "generated": False,
            }
        )
    return output


def assemble_sections(pipelines: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    sections = {section: [] for section in SECTION_ORDER}
    seen: set[str] = set()
    for pipeline in pipelines:
        for item in pipeline.get("items") or []:
            category = item.get("category")
            section = category if category in sections else pipeline.get("pipeline_id")
            if section not in sections:
                continue
            key = f"{_key(item.get('question'))}|{_key(item.get('answer'))}"
            if not key.strip("|") or key in seen:
                continue
            seen.add(key)
            if len(sections[section]) < SECTION_LIMITS[section]:
                sections[section].append(item)
    return sections


def validate_response(response: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []
    seen: set[str] = set()
    for location, items in [
        ("high_yield_questions", response.get("high_yield_questions") or []),
        *list((response.get("sections") or {}).items()),
    ]:
        for item in items:
            if not item.get("question") or not item.get("answer"):
                warnings.append(f"Removed incomplete item from {location}.")
                continue
            key = f"{_key(item['question'])}|{_key(item['answer'])}"
            if key in seen:
                warnings.append(f"Duplicate item detected in {location}.")
            seen.add(key)
            if not item.get("source_ids"):
                warnings.append(f"Item without provenance in {location}: {item.get('id')}.")
    case = response.get("case") or {}
    if not case.get("canonical_slug"):
        warnings.append("Procedure could not be resolved to a canonical CasePrep slug.")
    return list(dict.fromkeys(warnings))


def collect_sources(
    high_yield: Iterable[Dict[str, Any]], pipelines: Iterable[Dict[str, Any]]
) -> List[Dict[str, str]]:
    sources: Dict[str, Dict[str, str]] = {}
    for item in high_yield:
        for source_id in item.get("source_ids") or []:
            if source_id:
                sources[str(source_id)] = {"source_id": str(source_id), "url": "", "title": "Pinecone Q&A"}
    for pipeline in pipelines:
        for source_id in pipeline.get("source_ids") or []:
            if source_id:
                source = str(source_id)
                sources[source] = {
                    "source_id": source,
                    "url": source if source.startswith("http") else "",
                    "title": "Published CasePrep source",
                }
    return list(sources.values())
