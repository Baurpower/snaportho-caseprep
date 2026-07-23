"""CasePrep v1.1 LLM enrichment — curated content always wins.

One batched JSON-mode completion per procedure, cached by canonical slug.
Merge rules are enforced in code, not prompts:

- Curated items are never modified or removed; enrichment only appends and
  only annotates pedagogy fields that are empty.
- Operative-flow generation is structurally refused for certified procedures.
- Every enrichment-derived item is marked ``generated: True`` with reduced
  confidence so the UI/debug layer can distinguish it.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from caseprep.pipelines.shared import clean, item
from caseprep.services.enrichment_prompts import SYSTEM_PROMPT, build_enrichment_prompt
from caseprep.services.ttl_cache import enrichment_cache

GENERATED_CONFIDENCE = 0.6
_DIFFICULTIES = {"easy", "medium", "hard"}
_DECISION_CATEGORIES = {
    "when_to_operate",
    "who_should_not",
    "when_to_convert",
    "when_to_stop",
    "alternatives",
}
_FLOW_PHASES = {
    "position",
    "equipment",
    "incision",
    "exposure",
    "critical_step",
    "closure",
    "pearl",
}
_ANATOMY_CATEGORIES = {
    "blood_supply",
    "motor_innervation",
    "sensory_innervation",
    "danger_zone",
}
_PEDAGOGY_FIELDS = ("teaching_pearl", "why_attendings_ask", "common_mistake", "difficulty")

MAX_PIMP_QUESTIONS = 15


def _is_certified(payload: Optional[Dict[str, Any]]) -> bool:
    return bool(payload) and clean(payload.get("case_prep_status")).lower() == "certified"


def _sanitize(raw: Any) -> Dict[str, Any]:
    """Whitelist and clean the model output; drop anything malformed."""
    data = raw if isinstance(raw, dict) else {}

    def rows(key: str) -> List[Dict[str, Any]]:
        return [row for row in (data.get(key) or []) if isinstance(row, dict)]

    def texts(key: str, limit: int) -> List[str]:
        return [clean(v) for v in (data.get(key) or [])[:limit] if clean(v)]

    pedagogy: Dict[str, Dict[str, str]] = {}
    for row in rows("pimp_pedagogy"):
        row_id = clean(row.get("id"))
        if not row_id:
            continue
        difficulty = clean(row.get("difficulty")).lower()
        pedagogy[row_id] = {
            "teaching_pearl": clean(row.get("teaching_pearl")),
            "why_attendings_ask": clean(row.get("why_attendings_ask")),
            "common_mistake": clean(row.get("common_mistake")),
            "difficulty": difficulty if difficulty in _DIFFICULTIES else "medium",
        }

    generated_questions: List[Dict[str, str]] = []
    for row in rows("generated_pimp_questions")[:6]:
        question, answer = clean(row.get("question")), clean(row.get("answer"))
        if not question or not answer:
            continue
        difficulty = clean(row.get("difficulty")).lower()
        generated_questions.append(
            {
                "question": question,
                "answer": answer,
                "teaching_pearl": clean(row.get("teaching_pearl")),
                "why_attendings_ask": clean(row.get("why_attendings_ask")),
                "common_mistake": clean(row.get("common_mistake")),
                "difficulty": difficulty if difficulty in _DIFFICULTIES else "medium",
            }
        )

    decision_points: List[Dict[str, str]] = []
    for row in rows("decision_points")[:8]:
        category = clean(row.get("category")).lower()
        question, answer = clean(row.get("question")), clean(row.get("answer"))
        if not answer or category not in _DECISION_CATEGORIES:
            continue
        decision_points.append(
            {"category": category, "question": question or category, "answer": answer}
        )

    evidence: List[Dict[str, str]] = []
    for row in rows("evidence")[:4]:
        title, finding = clean(row.get("title")), clean(row.get("finding"))
        if not title or not finding:
            continue
        evidence.append(
            {"title": title, "finding": finding, "why_it_matters": clean(row.get("why_it_matters"))}
        )

    anatomy: List[Dict[str, str]] = []
    for row in rows("anatomy_gap_fill")[:8]:
        category = clean(row.get("category")).lower()
        question, answer = clean(row.get("question")), clean(row.get("answer"))
        if not answer or category not in _ANATOMY_CATEGORIES:
            continue
        anatomy.append({"category": category, "question": question or category, "answer": answer})

    flow: List[Dict[str, str]] = []
    for row in rows("operative_flow")[:12]:
        phase = clean(row.get("phase")).lower()
        step = clean(row.get("step"))
        if not step or phase not in _FLOW_PHASES:
            continue
        flow.append({"phase": phase, "step": step})

    return {
        "pimp_pedagogy": pedagogy,
        "generated_pimp_questions": generated_questions,
        "teaching_topics": texts("teaching_topics", 5),
        "decision_points": decision_points,
        "evidence": evidence,
        "anatomy_gap_fill": anatomy,
        "operative_flow": flow,
        "pitfalls": texts("pitfalls", 6),
        "postop": texts("postop", 6),
    }


class EnrichmentResult:
    """Applies sanitized enrichment data to packet sections. Curated wins."""

    def __init__(self, data: Dict[str, Any], *, certified: bool) -> None:
        self.data = data
        self.certified = certified

    # ── Pimp questions ───────────────────────────────────────────────────────
    def apply_to_pimp_questions(
        self, items: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        generated_paths: List[str] = []
        pedagogy = self.data["pimp_pedagogy"]
        output: List[Dict[str, Any]] = []
        for index, entry in enumerate(items):
            merged = dict(entry)
            extra = pedagogy.get(str(entry.get("id")) or "")
            if extra:
                for field in _PEDAGOGY_FIELDS:
                    # Annotate only empty fields — curated values are never replaced.
                    if not clean(merged.get(field)) and extra.get(field):
                        merged[field] = extra[field]
                        generated_paths.append(f"items[{index}].{field}")
            output.append(merged)
        for row in self.data["generated_pimp_questions"]:
            if len(output) >= MAX_PIMP_QUESTIONS:
                break
            entry = item(
                prefix="genpimp",
                question=row["question"],
                answer=row["answer"],
                category="attending_question",
                sources=[],
                confidence=GENERATED_CONFIDENCE,
                generated=True,
            )
            if entry is None:
                continue
            entry.update(
                {
                    "source": "generated",
                    "rank": len(output) + 1,
                    "teaching_pearl": row["teaching_pearl"],
                    "why_attendings_ask": row["why_attendings_ask"],
                    "common_mistake": row["common_mistake"],
                    "difficulty": row["difficulty"],
                }
            )
            generated_paths.append(f"items[{len(output)}]")
            output.append(entry)
        return output, generated_paths

    # ── Section fill (append-only; curated first) ────────────────────────────
    def _generated_items(self, section_id: str) -> List[Dict[str, Any]]:
        rows: List[Tuple[str, str, str]] = []  # (question, answer, category)
        if section_id == "teaching_topics":
            rows = [("Teach this tomorrow", topic, "teaching_topics") for topic in self.data["teaching_topics"]]
        elif section_id == "decision_points":
            rows = [(r["question"], r["answer"], r["category"]) for r in self.data["decision_points"]]
        elif section_id == "evidence":
            rows = [
                (r["title"], f"{r['finding']} {r['why_it_matters']}".strip(), "evidence")
                for r in self.data["evidence"]
            ]
        elif section_id == "anatomy":
            rows = [(r["question"], r["answer"], r["category"]) for r in self.data["anatomy_gap_fill"]]
        elif section_id == "pitfalls":
            rows = [("Common junior mistake", text, "pitfall") for text in self.data["pitfalls"]]
        elif section_id == "postop":
            rows = [("Post-op protocol", text, "postop") for text in self.data["postop"]]
        elif section_id == "operative_flow":
            if self.certified:
                # Structural guard: never generate operative steps for certified
                # procedures, regardless of what the model returned.
                return []
            rows = [(r["phase"].replace("_", " ").title(), r["step"], r["phase"]) for r in self.data["operative_flow"]]
        output: List[Dict[str, Any]] = []
        for question, answer, category in rows:
            entry = item(
                prefix="gen",
                question=question,
                answer=answer,
                category=category,
                sources=[],
                confidence=GENERATED_CONFIDENCE,
                generated=True,
            )
            if entry is not None:
                entry["source"] = "generated"
                output.append(entry)
        return output

    def apply_to_section(
        self, section_id: str, items: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        from caseprep.services.rag_retrieval_v1_1 import _near_duplicate

        output = list(items)  # curated content is never modified or removed
        generated_paths: List[str] = []
        for entry in self._generated_items(section_id):
            if any(
                _near_duplicate(entry["question"] + " " + entry["answer"], kept.get("question", "") + " " + kept.get("answer", ""))
                for kept in output
            ):
                continue
            generated_paths.append(f"items[{len(output)}]")
            output.append(entry)
        return output, generated_paths


def enrich_packet_sections(
    slug: str,
    curated_payload: Optional[Dict[str, Any]],
    *,
    identity: Dict[str, Any],
    pimp_questions: Optional[List[Dict[str, Any]]] = None,
    openai_client: Any,
    model: str = "gpt-4o-mini",
) -> Optional[EnrichmentResult]:
    """Batched, cached enrichment call. Returns None when unavailable."""
    certified = _is_certified(curated_payload)
    cache_key = f"{slug}|{model}"
    cached = enrichment_cache.get(cache_key)
    if cached is not None:
        return EnrichmentResult(cached, certified=certified)
    if openai_client is None:
        return None

    prompt = build_enrichment_prompt(
        display_name=identity.get("canonical_name") or slug,
        identity=identity,
        curated_payload=curated_payload,
        pimp_questions=pimp_questions or [],
        certified=certified,
    )
    response = openai_client.chat.completions.create(
        model=model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    try:
        raw = json.loads(response.choices[0].message.content or "{}")
    except (json.JSONDecodeError, AttributeError, IndexError):
        return None
    data = _sanitize(raw)
    enrichment_cache.set(cache_key, data)
    return EnrichmentResult(data, certified=certified)
