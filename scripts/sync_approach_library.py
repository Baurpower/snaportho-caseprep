#!/usr/bin/env python3
"""Synchronize the approach source inventory without copying source prose.

AO pages are discovered from the public sitemap. Orthobullets approach pages
are discovered from the navigation links embedded in a public approach page.
Generated records contain titles, URLs, taxonomy hints, and fingerprints only.
Clinical synthesis is a separate, review-gated operation.
"""

from __future__ import annotations

import argparse
from difflib import SequenceMatcher
import hashlib
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List
from urllib.parse import urljoin, urlparse, urlunparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from caseprep.approach_library.schema import empty_packet

OUTPUT = ROOT / "data/approach_library"
AO_SITEMAP_INDEX = "https://surgeryreference.aofoundation.org/seo/sitemapindex"
OB_SEED = "https://www.orthobullets.com/approaches/12022/hip-direct-lateral-approach-hardinge-transgluteal"
USER_AGENT = "SnapOrthoApproachInventory/1.0 (+source-link-index; no-content-mirroring)"


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return response.read()
        except Exception as error:  # network retry is intentionally bounded
            last_error = error
            if attempt < 2:
                time.sleep(2**attempt)
    assert last_error is not None
    raise last_error


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def title_from_url(url: str) -> str:
    tail = urlparse(url).path.rstrip("/").split("/")[-1]
    return re.sub(r"\s+", " ", tail.replace("-", " ")).strip().title()


def clean_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/"), "", "", ""))


def fingerprint(url: str) -> str:
    return hashlib.sha256(clean_url(url).encode("utf-8")).hexdigest()


def ao_scope(url: str) -> Dict[str, str]:
    parts = [part for part in urlparse(url).path.split("/") if part]
    result = {"clinical_domain": parts[0] if parts else "", "collection": "", "region": "", "anatomic_area": ""}
    if len(parts) >= 3:
        result["collection"] = parts[1]
        result["region"] = parts[2]
    if "approach" in parts:
        index = parts.index("approach")
        if index > 0:
            result["anatomic_area"] = parts[index - 1]
    return result


def ob_region(title: str) -> str:
    normalized = title.lower()
    groups = {
        "spine": ("spine", "cervical", "lumbar", "thoracic"),
        "shoulder": ("shoulder", "scapula"),
        "humerus": ("humerus",),
        "elbow": ("elbow", "radial head"),
        "forearm_wrist": ("radius", "ulnar", "wrist"),
        "pelvis_acetabulum": ("acetabul", "stoppa"),
        "hip_femur": ("hip", "femur"),
        "knee_tibia": ("knee", "tibia", "fibula"),
        "ankle_foot": ("ankle", "malleolus", "calcaneus", "tarsus", "toe", "mtp"),
    }
    for region, terms in groups.items():
        if any(term in normalized for term in terms):
            return region
    return "other"


def discover_ao() -> List[Dict[str, Any]]:
    root = ET.fromstring(fetch(AO_SITEMAP_INDEX))
    sitemap_urls = [node.text or "" for node in root.findall("{*}sitemap/{*}loc")]
    page_urls: set[tuple[str, str]] = set()
    for sitemap_url in sitemap_urls:
        sitemap = ET.fromstring(fetch(sitemap_url))
        for url_node in sitemap.findall("{*}url"):
            loc = url_node.find("{*}loc")
            lastmod = url_node.find("{*}lastmod")
            url = clean_url(loc.text if loc is not None and loc.text else "")
            if "/approach/" in url and not url.endswith("/all-approaches"):
                page_urls.add((url, lastmod.text if lastmod is not None else ""))
    rows = []
    for url, source_last_modified in sorted(page_urls):
        scope = ao_scope(url)
        rows.append(
            {
                "source_page_id": "ao_" + fingerprint(url)[:16],
                "provider": "ao_surgery_reference",
                "title": title_from_url(url),
                "url": url,
                "page_type": "approach",
                "clinical_domain": "orthopedics",
                **scope,
                "discovery_method": "public_sitemap",
                "url_fingerprint": fingerprint(url),
                "source_last_modified": source_last_modified,
            }
        )
    return rows


def discover_orthobullets() -> List[Dict[str, Any]]:
    parser = LinkParser()
    parser.feed(fetch(OB_SEED).decode("utf-8", errors="ignore"))
    urls = {
        clean_url(urljoin(OB_SEED, href))
        for href in parser.links
        if re.match(r"^/?approaches/\d+/", href.split("?", 1)[0])
    }
    rows = []
    for url in sorted(urls):
        title = title_from_url(url)
        rows.append(
            {
                "source_page_id": "orthobullets_" + fingerprint(url)[:16],
                "provider": "orthobullets",
                "title": title,
                "url": url,
                "page_type": "approach",
                "clinical_domain": "orthopedics",
                "collection": "approaches",
                "region": ob_region(title),
                "anatomic_area": "",
                "discovery_method": "public_approach_navigation",
                "url_fingerprint": fingerprint(url),
            }
        )
    return rows


def canonical_id(row: Dict[str, Any]) -> str:
    # Domain, collection, and region are part of the seed key so generic labels
    # cannot be dangerously merged across anatomy or adult/pediatric contexts.
    # True cross-source synonym merging happens only in reviewed authored data.
    region = row.get("anatomic_area") or row.get("region") or "unclassified"
    return "approach_seed_" + slug(
        f"{row.get('provider')}_{row.get('clinical_domain')}_{row.get('collection')}_{region}_{row['title']}"
    )


def merge_seed_packets(source_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    packets: Dict[str, Dict[str, Any]] = {}
    for row in source_rows:
        approach_id = canonical_id(row)
        packet = packets.setdefault(
            approach_id,
            empty_packet(approach_id, row["title"], region=row.get("region") or ""),
        )
        packet["sources"].append(
            {
                "source_id": row["source_page_id"],
                "provider": row["provider"],
                "url": row["url"],
                "title": row["title"],
                "use": "source_index_only",
            }
        )
    return sorted(packets.values(), key=lambda row: row["approach_id"])


def existing_procedure_mappings() -> Iterable[Dict[str, Any]]:
    path = ROOT / "data/approach_playbook/procedure_to_approach_map_v2.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        for approach_id in row.get("recommended_approach_ids") or []:
            yield {
                "procedure_id": row["procedure_id"],
                "approach_id": approach_id,
                "relationship": "recommended",
                "condition": "",
                "triggers": [],
                "evidence_urls": row.get("evidence_urls") or [],
                "mapping_status": "legacy_review_required",
            }
        for conditional in row.get("conditional_approach_ids") or []:
            if not isinstance(conditional, dict):
                continue
            for approach_id in conditional.get("approach_ids") or []:
                yield {
                    "procedure_id": row["procedure_id"],
                    "approach_id": approach_id,
                    "relationship": "conditional",
                    "condition": conditional.get("condition") or "",
                    "triggers": conditional.get("triggers") or [],
                    "evidence_urls": row.get("evidence_urls") or [],
                    "mapping_status": "legacy_review_required",
                }


def authored_packets_and_mappings() -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    packets: Dict[str, Dict[str, Any]] = {}
    mappings: List[Dict[str, Any]] = []
    procedure_root = ROOT / "data/caseprep/procedures"
    for path in sorted(procedure_root.glob("*/approaches_v3.json")):
        procedure_id = path.parent.name
        value = json.loads(path.read_text(encoding="utf-8"))
        for source in value.get("approaches") or []:
            approach_id = str(source.get("approach_id") or "")
            if not approach_id:
                continue
            packet = empty_packet(
                approach_id,
                str(source.get("name") or approach_id.replace("_", " ").title()),
                region=str(source.get("region") or ""),
            )
            packet.update(
                {
                    "aliases": source.get("aliases") or [],
                    "corridor": source.get("corridor") or "See layer-by-layer exposure.",
                    "positioning": source.get("positioning") or [],
                    "surface_landmarks": source.get("landmarks") or [],
                    "incision": source.get("incision") or source.get("exposure") or [],
                    "layers": source.get("layers") or [],
                    "structures_at_risk": source.get("structures_at_risk") or [],
                    "danger_zones": source.get("danger_zones") or source.get("pitfalls") or [],
                    "exposure": source.get("exposure") or [],
                    "limitations": source.get("selection_limitations") or [],
                    "indications": source.get("selection_indications") or [],
                    "closure": source.get("closure") or source.get("pitfalls") or [],
                    "complications": source.get("pitfalls") or [],
                    "procedure_applications": [procedure_id],
                    "questions": source.get("questions") or [],
                    "claims": source.get("claims") or [],
                    "sources": [
                        {
                            "source_id": "url_" + fingerprint(url)[:16],
                            "provider": urlparse(url).hostname or "",
                            "url": url,
                            "title": "Linked operative/evidence source",
                            "use": "clinical_synthesis",
                        }
                        for url in source.get("source_urls") or []
                    ],
                    "content_status": source.get("content_status") or "curated",
                    "runtime_fields": source,
                }
            )
            packets[approach_id] = packet
            mappings.append(
                {
                    "procedure_id": procedure_id,
                    "approach_id": approach_id,
                    "relationship": source.get("role") or "alternative",
                    "condition": "",
                    "triggers": [],
                    "evidence_urls": source.get("source_urls") or [],
                    "mapping_status": "authored_v3_agent_review_pending",
                }
            )
    return sorted(packets.values(), key=lambda row: row["approach_id"]), mappings


def alias_candidates(source_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ao_rows = [row for row in source_rows if row.get("provider") == "ao_surgery_reference"]
    ob_rows = [row for row in source_rows if row.get("provider") == "orthobullets"]
    candidates: List[Dict[str, Any]] = []

    def anatomy_signature(row: Dict[str, Any]) -> set[str]:
        text = " ".join(
            str(row.get(key) or "")
            for key in ("title", "anatomic_area", "region")
        ).lower()
        groups = {
            "cervical_spine": ("cervical",),
            "thoracolumbar_spine": ("thoracic", "thoracolumbar", "lumbar"),
            "shoulder_scapula": ("shoulder", "scapula", "proximal-humerus"),
            "humerus": ("humeral", "humerus", "distal-humerus", "humeral-shaft"),
            "elbow": ("elbow", "proximal-forearm", "radial-head"),
            "forearm": ("forearm", "radius", "ulna"),
            "wrist_hand": ("wrist", "carpal", "metacarp", "phalan", "finger", "thumb"),
            "pelvis_acetabulum": ("pelvis", "acetabul", "pelvic-ring"),
            "hip": (" hip", "hip ", "proximal-femur"),
            "femur": ("femur", "femoral-shaft"),
            "knee": ("knee", "distal-femur", "patella", "proximal-tibia"),
            "tibia_fibula": ("tibia", "fibula", "tibial-shaft"),
            "ankle_talus": ("ankle", "malleol", "talus", "distal-tibia"),
            "foot": ("calcane", "tars", "metatars", "toe", "hallux", "mtp", "navicular", "cuboid"),
        }
        return {group for group, terms in groups.items() if any(term in text for term in terms)}

    for ao in ao_rows:
        ao_title = slug(str(ao.get("title") or "")).replace("approach", "")
        if len(ao_title) < 5:
            continue
        for ob in ob_rows:
            if not anatomy_signature(ao).intersection(anatomy_signature(ob)):
                continue
            ob_title = slug(str(ob.get("title") or "")).replace("approach", "")
            score = SequenceMatcher(None, ao_title, ob_title).ratio()
            if score < 0.72:
                continue
            candidates.append(
                {
                    "candidate_id": "alias_" + fingerprint(ao["url"] + "|" + ob["url"])[:16],
                    "left_source_page_id": ao["source_page_id"],
                    "right_source_page_id": ob["source_page_id"],
                    "title_similarity": round(score, 4),
                    "decision": "agent_review_required",
                    "safety_note": "Title similarity alone must never merge clinical approaches.",
                }
            )
    return sorted(candidates, key=lambda row: (-row["title_similarity"], row["candidate_id"]))


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="Rebuild derived files from an existing registry")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    registry_path = OUTPUT / "source_registry.jsonl"
    if args.offline:
        source_rows = [json.loads(line) for line in registry_path.read_text().splitlines() if line.strip()]
        for row in source_rows:
            if not row.get("clinical_domain"):
                row["clinical_domain"] = (
                    "orthopedics"
                    if row.get("provider") == "orthobullets"
                    else ao_scope(str(row.get("url") or ""))["clinical_domain"]
                )
        write_jsonl(registry_path, source_rows)
    else:
        previous_urls = set()
        if registry_path.exists():
            previous_urls = {
                json.loads(line).get("url")
                for line in registry_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }
        source_rows = discover_ao() + discover_orthobullets()
        now = datetime.now(timezone.utc).isoformat()
        for row in source_rows:
            row["verified_at"] = now
        source_rows.sort(key=lambda row: (row["provider"], row["url"]))
        current_urls = {row["url"] for row in source_rows}
        changes = {
            "checked_at": now,
            "added_urls": sorted(current_urls - previous_urls),
            "removed_urls": sorted(previous_urls - current_urls),
            "requires_review": bool(previous_urls and previous_urls != current_urls),
        }
        (OUTPUT / "source_changes.json").write_text(json.dumps(changes, indent=2) + "\n")
        write_jsonl(registry_path, source_rows)

    packets = merge_seed_packets(source_rows)
    candidates = alias_candidates(source_rows)
    authored_packets, authored_mappings = authored_packets_and_mappings()
    mappings = sorted(
        [*existing_procedure_mappings(), *authored_mappings],
        key=lambda row: (row["procedure_id"], row["approach_id"], row["condition"]),
    )
    write_jsonl(OUTPUT / "approach_packets.jsonl", packets)
    write_jsonl(OUTPUT / "authored_approach_packets.jsonl", authored_packets)
    write_jsonl(OUTPUT / "alias_candidates.jsonl", candidates)
    write_jsonl(OUTPUT / "procedure_mappings.jsonl", mappings)
    providers: Dict[str, int] = {}
    for row in source_rows:
        providers[row["provider"]] = providers.get(row["provider"], 0) + 1
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_pages": len(source_rows),
        "providers": providers,
        "canonical_seed_packets": len(packets),
        "cross_source_alias_candidates": len(candidates),
        "authored_clinical_packets": len(authored_packets),
        "procedure_mappings": len(mappings),
        "publication_ready": 0,
        "note": "Inventory completeness is distinct from clinical packet publication readiness.",
    }
    (OUTPUT / "coverage_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
