"""Prompt templates for optional LLM-assisted synthesis (Phase 1)."""

from __future__ import annotations

import json
from typing import Any, Dict


def synthesis_system_prompt() -> str:
    return (
        "You are a senior orthopaedic surgery educator drafting resident night-before CasePrep content. "
        "Use ONLY facts from the provided extracted_knowledge JSON. "
        "Do not invent anatomy, nerves, approaches, or postoperative protocols not supported by sources. "
        "Write concise OR-focused bullets. No textbook filler. No generic placeholders. "
        "Structures at risk must include structure, why_at_risk, how_to_avoid_injury, consequence_of_injury. "
        "Post-op section must be clinical protocol (weight-bearing, immobilization, DVT, activity restrictions) "
        "— never a study checklist."
    )


def synthesis_user_prompt(
    slug: str,
    display_name: str,
    body_region: str,
    extracted: Dict[str, Any],
) -> str:
    return (
        f"Procedure: {display_name} ({slug}), body region: {body_region}.\n"
        "Return JSON with keys matching modules.json sections:\n"
        "indications, setup_positioning, approach_landmarks, surgical_layers, structures_at_risk, "
        "implant_strategy, reduction_or_fluoro_checkpoints, pitfalls, attending_pimp_questions, postop_plan.\n"
        "attending_pimp_questions: list of {question, answer}.\n"
        "surgical_layers and structures_at_risk: structured objects.\n"
        f"Extracted knowledge:\n{json.dumps(extracted, indent=2)}"
    )