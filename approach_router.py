"""
Deterministic Approach Router (pre-GPT safety layer) + Supported Case Gate.

Purpose:
- Load the Orthobullets-sourced v1 playbook (procedure_to_approach_map_v1.jsonl).
- For common, obvious procedures with high/medium confidence + non-empty recommended approach IDs: return supported=true + constraints.
- This gates both legacy GPT approach guessing and Miller retrieval (when ENABLE_LOCAL_ANATOMY_RAG=true).
- Prevents guessing for unknown/manual_review/catalog-gap cases (e.g. tibial shaft ORIF, bimalleolar while lateral/medial IDs missing).
- GPT (or Miller) is only used inside the supported subset, or fully skipped for unsupported.

Public API (new primary gate):
    get_supported_case(case_prompt: str) -> dict
    Returns:
    {
      "case_family": "distal_radius_fracture_orif" | "unknown" | procedure_id,
      "supported": true/false,
      "confidence": "high" | "medium" | "low" | "unknown",
      "recommended_approach_ids": [...],
      "conditional_approach_ids": [...],
      "blocked_approach_ids": [...],
      "reason": "...",
      "matched_triggers": [...]
    }

Backward-compatible (delegates to new gate):
    route_approaches(case_prompt: str) -> dict   # old shape with allowed_*/case_family
    get_allowed_and_blocked(case_prompt: str) -> dict

supported=true only for high/medium confidence entries that have non-empty recommended_approach_ids.
manual_review entries, entries with empty recommended (catalog gaps), and true unknowns → supported=false.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Robust procedure resolver (Phase 1-5 of matching layer). Used before any trigger/playbook scoring.
try:
    from procedure_registry import resolve_procedure, is_certified
except Exception:
    resolve_procedure = None
    is_certified = None  # type: ignore

BASE_DIR = Path(__file__).resolve().parent
PLAYBOOK_JSONL = BASE_DIR / "data" / "approach_playbook" / "procedure_to_approach_map_v1.jsonl"
PLAYBOOK_YAML = BASE_DIR / "data" / "approach_playbook" / "procedure_to_approach_map_v1.yaml"
# Full Orthobullets anatomy playbook (primary content source)
ANATOMY_PLAYBOOK_JSONL = BASE_DIR / "data" / "approach_playbook" / "orthobullets_procedure_playbook_v1.jsonl"
ANATOMY_PLAYBOOK_YAML = BASE_DIR / "data" / "approach_playbook" / "orthobullets_procedure_playbook_v1.yaml"
# Legacy fallback (for transition)
MAPPINGS_PATH = BASE_DIR / "data" / "approach_router" / "approach_mappings.yaml"

# Caches
_PLAYBOOK: Optional[List[Dict[str, Any]]] = None
_ANATOMY_PLAYBOOK: Optional[List[Dict[str, Any]]] = None
_MAPPINGS: Optional[Dict[str, Any]] = None

def _load_playbook() -> List[Dict[str, Any]]:
    global _PLAYBOOK
    if _PLAYBOOK is None:
        _PLAYBOOK = []
        loaded = False
        for p in (PLAYBOOK_JSONL, PLAYBOOK_YAML):
            if p.exists():
                if p.suffix == ".jsonl":
                    with p.open("r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                _PLAYBOOK.append(json.loads(line))
                    loaded = True
                    break
                else:
                    with p.open("r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or []
                    if isinstance(data, list):
                        _PLAYBOOK = data
                    elif isinstance(data, dict):
                        # convert keyed yaml to list if needed
                        _PLAYBOOK = [{"procedure_id": k, **v} for k, v in data.items()]
                    loaded = True
                    break
        if not loaded:
            # fallback to legacy yaml structure if present
            legacy = _load_mappings()
            for fam, entry in legacy.items():
                if fam == "unknown": continue
                _PLAYBOOK.append({
                    "procedure_id": fam,
                    "display_name": fam.replace("_", " ").title(),
                    "triggers": entry.get("triggers", []),
                    "recommended_approach_ids": entry.get("allowed_approach_ids", []),
                    "conditional_approach_ids": entry.get("conditional_approach_ids", []),
                    "blocked_approach_ids": entry.get("blocked_approach_ids", []),
                    "confidence": "high",
                    "evidence_note": entry.get("notes", ""),
                })
    return _PLAYBOOK

def _load_mappings() -> Dict[str, Any]:
    global _MAPPINGS
    if _MAPPINGS is None:
        if not MAPPINGS_PATH.exists():
            _MAPPINGS = {}
        else:
            with MAPPINGS_PATH.open("r", encoding="utf-8") as f:
                _MAPPINGS = yaml.safe_load(f) or {}
    return _MAPPINGS

def _load_anatomy_playbook() -> List[Dict[str, Any]]:
    global _ANATOMY_PLAYBOOK
    if _ANATOMY_PLAYBOOK is None:
        _ANATOMY_PLAYBOOK = []
        loaded = False
        for p in (ANATOMY_PLAYBOOK_JSONL, ANATOMY_PLAYBOOK_YAML):
            if p.exists():
                if p.suffix == ".jsonl":
                    with p.open("r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                _ANATOMY_PLAYBOOK.append(json.loads(line))
                    loaded = True
                    break
                else:
                    with p.open("r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or []
                    if isinstance(data, list):
                        _ANATOMY_PLAYBOOK = data
                    elif isinstance(data, dict):
                        _ANATOMY_PLAYBOOK = [{"procedure_id": k, **v} for k, v in data.items()]
                    loaded = True
                    break
        if not loaded:
            # fallback empty
            _ANATOMY_PLAYBOOK = []
    return _ANATOMY_PLAYBOOK

def get_playbook_anatomy_entry(procedure_id: str) -> Optional[Dict[str, Any]]:
    """Lookup full OB playbook entry by procedure_id. Primary source for anatomy content."""
    apb = _load_anatomy_playbook()
    for entry in apb:
        if entry.get("procedure_id") == procedure_id:
            return entry
    return None

def get_supported_case_with_playbook(case_prompt: str) -> Dict[str, Any]:
    """Extended supported case that also attaches the full anatomy playbook entry if matched."""
    sc = get_supported_case(case_prompt)
    if sc.get("supported") and sc.get("case_family"):
        entry = get_playbook_anatomy_entry(sc["case_family"])
        if entry:
            sc["playbook_entry"] = entry
    return sc

def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())

def _matches_any(text: str, triggers: List[str]) -> bool:
    if not triggers:
        return False
    norm = _normalize(text)
    for t in triggers:
        if t.lower() in norm:
            return True
    return False

def _score_match(prompt_norm: str, triggers: List[str]) -> int:
    """Simple score: number of triggers that hit (more specific wins)."""
    if not triggers:
        return 0
    hits = 0
    for t in triggers:
        if t.lower() in prompt_norm:
            hits += 1
    return hits

def get_supported_case(case_prompt: str) -> Dict[str, Any]:
    """
    New primary supported-case gate.
    Procedure resolver runs FIRST: raw user text -> canonical slug.
    Router then does EXACT slug lookup in playbook (never re-matches raw text).
    """
    playbook = _load_playbook()
    prompt = case_prompt or ""

    # --- Dedicated resolver layer (before any playbook routing) ---
    canonical_slug: Optional[str] = None
    resolver_meta: Dict[str, Any] = {}
    if resolve_procedure is not None:
        try:
            resolver_meta = resolve_procedure(prompt) or {}
            canonical_slug = resolver_meta.get("procedure_slug")
        except Exception:
            canonical_slug = None

    # If resolver gave us a canonical slug, do exact (not text) lookup in the playbook.
    if canonical_slug:
        for entry in playbook:
            if entry.get("procedure_id") == canonical_slug:
                proc_id = canonical_slug
                conf = (entry.get("confidence") or "high").lower()
                rec = list(entry.get("recommended_approach_ids", []) or [])
                cond = entry.get("conditional_approach_ids", []) or []
                blk = list(entry.get("blocked_approach_ids", []) or [])
                supported = (conf in ("high", "medium")) and (len(rec) > 0)
                reason = ""
                if not supported:
                    if conf == "manual_review":
                        reason = "manual_review (catalog gap or pending review per playbook)"
                    elif len(rec) == 0:
                        reason = "no recommended approach IDs in playbook (catalog gap)"
                    else:
                        reason = f"confidence={conf} insufficient for support"
                return {
                    "case_family": proc_id,
                    "supported": supported,
                    "confidence": conf,
                    "recommended_approach_ids": rec,
                    "conditional_approach_ids": cond,
                    "blocked_approach_ids": blk,
                    "reason": reason or entry.get("evidence_note", "")[:200],
                    "matched_triggers": [canonical_slug],  # explicit: driven by resolver slug
                    "resolver": {
                        "method": resolver_meta.get("match_method"),
                        "score": resolver_meta.get("match_score"),
                    },
                }
        # Slug resolved but this playbook (map) has no entry for it (e.g. certified BroBot path only).
        # Still return a usable record so downstream certified payload logic can short-circuit.
        rec = []
        supported = bool(is_certified and is_certified(canonical_slug))
        return {
            "case_family": canonical_slug,
            "supported": supported,
            "confidence": "high" if supported else "medium",
            "recommended_approach_ids": rec,
            "conditional_approach_ids": [],
            "blocked_approach_ids": [],
            "reason": "",
            "matched_triggers": [canonical_slug],
            "resolver": {
                "method": resolver_meta.get("match_method"),
                "score": resolver_meta.get("match_score"),
            },
        }

    # --- Fallback: legacy text trigger scoring on raw prompt (only for truly unknown wording) ---
    prompt_norm = _normalize(prompt)

    best: Optional[Dict[str, Any]] = None
    best_score = -1
    best_conf_priority = 0  # high=3, med=2, low=1, unknown/manual=0

    conf_priority = {"high": 3, "medium": 2, "low": 1, "manual_review": 0, "unknown": 0}

    for entry in playbook:
        triggers = entry.get("triggers", []) or []
        score = _score_match(prompt_norm, triggers)
        if score <= 0:
            continue
        conf = (entry.get("confidence") or "unknown").lower()
        pri = conf_priority.get(conf, 0)
        # tie-break: higher conf or more hits
        if (pri > best_conf_priority) or (pri == best_conf_priority and score > best_score):
            best = entry
            best_score = score
            best_conf_priority = pri

    if not best:
        return {
            "case_family": "unknown",
            "supported": False,
            "confidence": "unknown",
            "recommended_approach_ids": [],
            "conditional_approach_ids": [],
            "blocked_approach_ids": [],
            "reason": "Could not confidently identify a supported procedure from the case description.",
            "matched_triggers": [],
            "suggestedMatches": [],
        }

    proc_id = best.get("procedure_id") or best.get("case_family") or "unknown"
    conf = (best.get("confidence") or "unknown").lower()
    rec = list(best.get("recommended_approach_ids", []) or [])
    cond = best.get("conditional_approach_ids", []) or []
    blk = list(best.get("blocked_approach_ids", []) or [])
    matched = [t for t in (best.get("triggers") or []) if t.lower() in prompt_norm]

    # supported rule per spec
    supported = (conf in ("high", "medium")) and (len(rec) > 0)
    reason = ""
    if not supported:
        if conf == "manual_review":
            reason = "manual_review (catalog gap or pending review per playbook)"
        elif len(rec) == 0:
            reason = "no recommended approach IDs in playbook (catalog gap)"
        else:
            reason = f"confidence={conf} insufficient for support"

    return {
        "case_family": proc_id,
        "supported": supported,
        "confidence": conf,
        "recommended_approach_ids": rec,
        "conditional_approach_ids": cond,
        "blocked_approach_ids": blk,
        "reason": reason or best.get("evidence_note", "")[:200],
        "matched_triggers": matched,
    }

def route_approaches(case_prompt: str) -> Dict[str, Any]:
    """
    Backward-compatible wrapper.
    Maps new supported gate result to the legacy shape used by anatomy_gpt + validate.
    """
    sc = get_supported_case(case_prompt)
    # Map to old expected keys for minimal disruption
    allowed = list(sc.get("recommended_approach_ids", []))
    # merge any fired conditionals into allowed for legacy callers (simple union)
    for c in (sc.get("conditional_approach_ids") or []):
        if isinstance(c, dict):
            allowed.extend(c.get("approach_ids", []) or [])
        elif isinstance(c, list):
            allowed.extend(c)
    allowed = sorted(set(allowed))

    return {
        "case_family": sc.get("case_family", "unknown"),
        "allowed_approach_ids": allowed,
        "blocked_approach_ids": sc.get("blocked_approach_ids", []),
        "conditional_approach_ids": sc.get("conditional_approach_ids", []),
        "confidence": sc.get("confidence", "unknown"),
        "rationale": sc.get("reason", ""),
        "notes": "",
        # extra for new gate consumers
        "supported": sc.get("supported", False),
        "matched_triggers": sc.get("matched_triggers", []),
    }

def get_allowed_and_blocked(case_prompt: str) -> Dict[str, Any]:
    """Convenience wrapper used by callers (anatomy_gpt etc.)."""
    return route_approaches(case_prompt)


def validate_selected_approaches(
    selected_ids: List[str],
    catalog_ids: set,
    router_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Post-selection safety validator.
    Returns a dict with:
      - valid_selected: list of IDs that passed all checks
      - removed: list of removed IDs + reason
      - confidence_adjustment: "ok" | "downgraded" | "blocked"
      - notes: ...
    """
    valid = []
    removed = []
    confidence = "ok"
    notes = []

    allowed = set(router_result.get("allowed_approach_ids", [])) if router_result else set()
    blocked = set(router_result.get("blocked_approach_ids", [])) if router_result else set()

    for aid in selected_ids:
        if aid not in catalog_ids:
            removed.append({"id": aid, "reason": "ID does not exist in loaded catalog"})
            confidence = "downgraded"
            continue
        if blocked and aid in blocked:
            removed.append({"id": aid, "reason": "explicitly blocked by deterministic router for this case family"})
            confidence = "blocked"
            continue
        if allowed and aid not in allowed:
            # If router gave a strict allowed list and this wasn't in it, be conservative
            removed.append({"id": aid, "reason": "not in router-allowed list for this case family"})
            confidence = "downgraded"
            continue
        valid.append(aid)

    if not valid and selected_ids:
        notes.append("All selected approaches were removed by safety validation. Falling back to empty selection.")

    return {
        "valid_selected": valid,
        "removed": removed,
        "confidence_adjustment": confidence,
        "notes": "; ".join(notes) if notes else "",
    }
