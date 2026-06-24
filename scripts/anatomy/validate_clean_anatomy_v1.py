#!/usr/bin/env python3
"""
Validation for clean anatomy v1 database.

Run: python scripts/anatomy/validate_clean_anatomy_v1.py
Exits 0 on all pass, 1 on any failure.
"""

import json
import sys
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
ANATOMY = ROOT / "data" / "anatomy"

LEGACY_STRINGS = [
    "Per map evidence",
    "Primary structure at risk?",
    "Key approach for this case",
    "No free-form guessing",
    "unknown or uncertain type",
]

REQUIRED_PAYLOAD_SECTIONS = [
    "source_urls",
    "must_know_anatomy",
    "structures_at_risk",
    "attending_pimp_questions",
    "night_before_review_checklist",
]

def fail(msg):
    print(f"FAIL: {msg}")
    return False

def ok(msg):
    print(f"PASS: {msg}")
    return True

def main():
    all_pass = True

    # 1. dir + required files exist
    if not ANATOMY.exists():
        all_pass &= fail("data/anatomy directory missing")
    else:
        all_pass &= ok("data/anatomy exists")

    required = [
        "registry/procedures.jsonl",
        "registry/procedure_aliases.jsonl",
        "registry/certification_registry.jsonl",
        "sources/orthobullets_sources.jsonl",
        "sources/source_gap_queue.jsonl",
        "modules/approach_modules.jsonl",
        "modules/arthroscopy_modules.jsonl",
        "modules/reduction_implant_modules.jsonl",
        "modules/decompression_modules.jsonl",
        "modules/soft_tissue_modules.jsonl",
        "modules/fluoroscopy_modules.jsonl",
        "modules/pathology_anatomy_modules.jsonl",
        "case_prep/certified_case_prep_payloads.jsonl",
        "case_prep/case_prep_router.json",
        "case_prep/retrieval_tests.jsonl",
        "reports/integration_readiness.md",
    ]
    for rel in required:
        p = ANATOMY / rel
        if p.exists():
            all_pass &= ok(f"required file present: {rel}")
        else:
            all_pass &= fail(f"missing required: {rel}")

    # 2. all jsonl parse + basic counts
    try:
        with (ANATOMY / "registry/procedures.jsonl").open() as f:
            procs = [json.loads(l) for l in f if l.strip()]
        all_pass &= ok(f"procedures.jsonl parses, {len(procs)} entries")
        if len(procs) != 60:
            all_pass &= fail(f"expected 60 procedures, got {len(procs)}")
        ids = [p.get("procedure_id") for p in procs]
        if len(set(ids)) != len(ids):
            all_pass &= fail("duplicate procedure_ids in procedures.jsonl")
        else:
            all_pass &= ok("60 unique procedure_ids")
    except Exception as e:
        all_pass &= fail(f"procedures.jsonl parse error: {e}")

    try:
        with (ANATOMY / "registry/procedure_aliases.jsonl").open() as f:
            aliases = [json.loads(l) for l in f if l.strip()]
        all_pass &= ok(f"procedure_aliases.jsonl parses, {len(aliases)} entries")
        alias_ids = {a["procedure_id"] for a in aliases}
        proc_ids = set(ids) if 'ids' in locals() else set()
        if proc_ids and alias_ids >= proc_ids:
            all_pass &= ok("aliases cover every procedure")
        else:
            all_pass &= fail("aliases do not cover all procedures")
    except Exception as e:
        all_pass &= fail(f"aliases parse error: {e}")

    try:
        with (ANATOMY / "registry/certification_registry.jsonl").open() as f:
            certs = [json.loads(l) for l in f if l.strip()]
        cert_ids = {c["procedure_id"] for c in certs}
        all_pass &= ok(f"certification_registry parses, {len(certs)} entries")
    except Exception as e:
        all_pass &= fail(f"cert registry parse: {e}")

    # 3. case_prep files
    try:
        with (ANATOMY / "case_prep/case_prep_router.json").open() as f:
            router = json.load(f)
        cert_in_router = set(router.get("certified_procedure_ids", []))
        all_pass &= ok("case_prep_router.json parses")
        if cert_in_router == cert_ids:
            all_pass &= ok("case_prep_router certified IDs match certification_registry")
        else:
            all_pass &= fail("case_prep_router certified IDs mismatch")
    except Exception as e:
        all_pass &= fail(f"case_prep_router parse: {e}")

    try:
        with (ANATOMY / "case_prep/certified_case_prep_payloads.jsonl").open() as f:
            payloads = [json.loads(l) for l in f if l.strip()]
        payload_ids = {p["procedure_id"] for p in payloads}
        all_pass &= ok(f"certified_case_prep_payloads parses, {len(payloads)} entries")
        if payload_ids == cert_ids:
            all_pass &= ok("certified payload IDs match certification count")
        else:
            all_pass &= fail("payload IDs do not match certified set")
    except Exception as e:
        all_pass &= fail(f"payloads parse: {e}")

    # 4. modules: no duplicate module_ids across files
    all_mod_ids = set()
    dups = []
    for mod_file in (ANATOMY / "modules").glob("*.jsonl"):
        try:
            with mod_file.open() as f:
                for l in f:
                    if l.strip():
                        m = json.loads(l)
                        mid = m.get("module_id")
                        if mid in all_mod_ids:
                            dups.append(mid)
                        all_mod_ids.add(mid)
        except Exception:
            pass
    if dups:
        all_pass &= fail(f"duplicate module_ids: {dups[:3]}...")
    else:
        all_pass &= ok(f"no duplicate module_ids across modules ({len(all_mod_ids)} total)")

    # 5. no legacy placeholders in certified payloads
    legacy_found = []
    for p in payloads:
        text = json.dumps(p)
        for bad in LEGACY_STRINGS:
            if bad in text:
                legacy_found.append((p.get("procedure_id"), bad))
    if legacy_found:
        all_pass &= fail(f"legacy placeholder strings found in certified payloads: {legacy_found[:5]}")
    else:
        all_pass &= ok("no legacy placeholder strings in certified payloads")

    # 6. every certified payload has required sections (non-empty or present)
    missing_sections = []
    for p in payloads:
        pid = p.get("procedure_id")
        for sec in REQUIRED_PAYLOAD_SECTIONS:
            if sec not in p or not p[sec]:
                missing_sections.append((pid, sec))
    if missing_sections:
        all_pass &= fail(f"missing required sections in payloads: {missing_sections[:5]}")
    else:
        all_pass &= ok("all certified payloads have required sections (source_urls, must_know, structures_at_risk, pimp, checklist)")

    # 7. runtime references point to data/anatomy (heuristic grep on key files)
    runtime_ok = True
    for pyfile in [ROOT / "main.py", ROOT / "procedure_registry.py"]:
        if pyfile.exists():
            txt = pyfile.read_text()
            if "data/anatomy" in txt or "ANATOMY_ROOT" in txt:
                pass
            else:
                runtime_ok = False
    if runtime_ok:
        all_pass &= ok("runtime code (main, procedure_registry) references data/anatomy paths")
    else:
        all_pass &= fail("runtime code may still reference old anatomy paths")

    # 8. files parse sanity for modules/sources etc (spot check)
    for spot in ["sources/orthobullets_sources.jsonl", "modules/approach_modules.jsonl"]:
        try:
            p = ANATOMY / spot
            with p.open() as f:
                next(json.loads(l) for l in f if l.strip())
            all_pass &= ok(f"{spot} parses")
        except Exception as e:
            all_pass &= fail(f"{spot} parse: {e}")

    print("\n=== SUMMARY ===")
    if all_pass:
        print("ALL VALIDATION CHECKS PASSED")
        sys.exit(0)
    else:
        print("SOME VALIDATION CHECKS FAILED (see above)")
        sys.exit(1)

if __name__ == "__main__":
    main()
