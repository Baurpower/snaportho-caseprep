"""
Source extraction from existing on-disk libraries (no web scraping).
"""

from __future__ import annotations

import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from caseprep.factory.paths import (
    GLOBAL_SOURCES_PATH,
    PLAYBOOK_PATH,
    SOURCES_FILENAME,
    procedure_dir,
)
from caseprep.factory.schemas import ExtractedKnowledge, SourcedClaim

def _playbook_helpers():
    try:
        from playbook_anatomy_builder import build_playbook_anatomy, _get_entry as get_playbook_entry

        return build_playbook_anatomy, get_playbook_entry
    except Exception:
        return None, None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _clean_text(value: Any, *, min_len: int = 12) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) < min_len:
        return None
    if text.startswith("{") and "'structure'" in text:
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, dict):
                parts = [str(parsed.get(k, "")) for k in ("text", "structure", "landmark", "why_it_matters")]
                text = " ".join(p for p in parts if p).strip()
        except (SyntaxError, ValueError):
            pass
    low = text.lower()
    if any(
        bad in low
        for bad in (
            "key approach for this case",
            "primary structure at risk?",
            "per map evidence",
            "see source-backed",
        )
    ):
        return None
    return text if len(text) >= min_len else None


def _claim(
    text: str,
    *,
    source_id: Optional[str] = None,
    source_url: Optional[str] = None,
    confidence: str = "medium",
) -> SourcedClaim:
    return SourcedClaim(
        text=text,
        source_id=source_id,
        source_url=source_url,
        confidence=confidence,
    )


def _dict_to_sar(item: Dict[str, Any], source_url: Optional[str] = None) -> Dict[str, Any]:
    structure = _clean_text(item.get("structure") or item.get("text"), min_len=3)
    if not structure:
        return {}
    return {
        "structure": structure,
        "why_at_risk": _clean_text(item.get("why_at_risk") or item.get("why_it_matters"), min_len=8) or "At risk during exposure or fixation for this procedure.",
        "how_to_avoid_injury": _clean_text(item.get("how_to_avoid_injury") or item.get("how_to_avoid"), min_len=8) or "Identify early, use blunt dissection, and limit retractor force.",
        "consequence_of_injury": _clean_text(item.get("consequence_of_injury") or item.get("consequence"), min_len=8) or "Functional deficit or need for secondary repair.",
        "approach_context": _clean_text(item.get("approach_context"), min_len=3),
        "source_refs": [u for u in [source_url or item.get("source_url")] if u],
    }


def _collect_global_sources(slug: str) -> List[Dict[str, Any]]:
    rows = _load_jsonl(GLOBAL_SOURCES_PATH)
    return [r for r in rows if slug in (r.get("procedure_ids") or [])]


def _recommended_approach_ids(slug: str) -> List[str]:
    if not PLAYBOOK_PATH.exists():
        return []
    for row in _load_jsonl(PLAYBOOK_PATH):
        if row.get("procedure_id") == slug:
            return list(row.get("recommended_approach_ids") or [])
    return []


def extract_knowledge(
    slug: str,
    *,
    manifest: Optional[Dict[str, Any]] = None,
) -> ExtractedKnowledge:
    folder = procedure_dir(slug)
    manifest = manifest or {}
    display_name = str(manifest.get("display_name") or slug)

    local_sources = _load_jsonl(folder / SOURCES_FILENAME)
    global_sources = _collect_global_sources(slug)
    all_sources = local_sources + [
        g for g in global_sources if g.get("url") not in {s.get("url") for s in local_sources}
    ]

    source_ids: List[str] = []
    source_urls: Set[str] = set()
    warnings: List[str] = []

    setup: List[SourcedClaim] = []
    landmarks: List[SourcedClaim] = []
    sar_rows: List[Dict[str, Any]] = []
    layers: List[Dict[str, Any]] = []
    implant: List[SourcedClaim] = []
    fluoro: List[SourcedClaim] = []
    complications: List[SourcedClaim] = []
    postop: List[SourcedClaim] = []
    pimp_facts: List[SourcedClaim] = []
    indications: List[SourcedClaim] = []
    contraindications: List[SourcedClaim] = []

    seen_text: Set[str] = set()

    def add_claim(bucket: List[SourcedClaim], text: Optional[str], **kwargs: Any) -> None:
        if not text:
            return
        key = text.lower()[:120]
        if key in seen_text:
            return
        seen_text.add(key)
        bucket.append(_claim(text, **kwargs))

    for src in all_sources:
        sid = str(src.get("source_id") or src.get("url") or "")
        url = str(src.get("url") or "").strip()
        if sid:
            source_ids.append(sid)
        if url:
            source_urls.add(url)

        for fact in src.get("extracted_facts") or []:
            text = _clean_text(fact)
            if text:
                add_claim(setup, text, source_id=sid, source_url=url)

        for lm in src.get("landmarks") or []:
            text = _clean_text(lm)
            if text:
                add_claim(landmarks, text, source_id=sid, source_url=url)

        for risk in src.get("structures_at_risk") or []:
            if isinstance(risk, dict):
                row = _dict_to_sar(risk, url)
            else:
                text = _clean_text(risk)
                row = (
                    {
                        "structure": text,
                        "why_at_risk": "Identified in source library as at-risk structure for this approach.",
                        "how_to_avoid_injury": "Maintain direct visualization and controlled retraction.",
                        "consequence_of_injury": "Iatrogenic injury with functional consequences.",
                        "source_refs": [url] if url else [],
                    }
                    if text
                    else {}
                )
            if row.get("structure"):
                sar_rows.append(row)

    build_playbook_anatomy, get_playbook_entry = _playbook_helpers()

    # Playbook enrichment
    if get_playbook_entry is not None:
        entry = get_playbook_entry(slug)
        if entry:
            for item in entry.get("important_anatomy") or []:
                if isinstance(item, dict):
                    text = _clean_text(item.get("text"))
                    url = item.get("source_url")
                else:
                    text = _clean_text(item)
                    url = None
                add_claim(setup, text, source_url=url, confidence="high")

            for item in entry.get("landmarks") or []:
                text = _clean_text(item.get("text") if isinstance(item, dict) else item)
                url = item.get("source_url") if isinstance(item, dict) else None
                add_claim(landmarks, text, source_url=url, confidence="high")

            for item in entry.get("structures_at_risk") or []:
                if isinstance(item, dict):
                    row = _dict_to_sar(item)
                    if row.get("structure"):
                        sar_rows.append(row)
                else:
                    text = _clean_text(item)
                    if text:
                        sar_rows.append(
                            {
                                "structure": text,
                                "why_at_risk": "Playbook-identified structure at risk.",
                                "how_to_avoid_injury": "Protect with retractors and anatomic dissection.",
                                "consequence_of_injury": "Functional deficit if injured.",
                                "source_refs": list(entry.get("orthobullets_urls") or [])[:1],
                            }
                        )

            for topic in entry.get("pimp_topics") or []:
                text = _clean_text(topic)
                add_claim(pimp_facts, text, confidence="medium")

            if entry.get("manual_review"):
                warnings.append(
                    f"Playbook flags manual_review: {entry.get('review_reason') or 'unspecified'}"
                )
        else:
            warnings.append("No playbook entry found for procedure.")

    if build_playbook_anatomy is not None:
        try:
            pb = build_playbook_anatomy(slug, _recommended_approach_ids(slug))
            for note in pb.get("approach", {}).get("notes") or []:
                add_claim(setup, _clean_text(note), confidence="high")
        except Exception as exc:
            warnings.append(f"Playbook anatomy build failed: {exc}")

    if not all_sources:
        warnings.append("No orthobullets source records linked to this procedure.")
    if not sar_rows:
        warnings.append("No structures_at_risk extracted from sources.")
    if not landmarks:
        warnings.append("No approach landmarks extracted from sources.")

    # Confidence: fraction of buckets populated
    buckets = [setup, landmarks, sar_rows, pimp_facts]
    populated = sum(1 for b in buckets if b)
    confidence = round(min(1.0, populated / 4.0) * 0.6 + min(1.0, len(source_urls) / 2.0) * 0.4, 2)

    return ExtractedKnowledge(
        procedure_id=slug,
        display_name=display_name,
        extracted_at=_utc_now_iso(),
        source_ids=sorted(set(source_ids)),
        indications=indications,
        contraindications=contraindications,
        setup_positioning=setup,
        approach_landmarks=landmarks,
        surgical_layers=layers,
        structures_at_risk=sar_rows,
        implant_strategy=implant,
        reduction_or_fluoro_checkpoints=fluoro,
        complications=complications,
        postop_protocol=postop,
        pimp_question_facts=pimp_facts,
        source_refs=sorted(source_urls),
        extraction_warnings=warnings,
        confidence_score=confidence,
    )


def write_extracted_knowledge(slug: str, knowledge: ExtractedKnowledge) -> Path:
    path = procedure_dir(slug) / "extracted_knowledge.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(knowledge.model_dump(), handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path