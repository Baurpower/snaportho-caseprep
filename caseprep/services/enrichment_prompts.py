"""Prompt templates for the CasePrep v1.1 enrichment layer.

Audience: medical students, sub-Is, new interns, away rotators, junior
residents preparing for tomorrow morning's case. Never the whole disease —
only what they need to walk into the OR prepared.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

SYSTEM_PROMPT = """\
You are an orthopaedic attending preparing a trainee for tomorrow's case.
Audience: medical students, sub-interns, new interns, away rotators, and junior residents.
Voice: direct, specific, OR-practical. "What do I need to know tomorrow morning?" — never textbook chapters.

Hard rules:
- CURATED FACTS ARE AUTHORITATIVE. Never contradict, restate incorrectly, or embellish the curated content provided.
- Never invent implant brand names, exact measurements, or study data you are not certain of.
- Evidence entries must be real, widely known landmark studies or guidelines that change management. If unsure, return fewer or none.
- Difficulty reflects how likely a JUNIOR trainee is to be asked and to miss it.
- Teaching pearls are one sentence, concrete, and actionable in the OR tomorrow.
Return ONLY valid JSON matching the requested schema."""

RESPONSE_SCHEMA_HINT = """\
{
  "pimp_pedagogy": [
    {"id": "<id of the provided question>", "teaching_pearl": str, "why_attendings_ask": str, "common_mistake": str, "difficulty": "easy"|"medium"|"hard"}
  ],
  "generated_pimp_questions": [
    {"question": str, "answer": str, "teaching_pearl": str, "why_attendings_ask": str, "common_mistake": str, "difficulty": "easy"|"medium"|"hard"}
  ],
  "decision_points": [
    {"category": "when_to_operate"|"who_should_not"|"when_to_convert"|"when_to_stop"|"alternatives", "question": str, "answer": str}
  ],
  "evidence": [
    {"title": str, "finding": str, "why_it_matters": str}
  ],
  "anatomy_gap_fill": [
    {"category": "blood_supply"|"motor_innervation"|"sensory_innervation"|"danger_zone", "question": str, "answer": str}
  ],
  "operative_flow": [
    {"phase": "position"|"equipment"|"incision"|"exposure"|"critical_step"|"closure"|"pearl", "step": str}
  ],
  "postop": [str]
}"""


def build_enrichment_prompt(
    *,
    display_name: str,
    identity: Dict[str, Any],
    curated_payload: Optional[Dict[str, Any]],
    pimp_questions: List[Dict[str, Any]],
    certified: bool,
) -> str:
    curated_block = "None — no curated content exists for this procedure yet."
    if curated_payload:
        trimmed = {
            key: curated_payload.get(key)
            for key in (
                "procedure_overview",
                "must_know_anatomy",
                "structures_at_risk",
                "surgical_approach_anatomy",
                "surgical_layers",
                "common_mistakes",
                "danger_zones",
                "key_landmarks",
                "attending_pimp_questions",
            )
            if curated_payload.get(key)
        }
        curated_block = json.dumps(trimmed, ensure_ascii=False)[:6000]

    questions_block = json.dumps(
        [
            {"id": q.get("id"), "question": q.get("question"), "answer": q.get("answer")}
            for q in pimp_questions[:15]
        ],
        ensure_ascii=False,
    )

    operative_flow_rule = (
        "Do NOT return operative_flow items — certified operative content exists and must not be overwritten."
        if certified
        else "Return operative_flow items ONLY for steps you are confident about; omit anything uncertain."
    )

    return f"""Procedure: {display_name}
Case context: {json.dumps({k: identity.get(k) for k in ("diagnosis", "approach", "specialty", "region", "laterality", "patient_age")}, ensure_ascii=False)}
Certified curated content (authoritative, do not contradict): {curated_block}

Pimp questions already selected for this packet (add pedagogy for each by id):
{questions_block}

Tasks:
1. pimp_pedagogy — for EVERY provided question id: a one-sentence teaching pearl, why an attending asks it, the common junior mistake, and difficulty.
2. generated_pimp_questions — 3-6 ADDITIONAL high-likelihood OR pimp questions not already covered above. Real attending questions, not trivia.
3. decision_points — cover: when do we operate, who should NOT get surgery, when to convert, when to stop/bail out, common alternatives.
4. evidence — up to 4 landmark trials/guidelines that actually change management for this procedure. Fewer is better than fabricated.
5. anatomy_gap_fill — blood supply, motor innervation, sensory innervation, danger zones NOT already in the curated content.
6. {operative_flow_rule}
7. postop — the concise postop protocol a trainee should recite (weight-bearing/immobilization, motion, follow-up, red flags).

Respond with JSON only, schema:
{RESPONSE_SCHEMA_HINT}"""
