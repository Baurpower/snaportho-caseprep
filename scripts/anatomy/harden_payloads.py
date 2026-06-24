#!/usr/bin/env python3
"""
Harden / normalize production certified payloads to target v2 schema.

- Standardizes structures_at_risk to list of dicts with consistent keys.
- Filters known bad patterns.
- Adds/enhances fields: surgical_layers (structured), anatomy_category, approach_id.
- Bumps schema to brobot_case_prep_payload_v2.
- Preserves as much source-backed content as possible.
- Rewrites the jsonl in place (backup created).

Run after audit. Then re-run audit/validate.

This does bulk mechanical hardening. Manual review still recommended for clinical accuracy per the audit report.
"""

import json
import re
import shutil
from pathlib import Path
from typing import List, Dict, Any

ROOT = Path(__file__).resolve().parents[2]
PAYLOADS_IN = ROOT / "data" / "anatomy" / "case_prep" / "certified_case_prep_payloads.jsonl"

BAD_PATTERNS = [
    r"Key approach for this case per OB and map\?",
    r"Primary structure at risk\?",
    r"Per map evidence",
    r"No free-form guessing",
    r"unknown or uncertain type",
    r"Source-specific attending pimp question from current pipeline content",
    r"Compartment syndrome risk and monitoring in tibial shaft fractures\.",
]

GENERIC = [r"\bkey anatomy\b", r"\bimportant anatomy\b"]

def parse_dictish(item: Any) -> Dict[str, str]:
    if isinstance(item, dict):
        return {k: str(v) for k, v in item.items()}
    if isinstance(item, str):
        s = item.strip()
        if s.startswith("{") and s.endswith("}"):
            s = s.replace("'", '"')
            try:
                return json.loads(s)
            except:
                pass
        return {"raw": s}
    return {"raw": str(item)}

def standardize_sar(item: Any, approach_ctx: str = "") -> Dict[str, Any]:
    d = parse_dictish(item)
    if "raw" in d:
        # Try to salvage
        return {
            "structure": d["raw"][:120],
            "why_at_risk": "",
            "how_to_avoid_injury": "",
            "consequence_of_injury": "",
            "approach_context": approach_ctx,
            "source_refs": []
        }
    return {
        "structure": d.get("structure", d.get("text", ""))[:200],
        "why_at_risk": d.get("why_it_matters", d.get("why_at_risk", "")),
        "how_to_avoid_injury": d.get("how_to_avoid", ""),
        "consequence_of_injury": d.get("consequence", ""),
        "approach_context": approach_ctx or d.get("approach_context", ""),
        "source_refs": [d.get("source_url", "")] if d.get("source_url") else d.get("source_refs", [])
    }

def is_bad(text: str) -> bool:
    t = str(text).lower()
    for p in BAD_PATTERNS + GENERIC:
        if re.search(p, t, re.I):
            return True
    return False

def harden_payload(p: Dict) -> Dict:
    out = dict(p)  # copy
    pid = p.get("procedure_id", "")
    pname = p.get("procedure_name", "")
    # Infer category / approach from id for these
    if "tha_posterior" in pid:
        out["anatomy_category"] = "arthroplasty_approach"
        out["approach_id"] = "posterior_hip"
        out["approach_name"] = "Posterior (Moore/Southern)"
    elif "tha_anterior" in pid:
        out["anatomy_category"] = "arthroplasty_approach"
        out["approach_id"] = "direct_anterior_hip"
        out["approach_name"] = "Direct Anterior (Smith-Petersen)"
    elif "hip_hemi" in pid:
        out["anatomy_category"] = "arthroplasty_approach"
        out["approach_id"] = "lateral_hardinge_hip"
        out["approach_name"] = "Lateral (Hardinge)"
    else:
        out["anatomy_category"] = "open_approach" if "orif" in pid.lower() or "fracture" in pid.lower() else "procedure"
        out["approach_id"] = pid  # for non-approach specific, use procedure
        out["approach_name"] = pname

    out["schema_version"] = "brobot_case_prep_payload_v2"

    # Clean must_know
    mkn = [x for x in p.get("must_know_anatomy", []) if not is_bad(str(x))]
    out["must_know_anatomy"] = mkn[:12]  # cap for usability

    # Standardize structures_at_risk
    sar_in = p.get("structures_at_risk", [])
    sar_out = []
    for item in sar_in:
        if is_bad(str(item)):
            continue
        std = standardize_sar(item, out.get("approach_name", ""))
        if std.get("structure") and len(std["structure"]) > 3:
            sar_out.append(std)
    out["structures_at_risk"] = sar_out

    # surgical_layers: turn surgical_approach_anatomy into structured
    approach_in = p.get("surgical_approach_anatomy", [])
    layers = []
    for i, item in enumerate(approach_in):
        if is_bad(str(item)): continue
        txt = str(item).strip()
        if not txt: continue
        layers.append({
            "layer_name": f"Layer {i+1}" if len(approach_in) > 1 else "Primary surgical interval / exposure",
            "what_user_should_know": txt[:300],
            "key_structures": [],
            "structures_at_risk": [],
            "surgical_relevance": "Approach-specific for this procedure",
            "source_refs": []
        })
    out["surgical_layers"] = layers if layers else p.get("surgical_approach_anatomy", [])

    # Keep other fields but clean obvious bad
    for k in ["attending_pimp_questions", "common_mistakes", "night_before_review_checklist"]:
        if k in out:
            out[k] = [x for x in out[k] if not is_bad(str(x))]

    # Add validation placeholders
    out["validation_warnings"] = []
    out["payload_quality_status"] = "hardened_v2_draft"
    out["source_status"] = "partial" if out.get("source_urls") else "weak"

    return out

def main():
    print("Harden payloads v1 -> v2 (standardized structures, remove bad, add fields)...")
    backup = PAYLOADS_IN.with_suffix(PAYLOADS_IN.suffix + ".pre_harden_v2")
    if not backup.exists():
        shutil.copy(PAYLOADS_IN, backup)
        print("Backup:", backup)

    hardened = []
    with PAYLOADS_IN.open() as f:
        for line in f:
            if line.strip():
                p = json.loads(line)
                hp = harden_payload(p)
                hardened.append(hp)

    with PAYLOADS_IN.open("w") as f:
        for hp in hardened:
            f.write(json.dumps(hp, ensure_ascii=False) + "\n")

    print(f"Rewrote {len(hardened)} payloads to v2 structure in {PAYLOADS_IN}")
    print("Run audit_payloads.py and validate again to check improvement.")

if __name__ == "__main__":
    main()
