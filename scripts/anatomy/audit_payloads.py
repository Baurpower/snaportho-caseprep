#!/usr/bin/env python3
"""
Audit script for production anatomy/case-prep payloads.

Rebalanced philosophy (2026 update):
- MAJOR severity prioritizes clinical usability, approach accuracy, safety, and missing critical structures/layers for the resident night-before case prep product.
- Source issues are usually MINOR (one good URL + item source_refs is acceptable). Source only becomes MAJOR for total lack of provenance, malformed refs on high-risk claims, or certified payload with zero support.
- Report issues are tagged with one of: clinical_usability, approach_accuracy, structures_at_risk_quality, surgical_layers_quality, source_quality, schema_quality, safety_quality.
- Goal: clinically usable, approach-specific, structured payload is PASS even with limited source breadth.

Checks schema, content quality, safety, approach consistency against the target standard.

Run: python scripts/anatomy/audit_payloads.py

Outputs report to stdout and reports/anatomy_payload_audit_report.md
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any

ROOT = Path(__file__).resolve().parents[2]
ANATOMY_PROD = ROOT / "data" / "anatomy"   # currently the prod root; will evolve to /production/
PAYLOADS_PATH = ANATOMY_PROD / "case_prep" / "certified_case_prep_payloads.jsonl"
REGISTRY_PATH = ANATOMY_PROD / "registry" / "procedures.jsonl"
ALIASES_PATH = ANATOMY_PROD / "registry" / "procedure_aliases.jsonl"
CERT_REGISTRY_PATH = ANATOMY_PROD / "registry" / "certification_registry.jsonl"
MODULES_DIR = ANATOMY_PROD / "modules"
SOURCES_PATH = ANATOMY_PROD / "sources" / "orthobullets_sources.jsonl"

# Target schema (v2 proposed, current payloads are v1)
REQUIRED_FIELDS = [
    "schema_version", "procedure_id", "procedure_name", "case_prep_status",
    "procedure_overview", "must_know_anatomy", "structures_at_risk",
    "attending_pimp_questions", "night_before_review_checklist", "source_urls"
]

# Known bad patterns from previous hygiene and common issues
BAD_PATTERNS = [
    r"Key approach for this case per OB and map\?",
    r"Primary structure at risk\?",
    r"Per map evidence",
    r"No free-form guessing",
    r"unknown or uncertain type",
    r"Source-specific attending pimp question from current pipeline content",
    r"Compartment syndrome risk and monitoring in tibial shaft fractures\.",  # example of copy-paste error
]

GENERIC_FILLERS = [
    r"\bimportant anatomy\b", r"\bkey anatomy\b", r"\bcrucial\b", r"\bessential to know\b",
]

def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    items = []
    with path.open() as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items

def load_certified_procedure_ids() -> set:
    try:
        with CERT_REGISTRY_PATH.open() as f:
            data = json.load(f)
        return set(data.get("certified_procedure_ids", []))
    except:
        return set()

def is_structured_dict(item: Any) -> bool:
    if isinstance(item, dict):
        return "structure" in item or "text" in item or "layer_name" in item
    if isinstance(item, str):
        return item.strip().startswith("{") and "structure" in item
    return False

def parse_if_string_dict(item: Any) -> Dict:
    if isinstance(item, dict):
        return item
    if isinstance(item, str):
        s = item.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                # Very loose, since they are often truncated or single-quoted
                s = s.replace("'", '"')
                return json.loads(s)
            except:
                return {"raw": item}
    return {"raw": str(item)}

def audit_payload(payload: Dict, certified_ids: set, all_procs: Dict, modules_index: Dict) -> List[Dict]:
    issues = []
    pid = payload.get("procedure_id", "UNKNOWN")
    pname = payload.get("procedure_name", "")
    is_cert = pid in certified_ids

    is_approach_based = (
        payload.get("anatomy_category") in ("arthroplasty_approach", "open_approach") or
        "approach" in str(pname).lower() or
        "approach" in str(payload.get("approach_name", "")).lower() or
        "tha_" in pid or ("orif" in pid and "humerus" not in pid) or "arthroplasty" in pid or "repair" in pid or "decompression" in pid
    )

    # Schema + core clinical requirements (FAIL for truly broken, MAJOR for missing core clinical)
    for field in REQUIRED_FIELDS:
        if field not in payload or payload[field] in (None, "", [], {}):
            if field in ["procedure_id", "case_prep_status"]:
                sev = "fail"
                cat = "schema_quality"
            elif field in ["must_know_anatomy", "structures_at_risk"]:
                sev = "major"
                cat = "clinical_usability" if field == "must_know_anatomy" else "structures_at_risk_quality"
            else:
                sev = "major"
                cat = "schema_quality"
            issues.append({
                "severity": sev,
                "category": cat,
                "field": field,
                "problem": f"Missing or empty required field '{field}'",
                "suggested_fix": "Populate from modules/sources or mark as limitation."
            })

    schema = payload.get("schema_version", "")
    if not schema or "v1" not in str(schema).lower():
        issues.append({
            "severity": "minor",
            "category": "schema_quality",
            "field": "schema_version",
            "problem": f"Old or missing schema_version: {schema}",
            "suggested_fix": "Bump to brobot_case_prep_payload_v2 and migrate structure."
        })

    # Structures at risk
    sar = payload.get("structures_at_risk", []) or []
    structured_sar_count = 0
    for i, item in enumerate(sar):
        d = parse_if_string_dict(item)
        if "raw" in d or not d.get("structure"):
            issues.append({
                "severity": "major",
                "category": "structures_at_risk_quality",
                "field": "structures_at_risk",
                "problem": f"Item {i} is not structured or missing 'structure' key: {str(item)[:80]}",
                "suggested_fix": "Convert to dict with structure, why_at_risk, how_to_avoid_injury, consequence_of_injury, approach_context, source_refs."
            })
        else:
            structured_sar_count += 1
            if not d.get("why_it_matters") and not d.get("why_at_risk"):
                issues.append({"severity": "minor", "category": "safety_quality", "field": "structures_at_risk",
                               "problem": f"Structure '{d.get('structure')}' lacks why_at_risk / consequence.",
                               "suggested_fix": "Add explanation and consequence."})

    if is_approach_based and structured_sar_count == 0:
        issues.append({
            "severity": "major",
            "category": "structures_at_risk_quality",
            "field": "structures_at_risk",
            "problem": "Empty or non-meaningful structures_at_risk for approach-based procedure.",
            "suggested_fix": "Add >=3 rich SAR entries (structure, why_at_risk, how_to_avoid_injury, consequence_of_injury, approach_context, source_refs) from modules."
        })

    # must_know_anatomy (clinical_usability focus)
    mkn = payload.get("must_know_anatomy", []) or []
    usable_count = 0
    for item in mkn:
        s = str(item)
        low = s.lower()
        if len(s) > 25 and not any(re.search(pat, low, re.I) for pat in BAD_PATTERNS + GENERIC_FILLERS):
            usable_count += 1

    if usable_count == 0:
        sev = "major" if len(mkn) > 0 else "major"
        issues.append({
            "severity": sev,
            "category": "clinical_usability",
            "field": "must_know_anatomy",
            "problem": f"Empty or unusable must_know_anatomy ({len(mkn)} raw items, {usable_count} high-yield after filtering generics/placeholders).",
            "suggested_fix": "Replace with 5+ specific, approach- or procedure-specific facts a resident can use the night before (what is exposed/protected/avoided + consequence)."
        })
    elif usable_count < 5:
        issues.append({
            "severity": "minor",
            "category": "clinical_usability",
            "field": "must_know_anatomy",
            "problem": f"Only {usable_count} high-yield must-know items (short but usable sections are MINOR).",
            "suggested_fix": "Add more specific high-yield items if available from modules; short usable is acceptable."
        })

    for i, item in enumerate(mkn):
        s = str(item).lower()
        for pat in BAD_PATTERNS:
            if re.search(pat, s, re.I):
                issues.append({"severity": "fail", "category": "clinical_usability", "field": "must_know_anatomy",
                               "problem": f"Contains legacy placeholder: {pat} at item {i}",
                               "suggested_fix": "Remove or replace with source-backed fact."})

    # surgical_approach_anatomy vs procedure
    approach_anat = payload.get("surgical_approach_anatomy", [])
    if "tha_posterior" in pid or "tha_anterior" in pid:
        # Check for mismatch
        text = " ".join(str(x) for x in approach_anat + mkn).lower()
        if "direct lateral" in text and "posterior" not in pid:
            issues.append({"severity": "major", "category": "approach_accuracy",
                           "field": "surgical_approach_anatomy",
                           "problem": "Posterior THA payload contains prominent direct lateral (Hardinge) content.",
                           "suggested_fix": "Keep approach-specific; reference shared modules for common hip anatomy."})

    # === NEW CORRUPTION DETECTORS (Task 3) - prevent tha_posterior-style corruption from passing ===
    full_edu_text = " ".join([
        json.dumps(payload.get("must_know_anatomy", [])),
        json.dumps(payload.get("structures_at_risk", [])),
        json.dumps(payload.get("surgical_layers", [])),
        json.dumps(payload.get("attending_pimp_questions", [])),
        json.dumps(payload.get("surgical_approach_anatomy", [])),
        json.dumps(payload.get("key_landmarks", [])),
        json.dumps(payload.get("common_mistakes", [])),
    ])

    # A. Stringified object corruption (MAJOR)
    stringified_patterns = [r"\{'structure'", r"\{'text'", r"\{'landmark'", r"\{'structure':\s*\{", r"'structure':\s*'\{'"]
    for pat in stringified_patterns:
        if re.search(pat, full_edu_text, re.I):
            issues.append({
                "severity": "major",
                "category": "clinical_usability",
                "field": "various",
                "problem": "Stringified dict corruption detected in educational fields (e.g. {'structure': '{...} or similar).",
                "suggested_fix": "Rebuild lists from clean source-backed strings or properly structured dicts. Remove any JSON-string artifacts from prior synthesis."
            })
            break

    # B. Truncated / cut-off content (MAJOR)
    truncated_indicators = [
        r"ends with t(?!\w)", r"ends with glu(?!\w)", r"ends with moo(?!\w)", r"ends with ap(?!\w)",
        r"glu\s*$", r"moo\s*$", r"ap\s*$", r"t\s*$",
        r"\{[^}]*$",  # unmatched open brace at end
    ]
    for item in payload.get("must_know_anatomy", []) + payload.get("structures_at_risk", []) + payload.get("surgical_layers", []):
        s = str(item)
        if len(s) > 5:
            low_s = s.lower().rstrip()
            if any(re.search(ind, low_s) for ind in truncated_indicators) or (low_s.endswith("t") and len(low_s) > 10 and not low_s[-2].isalpha()):
                issues.append({
                    "severity": "major",
                    "category": "clinical_usability",
                    "field": "various",
                    "problem": f"Truncated or cut-off content detected: '{s[-30:]}' (incomplete word or unmatched structure).",
                    "suggested_fix": "Replace with complete, source-backed sentences from modules or OB pages. Do not use truncated synthesis output."
                })
                break

    # C. Approach contamination (FAIL/MAJOR for known approach payloads)
    if pid == "tha_posterior":
        contamination_terms = ["hardinge", "direct lateral", "transgluteal", "tfl", "sartorius", "rectus", "lister", "epl", "distal radius"]
        edu_lower = full_edu_text.lower()
        found = [term for term in contamination_terms if term in edu_lower]
        if found:
            issues.append({
                "severity": "fail",
                "category": "approach_accuracy",
                "field": "various",
                "problem": f"tha_posterior contains non-posterior contamination terms in educational fields: {found}. Posterior payload must not include Hardinge, anterior, or distal radius anatomy except in explicit 'not this approach' validation warnings.",
                "suggested_fix": "Rebuild tha_posterior from 12023 Moore/Southern posterior-only facts only. Move any comparison language to validation_warnings or approach_specific_notes as 'not applicable'."
            })

    if pid == "tha_anterior":
        contamination_terms = ["hardinge", "posterior", "moore", "southern", "short external rotators", "piriformis", "obturator internus", "sciatic"]
        edu_lower = full_edu_text.lower()
        found = [term for term in contamination_terms if term in edu_lower]
        if found:
            issues.append({
                "severity": "fail",
                "category": "approach_accuracy",
                "field": "various",
                "problem": f"tha_anterior contains non-anterior contamination: {found}.",
                "suggested_fix": "Keep strictly direct anterior (TFL/sartorius/rectus/LFCN/LFCA). Move posterior comparisons to validation_warnings only."
            })

    # D. Empty SAR fields (upgrade to MAJOR for approach-based)
    sar = payload.get("structures_at_risk", []) or []
    for i, item in enumerate(sar):
        d = parse_if_string_dict(item)
        if d.get("structure"):
            if not d.get("why_at_risk") and not d.get("why_it_matters"):
                issues.append({
                    "severity": "major",
                    "category": "structures_at_risk_quality",
                    "field": "structures_at_risk",
                    "problem": f"SAR item {i} has empty why_at_risk / how_to_avoid_injury / consequence_of_injury.",
                    "suggested_fix": "Provide full 6-field rich SAR (structure, why_at_risk, how_to_avoid_injury, consequence_of_injury, approach_context, source_refs)."
                })

    # E. Placeholder layers (MAJOR)
    layers = payload.get("surgical_layers", []) or []
    for i, l in enumerate(layers):
        name = str(l.get("layer_name", "")).strip().lower()
        content = str(l.get("what_user_should_know", "") + " " + str(l.get("surgical_relevance", ""))).lower()
        if name in ["layer 1", "layer 2", "layer 3", "primary surgical interval / exposure"] and ("see linked" in content or "key approach for this case" in content or len(content) < 40):
            issues.append({
                "severity": "major",
                "category": "surgical_layers_quality",
                "field": "surgical_layers",
                "problem": f"Layer {i} is a placeholder ('{name}') with generic/empty content.",
                "suggested_fix": "Replace with 3+ meaningful structured layers (layer_name, what_user_should_know, key_structures, structures_at_risk, surgical_relevance, source_refs) from approach modules."
            })

    # F. Local development source URLs (MINOR, or MAJOR if in top-level source_urls for certified)
    srcs = payload.get("source_urls", []) or []
    local_dev = [s for s in srcs if "data/approach_playbook" in str(s) or "data/upper_extremity" in str(s) or "data/lower_extremity" in str(s) or ("data/" in str(s) and "orthobullets" not in str(s).lower())]
    if local_dev:
        sev = "major" if is_cert else "minor"
        issues.append({
            "severity": sev,
            "category": "source_quality",
            "field": "source_urls",
            "problem": f"Local development file paths in source_urls: {local_dev[:2]}.",
            "suggested_fix": "Replace with public Orthobullets URLs only. Internal data/ paths may be referenced in item source_refs but not as top-level source_urls for certified payloads."
        })

    # surgical_layers_quality (new emphasis for open/approach-based procedures)
    layers = payload.get("surgical_layers", []) or []
    meaningful_layers = 0
    for l in layers:
        d = parse_if_string_dict(l)
        txt = str(d.get("what_user_should_know", "")) + " " + str(d.get("surgical_relevance", "")) + " " + str(d.get("layer_name", ""))
        if len(txt) > 30 and not any(b in txt.lower() for b in ["key approach for this case", "primary structure", "see linked", "essential palpable"]):
            meaningful_layers += 1

    is_approach_based = (
        payload.get("anatomy_category") in ("arthroplasty_approach", "open_approach") or
        "approach" in str(payload.get("procedure_name", "")).lower() or
        "approach" in str(payload.get("approach_name", "")).lower() or
        "tha_" in pid or ("orif" in pid and "humerus" not in pid) or "arthroplasty" in pid or "repair" in pid or "decompression" in pid
    )
    if is_approach_based and meaningful_layers < 3:
        issues.append({
            "severity": "major",
            "category": "surgical_layers_quality",
            "field": "surgical_layers",
            "problem": f"Only {meaningful_layers} meaningful surgical_layers for approach-based procedure (expected >=3 structured entries with what_user_should_know, key_structures, structures_at_risk, source_refs).",
            "suggested_fix": "Add or expand surgical_layers from approach modules (layer_name, what_user_should_know, key_structures, structures_at_risk, surgical_relevance, source_refs). Add validation_warning if legitimately thin (e.g. percutaneous-dominant)."
        })

    # source_quality (rebalanced: one good URL + item-level source_refs is acceptable for clinical usability)
    srcs = payload.get("source_urls", []) or []
    has_item_provenance = False
    for sec in ["structures_at_risk", "surgical_layers", "must_know_anatomy"]:
        for item in payload.get(sec, []) or []:
            d = parse_if_string_dict(item)
            refs = d.get("source_refs") or d.get("source_url") or d.get("source_urls")
            if refs:
                if isinstance(refs, (list, tuple)) and any(refs):
                    has_item_provenance = True
                elif refs:
                    has_item_provenance = True
                break
        if has_item_provenance:
            break

    if not srcs and not has_item_provenance:
        issues.append({
            "severity": "major",
            "category": "source_quality",
            "field": "source_urls",
            "problem": "No provenance anywhere (no source_urls and no item-level source_refs).",
            "suggested_fix": "Add at least primary OB source URL and/or source_refs on high-yield items; or add validation_warning explaining limitation."
        })
    elif len(srcs) < 2 or not srcs:
        # Low diversity or single URL is acceptable if item refs or one clean primary exists
        issues.append({
            "severity": "minor",
            "category": "source_quality",
            "field": "source_urls",
            "problem": f"Low source diversity ({len(srcs)} URL(s)); item-level source_refs provide support.",
            "suggested_fix": "Add additional primary sources if available; otherwise acceptable for clinically usable payload."
        })
    # Note: we no longer auto-MAJOR on <2 URLs. Source only MAJOR for zero provenance on certified payloads or high-risk unsupported claims.

    # procedure_overview
    ov = payload.get("procedure_overview", "")
    if "certified" not in ov.lower() and is_cert:
        issues.append({"severity": "minor", "category": "schema_quality",
                       "field": "procedure_overview",
                       "problem": "Overview does not clearly state certified status and version.",
                       "suggested_fix": "Update to include 'Certified. Source-backed from vX.'"})

    # Check for generic filler (clinical_usability)
    full_text = json.dumps(payload).lower()
    for filler in GENERIC_FILLERS:
        if re.search(filler, full_text):
            issues.append({"severity": "minor", "category": "clinical_usability",
                           "field": "various",
                           "problem": f"Contains generic filler pattern: {filler}",
                           "suggested_fix": "Replace with specific, actionable fact for this case/approach."})

    return issues

def main():
    print("=== Anatomy Payload Audit ===\n")
    certified_ids = load_certified_procedure_ids()
    procs = {p["procedure_id"]: p for p in load_jsonl(REGISTRY_PATH)}
    aliases = load_jsonl(ALIASES_PATH)
    payloads = load_jsonl(PAYLOADS_PATH)

    # Simple modules index for cross check (procedure_ids used_by)
    modules_index = {}
    for mf in MODULES_DIR.glob("*.jsonl"):
        for m in load_jsonl(mf):
            for pid in m.get("used_by_procedure_ids", []):
                modules_index.setdefault(pid, []).append(m.get("module_id"))

    all_issues = []
    for p in payloads:
        pid = p.get("procedure_id")
        issues = audit_payload(p, certified_ids, procs, modules_index)
        for iss in issues:
            iss["procedure_id"] = pid
            iss["payload_path"] = str(PAYLOADS_PATH)
            all_issues.append(iss)

    # Group by severity and by new output category for separation of concerns
    by_sev = {"fail": [], "major": [], "minor": [], "pass": []}
    by_cat = {c: [] for c in ["clinical_usability", "approach_accuracy", "structures_at_risk_quality",
                               "surgical_layers_quality", "source_quality", "schema_quality", "safety_quality"]}
    for iss in all_issues:
        sev = iss.get("severity", "minor")
        by_sev.setdefault(sev, []).append(iss)
        cat = iss.get("category", "clinical_usability")
        by_cat.setdefault(cat, []).append(iss)

    print(f"Total issues found: {len(all_issues)} across {len(payloads)} payloads")
    print(f"  FAIL: {len(by_sev['fail'])}, MAJOR: {len(by_sev['major'])}, MINOR: {len(by_sev.get('minor',[]))}")
    print()

    # Summary by output category (source separated from clinical)
    print("=== Issues by output category ===")
    for c in ["clinical_usability", "approach_accuracy", "structures_at_risk_quality", "surgical_layers_quality",
              "source_quality", "schema_quality", "safety_quality"]:
        cnt = len(by_cat.get(c, []))
        if cnt:
            print(f"  {c}: {cnt}")
    print()

    # Print summary report - clinical/approach/safety first, source last
    priority_sevs = ["fail", "major"]
    for sev in priority_sevs:
        if not by_sev.get(sev): continue
        print(f"=== {sev.upper()} issues ===")
        # prefer non-source for visibility
        non_source = [iss for iss in by_sev[sev] if iss.get("category") != "source_quality"]
        source_only = [iss for iss in by_sev[sev] if iss.get("category") == "source_quality"]
        for iss in (non_source + source_only)[:15]:
            print(f"  {iss['procedure_id']}: [{iss['category']}] {iss['problem']}")
            print(f"    -> {iss['suggested_fix']}")
        if len(by_sev[sev]) > 15:
            print(f"  ... and {len(by_sev[sev])-15} more")
        print()

    # Write full report (source_quality separated from clinical usability etc.)
    report_path = ROOT / "reports" / "anatomy_payload_audit_report.md"
    with report_path.open("w") as f:
        f.write("# Anatomy Payload Audit Report\n\n")
        f.write(f"Payloads audited: {len(payloads)}\n")
        f.write(f"Issues: {len(all_issues)}\n")
        f.write(f"FAIL: {len(by_sev['fail'])}, MAJOR: {len(by_sev['major'])}, MINOR: {len(by_sev.get('minor',[]))}\n\n")

        f.write("## Issues by output category (source separated from clinical usability)\n\n")
        for c in ["clinical_usability", "approach_accuracy", "structures_at_risk_quality", "surgical_layers_quality",
                  "source_quality", "schema_quality", "safety_quality"]:
            cnt = len(by_cat.get(c, []))
            if cnt:
                f.write(f"- **{c}**: {cnt}\n")
        f.write("\n")

        f.write("## Detailed issues\n\n")
        for iss in all_issues:
            f.write(f"- **{iss['procedure_id']}** | {iss['severity'].upper()} | {iss['category']}\n")
            f.write(f"  Problem: {iss['problem']}\n")
            f.write(f"  Fix: {iss['suggested_fix']}\n\n")
    print(f"Full report written to {report_path}")

if __name__ == "__main__":
    main()
