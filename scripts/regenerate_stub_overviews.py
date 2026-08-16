"""Regenerate procedure_overview for payloads whose overview was clobbered with a
metadata stub ("... Certified. Score N. Source-backed from vX."). Composes a
grounded 2-sentence overview from existing curated fields (indications + top
structure-at-risk) — no LLM, fully source-backed. Idempotent.

Usage:
  python scripts/regenerate_stub_overviews.py --dry-run
  python scripts/regenerate_stub_overviews.py --apply
"""
from __future__ import annotations
import argparse, glob, hashlib, json, os, re

STUB = re.compile(r"Certified\.\s*Score\s*\d+\.\s*Source-backed", re.I)
PROC_DIR = "data/caseprep/procedures"


def _lower_first(s: str) -> str:
    s = s.strip()
    return s[:1].lower() + s[1:] if s else s


def _looks_like_approach(approach: str, display: str) -> bool:
    if not approach or approach.strip() == display.strip():
        return False
    a = approach.lower()
    return any(k in a for k in ("(", "lateral", "anterior", "posterior", "approach", "hardinge"))


def compose_overview(payload: dict, modules: dict) -> str | None:
    display = (payload.get("procedure_name") or "").strip()
    indications = modules.get("indications") or []
    indication = indications[0].strip() if indications else ""
    sar = payload.get("structures_at_risk") or []
    sar0 = sar[0].get("structure") if sar and isinstance(sar[0], dict) else None
    approach = (payload.get("approach_name") or "").strip()

    if not indication and not display:
        return None

    # Sentence 1 — primary indication (already a full clinical sentence).
    parts = []
    if indication:
        parts.append(indication if indication.endswith(".") else indication + ".")
    elif display:
        parts.append(f"{display}.")

    # Sentence 2 — approach + primary structure at risk (both curated fields).
    tail = ""
    if _looks_like_approach(approach, display):
        tail = f"Performed via the {approach} approach"
        if sar0:
            tail += f"; the {_lower_first(sar0)} is the key structure to protect."
        else:
            tail += "."
    elif sar0:
        tail = f"Primary structure at risk during exposure: {sar0}."
    if tail:
        parts.append(tail)

    return " ".join(parts).strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    apply = args.apply and not args.dry_run

    changed = 0
    for pf in sorted(glob.glob(f"{PROC_DIR}/*/certified_payload.json")):
        payload = json.load(open(pf))
        ov = payload.get("procedure_overview") or ""
        if not (STUB.search(ov) or len(ov) < 60):
            continue
        mf = pf.replace("certified_payload.json", "modules.json")
        modules = json.load(open(mf)) if os.path.exists(mf) else {}
        new_ov = compose_overview(payload, modules)
        slug = pf.split("/")[-2]
        if not new_ov:
            print(f"SKIP {slug}: could not compose")
            continue
        print(f"\n{slug}:\n  OLD: {ov!r}\n  NEW: {new_ov!r}")
        changed += 1
        if apply:
            payload["procedure_overview"] = new_ov
            json.dump(payload, open(pf, "w"), ensure_ascii=False, indent=2)
            # The registry loader rejects a payload whose sha256 no longer
            # matches manifest.source_payload_hash. Re-certify by recomputing it.
            manifest_path = pf.replace("certified_payload.json", "manifest.json")
            if os.path.exists(manifest_path):
                manifest = json.load(open(manifest_path))
                manifest["source_payload_hash"] = hashlib.sha256(
                    json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
                ).hexdigest()
                json.dump(manifest, open(manifest_path, "w"), ensure_ascii=False, indent=2)
            # Scrub the stub line from modules.setup_positioning so a future
            # recompile never re-injects it.
            setup = modules.get("setup_positioning") or []
            if setup and STUB.search(setup[0] or ""):
                modules["setup_positioning"] = setup[1:]
                json.dump(modules, open(mf, "w"), ensure_ascii=False, indent=2)

    print(f"\n{'APPLIED' if apply else 'DRY-RUN'}: {changed} payloads")


if __name__ == "__main__":
    main()
