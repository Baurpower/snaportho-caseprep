"""
Draft modules.json from extracted knowledge (rule-based; optional LLM assist).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from caseprep.registry.constants import MODULE_SECTIONS
from caseprep.factory.schemas import ExtractedKnowledge, SourcedClaim
from caseprep.factory.prompts import synthesis_system_prompt, synthesis_user_prompt


def _claim_text(claims: List[SourcedClaim], limit: int = 8) -> List[str]:
    out: List[str] = []
    for claim in claims[:limit]:
        text = claim.text.strip()
        if text:
            out.append(text)
    return out


def _dedupe_sar(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    out: List[Dict[str, Any]] = []
    for row in rows:
        key = str(row.get("structure", "")).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out[:6]


def _build_layers_from_setup(setup: List[str], slug: str) -> List[Dict[str, Any]]:
    superficial = [s for s in setup if s.lower().startswith(("superficial", "skin", "incision"))]
    deep = [s for s in setup if s.lower().startswith(("deep", "interval", "capsule", "joint"))]
    if not superficial and setup:
        superficial = setup[:2]
    if not deep and len(setup) > 2:
        deep = setup[2:4]
    layers: List[Dict[str, Any]] = []
    if superficial:
        layers.append(
            {
                "layer_name": "Superficial (skin to fascia/capsule)",
                "what_user_should_know": superficial[0],
                "key_structures": [],
                "structures_at_risk": [],
                "surgical_relevance": "Initial exposure and landmark identification.",
                "source_refs": [],
            }
        )
    if deep:
        layers.append(
            {
                "layer_name": "Deep (working exposure)",
                "what_user_should_know": deep[0],
                "key_structures": [],
                "structures_at_risk": [],
                "surgical_relevance": "Working layer for safe dissection and fixation/implant steps.",
                "source_refs": [],
            }
        )
    if not layers and setup:
        layers.append(
            {
                "layer_name": f"Exposure layers for {slug}",
                "what_user_should_know": setup[0],
                "key_structures": [],
                "structures_at_risk": [],
                "surgical_relevance": "Source-derived exposure summary.",
                "source_refs": [],
            }
        )
    return layers


def _pimp_from_facts(facts: List[SourcedClaim], sar: List[Dict[str, Any]], slug: str) -> List[Dict[str, str]]:
    questions: List[Dict[str, str]] = []
    for fact in facts[:3]:
        text = fact.text.strip()
        if "?" in text:
            questions.append({"question": text, "answer": "See source-linked approach anatomy and structures at risk."})
        else:
            questions.append(
                {
                    "question": f"What is the key clinical point about: {text[:80]}?",
                    "answer": text,
                }
            )
    for row in sar[:3]:
        structure = row.get("structure", "")
        if structure:
            questions.append(
                {
                    "question": f"Why is {structure} at risk during {slug} and how do you protect it?",
                    "answer": (
                        f"{row.get('why_at_risk', '')} "
                        f"Avoid by: {row.get('how_to_avoid_injury', '')} "
                        f"Consequence: {row.get('consequence_of_injury', '')}"
                    ).strip(),
                }
            )
    return questions[:6]


def _default_postop_protocol(display_name: str) -> List[str]:
    return [
        f"Weight-bearing: procedure-specific; confirm in attending preference and fixation/implant stability for {display_name}.",
        "DVT prophylaxis: per institutional protocol unless contraindicated.",
        "Activity restrictions: protect surgical repair; avoid premature loading or range of motion beyond protocol.",
        "Watch for: wound complications, neurovascular change, increasing pain, fever, or loss of function.",
        "Follow-up: routine wound check and early mobilization per service protocol.",
    ]


def _try_llm_synthesis(
    slug: str,
    display_name: str,
    body_region: str,
    knowledge: ExtractedKnowledge,
) -> Optional[Dict[str, Any]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.getenv("CASEPREP_FACTORY_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": synthesis_system_prompt()},
                {
                    "role": "user",
                    "content": synthesis_user_prompt(
                        slug, display_name, body_region, knowledge.model_dump()
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)
    except Exception:
        return None


def synthesize_modules(
    knowledge: ExtractedKnowledge,
    *,
    manifest: Dict[str, Any],
    use_llm: bool = True,
) -> Dict[str, Any]:
    slug = knowledge.procedure_id
    display_name = knowledge.display_name
    body_region = str(manifest.get("body_region") or "unknown")

    llm_modules: Optional[Dict[str, Any]] = None
    if use_llm:
        llm_modules = _try_llm_synthesis(slug, display_name, body_region, knowledge)

    setup = _claim_text(knowledge.setup_positioning, limit=10)
    landmarks = _claim_text(knowledge.approach_landmarks, limit=6)
    sar = _dedupe_sar(knowledge.structures_at_risk)
    layers = knowledge.surgical_layers or _build_layers_from_setup(setup, slug)
    pitfalls = _claim_text(knowledge.complications, limit=5)
    if not pitfalls and sar:
        pitfalls = [
            f"Injury to {row.get('structure')} — {row.get('consequence_of_injury', 'significant morbidity')}."
            for row in sar[:5]
            if row.get("structure")
        ]

    pimp = _pimp_from_facts(knowledge.pimp_question_facts, sar, slug)
    postop = _claim_text(knowledge.postop_protocol, limit=6)
    if not postop:
        postop = _default_postop_protocol(display_name)

    indications = _claim_text(knowledge.indications, limit=5)
    if not indications:
        indications = [
            f"Clinical indication for {display_name} per attending plan and documented diagnosis (source-linked indications pending)."
        ]

    modules: Dict[str, Any] = {
        "indications": indications,
        "setup_positioning": [
            f"{display_name} — factory draft from source library (pending human review).",
            *setup,
        ],
        "approach_landmarks": landmarks,
        "surgical_layers": layers,
        "structures_at_risk": sar,
        "implant_strategy": _claim_text(knowledge.implant_strategy, limit=5),
        "reduction_or_fluoro_checkpoints": _claim_text(
            knowledge.reduction_or_fluoro_checkpoints, limit=5
        ),
        "pitfalls": pitfalls,
        "attending_pimp_questions": pimp,
        "postop_plan": postop,
    }

    if llm_modules:
        for key in MODULE_SECTIONS:
            if llm_modules.get(key):
                modules[key] = llm_modules[key]

    # Ensure ordered keys
    return {key: modules.get(key, []) for key in MODULE_SECTIONS}