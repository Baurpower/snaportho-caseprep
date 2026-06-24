#!/usr/bin/env python3
"""
Audit script for Orthobullets Playbook v2 quality.

Loads the current v2 playbook and produces per-procedure grades, priority, and suggestions
for v2_1 improvement pass. Scores are data-driven (counts, recs, manual, high-conf presence, source presence)
with adjustments from known strong entries in prior QC.

Outputs:
- reports/orthobullets_playbook_v2_line_quality_audit.jsonl (one object per procedure)
- reports/orthobullets_playbook_v2_line_quality_audit.csv
- reports/orthobullets_playbook_v2_quality_summary.md (aggregated + top must_fix list)

Run from repo root.
"""
import json
import csv
from pathlib import Path
from typing import Dict, Any, List

REPORTS = Path("reports")
REPORTS.mkdir(exist_ok=True)

def load_v2() -> List[Dict[str, Any]]:
    with open("data/approach_playbook/orthobullets_procedure_playbook_v2.jsonl") as f:
        return [json.loads(line) for line in f if line.strip()]

def has_high_conf(entry: Dict[str, Any]) -> bool:
    for key in ["important_anatomy", "structures_at_risk", "landmarks", "approach_notes"]:
        for item in entry.get(key, []):
            if item.get("confidence") == "high":
                return True
    return False

def count_sources(entry: Dict[str, Any]) -> int:
    urls = set()
    for key in ["important_anatomy", "structures_at_risk", "landmarks", "approach_notes"]:
        for item in entry.get(key, []):
            if item.get("source_url"):
                urls.add(item["source_url"])
    return len(urls)

def grade_dimension(count: int, has_high: bool, has_recs: bool, manual: bool, pimp_count: int = 0) -> int:
    if manual:
        return 1 if count > 0 else 0
    if not has_recs:
        return 1 if count > 0 else 0
    base = 1
    if count >= 1: base += 1
    if count >= 2: base += 1
    if count >= 3: base += 1
    if has_high: base += 1
    if pimp_count >= 3: base += 1
    return min(5, base)

def compute_overall(scores: Dict[str, int], facts_total: int, has_recs: bool, manual: bool, source_count: int) -> int:
    if manual:
        return min(2, max(0, facts_total // 2))
    if not has_recs:
        return min(2, max(0, facts_total // 2))
    avg = sum(scores.values()) / len(scores) if scores else 0
    bonus = 0
    if facts_total >= 6: bonus += 1
    if source_count >= 2: bonus += 1
    return min(5, int(round(avg + bonus)))

def get_priority(overall: int, has_recs: bool, manual: bool, facts_total: int, is_common: bool) -> str:
    if manual:
        return "unsupported_gap"
    if has_recs and overall <= 2:
        return "must_fix" if is_common or facts_total < 2 else "should_fix"
    if has_recs and overall == 3:
        return "should_fix" if is_common else "okay"
    if overall >= 4:
        return "excellent"
    return "okay"

# Known common resident cases (high volume / educational priority)
COMMON_CASES = {
    "acl_reconstruction", "rotator_cuff_repair", "proximal_humerus_fracture_orif",
    "both_bone_forearm_fracture_orif", "scaphoid_fracture_orif", "carpal_tunnel_release",
    "achilles_tendon_repair", "tka", "tha_posterior", "distal_radius_fracture_orif",
    "femoral_shaft_fracture_orif", "tibial_plateau_fracture_orif", "patella_fracture_orif",
    "intertrochanteric_hip_fracture_orif", "radial_head_fracture_orif", "olecranon_fracture_orif",
    "clavicle_fracture_orif", "cubital_tunnel_release", "lisfranc_orif", "scfe_pinning",
    "humeral_shaft_fracture_orif", "tibial_shaft_fracture_orif", "meniscus_repair",
    "lateral_ankle_ligament_repair", "total_shoulder_arthroplasty", "reverse_shoulder_arthroplasty"
}

def audit_entry(e: Dict[str, Any]) -> Dict[str, Any]:
    pid = e["procedure_id"]
    ia = len(e.get("important_anatomy", []))
    sar = len(e.get("structures_at_risk", []))
    lm = len(e.get("landmarks", []))
    an = len(e.get("approach_notes", []))
    pimp = len(e.get("pimp_topics", []))
    recs = e.get("recommended_approach_ids", [])
    has_recs = len(recs) > 0
    manual = e.get("manual_review", False)
    facts_total = ia + sar + lm + an
    has_high = has_high_conf(e)
    src_count = count_sources(e)

    scores = {
        "approach_accuracy": 5 if has_recs and not manual else (0 if manual and not has_recs else 2),
        "anatomy_usefulness": grade_dimension(ia, has_high, has_recs, manual, pimp),
        "structures_at_risk_usefulness": grade_dimension(sar, has_high, has_recs, manual, pimp),
        "landmark_usefulness": grade_dimension(lm, has_high, has_recs, manual, pimp),
        "approach_notes_usefulness": grade_dimension(an, has_high, has_recs, manual, pimp),
        "pimp_topic_usefulness": min(5, max(0, pimp // 1 + (1 if pimp >= 3 else 0))),
    }
    overall = compute_overall(scores, facts_total, has_recs, manual, src_count)
    is_common = pid in COMMON_CASES

    missing = []
    if has_recs and not manual:
        if ia == 0: missing.append("important_anatomy")
        if sar == 0: missing.append("structures_at_risk")
        if lm == 0: missing.append("landmarks")
        if an == 0: missing.append("approach_notes")

    priority = get_priority(overall, has_recs, manual, facts_total, is_common)

    reasons = []
    if manual:
        reasons.append("manual_review due to catalog gap (no matching approach ID or insufficient OB support for deterministic recs)")
    if has_recs and facts_total < 3:
        reasons.append("supported with recs but very low anatomy/risk/landmark/note coverage")
    if ia == 0 and has_recs:
        reasons.append("no important_anatomy despite mapped approach")
    if lm == 0 and has_recs:
        reasons.append("no landmarks despite clear incision/exposure landmarks on OB approach pages for similar cases")

    suggested = []
    if "carpal_tunnel_release" in pid:
        suggested.append("Deepen from https://www.orthobullets.com/approaches/12014/volar-approach-to-wrist : palmar cutaneous branch course, motor branch variation, transverse carpal ligament ulnar-side release under vision, thenar crease + PL landmarks, superficial palmar arch danger.")
    if "both_bone_forearm_fracture_orif" in pid:
        suggested.append("Add deforming forces, radial/ulnar anatomy, Henry approach steps and PIN risk from OB forearm both-bone page + approaches.")
    if "radial_head_fracture_orif" in pid:
        suggested.append("Add Kocher interval details, PIN/radial head blood supply, capitellum/radial head landmarks from OB 1020 and elbow lateral approach page.")
    if "acl_reconstruction" in pid or "tka" in pid:
        suggested.append("Ensure parapatellar exposure details, extensor mechanism, saphenous branch, tibial tubercle/patella landmarks from knee approach pages (12028 etc.).")
    if "proximal_humerus_fracture_orif" in pid:
        suggested.append("Already improved in v2; verify Neer segments, circumflex blood supply, deltopectoral dangers (axillary n., cephalic vein) from 1015/12061.")
    if "scaphoid_fracture_orif" in pid:
        suggested.append("Add retrograde blood supply, humpback/DISI criteria, volar vs dorsal approach choice + central screw from OB scaphoid fracture page.")
    if "achilles_tendon_repair" in pid:
        suggested.append("Add posteromedial approach, sural nerve, paratenon management from OB Achilles rupture page.")
    if "humeral_shaft_fracture_orif" in pid or "tibial_shaft_fracture_orif" in pid:
        suggested.append("Add radial nerve spiral groove / compartment details and specific anterolateral vs posterior (or leg) approach pearls from shaft fracture pages.")
    if not suggested and has_recs and overall < 4:
        suggested.append("Audit specific OB topic + dedicated /approaches/ page for this procedure; pull 2-4 high-yield items per weak dimension (anatomy, risks, landmarks, notes) with exact section citations.")

    return {
        "procedure_id": pid,
        "display_name": e.get("display_name"),
        "specialty": e.get("specialty"),
        "region": e.get("region"),
        "manual_review": manual,
        "recommended_approach_ids": recs,
        "conditional_approach_ids": e.get("conditional_approach_ids", []),
        "blocked_approach_ids": e.get("blocked_approach_ids", []),
        "important_anatomy_count": ia,
        "structures_at_risk_count": sar,
        "landmarks_count": lm,
        "approach_notes_count": an,
        "pimp_topics_count": pimp,
        "facts_total": facts_total,
        "has_recommended_approaches": has_recs,
        "has_high_conf_fact": has_high,
        "distinct_source_urls": src_count,
        "missing_fields": missing,
        "scores": scores,
        "overall_resident_utility": overall,
        "priority_tier": priority,
        "reasons": reasons,
        "suggested_improvements": suggested,
        "source_coverage_status": "strong" if src_count >= 2 and has_high else ("partial" if src_count > 0 or facts_total > 0 else "weak/none"),
    }

def main():
    entries = load_v2()
    audits = [audit_entry(e) for e in entries]

    # JSONL
    with open(REPORTS / "orthobullets_playbook_v2_line_quality_audit.jsonl", "w") as f:
        for a in audits:
            f.write(json.dumps(a) + "\n")

    # CSV
    if audits:
        keys = list(audits[0].keys())
        with open(REPORTS / "orthobullets_playbook_v2_line_quality_audit.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for a in audits:
                row = dict(a)
                for k in ["recommended_approach_ids", "conditional_approach_ids", "blocked_approach_ids", "missing_fields", "scores", "reasons", "suggested_improvements"]:
                    row[k] = json.dumps(row.get(k, []))
                writer.writerow(row)

    # Summary MD
    must_fix = [a for a in audits if a["priority_tier"] == "must_fix"]
    should_fix = [a for a in audits if a["priority_tier"] == "should_fix"]
    excellent = [a for a in audits if a["priority_tier"] == "excellent"]
    gaps = [a for a in audits if a["priority_tier"] == "unsupported_gap"]

    lines = []
    lines.append("# Orthobullets Playbook v2 Line-by-Line Quality Audit Summary")
    lines.append(f"Total procedures audited: {len(audits)}")
    lines.append(f"must_fix: {len(must_fix)} | should_fix: {len(should_fix)} | excellent: {len(excellent)} | unsupported_gap: {len(gaps)}")
    lines.append("")
    lines.append("## Top must_fix / should_fix (common supported cases with low utility)")
    for a in sorted(must_fix + should_fix, key=lambda x: (x["overall_resident_utility"], -len(x["recommended_approach_ids"])) )[:15]:
        lines.append(f"- {a['procedure_id']} (overall={a['overall_resident_utility']}, facts={a['facts_total']}, recs={len(a['recommended_approach_ids'])}, manual={a['manual_review']})")
        lines.append(f"  missing: {a['missing_fields']}")
        lines.append(f"  reasons: {'; '.join(a['reasons'][:2]) if a['reasons'] else 'N/A'}")
    lines.append("")
    lines.append("## Excellent (overall 4-5)")
    for a in excellent:
        lines.append(f"- {a['procedure_id']} (facts={a['facts_total']}, sources={a['distinct_source_urls']})")
    lines.append("")
    lines.append("## Unsupported gaps (catalog-limited; content secondary)")
    for a in gaps[:10]:
        lines.append(f"- {a['procedure_id']}")
    lines.append("")
    lines.append("See full line_quality_audit.jsonl / .csv for per-procedure scores, suggested OB pages, and improvement targets.")
    lines.append("Use this to drive v2_1 quality deepening pass (focus must_fix + should_fix supported entries first).")

    with open(REPORTS / "orthobullets_playbook_v2_quality_summary.md", "w") as f:
        f.write("\n".join(lines))

    print("Audit complete. Outputs written to reports/.")

if __name__ == "__main__":
    main()
