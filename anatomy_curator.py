"""
GPT Curator Layer for Playbook-Primary Anatomy.

Receives:
- procedure context (id, name, specialty, region)
- selected approach info (ids + notes)
- playbook fields (importantAnatomy, structuresAtRisk, landmarks, pearls from pimp/approach_notes, sources)
- filtered_miller_support (already relevance-filtered; only supporting/citing facts)

Strict rules (in prompt + post-processing):
- NEVER invent new anatomy, structures, landmarks, pearls, or claims.
- ONLY rephrase, deduplicate, prioritize, and format from the provided playbook content.
- Miller support facts may ONLY be used to add citations, short supporting quotes, or minor elaboration on EXISTING playbook items. Discard anything that would add new content.
- Concise, resident-facing, high-yield style (bullet or short paragraph).
- Hard limits: max 5 per category (anatomy, risks, landmarks, pearls).
- Output structured JSON only (no prose outside the JSON).

Public:
    curate_playbook_anatomy(
        procedure: dict,
        approach: dict,
        playbook_fields: dict,
        miller_support: list[dict],
        client: OpenAI = None
    ) -> dict

Returns the curated version of the builder output, ready for final schema (Approach, Key Anatomy, ... Sources).
"""

import json
import os
from typing import Any, Dict, List, Optional
from openai import OpenAI

# Reuse style from anatomy_gpt OpenAIJson if available, but keep self-contained for this module.
CURATOR_MODEL = os.getenv("ANATOMY_CURATOR_MODEL", "gpt-4o")  # or gpt-4o-mini for speed/cost

SYSTEM_PROMPT = """You are an expert orthopaedic surgical educator curating a procedure-specific anatomy reference for residents.

SOURCE OF TRUTH (in priority order):
1. The provided Orthobullets playbook fields (importantAnatomy, structuresAtRisk, landmarks, pearls/approach notes, sources). These are the primary and authoritative content. You may rephrase for clarity and teaching value but must not add, expand, or invent any new facts, structures, landmarks, risks, or pearls.
2. Filtered Miller support facts (if any). These may ONLY be used as citations or very short supporting quotes/elaborations attached to EXISTING items from the playbook. If a Miller fact does not directly support or overlap an existing playbook item, ignore it completely. Never use Miller to fill gaps or introduce new anatomy.

STRICT RULES:
- NO invention of anatomy, intervals, structures at risk, landmarks, pearls, or clinical claims.
- NO unsupported claims or speculation.
- Deduplicate aggressively (same concept from playbook + Miller appears only once, with best source).
- Prioritize: procedure- and approach-specific items first. General or loosely related items last or omitted.
- Keep output concise and high-yield for a resident preparing for case or exam.
- Hard limits in final JSON: at most 5 items in importantAnatomy, 5 in structuresAtRisk, 5 in landmarks, 5 in pearls.
- Every item in the output must trace back to the provided playbook content (or explicitly as "supporting citation" from Miller).
- If the playbook entry has manual_review=true or very sparse fields, keep the output honest and limited; do not fabricate to make it look complete.
- Output MUST be valid JSON matching the exact schema below. No additional text, explanations, or markdown outside the JSON object.

OUTPUT SCHEMA (return exactly this structure):
{
  "approach": {
    "selectedIds": ["approach_..."],
    "notes": ["short note from playbook..."]
  },
  "importantAnatomy": [
    {"text": "concise fact or relation", "sources": ["url or miller:id"], "confidence": "high|medium|low"}
  ],
  "structuresAtRisk": [
    {"structure": "...", "whyItMatters": "short explanation from playbook", "sources": [...], "confidence": "..."}
  ],
  "landmarks": [
    {"landmark": "...", "whyItMatters": "...", "sources": [...], "confidence": "..."}
  ],
  "pearls": [
    "high-yield operative or exam pearl (from playbook pimp or notes, curated for teaching)"
  ],
  "sources": [
    {"type": "orthobullets" | "miller_support", "url"?: "...", "id"?: "...", "note"?: "short attribution"}
  ],
  "meta": {
    "procedureId": "...",
    "supported": true/false,
    "manualReview": true/false,
    "reviewReason": "" | "reason if manual_review"
  }
}

If there is insufficient content in the playbook input, produce the schema with empty or minimal arrays and honest meta. Never pad with invented content.
"""

def _get_client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY required for anatomy curator GPT calls.")
    proj = os.getenv("OPENAI_PROJECT_ID")
    return OpenAI(api_key=key, project=proj)

def curate_playbook_anatomy(
    procedure: Dict[str, Any],
    approach: Dict[str, Any],
    playbook_fields: Dict[str, Any],
    miller_support: List[Dict[str, Any]],
    client: Optional[OpenAI] = None,
) -> Dict[str, Any]:
    """
    Curate using GPT under strict no-invention rules.
    Returns the structured dict ready for final presentation layer.
    """
    if client is None:
        client = _get_client()

    # Prepare compact input for the model (avoid token bloat)
    input_payload = {
        "procedure": {
            "id": procedure.get("procedure_id") or procedure.get("id"),
            "displayName": procedure.get("display_name") or procedure.get("name"),
            "specialty": procedure.get("specialty"),
            "region": procedure.get("region"),
        },
        "approach": approach,  # already structured from builder
        "playbook": {
            "importantAnatomy": playbook_fields.get("importantAnatomy", playbook_fields.get("important_anatomy", [])),
            "structuresAtRisk": playbook_fields.get("structuresAtRisk", playbook_fields.get("structures_at_risk", [])),
            "landmarks": playbook_fields.get("landmarks", []),
            "pearls": playbook_fields.get("pearls", playbook_fields.get("pimp_topics", [])),
            "approachNotes": playbook_fields.get("approachNotes", playbook_fields.get("approach_notes", [])),
            "sources": playbook_fields.get("sources", []),
            "manualReview": playbook_fields.get("manual_review", False),
            "reviewReason": playbook_fields.get("review_reason", ""),
        },
        "millerSupport": miller_support,  # pre-filtered
    }

    user_content = (
        "Curate the following into the exact output JSON schema. "
        "Playbook content is authoritative. Use Miller support ONLY for citations on existing items.\n\n"
        + json.dumps(input_payload, ensure_ascii=False)
    )

    resp = client.chat.completions.create(
        model=CURATOR_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,  # low for consistency / fidelity
        max_tokens=2000,
    )

    content = resp.choices[0].message.content
    try:
        curated = json.loads(content)
    except Exception:
        # Fallback to safe minimal if parse fails (never invent)
        curated = {
            "approach": approach,
            "importantAnatomy": playbook_fields.get("importantAnatomy", playbook_fields.get("important_anatomy", []))[:5],
            "structuresAtRisk": playbook_fields.get("structuresAtRisk", playbook_fields.get("structures_at_risk", []))[:5],
            "landmarks": playbook_fields.get("landmarks", [])[:5],
            "pearls": playbook_fields.get("pearls", playbook_fields.get("pimp_topics", []))[:5],
            "sources": playbook_fields.get("sources", []),
            "meta": {
                "procedureId": procedure.get("procedure_id") or procedure.get("id"),
                "supported": not playbook_fields.get("manual_review", False),
                "manualReview": playbook_fields.get("manual_review", False),
                "reviewReason": playbook_fields.get("review_reason", ""),
                "curatorNote": "GPT curation parse fallback; raw playbook used.",
            },
        }
    # Ensure meta
    if "meta" not in curated:
        curated["meta"] = {
            "procedureId": procedure.get("procedure_id") or procedure.get("id"),
            "supported": not playbook_fields.get("manual_review", False),
            "manualReview": playbook_fields.get("manual_review", False),
            "reviewReason": playbook_fields.get("review_reason", ""),
        }
    return curated
