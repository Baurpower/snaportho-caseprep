"""ROCK curriculum grounding for CasePrep + Chat.

Queries the `rock-v1` Pinecone namespace (see
../snaportho-web/docs/education/rock-v1-schema.md) and returns authoritative AAOS
ROCK chapter passages + canonical citations to ground LLM answers.

Two entry paths:
  resolve_rock_context_by_text(query)   -- free-text / procedure-anchored (vector search)
  resolve_rock_context_by_chapters(ids) -- card-anchored (direct chapter fetch; ids come
                                           from the published overlay's ROCK_Link)

Everything is flag-gated (CASEPREP_ROCK_GROUNDING_ENABLED, default off). Grounding text is
length-capped per passage so downstream prompts can enforce an anti-verbatim policy on
copyrighted ROCK content.
"""
from __future__ import annotations

import os
import re
from typing import Any, Callable, Dict, List, Optional

ROCK_NAMESPACE = os.getenv("ROCK_PINECONE_NAMESPACE", "rock-v1")
SOURCE_COLLECTION = "rock"

# Guardrails (see docs/education/rock-v1-schema.md + the grounding prompt).
DEFAULT_TOP_K = 12          # raw chunk hits to pull before de-duping to chapters
DEFAULT_MAX_CHAPTERS = 3    # distinct chapters returned
DEFAULT_MAX_PASSAGES = 2    # passages per chapter fed as grounding
MAX_PASSAGE_CHARS = 700     # per-passage cap handed to the model
MIN_SCORE = 0.35            # drop weak semantic matches


def rock_grounding_enabled() -> bool:
    # On by default (rock-v1 is live and grounding is error-safe + additive).
    # Set CASEPREP_ROCK_GROUNDING_ENABLED=false to disable.
    return os.getenv("CASEPREP_ROCK_GROUNDING_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


def _clip(text: str, limit: int = MAX_PASSAGE_CHARS) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    sp = cut.rfind(" ")
    return (cut[:sp] if sp > limit * 0.6 else cut).rstrip() + "…"


def _matches(resp: Any) -> List[Dict[str, Any]]:
    if isinstance(resp, dict):
        return resp.get("matches") or []
    return list(getattr(resp, "matches", None) or [])


def _md(m: Any) -> Dict[str, Any]:
    if isinstance(m, dict):
        return m.get("metadata") or {}
    return getattr(m, "metadata", None) or {}


def _score(m: Any) -> float:
    return float((m.get("score") if isinstance(m, dict) else getattr(m, "score", 0.0)) or 0.0)


def _chapters_from_matches(
    matches: List[Dict[str, Any]], max_chapters: int, max_passages: int
) -> List[Dict[str, Any]]:
    ordered: List[str] = []
    by_id: Dict[str, Dict[str, Any]] = {}
    for m in matches:
        if _score(m) < MIN_SCORE:
            continue
        md = _md(m)
        cid = str(md.get("chapter_id") or "")
        if not cid:
            continue
        if cid not in by_id:
            if len(ordered) >= max_chapters:
                continue
            ordered.append(cid)
            by_id[cid] = {
                "chapter_id": cid,
                "canonical_id": str(md.get("canonical_id") or cid),
                "title": md.get("title") or "",
                "url": md.get("url") or "",
                "passages": [],
                "top_score": round(_score(m), 4),
            }
        entry = by_id[cid]
        if len(entry["passages"]) < max_passages:
            passage = _clip(md.get("text") or "")
            if passage:
                entry["passages"].append(passage)
    return [by_id[c] for c in ordered if by_id[c]["passages"]]


def _index_and_embed(index_obj, embed_fn):
    if index_obj is None or embed_fn is None:
        import vector_search
        index_obj = index_obj or vector_search.index
        embed_fn = embed_fn or vector_search.embed_text
    return index_obj, embed_fn


def resolve_rock_context_by_text(
    query_text: str,
    *,
    top_k: int = DEFAULT_TOP_K,
    max_chapters: int = DEFAULT_MAX_CHAPTERS,
    max_passages: int = DEFAULT_MAX_PASSAGES,
    index_obj: Any = None,
    embed_fn: Optional[Callable[[str], List[float]]] = None,
) -> Dict[str, Any]:
    """Free-text / procedure-anchored ROCK grounding via vector search on rock-v1."""
    if not (query_text or "").strip():
        return {"chapters": [], "retrieval": "empty_query"}
    try:
        index_obj, embed_fn = _index_and_embed(index_obj, embed_fn)
        vector = embed_fn(query_text)
        resp = index_obj.query(
            namespace=ROCK_NAMESPACE,
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            filter={"source_collection": {"$eq": SOURCE_COLLECTION}},
        )
    except Exception as exc:  # never let grounding break the packet
        return {"chapters": [], "retrieval": "error", "error": type(exc).__name__}
    chapters = _chapters_from_matches(_matches(resp), max_chapters, max_passages)
    return {"chapters": chapters, "retrieval": "vector"}


def resolve_rock_context_by_chapters(
    chapter_ids: List[str],
    *,
    max_chapters: int = DEFAULT_MAX_CHAPTERS,
    max_passages: int = DEFAULT_MAX_PASSAGES,
    index_obj: Any = None,
) -> Dict[str, Any]:
    """Card-anchored ROCK grounding: fetch top chunks for known chapter ids (from the
    published overlay's ROCK_Link). No embedding needed."""
    ids = [str(c) for c in (chapter_ids or []) if str(c).strip()][:max_chapters]
    if not ids:
        return {"chapters": [], "retrieval": "no_chapters"}
    try:
        index_obj, _ = _index_and_embed(index_obj, lambda _t: [])
        chapters: List[Dict[str, Any]] = []
        for cid in ids:
            # ids are `{chapter_id}#{chunk_index:04d}`; list the first N chunk ids by
            # prefix and fetch them (embedding-free, deterministic ordering).
            vids: List[str] = []
            for pg in index_obj.list(namespace=ROCK_NAMESPACE, prefix=f"{cid}#"):
                vids.extend(pg if isinstance(pg, list) else [pg])
            vids = sorted(vids)[:max_passages]
            if not vids:
                continue
            res = index_obj.fetch(ids=vids, namespace=ROCK_NAMESPACE)
            vectors = res.vectors if hasattr(res, "vectors") else res.get("vectors", {})
            rows = [(vid, (v.metadata if hasattr(v, "metadata") else v.get("metadata")) or {})
                    for vid, v in vectors.items()]
            rows.sort(key=lambda r: int(r[1].get("chunk_index") or 0))
            if not rows:
                continue
            first = rows[0][1]
            passages = [_clip(md.get("text") or "") for _, md in rows[:max_passages]]
            chapters.append({
                "chapter_id": cid,
                "canonical_id": str(first.get("canonical_id") or cid),
                "title": first.get("title") or "",
                "url": first.get("url") or "",
                "passages": [p for p in passages if p],
            })
    except Exception as exc:
        return {"chapters": [], "retrieval": "error", "error": type(exc).__name__}
    return {"chapters": chapters, "retrieval": "chapter_fetch"}


def chapter_ids_from_rock_link(rock_link: Optional[str]) -> List[str]:
    """Extract ROCK chapter id(s) from a published overlay ROCK_Link URL
    (https://rock.aaos.org/coursecontent.aspx?id=NNNN)."""
    if not rock_link:
        return []
    return re.findall(r"[?&]id=(\d+)", str(rock_link))


def format_grounding_block(context: Dict[str, Any]) -> str:
    """Render a compact, attributed grounding block for an LLM prompt.
    The consuming prompt must instruct: synthesize, do not quote verbatim, always cite."""
    chapters = (context or {}).get("chapters") or []
    if not chapters:
        return ""
    lines = ["AUTHORITATIVE SOURCE — AAOS ROCK curriculum (synthesize, do not copy verbatim; cite the chapter):"]
    for ch in chapters:
        lines.append(f"\n[{ch['title']}] ({ch['url']})")
        for p in ch["passages"]:
            lines.append(f"  - {p}")
    return "\n".join(lines)
