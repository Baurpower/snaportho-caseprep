"""CasePrep v3 procedure/approach normalization and review gates.

Legacy packets are useful source-backed drafts, but they model one approach as
the procedure and were migrated without a completed clinical-review record.
This module provides a backward-compatible runtime view that separates the
procedure core from independently reviewable approach options.  It never
manufactures missing technique: catalog-only alternatives are explicitly
marked as coverage gaps.
"""

from __future__ import annotations

import json
import hashlib
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from caseprep.approach_library import ApproachLibrary

BASE_DIR = Path(__file__).resolve().parents[2]
APPROACH_MAP_PATH = BASE_DIR / "data/approach_playbook/procedure_to_approach_map_v2.jsonl"
APPROACH_CATALOG_PATHS = (
    BASE_DIR / "data/lower_extremity/approaches/lower_extremity_approaches.jsonl",
    BASE_DIR / "data/upper_extremity/approaches/upper_extremity_approaches.jsonl",
)

AGENT_REVIEW_ROLES = frozenset(
    {
        "procedure_scope_reviewer",
        "approach_anatomy_reviewer",
        "operative_sequence_reviewer",
        "evidence_reviewer",
        "adversarial_safety_reviewer",
        "educational_value_reviewer",
    }
)
AUTHORITATIVE_HOSTS = (
    "surgeryreference.aofoundation.org",
    "pubmed.ncbi.nlm.nih.gov",
    "pmc.ncbi.nlm.nih.gov",
    "aaos.org",
    "orthobullets.com",
)


def _read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


@lru_cache(maxsize=1)
def approach_catalog() -> Dict[str, Dict[str, Any]]:
    catalog: Dict[str, Dict[str, Any]] = {}
    for path in APPROACH_CATALOG_PATHS:
        for row in _read_jsonl(path):
            if row.get("id"):
                catalog[str(row["id"])] = row
    return catalog


@lru_cache(maxsize=1)
def procedure_approach_map() -> Dict[str, Dict[str, Any]]:
    return {
        str(row["procedure_id"]): row
        for row in _read_jsonl(APPROACH_MAP_PATH)
        if row.get("procedure_id")
    }


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def reviewable_content_hash(packet: Dict[str, Any]) -> str:
    content = {key: value for key, value in packet.items() if key != "review"}
    encoded = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _agent_review_records(procedure_id: str, content_hash: str) -> List[Dict[str, Any]]:
    path = BASE_DIR / "data/caseprep/procedures" / procedure_id / "agent_reviews_v3.jsonl"
    records: List[Dict[str, Any]] = []
    for row in _read_jsonl(path):
        if (
            row.get("content_hash") == content_hash
            and row.get("role") in AGENT_REVIEW_ROLES
            and row.get("decision") == "pass"
            and row.get("reviewer_id")
        ):
            records.append(row)
    return records


def _legacy_primary(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    approach_id = str(payload.get("approach_id") or "").strip()
    approach_name = str(payload.get("approach_name") or "").strip()
    procedure_id = str(payload.get("procedure_id") or "").strip()
    if not approach_id and not approach_name:
        return None
    # A legacy approach id equal to the procedure slug is an unspecified
    # approach, not a safely inferred named technique.
    specific = bool(approach_id and approach_id != procedure_id) or bool(
        payload.get("approach_specific_notes")
    )
    return {
        "approach_id": approach_id or _slug(approach_name),
        "name": approach_name or approach_id.replace("_", " ").title(),
        "role": "primary" if specific else "unspecified",
        "content_status": "curated" if specific else "coverage_gap",
        "selection_indications": [],
        "selection_limitations": list(payload.get("validation_warnings") or []),
        "positioning": [],
        "exposure": list(payload.get("surgical_approach_anatomy") or []),
        "layers": list(payload.get("surgical_layers") or []),
        "landmarks": list(payload.get("key_landmarks") or []),
        "structures_at_risk": list(payload.get("structures_at_risk") or []),
        "pitfalls": list(payload.get("common_mistakes") or []),
        "questions": list(payload.get("attending_pimp_questions") or []),
        "source_urls": list(payload.get("source_urls") or []),
        "review_status": "agent_review_pending",
        "review_evidence": [],
        "coverage_notes": str(payload.get("approach_specific_notes") or "").strip(),
    }


def _authored_approaches(procedure_id: str) -> List[Dict[str, Any]]:
    library_rows = []
    for packet in ApproachLibrary().for_procedure(procedure_id):
        runtime = packet.get("runtime_fields")
        if isinstance(runtime, dict) and packet.get("content_status") != "source_indexed":
            library_rows.append(dict(runtime))
            continue
        # Native approach-library packets use the richer reusable schema. They
        # remain review-pending, but can be rendered as clearly labelled curated
        # draft content without flattening the source-of-truth packet on disk.
        if packet.get("schema_version") == "brobot_approach_packet_v1" and packet.get(
            "content_status"
        ) != "source_indexed":
            mapping = packet.get("procedure_mapping") or {}

            def texts(field: str) -> List[str]:
                return [
                    str(item.get("text") or item.get("question") or "").strip()
                    for item in packet.get(field) or []
                    if isinstance(item, dict)
                    and str(item.get("text") or item.get("question") or "").strip()
                ]

            questions = [
                {
                    "question": item.get("question"),
                    "answer": item.get("answer"),
                }
                for item in packet.get("questions") or []
                if isinstance(item, dict) and item.get("question") and item.get("answer")
            ]
            library_rows.append(
                {
                    "approach_id": packet["approach_id"],
                    "name": packet["name"],
                    "role": mapping.get("relationship") or "applicable",
                    "content_status": "curated",
                    "selection_indications": texts("indications"),
                    "selection_limitations": texts("limitations"),
                    "positioning": texts("positioning") + texts("setup"),
                    "exposure": texts("exposure"),
                    "layers": texts("layers"),
                    "landmarks": texts("surface_landmarks"),
                    "structures_at_risk": texts("structures_at_risk") + texts("danger_zones"),
                    "pitfalls": texts("retraction_hazards") + texts("complications"),
                    "questions": questions,
                    "source_urls": [
                        source.get("url")
                        for source in packet.get("sources") or []
                        if source.get("url")
                    ],
                    "review_status": (packet.get("review") or {}).get(
                        "status", "agent_review_pending"
                    ),
                    "review_evidence": (packet.get("review") or {}).get("artifacts", []),
                    "coverage_notes": str(mapping.get("condition") or ""),
                }
            )
    if library_rows:
        return library_rows
    path = BASE_DIR / "data/caseprep/procedures" / procedure_id / "approaches_v3.json"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    rows = value.get("approaches") if isinstance(value, dict) else value
    return [dict(row) for row in (rows or []) if isinstance(row, dict)]


def _catalog_option(approach_id: str, *, role: str, condition: str = "") -> Dict[str, Any]:
    row = approach_catalog().get(approach_id, {})
    return {
        "approach_id": approach_id,
        "name": row.get("name") or approach_id.replace("approach_", "").replace("_", " ").title(),
        "role": role,
        "content_status": "coverage_gap",
        "selection_indications": [condition] if condition else [],
        "selection_limitations": [
            "This approach is relevant to the procedure, but a complete, evidence-bound module is not yet available."
        ],
        "positioning": [],
        "exposure": [row.get("text")] if row.get("text") else [],
        "layers": [],
        "landmarks": [],
        "structures_at_risk": [],
        "pitfalls": [],
        "questions": [],
        "source_urls": [],
        "review_status": "coverage_gap",
        "review_evidence": [],
        "coverage_notes": "Known alternative; do not use as an operative guide until its module passes review gates.",
    }


def _attach_review_state(packet: Dict[str, Any], *, migrated: bool) -> Dict[str, Any]:
    """Bind review state to packet content for both migrated and native v3 data."""
    normalized = dict(packet)
    procedure_id = str(normalized.get("procedure_id") or "")
    options = list(normalized.get("approaches") or [])
    gaps = [option for option in options if option.get("content_status") == "coverage_gap"]
    review = dict(normalized.get("review") or {})
    review.update(
        {
            "status": "agent_review_pending" if migrated else "draft",
            "label": "Curated · agent review pending" if migrated else "Draft content",
            "reviewed_approach_ids": [],
            "required_agent_roles": sorted(AGENT_REVIEW_ROLES),
            "completed_agent_reviews": [],
            "human_review_required": False,
            "evidence_gate_passed": False,
            "legacy_certification_migrated": migrated,
        }
    )
    normalized["review"] = review
    digest = reviewable_content_hash(normalized)
    records = _agent_review_records(procedure_id, digest)
    completed = sorted({str(row["role"]) for row in records})
    evidence_gate_passed = not gaps and bool(options) and all(
        len(option.get("source_urls") or []) >= 2 for option in options
    )
    review.update(
        {
            "content_hash": digest,
            "completed_agent_reviews": completed,
            "review_artifacts": records,
            "evidence_gate_passed": evidence_gate_passed,
        }
    )
    if set(completed) == AGENT_REVIEW_ROLES and evidence_gate_passed:
        review.update(
            {
                "status": "agent_reviewed",
                "label": "Independently agent reviewed",
                "reviewed_approach_ids": [option.get("approach_id") for option in options],
            }
        )
    return normalized


def normalize_packet(payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return a non-mutating v3 runtime view for v2 or v3 packet data."""
    if not payload:
        return None
    if payload.get("schema_version") == "brobot_case_prep_payload_v3":
        migrated = bool((payload.get("review") or {}).get("legacy_certification_migrated"))
        return _attach_review_state(dict(payload), migrated=migrated)

    procedure_id = str(payload.get("procedure_id") or "")
    mapping = procedure_approach_map().get(procedure_id, {})
    options: List[Dict[str, Any]] = _authored_approaches(procedure_id)
    primary = _legacy_primary(payload)
    recommended = list(mapping.get("recommended_approach_ids") or [])
    conditional_rows = list(mapping.get("conditional_approach_ids") or [])
    # A single mapped approach normally describes the approach already present
    # in the legacy packet. Attach the canonical identity rather than creating
    # a duplicate "missing" card. Multiple or conditional mappings represent
    # true choices and remain separate modules.
    if (
        primary
        and primary.get("role") == "unspecified"
        and len(recommended) == 1
        and mapping.get("confidence") == "high"
        and (primary.get("exposure") or primary.get("structures_at_risk"))
    ):
        canonical = approach_catalog().get(recommended[0], {})
        primary.update(
            {
                "approach_id": recommended[0],
                "name": canonical.get("name") or primary.get("name"),
                "role": "primary",
                "content_status": "curated",
            }
        )
    # An authored v3 module is the authoritative approach split. Do not append
    # the legacy aggregate card, which can blend multiple approaches and
    # undermine the point of separating them.
    if not options and primary and primary.get("approach_id") not in {
        row.get("approach_id") for row in options
    }:
        options.append(primary)
    seen = {str(item.get("approach_id")) for item in options}
    recommended_to_add = recommended if len(recommended) > 1 or not primary else []
    for approach_id in recommended_to_add:
        if approach_id not in seen:
            options.append(_catalog_option(approach_id, role="alternative"))
            seen.add(approach_id)
    for conditional in conditional_rows:
        if not isinstance(conditional, dict):
            continue
        for approach_id in conditional.get("approach_ids") or []:
            if approach_id not in seen:
                options.append(
                    _catalog_option(
                        approach_id,
                        role="conditional",
                        condition=str(conditional.get("condition") or ""),
                    )
                )
                seen.add(approach_id)

    complete = [a for a in options if a.get("content_status") in {"reviewed", "curated"}]
    gaps = [a for a in options if a.get("content_status") == "coverage_gap"]
    migrated = str(payload.get("case_prep_status") or "").lower() == "certified"
    normalized = {
        **payload,
        "schema_version": "brobot_case_prep_payload_v3",
        "procedure_core": {
            "overview": payload.get("procedure_overview") or "",
            "indications": payload.get("indications") or [],
            "shared_anatomy": payload.get("must_know_anatomy") or [],
            "implant_or_reduction": payload.get("reduction_or_implant_anatomy") or [],
            "fluoroscopy": payload.get("fluoroscopy_checkpoints") or [],
            "postop": payload.get("night_before_review_checklist") or [],
        },
        "approaches": options,
        "approach_coverage": {
            "known_count": len(options),
            "complete_count": len(complete),
            "gap_count": len(gaps),
            "is_multi_approach": len(options) > 1,
            "status": "complete" if options and not gaps else "partial",
        },
        "review": {},
    }
    return _attach_review_state(normalized, migrated=migrated)


def detect_requested_approach(prompt: str, packet: Optional[Dict[str, Any]]) -> Optional[str]:
    if not packet:
        return None
    blob = f" {prompt.lower()} "
    for option in packet.get("approaches") or []:
        approach_id = str(option.get("approach_id") or "")
        name = str(option.get("name") or "")
        tokens = {
            phrase.strip().lower()
            for phrase in (
                name,
                name.split("(")[0],
                *re.split(r"[/()]", name),
                approach_id.replace("_", " "),
            )
            if len(phrase.strip()) >= 5
        }
        if any(f" {token} " in blob or token in blob for token in tokens):
            return approach_id
    return None


def approach_decision_payload(prompt: str, payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    packet = normalize_packet(payload)
    if not packet:
        return {"status": "unavailable", "selected_approach_id": None, "approaches": []}
    selected = detect_requested_approach(prompt, packet)
    options = packet.get("approaches") or []
    if not selected and len(options) == 1 and options[0].get("role") == "primary":
        selected = options[0].get("approach_id")
    return {
        "status": "selected" if selected else ("choice_required" if len(options) > 1 else "unspecified"),
        "selected_approach_id": selected,
        "approaches": options,
        "coverage": packet.get("approach_coverage") or {},
        "review": packet.get("review") or {},
        "message": (
            "The case description does not identify an approach. Compare the options and confirm the planned approach with the attending."
            if not selected and len(options) > 1
            else ""
        ),
    }


def validate_review_gate(packet: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic gate intended for a second-agent review workflow."""
    normalized = normalize_packet(packet) or {}
    failures: List[str] = []
    approaches = normalized.get("approaches") or []
    if not approaches:
        failures.append("No approach options are modeled.")
    for approach in approaches:
        if approach.get("content_status") == "coverage_gap":
            failures.append(f"Approach coverage missing: {approach.get('name')}")
            continue
        if len(approach.get("source_urls") or []) < 2:
            failures.append(f"Approach has fewer than two sources: {approach.get('name')}")
        if not approach.get("structures_at_risk"):
            failures.append(f"Approach lacks structured risks: {approach.get('name')}")
        if not approach.get("questions"):
            failures.append(f"Approach lacks question-answer review: {approach.get('name')}")
    urls = {
        str(url)
        for approach in approaches
        for url in (approach.get("source_urls") or [])
    }
    if not any(any(host in url for host in AUTHORITATIVE_HOSTS) for url in urls):
        failures.append("No recognized authoritative source is linked.")
    completed = set((normalized.get("review") or {}).get("completed_agent_reviews") or [])
    missing_roles = sorted(AGENT_REVIEW_ROLES - completed)
    if missing_roles:
        failures.append("Missing independent agent reviews: " + ", ".join(missing_roles))
    return {
        "passed": not failures,
        "failures": failures,
        "missing_agent_roles": missing_roles,
        "approach_count": len(approaches),
    }
