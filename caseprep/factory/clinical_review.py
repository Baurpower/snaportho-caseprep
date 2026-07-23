"""Hash-bound, append-only multi-agent clinical review factory.

This module intentionally uses only the Python standard library so review and
revision safety checks can run even when optional AI/runtime dependencies are
unavailable. Model-backed agents can implement ``ClinicalReviewAgent`` later
without changing the persisted contracts.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Protocol

from caseprep.factory.paths import procedure_dir

REVIEW_ROOT = "clinical_review"
REVISIONS_DIR = "revisions"
RUNS_DIR = "agent_runs"
EVENTS_FILE = "review_events.jsonl"
PUBLISHED_POINTER = "published_revision.json"

VALID_CATEGORIES = {
    "incorrect", "unsafe", "unsupported", "ambiguous", "incomplete",
    "inconsistent", "preference_sensitive", "cross_procedure_contamination",
    "educational_gap", "style",
}
VALID_SEVERITIES = {"critical", "high", "moderate", "low"}
VALID_DISPOSITIONS = {
    "accepted_by_repeated_clinical_review", "accepted_with_qualification",
    "preference_sensitive", "evidence_check_requested",
    "human_decision_required", "rejected",
}
REQUIRED_SECTIONS = {
    "identity_scope", "operative_objective", "indications_diagnostic",
    "anatomy", "setup_positioning", "open_approach", "endoscopic_approach",
    "procedure_sequence", "structures_at_risk", "decision_points_bailouts",
    "pitfalls", "attending_questions", "resident_responsibilities",
    "things_to_say_or_ask", "postoperative_expectations",
    "complications_failure_analysis", "after_case_review",
}
REQUIRED_RISK_STRUCTURES = {
    "median nerve", "recurrent motor branch", "palmar cutaneous branch",
    "superficial palmar arch", "flexor tendons",
}
MANUFACTURING_LANGUAGE = (
    "certified", "score 4", "source-backed from", "migration note",
    "factory draft", "pending human review",
)
CONTAMINATION_TERMS = (
    "acl", "femoral", "acetabul", "glenoid", "rotator cuff", "tibial",
    "ankle mortise", "lumbar", "cervical spine",
)
UNSUPPORTED_NUMBER = re.compile(
    r"\b(?:always|never|must)\b.{0,40}\b\d+(?:\.\d+)?(?:%| mm| cm| weeks?| days?)\b",
    re.IGNORECASE,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def section_hashes(content: Dict[str, Any]) -> Dict[str, str]:
    return {key: content_hash(value) for key, value in sorted(content["sections"].items())}


def _atomic_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def review_dir(slug: str) -> Path:
    return procedure_dir(slug) / REVIEW_ROOT


def append_event(slug: str, event: Dict[str, Any]) -> Dict[str, Any]:
    row = {"event_id": secrets.token_hex(16), "occurred_at": _now(), **event}
    path = review_dir(slug) / EVENTS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    return row


def create_revision(
    slug: str,
    content: Dict[str, Any],
    *,
    parent_revision_id: Optional[str],
    created_by: str,
    change_summary: List[str],
) -> Dict[str, Any]:
    validate_content_shape(content)
    digest = content_hash(content)
    revision_id = f"ctr-{digest[:12]}"
    revision = {
        "revision_id": revision_id,
        "procedure_slug": slug,
        "parent_revision_id": parent_revision_id,
        "created_at": _now(),
        "created_by": created_by,
        "content_hash": digest,
        "section_hashes": section_hashes(content),
        "change_summary": change_summary,
        "content": content,
    }
    path = review_dir(slug) / REVISIONS_DIR / revision_id / "revision.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing["content_hash"] != digest:
            raise ValueError("Revision identifier collision")
        return existing
    _atomic_json(path, revision)
    append_event(
        slug,
        {
            "event_type": "revision_created",
            "revision_id": revision_id,
            "content_hash": digest,
            "section_hashes": revision["section_hashes"],
            "actor_type": "agent",
            "actor_id": created_by,
        },
    )
    return revision


def load_revision(slug: str, revision_id: str) -> Dict[str, Any]:
    path = review_dir(slug) / REVISIONS_DIR / revision_id / "revision.json"
    if not path.exists():
        raise FileNotFoundError(f"Unknown revision: {revision_id}")
    revision = json.loads(path.read_text(encoding="utf-8"))
    if content_hash(revision["content"]) != revision["content_hash"]:
        raise ValueError("Stored revision content hash mismatch")
    if section_hashes(revision["content"]) != revision["section_hashes"]:
        raise ValueError("Stored revision section hash mismatch")
    return revision


def validate_content_shape(content: Dict[str, Any]) -> None:
    if content.get("canonical_slug") != "carpal_tunnel_release":
        raise ValueError("Content canonical slug must be carpal_tunnel_release")
    sections = content.get("sections")
    if not isinstance(sections, dict):
        raise ValueError("Content sections must be an object")
    missing = REQUIRED_SECTIONS - set(sections)
    if missing:
        raise ValueError(f"Missing required sections: {sorted(missing)}")


def validate_finding(finding: Dict[str, Any], section_ids: Iterable[str]) -> None:
    required = {
        "finding_id", "reviewer_role", "section_id", "category", "severity",
        "explanation", "requires_human_review", "confidence",
    }
    missing = required - set(finding)
    if missing:
        raise ValueError(f"Malformed review finding; missing {sorted(missing)}")
    if finding["section_id"] not in set(section_ids):
        raise ValueError(f"Finding references nonexistent section: {finding['section_id']}")
    if finding["category"] not in VALID_CATEGORIES:
        raise ValueError(f"Invalid finding category: {finding['category']}")
    if finding["severity"] not in VALID_SEVERITIES:
        raise ValueError(f"Invalid finding severity: {finding['severity']}")
    confidence = finding["confidence"]
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise ValueError("Finding confidence must be between 0 and 1")
    if len(str(finding["explanation"]).strip()) < 20:
        raise ValueError("Finding explanation is too generic")


@dataclass(frozen=True)
class AgentSpec:
    role: str
    prompt_version: str
    focus: str
    model: str = "deterministic-clinical-review-v1"


class ClinicalReviewAgent(Protocol):
    spec: AgentSpec

    def review(self, revision: Dict[str, Any]) -> List[Dict[str, Any]]: ...


def finding(
    role: str,
    section: str,
    category: str,
    severity: str,
    explanation: str,
    correction: Optional[str] = None,
    *,
    human: bool = False,
    confidence: float = 0.9,
    claim: Optional[str] = None,
) -> Dict[str, Any]:
    identity = content_hash([role, section, category, explanation])[:16]
    return {
        "finding_id": f"finding-{identity}",
        "reviewer_role": role,
        "section_id": section,
        "claim_text": claim,
        "category": category,
        "severity": severity,
        "explanation": explanation,
        "proposed_correction": correction,
        "requires_human_review": human,
        "confidence": confidence,
    }


class RuleReviewAgent:
    def __init__(self, spec: AgentSpec):
        self.spec = spec

    def review(self, revision: Dict[str, Any]) -> List[Dict[str, Any]]:
        sections = revision["content"]["sections"]
        role = self.spec.role
        findings: List[Dict[str, Any]] = []
        if role == "hand_surgery_content_reviewer":
            text = canonical_json(sections)
            for term in ("recurrent motor branch", "palmar cutaneous branch", "superficial palmar arch"):
                if term not in text.lower():
                    findings.append(finding(role, "anatomy", "incomplete", "high",
                        f"The complete draft omits clinically important discussion of {term}.",
                        f"Add location, risk phase, protection, consequence, and relevant variation for {term}."))
        elif role == "operative_sequence_reviewer":
            for approach in ("open", "endoscopic"):
                steps = sections["procedure_sequence"].get(approach) or []
                if len(steps) < 5:
                    findings.append(finding(role, "procedure_sequence", "incomplete", "high",
                        f"The {approach} sequence is too short to establish setup, safe exposure, release endpoint, and closure.",
                        f"Expand the supervised {approach} sequence while avoiding device-specific mandates."))
        elif role == "anatomy_injury_risk_reviewer":
            names = {row.get("structure", "").lower() for row in sections["structures_at_risk"]}
            for required in REQUIRED_RISK_STRUCTURES - names:
                findings.append(finding(role, "structures_at_risk", "incomplete", "high",
                    f"Required high-consequence structure '{required}' is absent from structured risk analysis.",
                    f"Add a complete structured risk record for {required}."))
        elif role == "complications_failure_reviewer":
            text = canonical_json(sections["complications_failure_analysis"]).lower()
            if not all(term in text for term in ("persistent", "recurrent", "new")):
                findings.append(finding(role, "complications_failure_analysis", "ambiguous", "high",
                    "Failure analysis does not clearly distinguish persistent, recurrent, and new postoperative symptoms.",
                    "Define each timing pattern and link it to incomplete release, scarring, alternate diagnosis, or iatrogenic injury."))
        elif role == "postoperative_care_reviewer":
            text = canonical_json(sections["postoperative_expectations"]).lower()
            if "preference" not in text and "var" not in text:
                findings.append(finding(role, "postoperative_expectations", "preference_sensitive", "moderate",
                    "Postoperative restrictions are presented without clearly labeling surgeon and patient variability.",
                    "Qualify splinting, lifting, wrist motion, and return-to-work guidance as individualized.", human=True))
        elif role == "educational_value_reviewer":
            if len(sections["things_to_say_or_ask"]) < 4:
                findings.append(finding(role, "things_to_say_or_ask", "educational_gap", "moderate",
                    "The learner-facing prompts are too sparse to support practical participation in tomorrow's case.",
                    "Add natural prompts about approach, tourniquet, variant anatomy, release endpoint, closure, and restrictions."))
        elif role == "adversarial_hallucination_reviewer":
            for section_id, value in sections.items():
                text = canonical_json(value)
                if UNSUPPORTED_NUMBER.search(text):
                    findings.append(finding(role, section_id, "unsupported", "high",
                        "The section includes a universal numerical instruction without an evidence binding.",
                        "Remove the number or qualify it and request targeted evidence review.", human=True))
                for term in CONTAMINATION_TERMS:
                    if term in text.lower():
                        findings.append(finding(role, section_id, "cross_procedure_contamination", "critical",
                            f"Potential unrelated procedure contamination detected: '{term}'.",
                            "Remove the unrelated content or explicitly justify its diagnostic relevance.", human=True))
        elif role == "cross_section_consistency_reviewer":
            open_text = canonical_json(sections["open_approach"]).lower()
            endo_text = canonical_json(sections["endoscopic_approach"]).lower()
            if "portal" in open_text or "incision" in endo_text and "convert" not in endo_text:
                findings.append(finding(role, "endoscopic_approach", "inconsistent", "high",
                    "Open and endoscopic terminology may be mixed without an explicit conversion context.",
                    "Keep portal/device concepts in the endoscopic branch and incision/layer concepts in the open branch."))
        return findings


def run_agent(slug: str, revision_id: str, agent: ClinicalReviewAgent, wave: int) -> Dict[str, Any]:
    revision = load_revision(slug, revision_id)
    started = _now()
    findings = agent.review(revision)
    for row in findings:
        validate_finding(row, revision["content"]["sections"])
    run = {
        "agent_run_id": f"run-{secrets.token_hex(12)}",
        "agent_role": agent.spec.role,
        "model": agent.spec.model,
        "prompt_version": agent.spec.prompt_version,
        "prompt_focus": agent.spec.focus,
        "wave": wave,
        "input_revision_id": revision_id,
        "input_content_hash": revision["content_hash"],
        "started_at": started,
        "completed_at": _now(),
        "status": "completed",
        "findings": findings,
        "usage": {"input_tokens": None, "output_tokens": None, "cost_usd": None},
    }
    run["output_hash"] = content_hash(findings)
    path = review_dir(slug) / RUNS_DIR / f"{run['agent_run_id']}.json"
    _atomic_json(path, run)
    append_event(
        slug,
        {
            "event_type": "agent_review_completed",
            "revision_id": revision_id,
            "content_hash": revision["content_hash"],
            "reviewer_type": "agent",
            "reviewer_id": run["agent_run_id"],
            "reviewer_role": agent.spec.role,
            "decision": "findings_recorded",
            "findings": findings,
            "wave": wave,
        },
    )
    return run


def duplicated_review_outputs(runs: List[Dict[str, Any]]) -> List[List[str]]:
    groups: Dict[str, List[str]] = {}
    for run in runs:
        groups.setdefault(run["output_hash"], []).append(run["agent_run_id"])
    return [ids for ids in groups.values() if len(ids) > 1 and json.loads(
        (review_dir("carpal_tunnel_release") / RUNS_DIR / f"{ids[0]}.json").read_text()
    )["findings"]]


def deterministic_validate(
    revision: Dict[str, Any],
    *,
    dispositions: Optional[List[Dict[str, Any]]] = None,
    findings: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    sections = revision["content"]["sections"]
    failures: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []

    for key in REQUIRED_SECTIONS:
        value = sections.get(key)
        if value in (None, "", [], {}):
            failures.append({"code": "empty_required_section", "section": key})

    all_text = canonical_json(sections).lower()
    for phrase in MANUFACTURING_LANGUAGE:
        if phrase in all_text:
            failures.append({"code": "manufacturing_language", "section": "all"})
    for term in CONTAMINATION_TERMS:
        if term in all_text:
            failures.append({"code": f"cross_procedure_contamination:{term}", "section": "all"})
    if UNSUPPORTED_NUMBER.search(all_text):
        failures.append({"code": "unsupported_universal_number", "section": "all"})

    for section_id, value in sections.items():
        if isinstance(value, list):
            rendered = [canonical_json(item) for item in value]
            if len(rendered) != len(set(rendered)):
                failures.append({"code": "duplicate_item", "section": section_id})

    identity_text = canonical_json(sections["identity_scope"]).lower()
    if not all(term in identity_text for term in ("open", "endoscopic")):
        failures.append({"code": "approach_scope_missing", "section": "identity_scope"})
    for approach in ("open", "endoscopic"):
        if len(sections["procedure_sequence"].get(approach) or []) < 5:
            failures.append({"code": f"{approach}_sequence_incomplete", "section": "procedure_sequence"})
    objective_text = canonical_json(sections["operative_objective"]).lower()
    if not all(term in objective_text for term in ("complete", "proximal", "distal")):
        failures.append({"code": "release_endpoints_missing", "section": "operative_objective"})

    risk_names = {row.get("structure", "").lower() for row in sections["structures_at_risk"]}
    for required in REQUIRED_RISK_STRUCTURES - risk_names:
        failures.append({"code": f"missing_risk_structure:{required}", "section": "structures_at_risk"})
    for row in sections["structures_at_risk"]:
        required_fields = {"structure", "relationship", "why_at_risk", "protection", "consequence", "variants"}
        if required_fields - set(row):
            failures.append({"code": "incomplete_risk_record", "section": "structures_at_risk"})

    failure_text = canonical_json(sections["complications_failure_analysis"]).lower()
    if not all(term in failure_text for term in ("persistent", "recurrent", "new symptoms")):
        failures.append({"code": "failure_timing_not_distinguished", "section": "complications_failure_analysis"})

    postop = canonical_json(sections["postoperative_expectations"]).lower()
    if "study" in postop or "review anatomy" in postop:
        failures.append({"code": "study_checklist_in_postop", "section": "postoperative_expectations"})
    if "no wrist motion" in postop and "immediate wrist motion" in postop:
        failures.append({"code": "contradictory_postop_motion", "section": "postoperative_expectations"})

    finding_rows = findings or []
    disposition_rows = dispositions or []
    disposition_ids = {row["finding_id"] for row in disposition_rows}
    for row in finding_rows:
        if row["finding_id"] not in disposition_ids:
            failures.append({"code": "finding_without_disposition", "section": row["section_id"]})
        if row["severity"] in {"critical", "high"}:
            disposition = next((d for d in disposition_rows if d["finding_id"] == row["finding_id"]), None)
            if not disposition or disposition["disposition"] in {
                "human_decision_required", "evidence_check_requested"
            }:
                failures.append({"code": "unresolved_high_risk_finding", "section": row["section_id"]})

    return {
        "revision_id": revision["revision_id"],
        "content_hash": revision["content_hash"],
        "checked_at": _now(),
        "dimensions": {
            "clinical_correctness": "human_review_required",
            "anatomic_correctness": "pass" if not any("risk" in f["code"] for f in failures) else "fail",
            "operative_coherence": "pass" if not any("sequence" in f["code"] for f in failures) else "fail",
            "risk_coverage": "pass" if not any("risk_structure" in f["code"] for f in failures) else "fail",
            "complication_coverage": "pass" if "persistent" in failure_text and "recurrent" in failure_text else "fail",
            "postoperative_usefulness": "pass" if not any("postop" in f["code"] for f in failures) else "fail",
            "educational_usefulness": "pass",
            "internal_consistency": "pass" if not any("contradictory" in f["code"] for f in failures) else "fail",
            "approach_separation": "pass" if not any("approach" in f["code"] for f in failures) else "fail",
            "uncertainty_handling": "pass" if "preference" in all_text or "var" in all_text else "warning",
        },
        "failures": failures,
        "warnings": warnings,
        "passed": not failures,
    }


def record_human_decision(
    slug: str,
    revision_id: str,
    *,
    reviewer_id: str,
    decision: str,
    section_hash_bindings: Dict[str, str],
    comment: Optional[str] = None,
) -> Dict[str, Any]:
    if decision not in {"approve", "request_changes", "reject"}:
        raise ValueError("Invalid human review decision")
    revision = load_revision(slug, revision_id)
    if section_hash_bindings != revision["section_hashes"]:
        raise ValueError("Human decision section hashes do not match current revision")
    return append_event(
        slug,
        {
            "event_type": "human_review_decision",
            "revision_id": revision_id,
            "content_hash": revision["content_hash"],
            "section_hashes": section_hash_bindings,
            "reviewer_type": "human",
            "reviewer_id": reviewer_id,
            "decision": decision,
            "comment": comment,
        },
    )


def current_human_approval(slug: str, revision_id: str) -> Optional[Dict[str, Any]]:
    revision = load_revision(slug, revision_id)
    path = review_dir(slug) / EVENTS_FILE
    if not path.exists():
        return None
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    for event in reversed(events):
        if (
            event.get("event_type") == "human_review_decision"
            and event.get("revision_id") == revision_id
        ):
            return event if (
                event.get("decision") == "approve"
                and event.get("content_hash") == revision["content_hash"]
                and event.get("section_hashes") == revision["section_hashes"]
            ) else None
    return None


def certification_readiness(
    slug: str,
    revision_id: str,
    *,
    qa: Dict[str, Any],
    wave_count: int,
) -> Dict[str, Any]:
    revision = load_revision(slug, revision_id)
    reasons: List[str] = []
    approval = current_human_approval(slug, revision_id)
    if not qa.get("passed"):
        reasons.append("deterministic validation has blocking failures")
    if wave_count < 2:
        reasons.append("two review waves have not completed")
    if not approval:
        reasons.append("no current hash-bound human approval")
    return {
        "eligible": not reasons,
        "revision_id": revision_id,
        "content_hash": revision["content_hash"],
        "section_hashes": revision["section_hashes"],
        "reasons": reasons,
    }


def compile_approved_revision(
    slug: str,
    revision_id: str,
    *,
    qa: Dict[str, Any],
    wave_count: int,
    output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Deterministically compile the exact approved revision; never promotes it."""
    readiness = certification_readiness(
        slug, revision_id, qa=qa, wave_count=wave_count
    )
    if not readiness["eligible"]:
        raise ValueError(f"Compile refused: {'; '.join(readiness['reasons'])}")
    revision = load_revision(slug, revision_id)
    payload = {
        "schema_version": "brobot_case_prep_payload_v3",
        "procedure_id": slug,
        "procedure_name": revision["content"]["canonical_name"],
        "revision_id": revision_id,
        "content_hash": revision["content_hash"],
        "section_hashes": revision["section_hashes"],
        "approach_scope": revision["content"].get("approach_scope") or [],
        "audience": revision["content"].get("audience"),
        "sections": revision["content"]["sections"],
    }
    digest = content_hash(payload)
    result = {
        "revision_id": revision_id,
        "content_hash": revision["content_hash"],
        "payload_hash": digest,
        "payload": payload,
    }
    if output_path:
        _atomic_json(output_path, payload)
        append_event(
            slug,
            {
                "event_type": "approved_revision_compiled",
                "revision_id": revision_id,
                "content_hash": revision["content_hash"],
                "payload_hash": digest,
                "reviewer_type": "system",
                "reviewer_id": "deterministic_revision_compiler_v1",
                "decision": "compiled",
            },
        )
    return result


def update_published_pointer(
    slug: str,
    revision_id: str,
    payload_hash: str,
    *,
    actor: str,
    qa: Dict[str, Any],
    wave_count: int,
) -> Dict[str, Any]:
    readiness = certification_readiness(slug, revision_id, qa=qa, wave_count=wave_count)
    if not readiness["eligible"]:
        raise ValueError(f"Publication refused: {'; '.join(readiness['reasons'])}")
    previous = None
    pointer_path = review_dir(slug) / PUBLISHED_POINTER
    if pointer_path.exists():
        previous = json.loads(pointer_path.read_text(encoding="utf-8"))
    pointer = {
        "procedure_slug": slug,
        "revision_id": revision_id,
        "content_hash": readiness["content_hash"],
        "payload_hash": payload_hash,
        "published_at": _now(),
        "published_by": actor,
        "previous_revision_id": previous.get("revision_id") if previous else None,
    }
    _atomic_json(pointer_path, pointer)
    append_event(slug, {"event_type": "published_pointer_updated", **pointer})
    return pointer
