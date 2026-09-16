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

TECHNIQUE_FAMILIES = {
    "nailing": {
        "prompt": re.compile(
            r"\b(?:imn|im\s+nails?|intramedullary(?:\s+nails?|\s+nailing)?|nails?|nailing|esin|cephalomedullary)\b",
            re.IGNORECASE,
        ),
        "identity": re.compile(
            r"\b(?:imn|intramedullary|nails?|nailing|esin|cephalomedullary)\b",
            re.IGNORECASE,
        ),
    },
    "arthroscopy": {
        "prompt": re.compile(
            r"\b(?:arthroscopy|arthroscopic|scope|scoped)\b", re.IGNORECASE
        ),
        "identity": re.compile(
            r"\b(?:arthroscopy|arthroscopic|portal|portals)\b", re.IGNORECASE
        ),
    },
    "external_fixation": {
        "prompt": re.compile(
            r"\b(?:external\s+fix(?:ation|ator)?|ex[\s-]?fix|exfix|schanz)\b",
            re.IGNORECASE,
        ),
        "identity": re.compile(
            r"\b(?:external\s+fix(?:ation|ator)?|fixator|schanz|half[\s-]?pins?|pin\s+safe\s+zones?)\b",
            re.IGNORECASE,
        ),
    },
    "pinning": {
        "prompt": re.compile(
            r"\b(?:crpp|pinning|percutaneous\s+(?:pins?|screws?|fixation)|perc\s+(?:pins?|screws?)|k[\s-]?wires?|kirschner\s+wires?)\b",
            re.IGNORECASE,
        ),
        "identity": re.compile(
            r"\b(?:crpp|pinning|percutaneous\s+(?:pins?|screws?|fixation)|k[\s-]?wires?|kirschner\s+wires?)\b",
            re.IGNORECASE,
        ),
    },
    "plating": {
        "prompt": re.compile(
            r"\b(?:plates?|plating|mipo|mio|bridge\s+plating|submuscular\s+plating)\b",
            re.IGNORECASE,
        ),
        "identity": re.compile(
            r"\b(?:plates?|plating|mipo|mio|bridge\s+plating|submuscular)\b",
            re.IGNORECASE,
        ),
    },
}


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
        not approach_id and payload.get("approach_specific_notes")
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
    if procedure_id == "tha_posterior":
        # Generic THA aliases still resolve to this legacy slug. Offer the
        # supported THA corridors rather than treating that slug as a choice.
        # The globally shared posterior module was authored for hemiarthroplasty;
        # retain the THA packet's own technique and provenance instead.
        path = BASE_DIR / "data/caseprep/procedures/tha_posterior/certified_payload.json"
        posterior = _legacy_primary(json.loads(path.read_text(encoding="utf-8")))
        if posterior:
            posterior.update({
                "approach_id": "tha_posterior_moore_southern",
                "name": "Posterior (Moore/Southern) approach",
                "aliases": ["posterior tha", "posterolateral", "moore southern"],
                "selection_indications": ["Posterior approach for total hip arthroplasty."],
            })
            return [posterior, *_authored_approaches("tha_anterior")]
    library_rows = []
    for packet in ApproachLibrary().for_procedure(procedure_id):
        runtime = packet.get("runtime_fields")
        if isinstance(runtime, dict):
            library_rows.append(dict(runtime))
            continue
        # Native approach-library packets use the richer reusable schema. They
        # remain review-pending, but can be rendered as clearly labelled curated
        # draft content without flattening the source-of-truth packet on disk.
        if packet.get("schema_version") == "brobot_approach_packet_v1":
            mapping = packet.get("procedure_mapping") or {}
            display_name = re.sub(
                r"\s+Indications\s+And\s+Approach$",
                "",
                str(packet.get("name") or ""),
                flags=re.IGNORECASE,
            )
            if procedure_id == "tha_anterior":
                display_name = display_name.removesuffix(" (periprosthetic)")

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
                    "name": display_name or packet["name"],
                    "aliases": list(packet.get("aliases") or []),
                    "role": mapping.get("relationship") or "applicable",
                    "content_status": packet.get("content_status") or "curated",
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
                    "corridor": str(packet.get("corridor") or ""),
                    "claim_count": len(packet.get("claims") or []),
                    "source_count": len(packet.get("sources") or []),
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
    gaps = [
        option
        for option in options
        if option.get("content_status") in {"coverage_gap", "source_indexed"}
    ]
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

    complete = [
        a
        for a in options
        if a.get("content_status")
        not in {"coverage_gap", "source_indexed", None, ""}
    ]
    gaps = [
        a
        for a in options
        if a.get("content_status") in {"coverage_gap", "source_indexed"}
    ]
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
    # Normalize punctuation and enforce word/phrase boundaries. Substring
    # matching makes "lateral" incorrectly match "posterolateral".
    blob = f" {' '.join(re.findall(r'[a-z0-9]+', prompt.lower()))} "
    ignored_words = {
        "approach", "to", "the", "of", "for", "and", "distal", "proximal",
        "radius", "ulna", "humerus", "femur", "tibia", "hip", "knee",
        "shoulder", "wrist", "ankle", "hand", "foot", "spine", "cervical",
        "shaft", "fracture", "orif", "nailing", "nail", "entry",
        "arthroplasty", "replacement", "reconstruction", "repair",
        "release", "fusion", "carpal", "tunnel", "total", "midline",
    }
    option_words: Dict[str, List[str]] = {}
    word_owners: Dict[str, set[str]] = {}
    for option in packet.get("approaches") or []:
        approach_id = str(option.get("approach_id") or "")
        words = [
            word for word in re.findall(r"[a-z0-9]+", str(option.get("name") or "").lower())
            if word not in ignored_words and len(word) >= 4
        ]
        option_words[approach_id] = words
        for word in set(words):
            word_owners.setdefault(word, set()).add(approach_id)
    matches: List[tuple[int, int, str]] = []
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
        tokens.update(
            str(alias).strip().lower()
            for alias in option.get("aliases") or []
            if len(str(alias).strip()) >= 3
        )
        name_words = option_words.get(approach_id, [])
        tokens.update(
            " ".join(name_words[index : index + 2])
            for index in range(max(0, len(name_words) - 1))
        )
        # A single corridor word (posterior, deltopectoral, suprapatellar) is
        # safe only when it identifies exactly one option for this procedure.
        tokens.update(word for word in name_words if len(word_owners.get(word, ())) == 1)
        if "arthroscopy" in name_words:
            tokens.add("arthroscopic")
        matched = [token for token in tokens if f" {token} " in blob]
        if matched:
            # Prefer the most specific phrase and, for duplicate legacy/native
            # identities, the richer claim-bound packet.
            matches.append(
                (
                    max(len(token.split()) for token in matched),
                    int(option.get("claim_count") or 0),
                    approach_id,
                )
            )
    return max(matches)[2] if matches else None


def _option_identity(option: Dict[str, Any]) -> str:
    return " ".join(
        [
            str(option.get("approach_id") or "").replace("_", " "),
            str(option.get("name") or ""),
            *(str(alias) for alias in option.get("aliases") or []),
        ]
    ).lower()


def _technique_filtered_options(
    prompt: str, options: List[Dict[str, Any]]
) -> tuple[List[Dict[str, Any]], Optional[str]]:
    """Hard-filter mixed packets by the technique explicitly named by the user.

    A technique family identifies eligible approaches, not necessarily a
    single corridor. If several eligible corridors remain, the decision layer
    asks a focused question instead of falling back to unrelated approaches.
    """
    requested_family = next(
        (
            family
            for family, patterns in TECHNIQUE_FAMILIES.items()
            if patterns["prompt"].search(prompt)
        ),
        None,
    )
    narrowed = options
    if requested_family:
        identity_pattern = TECHNIQUE_FAMILIES[requested_family]["identity"]
        narrowed = [
            option
            for option in options
            if identity_pattern.search(
                _option_identity(option)
                + (
                    " " + str(option.get("coverage_notes") or "").lower()
                    if requested_family == "plating"
                    else ""
                )
            )
        ]

    prompt_words = set(re.findall(r"[a-z0-9]+", prompt.lower()))
    pediatric_words = {"pediatric", "paediatric", "peds", "child", "adolescent"}
    pediatric_requested = bool(prompt_words & pediatric_words)
    if pediatric_requested:
        pediatric = [
            option
            for option in narrowed
            if re.search(r"\b(?:pediatric|paediatric|esin)\b", _option_identity(option))
        ]
        if pediatric:
            narrowed = pediatric
    elif requested_family:
        adult = [
            option
            for option in narrowed
            if not re.search(r"\b(?:pediatric|paediatric|esin)\b", _option_identity(option))
        ]
        if adult:
            narrowed = adult

    # These words identify a nail corridor within the nailing family. Apply
    # them as filters before the generic token matcher so a shared word such as
    # "retrograde" does not become ambiguous merely because pediatric and
    # adult modules coexist in the source library.
    qualifier_axes = (
        (("antegrade",), ("retrograde",)),
        (("suprapatellar",), ("infrapatellar",)),
        (("piriformis",), ("trochanteric", "trochanter")),
    )
    for axis in qualifier_axes:
        requested = [
            qualifiers
            for qualifiers in axis
            if any(word in prompt_words for word in qualifiers)
        ]
        if not requested:
            continue
        qualified = [
            option
            for option in narrowed
            if any(
                word in _option_identity(option)
                for qualifiers in requested
                for word in qualifiers
            )
        ]
        if qualified:
            narrowed = qualified

    # Open/endoscopic is an access choice rather than a fixation family. Only
    # interpret "open" as an access request when an endoscopic alternative is
    # actually modeled, avoiding the false inference that an open fracture
    # necessarily requests an open surgical exposure.
    identities = [_option_identity(option) for option in narrowed]
    has_endoscopic_choice = any("endoscopic" in value for value in identities)
    if re.search(r"\bendoscopic\b", prompt, re.IGNORECASE):
        endoscopic = [
            option for option in narrowed if "endoscopic" in _option_identity(option)
        ]
        narrowed = endoscopic
    elif has_endoscopic_choice and re.search(r"\bopen\b", prompt, re.IGNORECASE):
        opened = [
            option
            for option in narrowed
            if "open" in _option_identity(option)
            or "endoscopic" not in _option_identity(option)
        ]
        if opened:
            narrowed = opened
    return narrowed, requested_family


MAX_RUNTIME_APPROACHES = 3


def _filter_runtime_approaches(
    procedure_id: str,
    prompt: str,
    options: List[Dict[str, Any]],
    *,
    requested_family: Optional[str],
) -> List[Dict[str, Any]]:
    """Keep playbook-recommended corridors, not every library packet for the bone."""
    mapping = procedure_approach_map().get(procedure_id) or {}
    blocked = {str(value) for value in mapping.get("blocked_approach_ids") or [] if value}
    options = [
        option
        for option in options
        if str(option.get("approach_id") or "") not in blocked
    ]
    recommended = [str(value) for value in mapping.get("recommended_approach_ids") or [] if value]
    extra: List[str] = []
    prompt_l = prompt.lower()
    for row in mapping.get("conditional_approach_ids") or []:
        if not isinstance(row, dict):
            continue
        triggers = [str(trigger).lower() for trigger in row.get("triggers") or []]
        ids = [str(value) for value in row.get("approach_ids") or [] if value]
        if ids and (not triggers or any(trigger in prompt_l for trigger in triggers)):
            extra.extend(ids)
    allow = list(dict.fromkeys([*recommended, *extra]))
    by_id = {
        str(option.get("approach_id")): option
        for option in options
        if option.get("approach_id")
    }
    if allow and not requested_family:
        ordered = [by_id[approach_id] for approach_id in allow if approach_id in by_id]
        if ordered:
            options = ordered
    seen_corridors: set[str] = set()
    deduped: List[Dict[str, Any]] = []
    for option in options:
        corridor = re.sub(
            r"[^a-z0-9]+",
            " ",
            str(option.get("name") or option.get("approach_id") or "").lower(),
        ).strip()
        if corridor in seen_corridors:
            continue
        seen_corridors.add(corridor)
        deduped.append(option)
    return deduped[:MAX_RUNTIME_APPROACHES]


def approach_decision_payload(prompt: str, payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    packet = normalize_packet(payload)
    if not packet:
        return {"status": "unavailable", "selected_approach_id": None, "approaches": []}
    known_options = packet.get("approaches") or []
    # A coverage-gap card is useful in an editorial dashboard, but it must not
    # be presented to a resident as a selectable runtime approach. Selecting
    # one cannot produce setup/exposure/safety content and leaves the client on
    # an empty guide. Keep those records in the payload for coverage reporting
    # while limiting the interactive decision to content-capable approaches.
    unavailable_options = [
        option
        for option in known_options
        if option.get("content_status") in {"coverage_gap", "source_indexed", None, ""}
    ]
    options = [option for option in known_options if option not in unavailable_options]
    options, requested_family = _technique_filtered_options(prompt, options)
    if requested_family and not options:
        return {
            "status": "unavailable",
            "selected_approach_id": None,
            "selected_approach_ids": [],
            "approaches": [],
            "unavailable_approaches": unavailable_options,
            "coverage": packet.get("approach_coverage") or {},
            "review": packet.get("review") or {},
            "message": f"Reviewed {requested_family.replace('_', ' ')} approach guidance is not available for this procedure.",
        }
    normalized_prompt = " ".join(re.findall(r"[a-z0-9]+", prompt.lower()))
    explicitly_named = []
    for option in options:
        approach_id = str(option.get("approach_id") or "")
        phrases = [str(option.get("name") or ""), *(option.get("aliases") or [])]
        if any(
            len(phrase.split()) >= 2
            and " ".join(re.findall(r"[a-z0-9]+", phrase.lower())) in normalized_prompt
            for phrase in phrases
            if str(phrase).strip()
        ):
            explicitly_named.append(approach_id)
    selected_ids = list(dict.fromkeys(explicitly_named))
    selectable_packet = {**packet, "approaches": options}
    selected = selected_ids[0] if len(selected_ids) == 1 else detect_requested_approach(
        prompt, selectable_packet
    )
    named_ids = list(dict.fromkeys([*selected_ids, *([selected] if selected else [])]))
    filtered = _filter_runtime_approaches(
        str(packet.get("procedure_id") or ""),
        prompt,
        options,
        requested_family=requested_family,
    )
    by_id = {
        str(option.get("approach_id")): option
        for option in options
        if option.get("approach_id")
    }
    merged = list(filtered)
    seen = {str(option.get("approach_id")) for option in merged}
    for approach_id in named_ids:
        if approach_id in by_id and approach_id not in seen:
            merged.append(by_id[approach_id])
            seen.add(approach_id)
    options = merged or options
    if not selected and detect_requested_approach(
        prompt, {**packet, "approaches": unavailable_options}
    ):
        return {
            "status": "unavailable",
            "selected_approach_id": None,
            "selected_approach_ids": [],
            "approaches": [],
            "unavailable_approaches": unavailable_options,
            "coverage": packet.get("approach_coverage") or {},
            "review": packet.get("review") or {},
            "message": "Reviewed approach guidance is not available for the requested technique.",
        }
    if selected and not selected_ids:
        selected_ids = [selected]
    if len(selected_ids) > 1:
        selected = selected_ids[0]
    # Always land on a filled guide. A blank picker with empty Setup/Exposure
    # tabs is worse than showing the first recommended corridor with a switcher.
    if not selected and options:
        selected = options[0].get("approach_id")
        selected_ids = [selected]
    selected_name = next(
        (
            str(option.get("name") or "").strip()
            for option in options
            if option.get("approach_id") == selected
        ),
        "",
    )
    return {
        "status": ("multiple_selected" if len(selected_ids) > 1 else "selected") if selected else ("choice_required" if len(options) > 1 else "unspecified"),
        "selected_approach_id": selected,
        "selected_approach_ids": selected_ids,
        "approaches": options,
        "unavailable_approaches": unavailable_options,
        "coverage": packet.get("approach_coverage") or {},
        "review": packet.get("review") or {},
        "message": (
            f"Showing {selected_name}. Switch if your attending uses a different corridor."
            if selected and len(options) > 1 and selected_name
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
