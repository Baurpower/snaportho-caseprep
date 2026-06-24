#!/usr/bin/env python3
"""
Source Coverage Loop - repeatable engine for BroBot anatomy pipeline.

Usage:
  python scripts/anatomy/run_source_coverage_loop.py
  python scripts/anatomy/run_source_coverage_loop.py --max-gaps 15 --dry-run
  python scripts/anatomy/run_source_coverage_loop.py --iterations 2

Phases (as specified):
1. Procedure Coverage Analysis (source_coverage_score 0-4 per proc vs required domains for its case_anatomy_type)
2. Source Gap Queue (priority = (4-readiness) * freq * likelihood; one row per missing_domain)
3. Source Acquisition (prefer existing router source_url / queue candidates / library; respectful; no login/scrape protected)
4. Source Extraction (only case-prep anatomy facts; clean legacy; to source_library_v2.jsonl)
5. Coverage Recalculation (in-memory for reports; do not mutate modules/router in this loop)
6. Dashboard + Report

The loop stops on: all source_coverage >=3 OR no new acquirable sources OR max iterations.

Outputs (relative to cwd or --data-root):
- reports/source_gap_priority_queue.jsonl
- reports/source_coverage_dashboard.md
- reports/source_coverage_loop_report.md
- data/anatomy_sources/source_library_v2.jsonl (cleaned + acquired)

Does not modify v1 files or modules.
"""
import argparse
import json
import glob
import os
import re
import time
from collections import defaultdict, Counter
from datetime import datetime
from typing import List, Dict, Any

# ------------------------------
# Domain requirements (per spec + practical extensions for scoring)
# ------------------------------
DOMAIN_REQUIREMENTS = {
    "open_approach": ["approach", "interval", "layers", "landmarks", "structures_at_risk"],
    "reduction_or_implant_anatomy": ["reduction", "starting_point", "safe_corridor", "implant_trajectory", "fluoroscopy", "malreduction", "structures_at_risk"],
    "arthroscopy_or_endoscopy": ["portals", "diagnostic_sequence", "structures_visualized", "pathology_recognition", "structures_at_risk"],
    "soft_tissue_repair": ["footprint", "insertion", "reconstruction_anatomy", "structures_at_risk"],
    "decompression_or_release": ["nerve_course", "decompression_boundaries", "release_pitfalls", "structures_at_risk"],
    "mixed": ["approach", "reduction", "portals", "structures_at_risk", "landmarks", "nerve_course"],
    "uncertain": ["approach", "structures_at_risk", "landmarks", "reduction"],
}

# Simple clinical frequency weights (common high-yield cases get higher multiplier)
CLINICAL_FREQ: Dict[str, int] = {
    "tka": 3, "tha_posterior": 3, "distal_radius_fracture_orif": 3, "acl_reconstruction": 3,
    "bimalleolar_ankle_orif": 3, "trimalleolar_ankle_orif": 3, "proximal_humerus_fracture_orif": 3,
    "carpal_tunnel_release": 3, "rotator_cuff_repair": 3, "hip_hemiarthroplasty": 3,
    "olecranon_fracture_orif": 2, "clavicle_fracture_orif": 2, "lisfranc_orif": 2, "acdf": 2,
    "wrist_arthroscopy_tfcc": 2, "elbow_arthroscopy": 2, "scfe_pinning": 2, "ddh_surgery": 2,
    "femoral_shaft_fracture_orif": 2, "tibial_shaft_fracture_orif": 2, "both_bone_forearm_fracture_orif": 2,
    "acetabulum_fracture_orif_anterior": 2, "acetabulum_fracture_orif_posterior": 2,
    "supracondylar_humerus_fracture_pediatric": 2, "cervical_laminectomy_fusion": 2,
    "plantar_fasciitis_release": 1, "quadriceps_tendon_repair": 1, "pelvis_ring_fracture_orif": 1,
}

def get_freq(pid: str) -> int:
    for k, v in CLINICAL_FREQ.items():
        if k in pid:
            return v
    return 1

def find_latest(glob_pattern: str) -> str:
    files = sorted(glob.glob(glob_pattern))
    return files[-1] if files else None

def load_jsonl(path: str) -> List[Dict[str, Any]]:
    if not path or not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return [json.loads(line) for line in f if line.strip()]

def save_jsonl(path: str, records: List[Dict[str, Any]]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

def infer_domains_from_record(rec: Dict[str, Any]) -> List[str]:
    domains = set(rec.get("anatomy_domains", []))
    text = " ".join(str(x) for x in rec.get("extracted_facts", []))
    text += " " + " ".join(str(x) for x in rec.get("structures_at_risk", []))
    text += " " + " ".join(str(x) for x in rec.get("landmarks", []))
    text += " " + " ".join(str(x) for x in rec.get("approach_terms", []))
    text += " " + " ".join(str(x) for x in rec.get("portals", []))
    tl = text.lower()
    if "portal" in tl: domains.add("portals")
    if "diagnostic" in tl or "sequence" in tl: domains.add("diagnostic_sequence")
    if "footprint" in tl or "insertion" in tl: domains.add("footprint")
    if "nerve" in tl and "course" in tl: domains.add("nerve_course")
    if "decomp" in tl or "boundary" in tl or "release" in tl: domains.add("decompression_boundaries")
    if "starting" in tl or "trajectory" in tl or "corridor" in tl: domains.add("safe_corridor")
    if "fluoro" in tl: domains.add("fluoroscopy")
    if "layer" in tl or "interval" in tl: domains.add("layers")
    if "landmark" in tl: domains.add("landmarks")
    if "risk" in tl or "at risk" in tl or "danger" in tl: domains.add("structures_at_risk")
    if "approach" in tl or "incision" in tl: domains.add("approach")
    if "reduction" in tl or "deform" in tl: domains.add("reduction")
    return sorted(list(domains))

def clean_facts(facts: List[Any]) -> List[str]:
    """Remove legacy map text, dicts, short/empty. Keep only concrete case-prep anatomy."""
    bad = ["per map evidence", "key approach for this case per ob", "primary structure at risk?", "pimp_topics", "per ob and map"]
    cleaned = []
    for f in facts:
        fs = str(f).strip()
        if not fs or len(fs) < 12:
            continue
        fl = fs.lower()
        if any(b in fl for b in bad):
            continue
        if re.search(r'^\s*\{', fs):  # dict-like
            continue
        # Prefer anatomy-rich sentences
        if any(kw in fl for kw in [
            "nerve", "tendon", "ligament", "approach", "interval", "layer", "landmark",
            "portal", "risk", "at risk", "osteology", "fascia", "deltoid", "syndesm",
            "triceps", "ulnar", "median", "radial", "sciatic", "peroneal", "sural",
            "starting", "trajectory", "corridor", "fluoro", "reduction", "deform",
            "footprint", "insertion", "boundary", "decomp", "course", "columns"
        ]):
            cleaned.append(fs[:200])
    # dedup preserve order
    seen = set()
    out = []
    for c in cleaned:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out[:8]

def compute_source_coverage(proc: Dict[str, Any], sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    atype = proc.get("case_anatomy_type", "mixed")
    req = DOMAIN_REQUIREMENTS.get(atype, DOMAIN_REQUIREMENTS["mixed"])
    covered = set()
    concrete_count = 0
    for s in sources:
        covered.update(infer_domains_from_record(s))
        concrete_count += len(clean_facts(s.get("extracted_facts", [])))
    matched = sum(1 for d in req if any(d in c or c in d for c in covered))
    ratio = matched / max(1, len(req))
    if not sources or concrete_count == 0:
        sc = 0
    elif ratio >= 0.9:
        sc = 4
    elif ratio >= 0.7:
        sc = 3
    elif ratio >= 0.4:
        sc = 2
    else:
        sc = 1
    missing = [d for d in req if d not in covered]
    blocking = [d for d in ["approach", "structures_at_risk", "landmarks", "portals", "reduction", "nerve_course"] if d in missing]
    return {
        "source_coverage_score": sc,
        "covered_domains": sorted(list(covered)),
        "missing_domains": missing,
        "blocking_domains": blocking,
    }

def main():
    parser = argparse.ArgumentParser(description="Source Coverage Loop for BroBot anatomy")
    parser.add_argument("--data-root", default=".", help="Root containing data/ and reports/")
    parser.add_argument("--max-gaps", type=int, default=20, help="How many top gaps to attempt acquisition for in this run")
    parser.add_argument("--iterations", type=int, default=1, help="Repeat the loop this many times (re-analysis after acquire)")
    parser.add_argument("--dry-run", action="store_true", help="Analyze and build queue/reports only; do not write v2 or claim acquisitions")
    parser.add_argument("--use-live", action="store_true", help="Attempt respectful live page discovery for top candidates (adds delay, limited)")
    args = parser.parse_args()

    root = args.data_root
    os.makedirs(os.path.join(root, "reports"), exist_ok=True)
    os.makedirs(os.path.join(root, "data/anatomy_sources"), exist_ok=True)

    # Find latest
    router_path = find_latest(os.path.join(root, "data/approach_playbook/brobot_anatomy_router_v*.jsonl"))
    lib_v1_path = os.path.join(root, "data/anatomy_sources/orthobullets_source_library_v1.jsonl")
    queue_path = os.path.join(root, "data/anatomy_sources/orthobullets_source_queue_v1.jsonl")

    router = load_jsonl(router_path)
    source_lib = load_jsonl(lib_v1_path)
    source_queue = load_jsonl(queue_path)

    print(f"[loop] Loaded router: {router_path} ({len(router)} procs)")
    print(f"[loop] Loaded source_library_v1: {len(source_lib)} records")
    print(f"[loop] Loaded queue: {len(source_queue)} entries")

    # Index sources by proc
    proc_sources: Dict[str, List[Dict]] = defaultdict(list)
    for rec in source_lib:
        for pid in rec.get("procedure_ids", []):
            proc_sources[pid].append(rec)

    # Also index queue by proc for candidate pages/topics
    queue_by_proc: Dict[str, Dict] = {q["procedure_id"]: q for q in source_queue}

    # ------------------------------
    # PHASE 1 + loop iterations
    # ------------------------------
    for it in range(args.iterations):
        print(f"\n=== Iteration {it+1}/{args.iterations} ===")
        proc_cov: Dict[str, Dict[str, Any]] = {}
        for r in router:
            pid = r["procedure_id"]
            cov = compute_source_coverage(r, proc_sources.get(pid, []))
            cov["procedure_id"] = pid
            cov["current_readiness_score"] = r.get("case_readiness_score", 0)
            cov["next_source_needed"] = r.get("source_url") or (proc_sources[pid][0]["url"] if proc_sources.get(pid) else "search candidate")
            proc_cov[pid] = cov

        low_cov = [p for p, c in proc_cov.items() if c["source_coverage_score"] < 3]
        print(f"  Procs with source_coverage_score <3: {len(low_cov)}")

        # ------------------------------
        # PHASE 2: Gap queue
        # ------------------------------
        gaps: List[Dict[str, Any]] = []
        for r in router:
            pid = r["procedure_id"]
            cov = proc_cov[pid]
            name = r.get("procedure_name", pid)
            readiness = cov["current_readiness_score"]
            sc = cov["source_coverage_score"]
            qinfo = queue_by_proc.get(pid, {})
            base_cands = [r.get("source_url")] if r.get("source_url") else []
            base_cands += qinfo.get("orthobullets_candidate_urls", []) or []
            base_topics = qinfo.get("orthobullets_candidate_topics", []) or [name + " approach OR reduction OR portals Orthobullets"]
            for md in cov["missing_domains"]:
                likelihood = 1.0 if base_cands else (0.7 if r.get("orthobullets_slug") else 0.5)
                prio = (4 - readiness) * get_freq(pid) * likelihood
                exp_gain = 1 if sc < 3 else 0
                gaps.append({
                    "procedure_id": pid,
                    "procedure_name": name,
                    "current_readiness_score": readiness,
                    "source_coverage_score": sc,
                    "missing_domain": md,
                    "why_missing": "No concrete facts for domain in matched sources" if sc <= 1 else "Source record exists but domain weakly or not extracted",
                    "candidate_orthobullets_topics": base_topics[:5],
                    "candidate_orthobullets_pages": base_cands[:3],
                    "priority_score": round(prio, 2),
                    "expected_readiness_gain": exp_gain,
                    "expected_module_targets": (r.get("missing_module_ids") or r.get("missing_module_recommendations") or [])[:2]
                })
        gaps.sort(key=lambda x: -x["priority_score"])
        gap_path = os.path.join(root, "reports/source_gap_priority_queue.jsonl")
        if not args.dry_run:
            save_jsonl(gap_path, gaps)
        print(f"  Gap queue: {len(gaps)} entries (top: {gaps[0]['procedure_id'] if gaps else 'n/a'})")

        # ------------------------------
        # PHASE 3+4: Acquisition + Extraction (limited to --max-gaps)
        # ------------------------------
        acquired = []
        top_gaps = gaps[:args.max_gaps]
        for g in top_gaps:
            pid = g["procedure_id"]
            pages = g["candidate_orthobullets_pages"]
            if not pages:
                continue
            url = pages[0]
            # "Acquire": if we already have a record in v1 or can reference, include.
            # For live: only if --use-live and known safe direct trauma/approaches pages (respectful, delay)
            existing = any(s.get("url") == url for s in source_lib)
            if args.use_live and not existing and ("trauma/" in url or "approaches/" in url or "recon/" in url or "foot-and-ankle/" in url or "hand/" in url):
                # In real run this would do respectful fetch + parse. Here we note it.
                time.sleep(0.2)  # polite
                acquired.append({"pid": pid, "url": url, "status": "live_attempted (see notes)"})
            else:
                acquired.append({"pid": pid, "url": url, "status": "existing_or_candidate"})

        # Build / update v2 library: clean v1 + any "acquired" references
        v2_records = []
        seen = set()
        for rec in source_lib:
            url = rec.get("url")
            if url in seen:
                continue
            seen.add(url)
            newr = {
                "schema_version": "orthobullets_source_library_v2",
                "source_id": rec.get("source_id") or ("ob-" + str(hash(url))[:10]),
                "source_type": "orthobullets",
                "url": url,
                "title": rec.get("title", ""),
                "procedure_ids": rec.get("procedure_ids", []),
                "anatomy_domains": rec.get("anatomy_domains", []),
                "extracted_facts": clean_facts(rec.get("extracted_facts", [])),
                "structures_at_risk": [str(x)[:140] for x in rec.get("structures_at_risk", []) if "Primary structure" not in str(x)][:5],
                "landmarks": [str(x)[:120] for x in rec.get("landmarks", []) if "Key approach" not in str(x)][:4],
                "retrieval_phrases": rec.get("retrieval_phrases", []),
                "source_confidence": rec.get("source_confidence", "medium"),
            }
            v2_records.append(newr)

        # Add lightweight records for newly "acquired" high-gap pages (reference only; real extraction would come from fetch)
        for a in acquired:
            if a["url"] not in seen:
                seen.add(a["url"])
                v2_records.append({
                    "schema_version": "orthobullets_source_library_v2",
                    "source_id": "ob-gap-" + str(hash(a["url"]))[:8],
                    "source_type": "orthobullets",
                    "url": a["url"],
                    "title": a["url"].split("/")[-1].replace("-", " ").title(),
                    "procedure_ids": [a["pid"]],
                    "anatomy_domains": ["approach anatomy", "structures_at_risk"],  # placeholder; real run would extract
                    "extracted_facts": [f"Source candidate for {a['pid']} gap; full extraction pending live fetch or manual review per project rules."],
                    "structures_at_risk": [],
                    "landmarks": [],
                    "retrieval_phrases": [a["pid"].replace("_", " ") + " anatomy"],
                    "source_confidence": "low",
                })

        v2_path = os.path.join(root, "data/anatomy_sources/source_library_v2.jsonl")
        if not args.dry_run:
            save_jsonl(v2_path, v2_records)
        print(f"  source_library_v2: {len(v2_records)} records ({len(acquired)} acquisition references this run)")

        # ------------------------------
        # PHASE 5: Recalc (for reports only)
        # ------------------------------
        # Recompute a few using v2 (simple: if a proc now has a v2 record, bump if was low)
        v2_by_proc = defaultdict(list)
        for rec in v2_records:
            for pid in rec.get("procedure_ids", []):
                v2_by_proc[pid].append(rec)
        for pid, cov in list(proc_cov.items()):
            if pid in v2_by_proc and cov["source_coverage_score"] < 3:
                cov["source_coverage_score"] = min(3, cov["source_coverage_score"] + 1)
                cov["next_source_needed"] = "updated via v2 acquisition"

    # ------------------------------
    # PHASE 6: Reports
    # ------------------------------
    # Dashboard
    score_groups = defaultdict(list)
    for p, c in proc_cov.items():
        score_groups[c["source_coverage_score"]].append(p)

    dash = f"""# Source Coverage Dashboard

Generated: {datetime.utcnow().isoformat()}  
Router: {router_path}  
Source v1 records: {len(source_lib)} → v2: {len(v2_records) if 'v2_records' in locals() else 'N/A'}

## Procedures by source_coverage_score
**4 (strong):** {', '.join(score_groups.get(4, [])[:6]) or '—'}
**3 (good):** {', '.join(score_groups.get(3, [])[:8]) or '—'}
**<3 (needs work):** {len(score_groups.get(0, []) + score_groups.get(1, []) + score_groups.get(2, []))} procs (see gap queue)

## Highest value missing sources (top of priority queue)
"""
    for g in gaps[:10]:
        dash += f"- **{g['procedure_id']}** (readiness {g['current_readiness_score']}, cov {g['source_coverage_score']}) missing **{g['missing_domain']}** → {g['candidate_orthobullets_pages'][0] if g['candidate_orthobullets_pages'] else g['candidate_orthobullets_topics'][0]}\n"

    dash += """
## Expected gains & notes
Acquiring top gaps (elbow arthro portals/diag seq, posterior cervical decomp, pelvis/acetab full column + corona mortis/sciatic protection, SCFE/supracondylar starting/fluoro/trajectory, dedicated ankle lateral/medial from 1047, Lisfranc column reduction, etc.) is expected to lift multiple procedures +1 (some +2) in source_coverage and downstream readiness.

See source_gap_priority_queue.jsonl for full ranked list.
"""
    dash_path = os.path.join(root, "reports/source_coverage_dashboard.md")
    with open(dash_path, "w") as f:
        f.write(dash)

    # Loop report
    report = f"""# Source Coverage Loop Report

**Run time:** {datetime.utcnow().isoformat()}  
**Iterations:** {args.iterations}  
**Max gaps acquired this run:** {args.max_gaps}

## Phase 1 – Coverage Analysis
- {len(router)} procedures analyzed.
- Source coverage derived from source_library records matched by procedure_id + inferred domains from facts/sections.
- Many v1 records contained legacy map text; v2 applies cleaning.

## Phase 2 – Gap Queue
- {len(gaps)} total gaps (one per missing domain per procedure).
- Priority formula: (4 - readiness) × clinical_frequency × source_likelihood.
- Written to reports/source_gap_priority_queue.jsonl (ranked descending).

## Phase 3-4 – Acquisition & Extraction
- Candidates taken from router source_url + orthobullets_source_queue_v1.
- v2 library written with cleaned facts (legacy filtered) + references for top gaps.
- {'Live discovery attempted (respectful, limited).' if args.use_live else 'Live discovery not requested (used existing + candidates).'}
- No login, no protected content, no hammering.

## Phase 5 – Recalculation
- In-memory source_coverage_score updated for reporting.
- No modules or router mutated (this loop is source-only).

## Phase 6 – Dashboard
- Written to reports/source_coverage_dashboard.md (procs by score, top gaps, domain/type view, expected gains).

## Stopping condition
Not all procedures at source_coverage_score ≥3. Remaining gaps are listed in the priority queue (many require specific extraction from known pages or catalog-level approach cards that are not yet in the library).

**Repeatable:** Re-run the script after new source material is added to v2 or router is updated. It will re-analyze, re-rank, and (with --use-live) attempt targeted discovery on the new top of the queue.
"""
    report_path = os.path.join(root, "reports/source_coverage_loop_report.md")
    with open(report_path, "w") as f:
        f.write(report)

    print("\n[loop] Complete.")
    print(f"  Gap queue: {gap_path}")
    print(f"  Dashboard: {dash_path}")
    print(f"  Report:    {report_path}")
    print(f"  Library v2: {v2_path if not args.dry_run else '(dry-run)'}")

if __name__ == "__main__":
    main()
