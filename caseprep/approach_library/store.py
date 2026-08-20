"""Read-only runtime store for source pages and reusable approach packets."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .review import attach_review_state

ROOT = Path(__file__).resolve().parents[2]
LIBRARY_DIR = ROOT / "data/approach_library"


def _jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class ApproachLibrary:
    @staticmethod
    @lru_cache(maxsize=1)
    def source_pages() -> Dict[str, Dict[str, Any]]:
        return {row["source_page_id"]: row for row in _jsonl(LIBRARY_DIR / "source_registry.jsonl")}

    @staticmethod
    @lru_cache(maxsize=1)
    def packets() -> Dict[str, Dict[str, Any]]:
        packets = {
            row["approach_id"]: row for row in _jsonl(LIBRARY_DIR / "approach_packets.jsonl")
        }
        packets.update(
            {
                row["approach_id"]: row
                for row in _jsonl(LIBRARY_DIR / "authored_approach_packets.jsonl")
            }
        )
        authored_dir = LIBRARY_DIR / "authored"
        if authored_dir.exists():
            for path in authored_dir.glob("*.json"):
                row = json.loads(path.read_text(encoding="utf-8"))
                if row.get("approach_id"):
                    packets[row["approach_id"]] = row
        return packets

    @staticmethod
    @lru_cache(maxsize=1)
    def procedure_id_alias_map() -> Dict[str, List[str]]:
        """Live CasePrep slugs → extra authored procedure_ids."""
        mapping: Dict[str, List[str]] = {}
        for row in _jsonl(LIBRARY_DIR / "procedure_id_aliases.jsonl"):
            src = str(row.get("live_procedure_id") or "").strip()
            dest = str(row.get("authored_procedure_id") or "").strip()
            if not src or not dest:
                continue
            aliases = mapping.setdefault(src, [])
            if dest not in aliases:
                aliases.append(dest)
        return mapping

    @staticmethod
    @lru_cache(maxsize=1)
    def procedure_approach_alias_map() -> Dict[str, List[str]]:
        """Live CasePrep slugs → extra approach_ids (when a full procedure_id would over-attach)."""
        mapping: Dict[str, List[str]] = {}
        for row in _jsonl(LIBRARY_DIR / "procedure_id_aliases.jsonl"):
            src = str(row.get("live_procedure_id") or "").strip()
            approach_id = str(row.get("approach_id") or "").strip()
            if not src or not approach_id:
                continue
            aliases = mapping.setdefault(src, [])
            if approach_id not in aliases:
                aliases.append(approach_id)
        return mapping

    @staticmethod
    @lru_cache(maxsize=1)
    def mappings() -> List[Dict[str, Any]]:
        rows = list(_jsonl(LIBRARY_DIR / "procedure_mappings.jsonl"))
        seen = {
            (row.get("procedure_id"), row.get("approach_id"), row.get("condition", ""))
            for row in rows
        }
        for packet in ApproachLibrary.packets().values():
            for application in packet.get("procedure_applications") or []:
                if isinstance(application, str):
                    procedure_id, condition = application, ""
                    relationship = "applicable"
                else:
                    procedure_id = str(application.get("procedure_id") or "")
                    condition = str(application.get("condition") or "")
                    relationship = str(application.get("relationship") or "applicable")
                key = (procedure_id, packet.get("approach_id"), condition)
                if procedure_id and key not in seen:
                    rows.append(
                        {
                            "procedure_id": procedure_id,
                            "approach_id": packet["approach_id"],
                            "relationship": relationship,
                            "condition": condition,
                            "triggers": [],
                            "evidence_urls": [source.get("url") for source in packet.get("sources") or []],
                            "mapping_status": "authored_packet",
                        }
                    )
                    seen.add(key)
        return rows

    def get(self, approach_id: str) -> Optional[Dict[str, Any]]:
        packet = self.packets().get(approach_id)
        return attach_review_state(dict(packet)) if packet else None

    def for_procedure(self, procedure_id: str) -> List[Dict[str, Any]]:
        lookup_ids = {procedure_id, *self.procedure_id_alias_map().get(procedure_id, [])}
        rows = [row for row in self.mappings() if row.get("procedure_id") in lookup_ids]
        result: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for mapping in rows:
            approach_id = str(mapping.get("approach_id") or "")
            if not approach_id or approach_id in seen:
                continue
            packet = self.get(approach_id)
            if packet:
                result.append({**packet, "procedure_mapping": mapping})
                seen.add(approach_id)
        for approach_id in self.procedure_approach_alias_map().get(procedure_id, []):
            if not approach_id or approach_id in seen:
                continue
            packet = self.get(approach_id)
            if not packet:
                continue
            result.append(
                {
                    **packet,
                    "procedure_mapping": {
                        "procedure_id": procedure_id,
                        "approach_id": approach_id,
                        "relationship": "applicable",
                        "condition": "",
                        "triggers": [],
                        "evidence_urls": [
                            source.get("url")
                            for source in packet.get("sources") or []
                            if source.get("url")
                        ],
                        "mapping_status": "procedure_id_alias",
                    },
                }
            )
            seen.add(approach_id)
        return result

    @classmethod
    def reset(cls) -> None:
        cls.source_pages.cache_clear()
        cls.packets.cache_clear()
        cls.mappings.cache_clear()
        cls.procedure_id_alias_map.cache_clear()
        cls.procedure_approach_alias_map.cache_clear()
