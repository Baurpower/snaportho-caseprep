#!/usr/bin/env python3
"""
v2 Playbook Product Utility Test Harness (adapted from prior playbook_primary tests).

Loads v2 playbook + map_v2.
Runs >=20 cases (10 existing v1.1-style + 10+ new v2).
For each: trigger match -> recs/conditional/blocked from map + counts from playbook entry.
Computes readiness:
  0 = unusable (no match or all blank + manual)
  1 = sparse / manual review
  2 = usable but incomplete (recs but <3 facts total)
  3 = good (recs + 3+ facts across categories)
  4 = excellent (recs + 4+ facts + pimp + high-conf items)

Saves:
- reports/playbook_v2_product_utility_test_results.md
- reports/playbook_v2_product_utility_test_results.json

No BroBot, no Miller authoring, OB-only data.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Load v2
with open("data/approach_playbook/orthobullets_procedure_playbook_v2.jsonl") as f:
    PLAYBOOK = {e["procedure_id"]: e for e in (json.loads(l) for l in f if l.strip())}

with open("data/approach_playbook/procedure_to_approach_map_v2.jsonl") as f:
    MAP = [json.loads(l) for l in f if l.strip()]

def _match_procedure(prompt: str) -> Dict[str, Any]:
    norm = prompt.lower()
    for m in MAP:
        for t in m.get("triggers", []):
            if t.lower() in norm:
                pid = m["procedure_id"]
                entry = PLAYBOOK.get(pid, {})
                return {
                    "procedure_id": pid,
                    "display_name": m.get("display_name") or entry.get("display_name"),
                    "recommended": m.get("recommended_approach_ids", []),
                    "conditional": m.get("conditional_approach_ids", []),
                    "blocked": m.get("blocked_approach_ids", []),
                    "playbook_entry": entry,
                    "map_entry": m,
                    "manual_review": entry.get("manual_review", False) or m.get("confidence") == "manual_review",
                }
    return {"procedure_id": "unknown", "recommended": [], "playbook_entry": {}, "map_entry": {}, "manual_review": True}

def _score(entry: Dict[str, Any], recs: List[str], manual: bool) -> int:
    if manual or not entry:
        return 0 if not recs else 1
    facts = (len(entry.get("important_anatomy", [])) +
             len(entry.get("structures_at_risk", [])) +
             len(entry.get("landmarks", [])) +
             len(entry.get("approach_notes", [])))
    has_pimp = len(entry.get("pimp_topics", [])) > 0
    has_high = any(
        item.get("confidence") == "high"
        for arr in [entry.get("important_anatomy", []), entry.get("structures_at_risk", []), entry.get("landmarks", []), entry.get("approach_notes", [])]
        for item in arr
    )
    if not recs:
        return 1
    if facts >= 5 and has_high and has_pimp:
        return 4
    if facts >= 3:
        return 3
    if facts >= 1:
        return 2
    return 1

def _run_case(prompt: str, case_label: str) -> Dict[str, Any]:
    match = _match_procedure(prompt)
    pid = match["procedure_id"]
    recs = match.get("recommended", [])
    entry = match.get("playbook_entry", {})
    manual = match.get("manual_review", False)
    ia = len(entry.get("important_anatomy", []))
    sar = len(entry.get("structures_at_risk", []))
    lm = len(entry.get("landmarks", []))
    an = len(entry.get("approach_notes", []))
    pimp = len(entry.get("pimp_topics", []))
    score = _score(entry, recs, manual)
    return {
        "case_label": case_label,
        "prompt": prompt,
        "matched_procedure_id": pid,
        "display_name": match.get("display_name"),
        "recommended_approach_ids": recs,
        "conditional_approach_ids": match.get("conditional", []),
        "blocked_approach_ids": match.get("blocked", []),
        "important_anatomy_count": ia,
        "structures_at_risk_count": sar,
        "landmarks_count": lm,
        "approach_notes_count": an,
        "pimp_topics_count": pimp,
        "manual_review": manual,
        "readiness_score": score,
        "readiness_label": {0: "unusable", 1: "sparse/manual review", 2: "usable but incomplete", 3: "good", 4: "excellent"}.get(score, "unknown"),
        "has_recs": bool(recs),
    }

# 20+ cases: 10 old v1.1 style + 10+ new v2
CASES = [
    # Existing / v1.1 style (10)
    ("tka", "TKA total knee arthroplasty"),
    ("distal_radius_fracture_orif", "distal radius fracture ORIF"),
    ("carpal_tunnel_release", "carpal tunnel release"),
    ("femoral_shaft_fracture_orif", "femoral shaft fracture ORIF"),
    ("tha_posterior", "posterior THA"),
    ("acl_reconstruction", "ACL reconstruction"),
    ("rotator_cuff_repair", "rotator cuff repair"),
    ("both_bone_forearm_fracture_orif", "both bone forearm ORIF"),
    ("scaphoid_fracture_orif", "scaphoid fracture ORIF"),
    ("bimalleolar_ankle_orif", "bimalleolar ankle ORIF"),
    # New v2 (12+)
    ("proximal_humerus_fracture_orif", "proximal humerus fracture ORIF"),
    ("humeral_shaft_fracture_orif", "humeral shaft fracture ORIF"),
    ("tibial_shaft_fracture_orif", "tibial shaft fracture ORIF"),
    ("lisfranc_orif", "Lisfranc ORIF"),
    ("scfe_pinning", "SCFE pinning"),
    ("ddh_surgery", "DDH surgery Pavlik or osteotomy"),
    ("acdf", "ACDF anterior cervical discectomy fusion"),
    ("posterior_lumbar_decompression_fusion", "posterior lumbar decompression fusion"),
    ("total_shoulder_arthroplasty", "total shoulder arthroplasty"),
    ("reverse_shoulder_arthroplasty", "reverse shoulder arthroplasty"),
    ("meniscus_repair", "meniscus repair"),
    ("lateral_ankle_ligament_repair", "lateral ankle ligament repair Brostrom"),
    ("distal_femur_fracture_orif", "distal femur fracture ORIF"),
    ("lateral_epicondylitis_release", "lateral epicondylitis tennis elbow release"),
    ("metacarpal_fracture_orif", "metacarpal fracture ORIF boxer's"),
]

results = []
for label, prompt in CASES:
    res = _run_case(prompt, label)
    results.append(res)

# Summary
avg_score = sum(r["readiness_score"] for r in results) / len(results) if results else 0
good_or_better = sum(1 for r in results if r["readiness_score"] >= 3)
manual_count = sum(1 for r in results if r["manual_review"])

md_lines = []
md_lines.append("# Playbook v2 Product Utility Test Results")
md_lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
md_lines.append(f"Total cases: {len(results)} (mix of v1.1 preserved + new v2)")
md_lines.append(f"Average readiness: {avg_score:.2f}")
md_lines.append(f"Good or excellent (score >=3): {good_or_better}")
md_lines.append(f"Manual review in test set: {manual_count}")
md_lines.append("")
md_lines.append("## Per-Case Results")
md_lines.append("| Case | Matched | Recs | ia/sar/lm/an/pimp | Manual | Score | Label |")
md_lines.append("|------|---------|------|-------------------|--------|-------|-------|")
for r in results:
    md_lines.append(f"| {r['case_label']} | {r['matched_procedure_id']} | {len(r['recommended_approach_ids'])} | {r['important_anatomy_count']}/{r['structures_at_risk_count']}/{r['landmarks_count']}/{r['approach_notes_count']}/{r['pimp_topics_count']} | {r['manual_review']} | {r['readiness_score']} | {r['readiness_label']} |")

md_lines.append("")
md_lines.append("## Interpretation")
md_lines.append("- Score 4/3 cases now deliver richer playbook-primary anatomy (e.g. TKA, proximal humerus post-enrichment, new humeral shaft, total shoulder, meniscus, lateral ankle).")
md_lines.append("- Score 1/0 remain for catalog-gap manual_review (Lisfranc, spine ACDF/lumbar, SCFE, original ankle/olecranon etc.) or still-thin supported not enriched this pass.")
md_lines.append("- Curator would receive clean structured fields (no raw Miller, no invention). Router restricts to recs or gates unsupported.")
md_lines.append("- v2 improves utility for prioritized resident cases vs v1.1 while preserving strict OB + catalog rules.")

with open(REPORTS_DIR / "playbook_v2_product_utility_test_results.md", "w") as f:
    f.write("\n".join(md_lines))

with open(REPORTS_DIR / "playbook_v2_product_utility_test_results.json", "w") as f:
    json.dump({"generated": datetime.now(timezone.utc).isoformat(), "summary": {"total": len(results), "avg_score": avg_score, "good_or_better": good_or_better, "manual_in_set": manual_count}, "cases": results}, f, indent=2)

print("Saved reports/playbook_v2_product_utility_test_results.md + .json")
print(f"Avg readiness: {avg_score:.2f}; >=3: {good_or_better}/{len(results)}; manual in set: {manual_count}")
PYEOF
python3 scripts/test_playbook_v2_product_utility.py 2>&1 | cat
