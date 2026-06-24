"""
Shared helpers for CasePrep procedure registry scripts.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
ANATOMY_ROOT = ROOT / "data" / "anatomy"
REGISTRY_ROOT = ROOT / "data" / "caseprep" / "procedures"
REGISTRY_INDEX_PATH = ROOT / "data" / "caseprep" / "registry_index.json"
ALIAS_INDEX_PATH = ROOT / "data" / "caseprep" / "alias_index.json"
CERTIFIED_EXPORT_PATH = ROOT / "data" / "caseprep" / "certified_payloads_export.jsonl"

ALIASES_PATH = ANATOMY_ROOT / "registry" / "procedure_aliases.jsonl"
PROCEDURES_PATH = ANATOMY_ROOT / "registry" / "procedures.jsonl"
CERTIFICATION_PATH = ANATOMY_ROOT / "registry" / "certification_registry.jsonl"
CERTIFIED_JSONL_PATH = ANATOMY_ROOT / "case_prep" / "certified_case_prep_payloads.jsonl"
ROUTER_PATH = ANATOMY_ROOT / "case_prep" / "case_prep_router.json"
SOURCES_PATH = ANATOMY_ROOT / "sources" / "orthobullets_sources.jsonl"

CONTENT_STATUSES = frozenset(
    {"missing", "draft", "partial", "complete", "certified", "deprecated"}
)
REVIEW_STATUSES = frozenset(
    {
        "unreviewed",
        "ai_drafted",
        "needs_review",
        "resident_review",
        "attending_review",
        "certified",
        "needs_revision",
        "approved",
    }
)

MANIFEST_REQUIRED = (
    "slug",
    "display_name",
    "specialty",
    "body_region",
    "procedure_family",
    "status",
    "content_status",
    "review_status",
    "version",
    "caseprep_schema_version",
    "coverage_score",
    "runtime_enabled",
    "deprecated",
    "replacement_slug",
    "reviewer",
    "certified_at",
    "last_reviewed_at",
    "source_payload_hash",
)

MODULE_SECTIONS = (
    "indications",
    "setup_positioning",
    "approach_landmarks",
    "surgical_layers",
    "structures_at_risk",
    "implant_strategy",
    "reduction_or_fluoro_checkpoints",
    "pitfalls",
    "attending_pimp_questions",
    "postop_plan",
)

# Weights sum to 120; score_modules clamps to 100.
COVERAGE_WEIGHTS = {
    "indications": 10,
    "setup_positioning": 10,
    "approach_landmarks": 15,
    "surgical_layers": 15,
    "structures_at_risk": 20,
    "implant_strategy": 10,
    "reduction_or_fluoro_checkpoints": 10,
    "pitfalls": 10,
    "attending_pimp_questions": 10,
    "postop_plan": 10,
}

PLACEHOLDER_PATTERNS = [
    "see source-backed module",
    "primary structure at risk?",
    "key approach for this case",
    "per map evidence",
]

REGION_FORBIDDEN_TERMS: Dict[str, List[str]] = {
    "hip": ["lister's tubercle", "lister tubercle", "scaphoid fossa", "median nerve at wrist"],
    "knee": ["lister's tubercle", "greater trochanter", "sciatic nerve on quadratus"],
    "wrist": ["greater trochanter", "sciatic nerve", "acetabular component", "femoral neck cut"],
    "shoulder": ["lister's tubercle", "tibial plateau", "ankle syndesmosis"],
    "ankle": ["greater trochanter", "glenohumeral", "lister's tubercle"],
    "spine": ["greater trochanter", "lister's tubercle"],
    "foot": ["greater trochanter", "sciatic nerve on quadratus femoris"],
    "femur": ["lister's tubercle", "glenohumeral joint"],
    "humerus": ["lister's tubercle", "tibial plafond"],
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_alias(text: str) -> str:
    t = (text or "").lower()
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def payload_hash(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: Any, *, force: bool, indent: int = 2) -> str:
    if path.exists() and not force:
        return "skipped"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=indent, ensure_ascii=False)
        f.write("\n")
    return "written"


def write_text(path: Path, text: str, *, force: bool) -> str:
    if path.exists() and not force:
        return "skipped"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return "written"


def write_jsonl(path: Path, rows: List[Dict[str, Any]], *, force: bool) -> str:
    if path.exists() and not force:
        return "skipped"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return "written"


def procedure_dir(slug: str) -> Path:
    return REGISTRY_ROOT / slug


def list_procedure_folders() -> List[Path]:
    if not REGISTRY_ROOT.exists():
        return []
    return sorted(
        [p for p in REGISTRY_ROOT.iterdir() if p.is_dir()],
        key=lambda p: p.name,
    )


def load_manifest(folder: Path) -> Optional[Dict[str, Any]]:
    return load_json(folder / "manifest.json")


def empty_modules() -> Dict[str, List[Any]]:
    return {k: [] for k in MODULE_SECTIONS}


def modules_from_payload(payload: Dict[str, Any]) -> Dict[str, List[Any]]:
    setup: List[Any] = list(payload.get("must_know_anatomy") or [])
    if payload.get("procedure_overview"):
        setup = [payload["procedure_overview"]] + setup
    if payload.get("surgical_approach_anatomy"):
        setup = setup + list(payload["surgical_approach_anatomy"])
    return {
        "indications": [],
        "setup_positioning": setup,
        "approach_landmarks": list(payload.get("key_landmarks") or []),
        "surgical_layers": list(payload.get("surgical_layers") or []),
        "structures_at_risk": list(payload.get("structures_at_risk") or []),
        "implant_strategy": list(payload.get("reduction_or_implant_anatomy") or []),
        "reduction_or_fluoro_checkpoints": list(payload.get("fluoroscopy_checkpoints") or []),
        "pitfalls": list(payload.get("common_mistakes") or []),
        "attending_pimp_questions": list(payload.get("attending_pimp_questions") or []),
        "postop_plan": list(payload.get("night_before_review_checklist") or []),
    }


def sources_from_payload_and_proc(
    payload: Optional[Dict[str, Any]],
    proc_row: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen = set()
    urls = list((payload or {}).get("source_urls") or [])
    if proc_row and proc_row.get("source_url"):
        urls.insert(0, proc_row["source_url"])
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            rows.append(
                {
                    "source_type": "orthobullets",
                    "url": url,
                    "title": proc_row.get("procedure_name") if proc_row else None,
                    "consumed": True,
                }
            )
    return rows


def infer_procedure_family(
    specialty: str, anatomy_category: Optional[str] = None
) -> str:
    if anatomy_category:
        return anatomy_category
    spec = (specialty or "").lower()
    if "recon" in spec or "arthroplasty" in spec:
        return "arthroplasty"
    if "trauma" in spec:
        return "trauma_orif"
    if "sports" in spec:
        return "sports"
    if "spine" in spec:
        return "spine"
    if "pediatric" in spec or "peds" in spec:
        return "pediatrics"
    if "foot" in spec:
        return "foot_ankle"
    return "general"


def build_manifest(
    *,
    slug: str,
    display_name: str,
    specialty: str,
    body_region: str,
    is_certified: bool,
    certified_at: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    proc_row: Optional[Dict[str, Any]] = None,
    partial: bool = False,
) -> Dict[str, Any]:
    now = utc_now_iso()
    anatomy_category = (payload or {}).get("anatomy_category")
    phash = payload_hash(payload) if payload else ""
    if is_certified:
        return {
            "slug": slug,
            "display_name": display_name,
            "specialty": specialty,
            "body_region": body_region,
            "procedure_family": infer_procedure_family(specialty, anatomy_category),
            "status": "active",
            "content_status": "certified",
            "review_status": "certified",
            "version": "1.0.0",
            "caseprep_schema_version": (payload or {}).get(
                "schema_version", "brobot_case_prep_payload_v2"
            ),
            "coverage_score": 0,
            "runtime_enabled": True,
            "deprecated": False,
            "replacement_slug": None,
            "reviewer": "brobot_migration",
            "certified_at": certified_at or now,
            "last_reviewed_at": certified_at or now,
            "source_payload_hash": phash,
        }
    content_status = "partial" if partial else "missing"
    return {
        "slug": slug,
        "display_name": display_name,
        "specialty": specialty,
        "body_region": body_region,
        "procedure_family": infer_procedure_family(
            specialty, proc_row.get("case_anatomy_type") if proc_row else None
        ),
        "status": "active",
        "content_status": content_status,
        "review_status": "unreviewed",
        "version": "0.1.0",
        "caseprep_schema_version": "brobot_case_prep_payload_v2",
        "coverage_score": 0,
        "runtime_enabled": False,
        "deprecated": False,
        "replacement_slug": None,
        "reviewer": None,
        "certified_at": None,
        "last_reviewed_at": None,
        "source_payload_hash": phash,
    }


def review_notes_template(
    slug: str, display_name: str, *, certified: bool, partial: bool
) -> str:
    status = "certified" if certified else ("partial" if partial else "missing")
    return f"""# {display_name} (`{slug}`)

## Review status
- Migrated content_status: **{status}**
- Generated by `migrate_flat_payloads_to_registry.py`

## Checklist before certification
- [ ] Setup / positioning verified
- [ ] Approach landmarks accurate for intended approach
- [ ] Structures at risk complete with avoid/consequence
- [ ] Implant / reduction strategy present if applicable
- [ ] Fluoroscopy checkpoints if applicable
- [ ] Attending pimp questions specific (no placeholders)
- [ ] Indications (clinical indication bullets)
- [ ] Post-op protocol (weight-bearing, immobilization, DVT, activity restrictions — not night-before checklist)
- [ ] Sources linked in sources.jsonl
- [ ] No cross-region landmark contamination

## Notes

"""


def section_has_content(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, list):
        if not value:
            return False
        for item in value:
            if isinstance(item, str) and item.strip():
                low = item.lower()
                if not any(p in low for p in PLACEHOLDER_PATTERNS):
                    return True
            elif isinstance(item, dict) and item:
                return True
            elif item:
                return True
        return False
    if isinstance(value, str):
        return bool(value.strip()) and not any(
            p in value.lower() for p in PLACEHOLDER_PATTERNS
        )
    return bool(value)


def score_modules(modules: Dict[str, Any], payload: Optional[Dict[str, Any]] = None) -> int:
    """Return coverage_score 0-100 from modules.json (fallback to payload sections)."""
    data = modules if any(section_has_content(modules.get(k)) for k in MODULE_SECTIONS) else {}
    if not data and payload:
        data = modules_from_payload(payload)
    total = 0
    for key, weight in COVERAGE_WEIGHTS.items():
        if section_has_content(data.get(key)):
            total += weight
    return min(100, total)


def collect_text_blobs(folder: Path) -> str:
    parts: List[str] = []
    for name in ("certified_payload.json", "modules.json"):
        obj = load_json(folder / name)
        if obj:
            parts.append(json.dumps(obj, ensure_ascii=False).lower())
    return " ".join(parts)


def cross_region_warnings(body_region: str, text: str) -> List[str]:
    region = (body_region or "").lower()
    forbidden = REGION_FORBIDDEN_TERMS.get(region, [])
    warnings: List[str] = []
    low = text.lower()
    for term in forbidden:
        if term in low:
            warnings.append(f"possible cross-region term '{term}' for body_region={region}")
    return warnings


def placeholder_hits(text: str) -> List[str]:
    low = text.lower()
    return [p for p in PLACEHOLDER_PATTERNS if p in low]