#!/usr/bin/env python3
"""
Tests for playbook-primary anatomy (builder + curator + filtering).

Exercises the 5 required cases using the orthobullets playbook + map for matching.
Simulates Miller chunks (some relevant, some irrelevant) to demonstrate filtering.
Calls the curator (real GPT if key present; otherwise falls back to builder output with note).

For each case reports:
- matched procedure + approaches from playbook/map
- playbook anatomy/risks/landmarks/pearls used (counts)
- Miller facts retained vs discarded (with reasons)
- final curated output (or builder output if no GPT)

Saves reports/playbook_primary_test_results.md
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playbook_anatomy_builder import build_playbook_anatomy
from anatomy_curator import curate_playbook_anatomy

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Load inputs once
with open("data/approach_playbook/orthobullets_procedure_playbook_v1.jsonl") as f:
    PLAYBOOK = [json.loads(l) for l in f if l.strip()]

with open("data/approach_playbook/procedure_to_approach_map_v1.jsonl") as f:
    MAP = [json.loads(l) for l in f if l.strip()]

def _match_procedure(prompt: str) -> Dict[str, Any]:
    """Simple match using triggers from map (mimics router). Return first good hit + full playbook entry."""
    norm = prompt.lower()
    for m in MAP:
        for t in m.get("triggers", []):
            if t.lower() in norm:
                pid = m["procedure_id"]
                entry = next((e for e in PLAYBOOK if e["procedure_id"] == pid), {})
                return {
                    "procedure_id": pid,
                    "display_name": m.get("display_name"),
                    "recommended": m.get("recommended_approach_ids", []),
                    "conditional": m.get("conditional_approach_ids", []),
                    "blocked": m.get("blocked_approach_ids", []),
                    "playbook_entry": entry,
                    "map_entry": m,
                }
    # fallback unknown
    return {"procedure_id": "unknown", "recommended": [], "playbook_entry": {}, "map_entry": {}}

def _fake_miller_chunks(procedure_id: str, approach_ids: List[str]) -> List[Dict[str, Any]]:
    """Simulated Miller chunks: mix of highly relevant (overlap with playbook) and irrelevant (cross-region or no overlap)."""
    chunks = []
    # Relevant ones (will be retained for good cases)
    if "distal_radius" in procedure_id:
        chunks.append({"id": "m-dr-1", "text": "Watershed line is the most volar prominence; plates must stay proximal to protect FPL.", "source_quote": "Watershed line...", "heading": "Anatomy", "region": "wrist", "score": 0.92})
        chunks.append({"id": "m-dr-2", "text": "Palmar cutaneous branch runs ulnar to FCR in the volar approach.", "source_quote": "", "heading": "Dangers", "region": "wrist", "score": 0.88})
    if "tha" in procedure_id or "hip" in procedure_id.lower():
        chunks.append({"id": "m-hip-1", "text": "Sciatic nerve protected by reflecting short external rotators posteriorly.", "source_quote": "", "heading": "Dangers", "region": "hip", "score": 0.9})
    if "carpal" in procedure_id:
        chunks.append({"id": "m-ctr-1", "text": "Transverse carpal ligament release; median nerve motor branch at risk.", "source_quote": "", "heading": "Approach", "region": "wrist", "score": 0.85})
    if "tka" in procedure_id:
        chunks.append({"id": "m-tka-1", "text": "Medial parapatellar provides access; infrapatellar saphenous branch crosses field.", "source_quote": "", "heading": "Approach", "region": "knee", "score": 0.87})
    if "femoral_shaft" in procedure_id:
        chunks.append({"id": "m-fem-1", "text": "Proximal fragment flexed by iliopsoas, abducted by gluteus medius/minimus.", "source_quote": "", "heading": "Deforming forces", "region": "thigh", "score": 0.91})

    # Irrelevant / cross-region (should be filtered for most cases)
    chunks.append({"id": "m-ir-1", "text": "Lateral malleolus approach: posterior fibula margin, protect sural nerve.", "source_quote": "", "heading": "Approach to Lateral Malleolus", "region": "ankle", "score": 0.75})
    chunks.append({"id": "m-ir-2", "text": "Shoulder deltopectoral interval between deltoid and pectoralis major.", "source_quote": "", "heading": "Approach", "region": "shoulder", "score": 0.65})
    chunks.append({"id": "m-ir-3", "text": "Generic lower extremity anatomy note unrelated to the specific procedure.", "source_quote": "", "heading": "Anatomy", "region": "leg", "score": 0.4})
    return chunks

def _run_case(prompt: str, case_label: str) -> Dict[str, Any]:
    match = _match_procedure(prompt)
    pid = match["procedure_id"]
    rec_ids = match.get("recommended", [])
    entry = match.get("playbook_entry", {})

    # Build (with simulated Miller)
    fake_miller = _fake_miller_chunks(pid, rec_ids)
    built = build_playbook_anatomy(
        procedure_id=pid,
        recommended_approach_ids=rec_ids,
        conditional_approach_ids=match.get("conditional"),
        blocked_approach_ids=match.get("blocked"),
        miller_support_chunks=fake_miller,
    )

    # Curate (real if key, else builder result)
    try:
        curated = curate_playbook_anatomy(
            procedure={"procedure_id": pid, "display_name": match.get("display_name")},
            approach=built.get("approach", {}),
            playbook_fields=built,
            miller_support=built.get("millerSupport", []),
        )
        curator_used = True
    except Exception as e:
        curated = built
        curated["curator_error"] = str(e)
        curator_used = False

    # Analyze retained vs discarded (simple: compare counts before/after filter inside builder)
    retained = len(built.get("millerSupport", []))
    total_fake = len(fake_miller)
    discarded = total_fake - retained

    return {
        "case": case_label,
        "prompt": prompt,
        "matched_procedure": pid,
        "matched_approaches": rec_ids,
        "playbook_used": {
            "importantAnatomy_count": len(built.get("importantAnatomy", built.get("important_anatomy", []))),
            "structuresAtRisk_count": len(built.get("structuresAtRisk", built.get("structures_at_risk", []))),
            "landmarks_count": len(built.get("landmarks", [])),
            "pearls_count": len(built.get("pearls", [])),
        },
        "miller": {
            "total_simulated": total_fake,
            "retained_after_filter": retained,
            "discarded": discarded,
            "discarded_examples": [c.get("text", "")[:80] for c in fake_miller if "millerSupport" not in str(built) or c.get("id") not in [s.get("source_url","") for s in built.get("millerSupport", []) ]][:2],
        },
        "curator_used": curator_used,
        "final_output_keys": list(curated.keys()),
        "sample_final": {k: (curated[k] if not isinstance(curated.get(k), (list,dict)) else f"<{len(curated.get(k,[]))} items>") for k in ["importantAnatomy", "structuresAtRisk", "landmarks", "pearls", "meta"] if k in curated},
    }

def main():
    cases = [
        ("distal radius fracture ORIF", "distal_radius_fracture_orif"),
        ("posterior THA", "tha_posterior"),
        ("carpal tunnel release", "carpal_tunnel_release"),
        ("TKA", "tka"),
        ("femoral shaft ORIF", "femoral_shaft_fracture_orif"),
    ]

    results = []
    for prompt, label in cases:
        res = _run_case(prompt, label)
        results.append(res)
        print(f"Processed {label}: retained {res['miller']['retained_after_filter']}/{res['miller']['total_simulated']} Miller, curator_used={res['curator_used']}")

    # Write report
    md = ["# Playbook Primary Test Results\n", f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n"]
    for r in results:
        md.append(f"## {r['case']} (prompt: {r['prompt']})\n")
        md.append(f"- Matched: {r['matched_procedure']} → approaches {r['matched_approaches']}\n")
        md.append(f"- Playbook content used: anatomy={r['playbook_used']['importantAnatomy_count']}, risks={r['playbook_used']['structuresAtRisk_count']}, landmarks={r['playbook_used']['landmarks_count']}, pearls={r['playbook_used']['pearls_count']}\n")
        md.append(f"- Miller: {r['miller']['retained_after_filter']} retained, {r['miller']['discarded']} discarded (examples of discarded: {r['miller']['discarded_examples']})\n")
        md.append(f"- Curator GPT used: {r['curator_used']}\n")
        md.append(f"- Final output sample keys: {r['final_output_keys']}\n\n")
        md.append("Sample final (truncated):\n")
        md.append("```json\n" + json.dumps(r['sample_final'], indent=2)[:800] + "\n```\n\n")

    path = REPORTS_DIR / "playbook_primary_test_results.md"
    path.write_text("".join(md))
    print(f"Wrote {path}")

if __name__ == "__main__":
    main()
