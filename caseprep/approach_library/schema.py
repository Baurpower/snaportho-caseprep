"""Schema and deterministic publication rules for surgical approach modules."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List
from urllib.parse import urlparse

SCHEMA_VERSION = "brobot_approach_packet_v1"
REQUIRED_REVIEW_ROLES = frozenset(
    {
        "approach_anatomy_reviewer",
        "operative_exposure_reviewer",
        "procedure_applicability_reviewer",
        "evidence_reviewer",
        "adversarial_safety_reviewer",
        "educational_value_reviewer",
    }
)
TRUSTED_EVIDENCE_HOSTS = frozenset(
    {
        "surgeryreference.aofoundation.org",
        "pubmed.ncbi.nlm.nih.gov",
        "pmc.ncbi.nlm.nih.gov",
        "aaos.org",
        "jbjs.org",
        "journals.lww.com",
    }
)
CLAIM_BOUND_FIELDS = (
    "positioning",
    "setup",
    "surface_landmarks",
    "incision",
    "superficial_interval",
    "deep_interval",
    "layers",
    "structures_encountered",
    "structures_at_risk",
    "danger_zones",
    "retraction_hazards",
    "exposure",
    "limitations",
    "extensions",
    "indications",
    "relative_contraindications",
    "implant_implications",
    "fluoroscopy_implications",
    "closure",
    "complications",
    "bailouts",
    "questions",
)


def content_hash(packet: Dict[str, Any]) -> str:
    content = {key: value for key, value in packet.items() if key != "review"}
    encoded = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def empty_packet(approach_id: str, name: str, *, region: str = "") -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "approach_id": approach_id,
        "name": name,
        "aliases": [],
        "region": region,
        "joint": "",
        "bones": [],
        "corridor": "",
        "positioning": [],
        "setup": [],
        "surface_landmarks": [],
        "incision": [],
        "superficial_interval": [],
        "deep_interval": [],
        "layers": [],
        "structures_encountered": [],
        "structures_at_risk": [],
        "danger_zones": [],
        "retraction_hazards": [],
        "exposure": [],
        "limitations": [],
        "extensions": [],
        "indications": [],
        "relative_contraindications": [],
        "implant_implications": [],
        "fluoroscopy_implications": [],
        "closure": [],
        "complications": [],
        "bailouts": [],
        "procedure_applications": [],
        "questions": [],
        "claims": [],
        "sources": [],
        "content_status": "source_indexed",
        "review": {
            "status": "not_started",
            "required_roles": sorted(REQUIRED_REVIEW_ROLES),
            "completed_roles": [],
        },
    }


def validate_packet(packet: Dict[str, Any], *, require_reviews: bool = True) -> Dict[str, Any]:
    failures: List[str] = []
    required_text = ("approach_id", "name", "region", "corridor")
    required_lists = (
        "positioning",
        "surface_landmarks",
        "incision",
        "layers",
        "structures_at_risk",
        "danger_zones",
        "exposure",
        "limitations",
        "indications",
        "closure",
        "complications",
        "procedure_applications",
        "questions",
        "claims",
        "sources",
    )
    for field in required_text:
        if not str(packet.get(field) or "").strip():
            failures.append(f"Missing required field: {field}")
    for field in required_lists:
        if not packet.get(field):
            failures.append(f"Missing required content: {field}")

    sources = packet.get("sources") or []
    source_ids = {str(source.get("source_id")) for source in sources if source.get("source_id")}
    trusted = {
        urlparse(str(source.get("url") or "")).hostname or ""
        for source in sources
        if source.get("url")
    }
    if len(source_ids) < 2:
        failures.append("At least two independent sources are required.")
    if not any(
        host == trusted_host or host.endswith("." + trusted_host)
        for host in trusted
        for trusted_host in TRUSTED_EVIDENCE_HOSTS
    ):
        failures.append("No recognized authoritative operative/evidence source.")

    claim_ids = {str(claim.get("claim_id")) for claim in packet.get("claims") or []}
    claim_values: Dict[str, set[str]] = {}
    for claim in packet.get("claims") or []:
        claim_sources = set(claim.get("source_ids") or [])
        if not claim_sources:
            failures.append(f"Uncited claim: {claim.get('claim_id') or claim.get('text')}")
        elif not claim_sources.issubset(source_ids):
            failures.append(f"Claim references unknown source: {claim.get('claim_id')}")
        if claim.get("risk_level") in {"high", "critical"} and len(claim_sources) < 2:
            failures.append(f"High-risk claim needs two sources: {claim.get('claim_id')}")
        claim_key = str(claim.get("claim_key") or "").strip()
        claim_value = str(claim.get("normalized_value") or "").strip().lower()
        if claim_key and claim_value:
            claim_values.setdefault(claim_key, set()).add(claim_value)

    resolved_keys = set(packet.get("resolved_contradiction_keys") or [])
    for claim_key, values in claim_values.items():
        if len(values) > 1 and claim_key not in resolved_keys:
            failures.append(f"Unresolved contradictory claim values: {claim_key}")

    for field in CLAIM_BOUND_FIELDS:
        for index, item in enumerate(packet.get(field) or []):
            if not isinstance(item, dict) or not str(item.get("text") or item.get("question") or "").strip():
                failures.append(f"Clinical item must be structured and claim-bound: {field}[{index}]")
                continue
            references = set(item.get("claim_ids") or [])
            if not references:
                failures.append(f"Clinical item has no claim_ids: {field}[{index}]")
            elif not references.issubset(claim_ids):
                failures.append(f"Clinical item references unknown claim: {field}[{index}]")

    review = packet.get("review") or {}
    completed = set(review.get("completed_roles") or [])
    if require_reviews:
        missing = sorted(REQUIRED_REVIEW_ROLES - completed)
        if missing:
            failures.append("Missing review roles: " + ", ".join(missing))
        if review.get("content_hash") != content_hash(packet):
            failures.append("Review hash does not match current content.")

    return {"passed": not failures, "failures": failures}
