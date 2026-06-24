"""Filesystem paths for the content factory."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = ROOT / "data" / "caseprep" / "procedures"
ANATOMY_ROOT = ROOT / "data" / "anatomy"
GLOBAL_SOURCES_PATH = ANATOMY_ROOT / "sources" / "orthobullets_sources.jsonl"
PLAYBOOK_PATH = ROOT / "data" / "approach_playbook" / "orthobullets_procedure_playbook_v1.jsonl"
APPROACH_MAP_PATH = ROOT / "data" / "approach_playbook" / "procedure_to_approach_map_v1.jsonl"

MODULES_FILENAME = "modules.json"
MANIFEST_FILENAME = "manifest.json"
EXTRACTED_KNOWLEDGE_FILENAME = "extracted_knowledge.json"
GENERATION_META_FILENAME = "generation_meta.json"
CERTIFIED_PAYLOAD_FILENAME = "certified_payload.json"
DRAFT_PAYLOAD_FILENAME = "certified_payload.draft.json"
SOURCES_FILENAME = "sources.jsonl"


def procedure_dir(slug: str) -> Path:
    return REGISTRY_ROOT / slug