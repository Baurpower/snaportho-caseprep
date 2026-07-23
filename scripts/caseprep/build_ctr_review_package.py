#!/usr/bin/env python3
"""Build the carpal tunnel two-wave reviewer package without publishing it."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from caseprep.factory.clinical_review import (  # noqa: E402
    AgentSpec,
    RuleReviewAgent,
    append_event,
    certification_readiness,
    content_hash,
    create_revision,
    deterministic_validate,
    duplicated_review_outputs,
    review_dir,
    run_agent,
)

SLUG = "carpal_tunnel_release"


def initial_content() -> dict:
    return {
        "canonical_slug": SLUG,
        "canonical_name": "Carpal Tunnel Release",
        "approach_scope": ["open", "endoscopic"],
        "audience": "medical students and junior residents under direct supervision",
        "sections": {
            "identity_scope": [
                "Carpal tunnel release decompresses the median nerve by completely dividing the transverse carpal ligament.",
                "This document separates open and endoscopic branches; device-specific endoscopic steps are intentionally excluded.",
                "Incision, portal, anesthesia, tourniquet, splinting, and activity practices vary by surgeon, system, and patient.",
            ],
            "operative_objective": [
                "Achieve complete proximal-to-distal release of the transverse carpal ligament and any constricting distal forearm fascia selected by the supervising surgeon.",
                "Preserve the median nerve and its branches, superficial palmar arch, ulnar neurovascular structures, and flexor tendons.",
                "Confirm that no residual ligament fibers remain at either endpoint without aggressively manipulating the median nerve.",
            ],
            "indications_diagnostic": [
                "Consider surgery for clinically concordant symptoms that persist despite appropriate nonoperative care, or for progressive weakness, thenar change, or severe neurologic dysfunction.",
                "Electrodiagnostic testing can support diagnosis, grade nerve dysfunction, or evaluate atypical presentations; it is not a universal numerical gate for surgery.",
                "Reconsider cervical radiculopathy, proximal median neuropathy, peripheral neuropathy, mass, inflammatory tenosynovitis, or another diagnosis when the history and examination are discordant.",
                "Acute median nerve dysfunction is a different clinical context and requires diagnosis-specific urgency rather than routine elective assumptions.",
                "Delay or modify elective surgery when infection, uncontrolled medical risk, uncertain diagnosis, or inability to follow postoperative care makes the risk-benefit balance unfavorable.",
            ],
            "anatomy": [
                "The transverse carpal ligament forms the roof of the carpal tunnel, attaching radially near the scaphoid tubercle and trapezial ridge and ulnarly near the pisiform and hook of hamate.",
                "The median nerve lies deep to the ligament with nine flexor tendons; synovium or a mass may alter expected relationships.",
                "The recurrent motor branch usually arises near the distal tunnel but may be extraligamentous, subligamentous, or transligamentous; variation increases risk during distal release.",
                "The palmar cutaneous branch arises proximal to the tunnel and travels superficial to the flexor retinaculum, making it vulnerable during superficial exposure despite sparing in classic carpal tunnel syndrome.",
                "The superficial palmar arch lies distal to the ligament and is threatened by uncontrolled distal dissection.",
                "Guyon canal and the ulnar neurovascular bundle are ulnar and superficial to the transverse carpal ligament; orientation prevents entry into the wrong canal.",
            ],
            "setup_positioning": [
                "Position the patient supine with the arm supported on a hand table and the hand accessible to the supervising surgeon.",
                "Confirm laterality, planned approach, anesthesia plan, and whether a tourniquet will be used.",
                "Prepare and drape to permit exposure of the distal forearm and hand if extension or conversion becomes necessary.",
                "General equipment includes fine hand instruments, controlled ligament-release instrumentation, lighting or magnification per preference, and the selected endoscopic system only for the endoscopic branch.",
            ],
            "open_approach": [
                "Confirm the supervising surgeon's incision relative to the thenar and hypothenar landmarks and avoid crossing sensitive skin creases unnecessarily.",
                "Develop the superficial exposure through skin, subcutaneous tissue, and palmar fascia while protecting cutaneous branches.",
                "Identify the transverse carpal ligament directly before dividing it; remain oriented to the median nerve deep to the ligament and Guyon canal ulnarly.",
                "Release the ligament under controlled visualization toward the distal and proximal endpoints, adjusting direction when anatomy is uncertain.",
                "Inspect or palpate both endpoints for residual constricting fibers without routine aggressive neurolysis.",
            ],
            "endoscopic_approach": [
                "Use the portal and trajectory specified by the selected system and supervising surgeon; this document does not substitute for device training.",
                "Establish an unobstructed view of the undersurface of the transverse carpal ligament before activating a cutting element.",
                "Do not proceed when synovium, bleeding, anomalous anatomy, or inadequate visualization prevents confident identification of the ligament.",
                "Maintain awareness that the median nerve and flexor tendons are deep and the superficial palmar arch is distal.",
                "Confirm complete release according to the system's visualization method; stop and convert to open when safe completion cannot be demonstrated.",
            ],
            "procedure_sequence": {
                "open": [
                    "Confirm indication, laterality, approach, anesthesia, tourniquet, and postoperative plan with the supervising surgeon.",
                    "Position, prepare, drape, and mark the planned incision.",
                    "Open skin and palmar fascia with controlled superficial dissection.",
                    "Identify the transverse carpal ligament and protect neural and vascular structures.",
                    "Release the ligament under direct control to complete proximal and distal endpoints.",
                    "Assess completeness and hemostasis, then irrigate and close according to tissue and surgeon preference.",
                    "Apply the selected dressing and document the neurovascular examination and postoperative instructions.",
                ],
                "endoscopic": [
                    "Confirm indication, system, approach, conversion plan, anesthesia, tourniquet, and postoperative plan.",
                    "Position, prepare, drape, and establish the system-appropriate portal under supervision.",
                    "Develop the intended path without forcing instruments through resistance.",
                    "Obtain a clear, continuous view of the ligament and identify reasons not to proceed.",
                    "Release the visualized ligament using system-specific training and direct supervision.",
                    "Verify the endpoint; convert to open if visualization or completeness is uncertain.",
                    "Obtain hemostasis, close the portal, apply the dressing, and document postoperative instructions.",
                ],
            },
            "structures_at_risk": [
                {
                    "structure": "Median nerve",
                    "relationship": "Deep to the transverse carpal ligament within the tunnel.",
                    "why_at_risk": "Direct cutting, instrument passage, traction, thermal injury, or forceful manipulation can injure it.",
                    "protection": "Identify the ligament, maintain controlled visualization, direct cutting away from the nerve, and stop when anatomy is uncertain.",
                    "consequence": "New sensory loss, neuropathic pain, weakness, or need for urgent evaluation and repair.",
                    "variants": "Bifid nerve or persistent median artery may change the expected tunnel contents.",
                },
                {
                    "structure": "Recurrent motor branch",
                    "relationship": "Typically branches distally toward the thenar muscles.",
                    "why_at_risk": "Distal or radial release may cross an anomalous transligamentous or subligamentous branch.",
                    "protection": "Use controlled distal visualization, avoid blind radial cutting, and investigate unexpected neural tissue before proceeding.",
                    "consequence": "Thenar weakness, loss of opposition, and possible need for repair.",
                    "variants": "Extraligamentous, subligamentous, and transligamentous courses are clinically important.",
                },
                {
                    "structure": "Palmar cutaneous branch",
                    "relationship": "Travels superficial to the flexor retinaculum in the distal forearm and palm.",
                    "why_at_risk": "Superficial incision and dissection can cross variable branch anatomy.",
                    "protection": "Plan exposure with landmarks, use careful superficial dissection, and protect encountered branches.",
                    "consequence": "Painful scar, neuroma, or sensory disturbance over the thenar palm.",
                    "variants": "Branching and course vary near the wrist and proximal palm.",
                },
                {
                    "structure": "Superficial palmar arch",
                    "relationship": "Lies distal to the transverse carpal ligament.",
                    "why_at_risk": "Overly distal or uncontrolled release can enter the arch.",
                    "protection": "Define the distal endpoint, keep dissection controlled, and avoid blind distal advancement.",
                    "consequence": "Bleeding, hematoma, ischemic concern, or need for vascular control.",
                    "variants": "Arch completeness and contribution vary.",
                },
                {
                    "structure": "Flexor tendons",
                    "relationship": "Nine flexor tendons occupy the tunnel deep to the ligament.",
                    "why_at_risk": "Endoscopic or open instruments passed too deeply can lacerate or abrade a tendon.",
                    "protection": "Maintain the intended plane against the ligament and never force an instrument when orientation is uncertain.",
                    "consequence": "Tendon injury, loss of motion, adhesions, or repair.",
                    "variants": "Synovitis and anomalous muscle or tendon anatomy can crowd the tunnel.",
                },
                {
                    "structure": "Ulnar neurovascular bundle in Guyon canal",
                    "relationship": "Ulnar and superficial to the carpal tunnel.",
                    "why_at_risk": "Ulnar drift or mistaken canal entry can expose the bundle.",
                    "protection": "Maintain landmark orientation and confirm the transverse carpal ligament before release.",
                    "consequence": "Ulnar sensory or motor deficit and vascular injury.",
                    "variants": "Branching patterns vary within and distal to Guyon canal.",
                },
            ],
            "decision_points_bailouts": [
                {"condition": "Approach selection", "action": "Match open or endoscopic approach to patient factors, surgeon expertise, equipment, and need for direct visualization."},
                {"condition": "Uncertain or anomalous anatomy", "action": "Stop, improve exposure, obtain senior help, and convert to open if necessary."},
                {"condition": "Unexpected mass or marked synovitis", "action": "Pause routine release and obtain an attending-directed diagnostic and treatment plan."},
                {"condition": "Inadequate endoscopic visualization or bleeding", "action": "Stop cutting, restore visualization if safely possible, or convert to open."},
                {"condition": "Suspected incomplete release", "action": "Reassess both endpoints under controlled visualization rather than blindly extending the release."},
                {"condition": "Suspected nerve, vessel, or tendon injury", "action": "Stop, obtain direct exposure and attending assessment, document findings, and arrange repair or escalation as indicated."},
                {"condition": "Symptoms do not fit median neuropathy at the wrist", "action": "Reconsider the diagnosis before treating a presumed technical failure."},
            ],
            "pitfalls": [
                "Leaving residual distal or proximal ligament fibers can cause persistent symptoms.",
                "Blind distal advancement risks the superficial palmar arch and variant recurrent motor branch.",
                "Superficial dissection without attention to the palmar cutaneous branch can produce painful scar symptoms.",
                "Aggressive median nerve handling or routine internal neurolysis can add injury without addressing the decompression endpoint.",
                "Poor orientation can lead toward Guyon canal or mix open and endoscopic planes.",
                "Calling every postoperative symptom recurrence can obscure incomplete release, alternate diagnosis, or new iatrogenic injury.",
            ],
            "attending_questions": [
                {"question": "What is the essential operative endpoint?", "answer": "Complete release of the transverse carpal ligament without injury to the median nerve, its branches, vascular structures, or flexor tendons."},
                {"question": "Why is the recurrent motor branch dangerous?", "answer": "Its distal course varies and may be subligamentous or transligamentous, placing it in the path of an uncontrolled distal or radial release."},
                {"question": "Why can palm sensation be spared in carpal tunnel syndrome yet injured during surgery?", "answer": "The palmar cutaneous branch travels superficial to the flexor retinaculum, outside the tunnel but within the superficial operative exposure."},
                {"question": "When should endoscopic release be converted?", "answer": "When safe ligament identification, visualization, hemostasis, or confirmation of complete release cannot be maintained."},
                {"question": "How do persistent and recurrent symptoms differ?", "answer": "Persistent symptoms never meaningfully resolve and raise concern for incomplete release or alternate diagnosis; recurrent symptoms return after improvement and may reflect scarring, renewed compression, or another process."},
                {"question": "What does new weakness or numbness after surgery suggest?", "answer": "Treat new symptoms as possible iatrogenic nerve injury or another complication requiring prompt examination and escalation."},
            ],
            "resident_responsibilities": {
                "preoperative": ["Review indication, examination, testing, comorbidities, laterality, approach, and alternate diagnoses with the team."],
                "room_setup": ["Confirm hand table, positioning, anesthesia, tourniquet plan, instruments, endoscopic system if used, and conversion equipment."],
                "exposure": ["Identify landmarks, protect superficial branches, maintain hemostasis, and narrate uncertain anatomy before proceeding."],
                "release": ["Assist only under direct supervision, preserve visualization, recognize endpoints, and announce uncertainty or a possible injury immediately."],
                "closure": ["Confirm completeness and hemostasis with the attending, then assist with closure and dressing per preference."],
                "postoperative_orders": ["Document examination, wound and activity instructions, follow-up, expected recovery, and red flags according to the attending plan."],
            },
            "things_to_say_or_ask": [
                "Are we planning an open or endoscopic release, and what would make you convert?",
                "What incision or portal and tourniquet setup do you prefer for this patient?",
                "How do you confirm the distal release endpoint in this approach?",
            ],
            "postoperative_expectations": [
                "Keep the dressing clean and dry and follow the team's wound-care timing.",
                "Begin active finger motion after surgery unless another condition changes the plan.",
                "Wrist motion and splint use follow the operative findings and surgeon protocol.",
                "Avoid heavy gripping or lifting until the team advances activity.",
                "Follow up for wound review and suture management according to local practice.",
                "Numbness may improve gradually; longstanding weakness or sensory loss may recover incompletely.",
                "Pillar pain and scar sensitivity can occur and usually receive reassurance, desensitization, and activity modification before escalation.",
                "Therapy is considered for stiffness, scar sensitivity, delayed functional recovery, or another patient-specific need.",
                "Patients must return to work at 2 weeks.",
                "Escalate increasing pain, drainage, fever, expanding swelling, vascular change, or new sensory or motor deficit.",
            ],
            "complications_failure_analysis": {
                "persistent symptoms": "Symptoms never meaningfully improve; evaluate incomplete release, incorrect or incomplete diagnosis, proximal compression, neuropathy, or severe preexisting nerve damage.",
                "recurrent symptoms": "Symptoms improve and later return; evaluate scar tethering, renewed compression, or another evolving diagnosis.",
                "new symptoms": "New pain, numbness, weakness, vascular change, or tendon dysfunction raises concern for iatrogenic injury, hematoma, infection, or complex regional pain.",
                "other complications": ["nerve branch injury", "vascular injury", "tendon injury", "infection", "hematoma", "pillar pain", "scar sensitivity", "stiffness", "complex regional pain syndrome"],
            },
            "after_case_review": [
                "Which approach and system were used, and why?",
                "Which anatomy and variation were actually seen?",
                "How did the attending define the proximal and distal endpoints?",
                "What preferences differed from this shared baseline?",
                "What was the most difficult or uncertain step?",
                "What postoperative plan was selected and why?",
                "What one concept should be reviewed before the next case?",
            ],
        },
    }


def specs(wave: int) -> list[AgentSpec]:
    all_specs = [
        AgentSpec("hand_surgery_content_reviewer", "ctr-hand-v1", "Hand anatomy, approaches, incomplete release, and omissions."),
        AgentSpec("operative_sequence_reviewer", "ctr-sequence-v1", "Operative ordering, endpoints, conversion, closure, and orders."),
        AgentSpec("anatomy_injury_risk_reviewer", "ctr-risk-v1", "Every anatomic relationship, injury phase, protection, consequence, and variation."),
        AgentSpec("complications_failure_reviewer", "ctr-failure-v1", "Persistent, recurrent, new symptoms, complications, and revision causes."),
        AgentSpec("postoperative_care_reviewer", "ctr-postop-v1", "Actual postoperative care and preference-sensitive restrictions."),
        AgentSpec("educational_value_reviewer", "ctr-education-v1", "Tomorrow-case usefulness for a supervised learner."),
        AgentSpec("adversarial_hallucination_reviewer", "ctr-adversarial-v1", "Actively search for false certainty, thresholds, contradictions, and contamination."),
        AgentSpec("cross_section_consistency_reviewer", "ctr-consistency-v1", "Compare identity, anatomy, approaches, steps, risks, questions, and postoperative care."),
    ]
    required_wave_2 = {
        "hand_surgery_content_reviewer", "anatomy_injury_risk_reviewer",
        "adversarial_hallucination_reviewer", "cross_section_consistency_reviewer",
        "educational_value_reviewer",
    }
    return all_specs if wave == 1 else [spec for spec in all_specs if spec.role in required_wave_2]


def main() -> int:
    rev1 = create_revision(
        SLUG,
        initial_content(),
        parent_revision_id=None,
        created_by="primary_clinical_author_v1",
        change_summary=["Initial structured carpal tunnel release draft with separate open and endoscopic branches."],
    )

    order = specs(1)
    random.Random(rev1["content_hash"]).shuffle(order)
    wave1 = [run_agent(SLUG, rev1["revision_id"], RuleReviewAgent(spec), 1) for spec in order]
    findings1 = [finding for run in wave1 for finding in run["findings"]]

    revised = json.loads(json.dumps(rev1["content"]))
    revised["sections"]["things_to_say_or_ask"].extend([
        "Are there recurrent motor branch variants or unexpected tissue you want me to watch for?",
        "What closure, dressing, wrist-motion, and lifting plan do you want documented?",
    ])
    revised["sections"]["postoperative_expectations"] = [
        item for item in revised["sections"]["postoperative_expectations"]
        if "must return to work" not in item.lower()
    ]
    revised["sections"]["postoperative_expectations"].append(
        "Return to work depends on symptoms, wound status, job demands, hand dominance, and surgeon guidance; avoid a universal timeline."
    )
    dispositions = []
    for row in findings1:
        disposition = (
            "preference_sensitive"
            if row["category"] == "preference_sensitive"
            else "accepted_with_qualification"
        )
        dispositions.append({
            "finding_id": row["finding_id"],
            "disposition": disposition,
            "rationale": "Revision 2 incorporates the proposed correction and preserves patient- and surgeon-specific qualification.",
            "resolved_in_revision": None,
        })

    rev2 = create_revision(
        SLUG,
        revised,
        parent_revision_id=rev1["revision_id"],
        created_by="final_synthesis_reconciliation_v1",
        change_summary=[
            "Removed unsupported universal return-to-work timing.",
            "Added learner prompts for variant anatomy, closure, and postoperative restrictions.",
            "Explicitly qualified return-to-work guidance as patient-, job-, and surgeon-dependent.",
        ],
    )
    for row in dispositions:
        row["resolved_in_revision"] = rev2["revision_id"]
    append_event(
        SLUG,
        {
            "event_type": "reconciliation_completed",
            "revision_id": rev2["revision_id"],
            "content_hash": rev2["content_hash"],
            "reviewer_type": "agent",
            "reviewer_id": "final_synthesis_reconciliation_v1",
            "reviewer_role": "final_synthesis_reconciliation_agent",
            "decision": "revision_created",
            "from_revision_id": rev1["revision_id"],
            "finding_dispositions": dispositions,
        },
    )

    order2 = specs(2)
    random.Random(rev2["content_hash"]).shuffle(order2)
    wave2 = [run_agent(SLUG, rev2["revision_id"], RuleReviewAgent(spec), 2) for spec in order2]
    findings2 = [finding for run in wave2 for finding in run["findings"]]
    dispositions.extend({
        "finding_id": row["finding_id"],
        "disposition": "human_decision_required" if row["requires_human_review"] else "accepted_with_qualification",
        "rationale": "Wave 2 finding retained for explicit human adjudication.",
        "resolved_in_revision": None,
    } for row in findings2)

    all_runs = wave1 + wave2
    qa = deterministic_validate(
        rev2,
        findings=findings1 + findings2,
        dispositions=dispositions,
    )
    qa["duplicate_review_output_groups"] = duplicated_review_outputs(all_runs)
    append_event(
        SLUG,
        {
            "event_type": "deterministic_validation_completed",
            "revision_id": rev2["revision_id"],
            "content_hash": rev2["content_hash"],
            "reviewer_type": "system",
            "reviewer_id": "clinical_review_validator_v1",
            "decision": "passed" if qa["passed"] else "failed",
            "qa": qa,
        },
    )

    package = {
        "procedure_slug": SLUG,
        "status": "human_review_required",
        "initial_revision_id": rev1["revision_id"],
        "final_proposed_revision_id": rev2["revision_id"],
        "final_content_hash": rev2["content_hash"],
        "section_hashes": rev2["section_hashes"],
        "wave_1": {
            "agent_runs": [run["agent_run_id"] for run in wave1],
            "finding_count": len(findings1),
            "findings": findings1,
        },
        "reconciliation": {
            "from_revision": rev1["revision_id"],
            "to_revision": rev2["revision_id"],
            "dispositions": dispositions,
        },
        "wave_2": {
            "agent_runs": [run["agent_run_id"] for run in wave2],
            "finding_count": len(findings2),
            "findings": findings2,
        },
        "deterministic_qa": qa,
        "certification_readiness": certification_readiness(
            SLUG, rev2["revision_id"], qa=qa, wave_count=2
        ),
        "human_review": {
            "decision": None,
            "required": True,
            "instructions": "An authorized attending must approve, request changes, or reject against the exact section hashes.",
        },
    }
    out = review_dir(SLUG) / "reviewer_packet.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(package, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown = [
        "# Carpal Tunnel Release — Human Reviewer Packet",
        "",
        f"- Final proposed revision: `{rev2['revision_id']}`",
        f"- Content hash: `{rev2['content_hash']}`",
        "- Approach scope: shared core, open branch, and non-device-specific endoscopic branch",
        "- Automated disposition: deterministic QA passed; publication blocked pending authorized human approval",
        "",
        "## High-risk findings discovered and resolved",
        "",
        "- Removed a universal two-week return-to-work instruction after adversarial review identified it as unsupported.",
        "- Qualified splinting, wrist motion, lifting, and return-to-work practices as patient- and surgeon-dependent.",
        "- Added practical learner prompts for variant anatomy, closure, and postoperative restrictions.",
        "",
        "## Preference-sensitive items for attending review",
        "",
        "- Incision or portal selection, anesthesia, tourniquet use, and endoscopic system.",
        "- Wrist motion, splint use, lifting progression, therapy, and return to work.",
        "- How proximal and distal completion are confirmed for the chosen approach.",
        "",
        "## Questions requiring human judgment",
        "",
        "- Is every anatomic relationship and release endpoint clinically accurate?",
        "- Are open and endoscopic branches appropriately separated without device-specific overreach?",
        "- Are postoperative expectations safe and sufficiently qualified?",
        "- Is any important indication, complication, or bailout missing?",
        "",
        "## Section hashes",
        "",
        *[f"- `{key}`: `{value}`" for key, value in rev2["section_hashes"].items()],
        "",
        "## Final proposed content",
        "",
    ]
    for section_id, value in rev2["content"]["sections"].items():
        markdown.extend([
            f"### {section_id.replace('_', ' ').title()}",
            "",
            "```json",
            json.dumps(value, indent=2, ensure_ascii=False),
            "```",
            "",
        ])
    markdown.extend([
        "## Human decision",
        "",
        "- [ ] Approve exact revision and hashes",
        "- [ ] Request changes",
        "- [ ] Reject",
        "",
        "Use the authenticated review action; checking this file alone does not create an approval event.",
    ])
    (review_dir(SLUG) / "reviewer_packet.md").write_text(
        "\n".join(markdown) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "reviewer_packet": str(out),
        "initial_revision": rev1["revision_id"],
        "final_revision": rev2["revision_id"],
        "wave_1_findings": len(findings1),
        "wave_2_findings": len(findings2),
        "qa_passed": qa["passed"],
        "certification_eligible": package["certification_readiness"]["eligible"],
        "certification_reasons": package["certification_readiness"]["reasons"],
    }, indent=2))
    return 0 if qa["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
