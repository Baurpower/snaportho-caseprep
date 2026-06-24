"""
Playbook-First Anatomy Builder (primary engine).

Makes the Orthobullets procedure playbook the source of truth for anatomy output.

- Router / supported gate determines the procedure + recommended approach IDs.
- This builder looks up the full playbook entry by procedure_id.
- Playbook fields (important_anatomy, structures_at_risk, landmarks, approach_notes, pimp_topics, sources) are primary.
- Miller support chunks (optional) are filtered for relevance (overlap with playbook terms + procedure/approach) and used only to support/cite/enrich (never override or invent).
- Output is clean, procedure/approach-focused, no raw retrieval noise.

Public function:
    build_playbook_anatomy(
        procedure_id: str,
        recommended_approach_ids: list[str],
        conditional_approach_ids: list | dict = None,
        blocked_approach_ids: list = None,
        miller_support_chunks: list[dict] = None,  # optional filtered Miller
        catalog: list[dict] = None  # for approach display names if needed
    ) -> dict

Returns:
{
  "approach": { "ids": [...], "notes": [...] from playbook or catalog },
  "importantAnatomy": [ {text, source_url, ...} from playbook primarily ],
  "structuresAtRisk": [...],
  "landmarks": [...],
  "pearls": [from playbook pimp_topics or approach_notes, curated later],
  "sources": [consolidated OB + supporting Miller sources]
}
"""

from typing import Any, Dict, List, Optional
import json
from pathlib import Path
import os

# Load the anatomy playbook (OB primary)
BASE_DIR = Path(__file__).resolve().parent
ANATOMY_PLAYBOOK_PATH = BASE_DIR / "data" / "approach_playbook" / "orthobullets_procedure_playbook_v1.jsonl"

_ANATOMY_PLAYBOOK: Optional[List[Dict[str, Any]]] = None

def _load_anatomy_playbook() -> List[Dict[str, Any]]:
    global _ANATOMY_PLAYBOOK
    if _ANATOMY_PLAYBOOK is None:
        _ANATOMY_PLAYBOOK = []
        if ANATOMY_PLAYBOOK_PATH.exists():
            with ANATOMY_PLAYBOOK_PATH.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        _ANATOMY_PLAYBOOK.append(json.loads(line))
    return _ANATOMY_PLAYBOOK

def _get_entry(procedure_id: str) -> Optional[Dict[str, Any]]:
    pb = _load_anatomy_playbook()
    for e in pb:
        if e.get("procedure_id") == procedure_id:
            return e
    return None

def _filter_miller_for_playbook(
    miller_chunks: List[Dict[str, Any]],
    playbook_entry: Dict[str, Any],
    approach_ids: List[str]
) -> List[Dict[str, Any]]:
    """
    Relevance filter (see reports/playbook_miller_filtering_rules.md for details).
    Keep only chunks with term overlap to playbook anatomy/risks/landmarks/approach_notes
    + procedure/region/selected approach IDs.
    Discard cross-region, low-overlap, or unsupported.
    """
    if not miller_chunks or not playbook_entry:
        return []

    # Collect key terms from playbook (lowercase for match)
    terms = set()
    proc = playbook_entry.get("procedure_id", "").lower().replace("_", " ")
    region = playbook_entry.get("region", "").lower()
    terms.add(proc)
    terms.add(region)
    for aid in approach_ids:
        terms.add(aid.lower().replace("approach_", "").replace("_", " "))

    for field in ("important_anatomy", "structures_at_risk", "landmarks", "approach_notes"):
        for item in playbook_entry.get(field, []):
            if isinstance(item, dict):
                txt = (item.get("text", "") + " " + item.get("why_it_matters", "")).lower()
            else:
                txt = str(item).lower()
            for w in txt.split():
                if len(w) > 3:
                    terms.add(w.strip(".,;:()[]"))

    # Also from pimp
    for p in playbook_entry.get("pimp_topics", []):
        for w in str(p).lower().split():
            if len(w) > 3:
                terms.add(w.strip(".,;:()[]"))

    filtered = []
    for chunk in miller_chunks:
        blob = " ".join([
            str(chunk.get("text", "")),
            str(chunk.get("source_quote", "")),
            str(chunk.get("heading", "")),
            str(chunk.get("region", "")),
            str(chunk.get("subregion", "")),
        ]).lower()
        overlap = sum(1 for t in terms if t in blob)
        # Require some overlap + not obviously wrong region (simple heuristic)
        if overlap >= 1:
            # crude region check: if chunk has region and doesn't match playbook region, lower priority but still consider if strong overlap
            chunk_region = str(chunk.get("region", "")).lower()
            if chunk_region and region and chunk_region != region and overlap < 2:
                continue
            filtered.append(chunk)
    return filtered

def build_playbook_anatomy(
    procedure_id: str,
    recommended_approach_ids: List[str],
    conditional_approach_ids: Optional[List | Dict] = None,
    blocked_approach_ids: Optional[List[str]] = None,
    miller_support_chunks: Optional[List[Dict[str, Any]]] = None,
    catalog: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Playbook is primary. Miller supports only (after filtering).
    """
    entry = _get_entry(procedure_id) or {}

    # Approach section: use IDs + notes from playbook or simple lookup in catalog
    approach_notes = []
    for note in entry.get("approach_notes", []):
        if isinstance(note, dict):
            approach_notes.append(note.get("text", str(note)))
        else:
            approach_notes.append(str(note))

    # If catalog provided, enrich with display names for the IDs
    id_to_name = {}
    if catalog:
        for a in catalog:
            id_to_name[a.get("id")] = a.get("name", a.get("id"))

    selected_approaches = []
    for aid in (recommended_approach_ids or []):
        selected_approaches.append({
            "id": aid,
            "name": id_to_name.get(aid, aid),
            "source": "playbook_recommended"
        })
    # conditionals if present (simplified)
    if conditional_approach_ids:
        # handle list of dicts or dict
        conds = conditional_approach_ids if isinstance(conditional_approach_ids, list) else [conditional_approach_ids]
        for c in conds:
            if isinstance(c, dict):
                for caid in (c.get("approach_ids") or []):
                    selected_approaches.append({
                        "id": caid,
                        "name": id_to_name.get(caid, caid),
                        "source": "playbook_conditional",
                        "condition": c.get("condition", "")
                    })

    # Filter Miller first
    filtered_miller = _filter_miller_for_playbook(
        miller_support_chunks or [], entry, recommended_approach_ids or []
    )

    # Primary fields from playbook (preserve structure + confidence)
    important = entry.get("important_anatomy", []) or []
    risks = entry.get("structures_at_risk", []) or []
    lands = entry.get("landmarks", []) or []
    notes = entry.get("approach_notes", []) or []

    # Merge supporting Miller (as citations only, deduped by text overlap later in curator)
    miller_support = []
    for m in filtered_miller:
        miller_support.append({
            "text": m.get("text") or m.get("source_quote", ""),
            "source_url": "miller:" + str(m.get("id", "")),
            "source_section": m.get("heading", "Miller gold"),
            "confidence": "supporting",
            "score": m.get("score"),
        })

    # Consolidated sources (playbook first)
    sources = []
    for u in entry.get("orthobullets_urls", []):
        sources.append({"type": "orthobullets", "url": u})
    for m in filtered_miller:
        sid = m.get("id")
        if sid:
            sources.append({"type": "miller_support", "id": sid, "page": m.get("page")})

    # Pearls: prefer playbook pimp_topics + approach notes (curator will format)
    pearls = entry.get("pimp_topics", []) or []
    for n in notes:
        if isinstance(n, dict):
            t = n.get("text", "")
            if t:
                pearls.append(t)
        elif isinstance(n, str):
            pearls.append(n)

    return {
        "approach": {
            "ids": recommended_approach_ids or [],
            "conditional": conditional_approach_ids or [],
            "blocked": blocked_approach_ids or [],
            "display": selected_approaches,
            "notes": approach_notes,
        },
        "importantAnatomy": important,
        "structuresAtRisk": risks,
        "landmarks": lands,
        "pearls": pearls,
        "millerSupport": miller_support,  # filtered only
        "sources": sources,
        "procedure_id": procedure_id,
        "manual_review": entry.get("manual_review", False),
        "review_reason": entry.get("review_reason", ""),
    }
