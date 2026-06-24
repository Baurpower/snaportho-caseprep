#!/usr/bin/env python3
"""
End-to-end CasePrep output QA for resident inputs.
Focuses on the certified short-circuit path (the final user-facing for supported cases).

Run: python scripts/anatomy/caseprep_e2e_qa.py

It:
- Calls resolve_procedure on real prompts
- If certified, loads and inspects the brobot_case_prep v2 payload returned in the response shape
- Evaluates per Task 2 criteria
- Checks for v2 fields (Task 3)
- Has snapshot/assert tests (Task 4)
- Can be called from smoke

Does not require full server or external APIs for the core certified path analysis.
"""

import os
import sys
import json
import io
import contextlib
import re
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from procedure_registry import resolve_procedure, is_certified, CERTIFIED_SLUGS

ANATOMY = ROOT / "data" / "anatomy"
CERT_PAYLOADS_PATH = ANATOMY / "case_prep" / "certified_case_prep_payloads.jsonl"

LEGACY_BAD = ["Per map evidence", "Primary structure at risk?", "Key approach for this case", "No free-form guessing", "unknown or uncertain type"]

def load_certified() -> Dict[str, Dict]:
    payloads = {}
    with CERT_PAYLOADS_PATH.open() as f:
        for line in f:
            if line.strip():
                p = json.loads(line)
                payloads[p["procedure_id"]] = p
    return payloads

CERTIFIED = load_certified()

def contains_legacy(text: str) -> bool:
    return any(bad in text for bad in LEGACY_BAD)

def get_v2_fields(payload: Dict) -> Dict[str, bool]:
    return {
        "has_surgical_layers": bool(payload.get("surgical_layers")),
        "has_structures_at_risk": bool(payload.get("structures_at_risk")),
        "has_danger_zones": bool(payload.get("danger_zones")),
        "has_common_pimp_questions": bool(payload.get("common_pimp_questions") or payload.get("attending_pimp_questions")),
        "has_validation_warnings": bool(payload.get("validation_warnings")),
        "has_source_status": bool(payload.get("source_status")),
        "has_payload_quality_status": bool(payload.get("payload_quality_status")),
        "has_approach_specific_notes": bool(payload.get("approach_specific_notes")),
        "has_must_know_anatomy": bool(payload.get("must_know_anatomy")),
    }

def evaluate_output_quality(prompt: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate per Task 2."""
    res = data.get("resolver") or {}
    slug = res.get("procedure_slug") or data.get("anatomy", {}).get("procedure_id")
    anatomy = data.get("anatomy") or {}
    payload = anatomy.get("payload") or data.get("brobot_case_prep") or {}
    is_cert = bool(payload and payload.get("case_prep_status") == "certified")
    used_fallback = "unsupported" in str(anatomy.get("mode", "")) or not is_cert
    ambiguity_handled = "suggestedMatches" in data or res.get("match_method") == "none" or "clarify" in str(data.get("reason", "")).lower()

    v2 = get_v2_fields(payload)

    # size
    payload_str = json.dumps(payload)
    size = len(payload_str)
    if size < 2000:
        size_note = "too_sparse"
    elif size > 15000:
        size_note = "too_verbose"
    else:
        size_note = "well_sized"

    no_false_certainty = not used_fallback or "suggested" in str(data).lower() or "Could not confidently" in str(data.get("retrievalSummary", {}).get("warning", ""))

    return {
        "resolved_slug": slug,
        "certified_payload_used": is_cert,
        "used_fallback": used_fallback,
        "ambiguity_handled_correctly": ambiguity_handled,
        "has_surgical_layers": v2["has_surgical_layers"],
        "has_structures_at_risk": v2["has_structures_at_risk"],
        "has_danger_zones": v2["has_danger_zones"],
        "has_common_pimp_questions": v2["has_common_pimp_questions"],
        "size": size_note,
        "avoids_false_certainty": no_false_certainty,
        "no_legacy": not contains_legacy(payload_str) if payload else True,
        "v2_fields": v2,
    }

def simulate_certified_response(prompt: str) -> Dict[str, Any]:
    """Simulate the certified short-circuit response shape from main.py /case-prep."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        resolved = resolve_procedure(prompt)
    logs = buf.getvalue()

    slug = resolved.get("procedure_slug")
    if slug and slug in CERTIFIED:
        payload = CERTIFIED[slug]
        # Minimal caseprep simulation (pimp etc would come from other pipeline)
        caseprep_sim = {
            "pimpQuestions": payload.get("attending_pimp_questions", [])[:5] or payload.get("common_pimp_questions", [])[:5],
            "otherUsefulFacts": [],
        }
        return {
            **caseprep_sim,
            "anatomy": {
                "mode": "certified_case_prep_payload",
                "procedure_id": slug,
                "procedure_name": payload.get("procedure_name"),
                "case_prep_status": "certified",
                "payload": payload,
                "resolver": {
                    "match_method": resolved.get("match_method"),
                    "match_score": resolved.get("match_score"),
                },
            },
            "brobot_case_prep": payload,
            "resolver": resolved,  # top level for convenience
        }
    else:
        # unsupported shape
        suggested = resolved.get("suggested_matches", [])
        return {
            "pimpQuestions": [],
            "otherUsefulFacts": [f"Anatomy case prep is still being improved for this procedure. Suggested: {suggested}"],
            "anatomy": {
                "mode": "unsupported_case",
                "procedure_id": slug or "unknown",
                "suggestedMatches": suggested,
            },
            "brobot_case_prep": None,
            "resolver": resolved,
        }

# The list from the query
TEST_PROMPTS = [
    "72 yo undergoing posterior THA tomorrow",
    "direct anterior THA",
    "SCFE pinning",
    "supracondylar humerus CRPP",
    "hallux valgus correction",
    "total shoulder arthroplasty",
    "posterior lumbar decompression fusion",
    "distal radius ORIF",
    "meniscus repair",
    "posterior wall acetabulum ORIF",
    "peds elbow fracture",
    "reverse shoulder",
    "Hardinge THA",
]

def run_e2e_qa():
    print("=== SnapOrtho CasePrep End-to-End Output QA ===\n")
    results = []
    for prompt in TEST_PROMPTS:
        print(f"--- Prompt: {prompt} ---")
        try:
            data = simulate_certified_response(prompt)
            eval_res = evaluate_output_quality(prompt, data)
            results.append({"prompt": prompt, "eval": eval_res, "data": data})
            print(f"  resolved: {eval_res['resolved_slug']}")
            print(f"  certified: {eval_res['certified_payload_used']}, fallback: {eval_res['used_fallback']}")
            print(f"  ambiguity handled: {eval_res['ambiguity_handled_correctly']}")
            print(f"  surgical_layers: {eval_res['has_surgical_layers']}, SAR: {eval_res['has_structures_at_risk']}, danger_zones: {eval_res['has_danger_zones']}, pimp: {eval_res['has_common_pimp_questions']}")
            print(f"  size: {eval_res['size']}, no_legacy: {eval_res['no_legacy']}, avoids_false_certainty: {eval_res['avoids_false_certainty']}")
            # v2 shape check
            v2 = eval_res["v2_fields"]
            print(f"  v2 fields present: surgical_layers={v2['has_surgical_layers']}, structured_SAR={v2['has_structures_at_risk']}, validation_warnings={v2['has_validation_warnings']}, source_status={v2['has_source_status']}, quality_status={v2['has_payload_quality_status']}, approach_notes={v2['has_approach_specific_notes']}")
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"prompt": prompt, "error": str(e)})

    # Task 4 snapshot/asserts
    print("\n=== Snapshot / Assertion Tests (Task 4) ===")
    snapshot_passed = 0
    snapshot_failed = 0
    for r in results:
        if "error" in r: continue
        p = r["data"].get("brobot_case_prep") or r["data"].get("anatomy", {}).get("payload")
        if not p: 
            print(f"FAIL snapshot for {r['prompt']}: no payload")
            snapshot_failed += 1
            continue
        checks = [
            ("procedure_id", bool(p.get("procedure_id"))),
            ("procedure_name", bool(p.get("procedure_name"))),
            ("must_know_anatomy", bool(p.get("must_know_anatomy"))),
            ("surgical_layers", bool(p.get("surgical_layers"))),
            ("structures_at_risk", bool(p.get("structures_at_risk"))),
            ("danger_zones", bool(p.get("danger_zones"))),
            ("common_pimp_questions or attending", bool(p.get("common_pimp_questions") or p.get("attending_pimp_questions"))),
            ("no legacy", not contains_legacy(json.dumps(p))),
        ]
        # also check no wrong approach contamination for known cases (simple heuristic)
        payload_text = json.dumps(p).lower()
        contamination = False
        if "tha_anterior" in r.get("eval", {}).get("resolved_slug", "") and ("hardinge" in payload_text or "posterior" in payload_text and "direct anterior" not in payload_text):
            contamination = True
        if "tha_posterior" in r.get("eval", {}).get("resolved_slug", "") and "direct lateral" in payload_text and "posterior" not in r["prompt"].lower():
            contamination = True
        checks.append(("no obvious approach contamination", not contamination))

        all_ok = all(c[1] for c in checks)
        if all_ok:
            snapshot_passed += 1
            print(f"PASS: {r['prompt'][:40]}")
        else:
            snapshot_failed += 1
            print(f"FAIL: {r['prompt'][:40]}")
            for name, ok in checks:
                if not ok: print(f"  - {name}")

    print(f"\nSnapshot asserts: {snapshot_passed} passed, {snapshot_failed} failed")

    # Overall
    good = sum(1 for r in results if r.get("eval", {}).get("certified_payload_used") and r.get("eval", {}).get("no_legacy") and r.get("eval", {}).get("avoids_false_certainty"))
    print(f"\n=== E2E QA SUMMARY: {good}/{len([r for r in results if 'eval' in r])} certified cases looked good and safe ===")

    # === Task 4 / regression: explicit tha_posterior corruption detectors ===
    print("\n=== tha_posterior specific corruption regression checks ===")
    tha_p = CERTIFIED.get("tha_posterior")
    if tha_p:
        tha_txt = json.dumps(tha_p).lower()
        edu_txt = " ".join([
            json.dumps(tha_p.get("must_know_anatomy", [])),
            json.dumps(tha_p.get("structures_at_risk", [])),
            json.dumps(tha_p.get("surgical_layers", [])),
            json.dumps(tha_p.get("attending_pimp_questions", [])),
            json.dumps(tha_p.get("surgical_approach_anatomy", [])),
            json.dumps(tha_p.get("key_landmarks", [])),
        ]).lower()

        tha_checks = [
            ("no Hardinge/direct lateral in edu fields", "hardinge" not in edu_txt and "direct lateral" not in edu_txt),
            ("no anterior TFL/sartorius/rectus in edu fields", "tfl" not in edu_txt and "sartorius" not in edu_txt and "rectus" not in edu_txt),
            ("no distal radius/Lister/EPL in edu fields", "lister" not in edu_txt and "epl" not in edu_txt and "distal radius" not in edu_txt),
            ("no stringified dicts in edu fields", not re.search(r"\{'structure'", edu_txt) and not re.search(r"\{'text'", edu_txt)),
            ("source_urls are clean (no data/approach_playbook or upper/lower dev paths)", all("orthobullets.com" in str(s) and "data/" not in str(s) for s in tha_p.get("source_urls", []))),
            ("no placeholder Layer 1/2/3 surgical_layers", not any(str(l.get("layer_name","")).lower() in ["layer 1","layer 2","layer 3"] for l in tha_p.get("surgical_layers", []))),
            ("SAR items have why_at_risk", all((s.get("why_at_risk") or s.get("why_it_matters")) for s in tha_p.get("structures_at_risk", []) if isinstance(s, dict) and s.get("structure"))),
        ]
        tha_pass = 0
        for name, ok in tha_checks:
            if ok:
                tha_pass += 1
                print(f"PASS: {name}")
            else:
                print(f"FAIL: {name}")
        print(f"tha_posterior regression: {tha_pass}/{len(tha_checks)} checks passed")
    else:
        print("tha_posterior not found in certified payloads")


    # === Batch 1 regression guards (added for tha_anterior, hip_hemi, distal_radius, total_shoulder, reverse_shoulder) ===
    print("\n=== Batch 1 fixed-payload regression guards ===")
    batch1_pass = 0
    batch1_total = 0

    # tha_anterior: no hardinge/posterior/short ER/sciatic/Perthes in educational fields (must_know/SAR/layers/pimp/danger/landmarks/approach/mistakes)
    tha_ant = CERTIFIED.get("tha_anterior")
    if tha_ant:
        edu = json.dumps([tha_ant.get("must_know_anatomy", []), tha_ant.get("structures_at_risk", []), tha_ant.get("surgical_layers", []), tha_ant.get("attending_pimp_questions", []), tha_ant.get("danger_zones", []), tha_ant.get("key_landmarks", []), tha_ant.get("common_mistakes", []), tha_ant.get("surgical_approach_anatomy", [])]).lower()
        batch1_total += 1
        bad = [t for t in ["hardinge", "posterior", "short external", "sciatic", "perthes"] if t in edu]
        if not bad:
            batch1_pass += 1
            print("PASS: tha_anterior - no posterior/Hardinge/Perthes contamination in edu fields")
        else:
            print(f"FAIL: tha_anterior still has contamination: {bad}")

    # hip_hemi: focused on Hardinge, no full posterior mix in edu, no Layer 1 placeholders
    hemi = CERTIFIED.get("hip_hemiarthroplasty")
    if hemi:
        edu = json.dumps([hemi.get("must_know_anatomy", []), hemi.get("surgical_layers", []), hemi.get("structures_at_risk", [])]).lower()
        layers = hemi.get("surgical_layers", [])
        batch1_total += 1
        if "hardinge" in edu and "posterior (moore" not in edu and not any(str(l.get("layer_name","")).lower() in ["layer 1","layer 2","layer 3"] for l in layers):
            batch1_pass += 1
            print("PASS: hip_hemi - Hardinge focus, no placeholder layers, limited posterior mix")
        else:
            print("FAIL: hip_hemi - mixed or placeholder issues remain")

    # distal_radius: no hip/THA/Hardinge terms in edu, no local dev srcs, SAR are proper dicts with why_at_risk/how/conseq filled (no stringified/empty sub)
    dr = CERTIFIED.get("distal_radius_fracture_orif")
    if dr:
        edu = json.dumps([dr.get("must_know_anatomy", []), dr.get("structures_at_risk", []), dr.get("surgical_layers", [])]).lower()
        srcs = dr.get("source_urls", [])
        sar = dr.get("structures_at_risk", [])
        batch1_total += 1
        has_forbidden = any(x in edu for x in ["hardinge", "tha ", "posterior (moore", "sciatic"])
        has_dev = any("data/" in str(s) for s in srcs)
        # stringified only if a SAR item itself is a bad string (not the serialized form of good dicts)
        has_string_in_sar = any(isinstance(s, str) and (s.strip().startswith("{") or "{'structure" in s[:20] or "{\"structure" in s[:20]) for s in sar)
        sar_ok = all(isinstance(s, dict) and bool(s.get("why_at_risk")) and bool(s.get("how_to_avoid_injury")) and bool(s.get("consequence_of_injury")) for s in sar) if sar else False
        if not has_forbidden and not has_dev and not has_string_in_sar and sar_ok:
            batch1_pass += 1
            print("PASS: distal_radius - no forbidden cross terms, no dev srcs, no stringified, proper filled SAR dicts")
        else:
            print(f"FAIL: distal_radius - forbidden={has_forbidden}, dev={has_dev}, string_in_sar={has_string_in_sar}, sar_ok={sar_ok}")

    # total_shoulder: strictly deltopectoral, no RSA/lateral mix (check separation phrase)
    tsa = CERTIFIED.get("total_shoulder_arthroplasty")
    if tsa:
        notes = str(tsa.get("approach_specific_notes", ""))
        batch1_total += 1
        if "Strictly deltopectoral" in notes or ("deltopectoral" in notes.lower() and "no rsa" in notes.lower()):
            batch1_pass += 1
            print("PASS: total_shoulder - strictly deltopectoral, no RSA mix")
        else:
            print("FAIL: total_shoulder - cross-contamination with RSA/lateral")

    # reverse_shoulder: has proper layers (not Layer 1), delto focus, no TSA mix
    rsa = CERTIFIED.get("reverse_shoulder_arthroplasty")
    if rsa:
        layers = rsa.get("surgical_layers", [])
        notes = str(rsa.get("approach_specific_notes", "")).lower()
        batch1_total += 1
        if not any(str(l.get("layer_name","")).lower() in ["layer 1","layer 2","layer 3"] for l in layers) and "deltopectoral" in notes and "anatomic tsa" not in notes:
            batch1_pass += 1
            print("PASS: reverse_shoulder - proper layers, delto focus, no TSA mix")
        else:
            print("FAIL: reverse_shoulder - placeholder layers or cross-contamination")

    print(f"Batch 1 guards: {batch1_pass}/{batch1_total} passed")

    # === Batch 2 regression guards (improved with field-aware helpers) ===
    print("\n=== Batch 2 fixed-payload regression guards ===")

    def get_educational_text(payload):
        """Concat only primary educational content. Explicitly excludes validation_warnings,
        approach_specific_notes, limitations, source_urls, and schema fields so that
        explanatory text and source notes do not trigger cross-contamination checks."""
        keys = [
            "must_know_anatomy",
            "surgical_approach_anatomy",
            "structures_at_risk",
            "surgical_layers",
            "danger_zones",
            "attending_pimp_questions",
            "key_landmarks",
            "common_mistakes",
        ]
        parts = []
        for k in keys:
            v = payload.get(k, [])
            parts.append(json.dumps(v))
        return " ".join(parts).lower()

    def contains_forbidden_terms(text, forbidden, allowed_contexts=None):
        """Return True if any forbidden term appears as a whole word/token outside of allowed context phrases.
        Uses word boundaries to avoid TOKENIZATION_BUGs like 'hip' inside 'relationships' or 'tha' inside 'TKA'."""
        if allowed_contexts is None:
            allowed_contexts = []
        for f in forbidden:
            # word boundary match for the term
            pattern = r'\b' + re.escape(f) + r'\b'
            if re.search(pattern, text):
                # allow if the occurrence is inside one of the allowed context phrases
                allowed = False
                for ctx in allowed_contexts:
                    if ctx in text:
                        # crude but sufficient: if the forbidden appears near the allowed phrase we tolerate
                        # (for meniscus-root ACL etc.)
                        if text.find(f) - text.find(ctx) < 80 and text.find(ctx) - text.find(f) < 80:
                            allowed = True
                if not allowed:
                    return True
        return False

    def instrument_forbidden_match(payload, forbidden_list, guard_name):
        """For diagnosis: search per educational field (not blob) and print exact match details
        including field path, term, matched substring (the f), char offset in the field's text, 80-char context.
        Called only on failure to avoid noise."""
        pid = payload.get("procedure_id", "unknown")
        edu_keys = [
            "must_know_anatomy", "surgical_approach_anatomy", "structures_at_risk",
            "surgical_layers", "danger_zones", "attending_pimp_questions",
            "key_landmarks", "common_mistakes"
        ]
        for k in edu_keys:
            v = payload.get(k, [])
            field_text = json.dumps(v).lower()
            for f in forbidden_list:
                if f in field_text:
                    idx = field_text.find(f)
                    start = max(0, idx - 40)
                    end = min(len(field_text), idx + len(f) + 40)
                    context = field_text[start:end]
                    print(f"payload={pid} guard={guard_name} term={f} matched_substring={f} offset={idx} context=\"...{context}...\" field={k}")
                    # also check for the extra standalone logic if relevant
                    if "acl reconstruction" in field_text and "root" not in field_text and "meniscus" not in field_text:
                        print(f"payload={pid} guard={guard_name} term=acl reconstruction (standalone) matched_substring=acl reconstruction offset={field_text.find('acl reconstruction')} field={k}")

    def assert_no_stringified_objects(payload):
        """Only flag when a *string leaf* inside educational fields contains an old synthesis
        stringified-dict literal (e.g. "{'structure': '...'"). Proper dicts for SAR/layers are
        desired and must not trigger this check."""
        def walk(v):
            if isinstance(v, str):
                for p in ["{'structure", "{\"structure", "{'text", "{\"text", "{'landmark", "{\"landmark", "{'structure", "{\"structure"]:
                    if p in v:
                        return True
                if v.strip().startswith("{") and ("structure" in v or "text" in v or "landmark" in v):
                    return True
                return False
            if isinstance(v, dict):
                return any(walk(x) for x in v.values())
            if isinstance(v, list):
                return any(walk(x) for x in v)
            return False
        edu = {
            "must_know_anatomy": payload.get("must_know_anatomy", []),
            "surgical_approach_anatomy": payload.get("surgical_approach_anatomy", []),
            "structures_at_risk": payload.get("structures_at_risk", []),
            "surgical_layers": payload.get("surgical_layers", []),
            "danger_zones": payload.get("danger_zones", []),
            "attending_pimp_questions": payload.get("attending_pimp_questions", []),
            "key_landmarks": payload.get("key_landmarks", []),
            "common_mistakes": payload.get("common_mistakes", []),
        }
        return walk(edu)

    def assert_no_empty_sar_subfields(payload):
        sar = payload.get("structures_at_risk", [])
        for s in sar:
            if isinstance(s, dict):
                if not s.get("why_at_risk") or not s.get("how_to_avoid_injury") or not s.get("consequence_of_injury"):
                    return True
        return False

    def assert_no_placeholder_layers(payload):
        layers = payload.get("surgical_layers", [])
        for l in layers:
            name = str(l.get("layer_name", "")).lower() if isinstance(l, dict) else str(l).lower()
            if name in ("layer 1", "layer 2", "layer 3", "primary surgical interval / exposure"):
                return True
        return False

    def assert_no_local_dev_source_urls(payload):
        srcs = payload.get("source_urls", [])
        for s in srcs:
            ss = str(s).lower()
            if "data/" in ss or "approach_playbook" in ss or "upper_extremity" in ss or "lower_extremity" in ss:
                return True
        return False

    b2_pass = 0
    b2_total = 0

    # Universal structural asserts (stringified, empty SAR, placeholder, dev)
    for pid in ["tka", "acl_reconstruction", "meniscus_repair", "acetabulum_fracture_orif_anterior", "acetabulum_fracture_orif_posterior"]:
        pay = CERTIFIED.get(pid)
        if pay:
            b2_total += 1
            if (not assert_no_stringified_objects(pay) and
                not assert_no_empty_sar_subfields(pay) and
                not assert_no_placeholder_layers(pay) and
                not assert_no_local_dev_source_urls(pay)):
                b2_pass += 1
                print(f"PASS: {pid} - no stringified / no empty SAR subs / no placeholder layers / no local dev sources")
            else:
                print(f"FAIL: {pid} - structural corruption still present (stringified/empty/placeholder/dev)")

    # tka: educational text only; no hip/THA/ACL-reconstruction specific contamination.
    # Legitimate: generic knee, patella, extensor, MCL, popliteal, peroneal, tibia/femur.
    tka = CERTIFIED.get("tka")
    if tka:
        edu = get_educational_text(tka)
        forbidden = ["hip", "tha", "acl reconstruction", "acl tear"]
        bad = contains_forbidden_terms(edu, forbidden)
        b2_total += 1
        if not bad:
            b2_pass += 1
            print("PASS: tka - no hip/THA/ACL-recon contamination in educational text only")
        else:
            print("FAIL: tka - forbidden cross term in educational text")
            instrument_forbidden_match(tka, forbidden, "tka_no_hip_tha_acl_contamination")

    # acl_reconstruction: no TKA or hip/THA in educational text. Meniscus/root references allowed.
    aclp = CERTIFIED.get("acl_reconstruction")
    if aclp:
        edu = get_educational_text(aclp)
        forbidden = ["tka", "total knee", "hip", "tha"]
        bad = contains_forbidden_terms(edu, forbidden)
        b2_total += 1
        if not bad:
            b2_pass += 1
            print("PASS: acl_reconstruction - no TKA/hip contamination in educational text only")
        else:
            print("FAIL: acl_reconstruction - forbidden cross term in educational text")
            instrument_forbidden_match(aclp, forbidden, "acl_no_tka_hip_tha_contamination")

    # meniscus_repair: no TKA/THA/hip. ACL only tolerated when explicitly tied to meniscus/root/arthro context.
    men = CERTIFIED.get("meniscus_repair")
    if men:
        edu = get_educational_text(men)
        forbidden = ["tka", "total knee", "hip", "tha"]
        # allow "acl" only in meniscus root context
        bad = contains_forbidden_terms(edu, forbidden)
        # extra check: standalone "acl reconstruction" (not near "root" or "meniscus" or "landmark" context)
        if re.search(r'\bacl reconstruction\b', edu) and not re.search(r'\b(root|meniscus|landmark)\b', edu[edu.find("acl reconstruction")-50:edu.find("acl reconstruction")+100] if "acl reconstruction" in edu else ""):
            bad = True
        b2_total += 1
        if not bad:
            b2_pass += 1
            print("PASS: meniscus_repair - no TKA/hip and ACL only in root context (edu text only)")
        else:
            print("FAIL: meniscus_repair - forbidden cross or standalone ACL recon in educational text")
            instrument_forbidden_match(men, forbidden, "meniscus_no_tka_hip_tha_acl_contamination")

    # anterior acetabulum: no posterior/KL/sciatic/short-ER as *main educational content*.
    # Those terms are only allowed inside the excluded validation/approach_notes.
    ant = CERTIFIED.get("acetabulum_fracture_orif_anterior")
    if ant:
        edu = get_educational_text(ant)
        forbidden = ["kocher", "kocher-langenbeck", "sciatic nerve protection", "short external rotators", "obturator internus cushion"]
        bad = contains_forbidden_terms(edu, forbidden)
        b2_total += 1
        if not bad:
            b2_pass += 1
            print("PASS: acetabulum anterior - no KL/sciatic/short-ER as main edu content (validation/notes excluded)")
        else:
            print("FAIL: acetabulum anterior - posterior approach terms in educational text")

    # posterior acetabulum: no anterior/ilioinguinal/corona/external-iliac as *main educational content*.
    post = CERTIFIED.get("acetabulum_fracture_orif_posterior")
    if post:
        edu = get_educational_text(post)
        forbidden = ["ilioinguinal", "corona mortis", "external iliac", "femoral nerve as main approach risk"]
        bad = contains_forbidden_terms(edu, forbidden)
        b2_total += 1
        if not bad:
            b2_pass += 1
            print("PASS: acetabulum posterior - no ilioinguinal/corona/external-iliac as main edu content (validation/notes excluded)")
        else:
            print("FAIL: acetabulum posterior - anterior approach terms in educational text")

    print(f"Batch 2 guards: {b2_pass}/{b2_total} passed")

    def report_batch3_cross_detail(payload, forbidden, guard_name):
        pid = payload.get("procedure_id")
        edu_keys = ["must_know_anatomy", "surgical_approach_anatomy", "structures_at_risk", "surgical_layers", "danger_zones", "attending_pimp_questions", "key_landmarks", "common_mistakes"]
        for k in edu_keys:
            v = payload.get(k, [])
            field_text = json.dumps(v).lower()
            for f in forbidden:
                if f in field_text:
                    idx = field_text.find(f)
                    start = max(0, idx-40)
                    end = min(len(field_text), idx + len(f) + 40)
                    ctx = field_text[start:end]
                    print(f"payload={pid} guard={guard_name} term={f} matched_substring={f} offset={idx} context="...{ctx}..." field={k}")

        # === Batch 3 regression guards (femoral_shaft, tibial_shaft, quadriceps_tendon, plantar_fasciitis, distal_femur) ===
    print("\n=== Batch 3 fixed-payload regression guards ===")
    b3_pass = 0
    b3_total = 0

    # Universal structural for Batch 3 (reuse helpers)
    for pid in ["femoral_shaft_fracture_orif", "tibial_shaft_fracture_orif", "quadriceps_tendon_repair", "plantar_fasciitis_release", "distal_femur_fracture_orif"]:
        pay = CERTIFIED.get(pid)
        if pay:
            b3_total += 1
            if (not assert_no_stringified_objects(pay) and
                not assert_no_empty_sar_subfields(pay) and
                not assert_no_placeholder_layers(pay) and
                not assert_no_local_dev_source_urls(pay)):
                b3_pass += 1
                print(f"PASS: {pid} - no stringified / no empty SAR subs / no placeholder layers / no local dev sources")
            else:
                print(f"FAIL: {pid} - structural corruption still present")

    # femoral_shaft: no hip/THA/ankle/TKA/peroneal-shaft contamination in edu text (lateral femur shaft specific)
    fem = CERTIFIED.get("femoral_shaft_fracture_orif")
    if fem:
        edu = get_educational_text(fem)
        forbidden = ["hip", "tha", "ankle", "tka", "tibial shaft", "peroneal", "fibular"]
        bad = contains_forbidden_terms(edu, forbidden)
        b3_total += 1
        if not bad:
            b3_pass += 1
            print("PASS: femoral_shaft - no hip/THA/ankle/TKA/peroneal-shaft contamination in edu text only")
        else:
            print("FAIL: femoral_shaft - forbidden cross term in educational text")
            report_batch3_cross_detail(fem, forbidden, "femoral_no_wrong_cross")

    # tibial_shaft: no femoral/hip/ankle-only contamination (tibia compartments specific)
    tib = CERTIFIED.get("tibial_shaft_fracture_orif")
    if tib:
        edu = get_educational_text(tib)
        forbidden = ["femoral", "hip", "tha", "ankle", "achilles", "lisfranc"]
        bad = contains_forbidden_terms(edu, forbidden)
        b3_total += 1
        if not bad:
            b3_pass += 1
            print("PASS: tibial_shaft - no femoral/hip/ankle-only contamination in edu text only")
        else:
            print("FAIL: tibial_shaft - forbidden cross term in educational text")

    # quadriceps_tendon: no patellar tendon/TKA/ACL/meniscus/hip as primary (quad layers/insertion specific)
    quad = CERTIFIED.get("quadriceps_tendon_repair")
    if quad:
        edu = get_educational_text(quad)
        forbidden = ["patellar tendon rupture", "tka", "acl reconstruction", "meniscus", "hip", "tha"]
        bad = contains_forbidden_terms(edu, forbidden)
        b3_total += 1
        if not bad:
            b3_pass += 1
            print("PASS: quadriceps_tendon - no patellar tendon/TKA/ACL/meniscus/hip as primary in edu text only")
        else:
            print("FAIL: quadriceps_tendon - forbidden cross term in educational text")

    # plantar_fasciitis: no Achilles/ankle/Lisfranc/hip contamination (plantar fascia/Baxter specific)
    plan = CERTIFIED.get("plantar_fasciitis_release")
    if plan:
        edu = get_educational_text(plan)
        forbidden = ["achilles", "ankle ligament", "lisfranc", "hip", "tha"]
        bad = contains_forbidden_terms(edu, forbidden)
        b3_total += 1
        if not bad:
            b3_pass += 1
            print("PASS: plantar_fasciitis - no Achilles/ankle/Lisfranc/hip contamination in edu text only")
        else:
            print("FAIL: plantar_fasciitis - forbidden cross term in educational text")

    # distal_femur: no TKA/hip/shaft-only contamination (distal condyles/Hoffa/lateral-parapatellar specific)
    df = CERTIFIED.get("distal_femur_fracture_orif")
    if df:
        edu = get_educational_text(df)
        forbidden = ["tka", "total knee", "hip arthroplasty", "femoral shaft only", "tibial shaft"]
        bad = contains_forbidden_terms(edu, forbidden)
        b3_total += 1
        if not bad:
            b3_pass += 1
            print("PASS: distal_femur - no TKA/hip/shaft-only contamination in edu text only")
        else:
            print("FAIL: distal_femur - forbidden cross term in educational text")

    print(f"Batch 3 guards: {b3_pass}/{b3_total} passed")
    if b3_pass != b3_total:
        print("NOTE: Remaining Batch 3 guard failures - report exact field/path if payload issue or classify as guard bug per prior process.")

    if b2_pass != b2_total:
        print("NOTE: Remaining failures after helper refactor are treated as true payload issues (audit is source of truth) or will be investigated; guard logic is now field-aware and excludes notes/warnings.")


    return results

if __name__ == "__main__":
    run_e2e_qa()
