"""Fast, bounded Pocket-Pimp-style retrieval for the web-only CasePrep v1.1 preview.

The legacy retriever is deliberately untouched. This module creates one embedding,
runs three scoped Pinecone queries concurrently, preserves native Q/A fields, and
reranks/deduplicates before returning a small candidate set.
"""

from __future__ import annotations

import hashlib
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

BRANCH_TOP_K = 24
MAX_RAW_CANDIDATES = BRANCH_TOP_K * 3
MAX_FINAL_QAS = 15
MIN_VECTOR_SCORE = 0.45
POCKET_PIMP_SOURCE_COLLECTION = "pocket_pimped"


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _clean(value).lower()).strip("_")


def _strings(value: Any) -> List[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    return [_slug(item) for item in values if _slug(item)]


def normalize_query(refined: Any) -> Dict[str, Any]:
    row = refined if isinstance(refined, dict) else {}
    search_text = _clean(row.get("search_text") or row.get("raw_prompt") or refined)
    approaches = _strings(row.get("approaches") or row.get("approach"))
    lowered = search_text.lower()
    if not approaches:
        for explicit in ("posterior", "anterior", "lateral", "medial", "volar", "dorsal"):
            if re.search(rf"\b{explicit}\b", lowered):
                approaches.append(explicit)
    return {
        "search_text": search_text,
        "specialties": _strings(row.get("specialties") or row.get("specialty")),
        "region": _slug(row.get("region")),
        "subregion": _slug(row.get("subregion")),
        "diagnoses": _strings(row.get("diagnoses") or row.get("diagnosis")),
        "procedures": _strings(row.get("procedures") or row.get("procedure")),
        "approaches": approaches,
    }


def embedding_text(query: Dict[str, Any]) -> str:
    anchors: List[str] = []
    for key in ("procedures", "diagnoses", "approaches", "specialties"):
        if query[key]:
            anchors.append(f"{key}: {' '.join(query[key])}")
    for key in ("region", "subregion"):
        if query[key]:
            anchors.append(f"{key}: {query[key]}")
    return " | ".join([query["search_text"], *anchors]).strip(" |")


def _and_filter(clauses: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    kept: List[Dict[str, Any]] = []
    for clause in clauses:
        if not clause:
            continue
        nested = clause.get("$and") if isinstance(clause, dict) else None
        if isinstance(nested, list):
            kept.extend(part for part in nested if isinstance(part, dict) and part)
        else:
            kept.append(clause)
    if not kept:
        return None
    return kept[0] if len(kept) == 1 else {"$and": kept}


def build_query_branches(query: Dict[str, Any]) -> List[Tuple[str, Optional[Dict[str, Any]]]]:
    procedure = {"procedures": {"$in": query["procedures"]}} if query["procedures"] else {}
    diagnosis = {"diagnoses": {"$in": query["diagnoses"]}} if query["diagnoses"] else {}
    region = {"region": {"$eq": query["region"]}} if query["region"] else {}
    subregion = {"subregion": {"$eq": query["subregion"]}} if query["subregion"] else {}
    specialty = {"specialty": {"$in": query["specialties"]}} if query["specialties"] else {}
    pocket_pimp = {
        "$and": [
            {"source_collection": {"$eq": POCKET_PIMP_SOURCE_COLLECTION}},
            {"content_type": {"$eq": "qa"}},
        ]
    }
    scoped = _and_filter([procedure, diagnosis, subregion, region, specialty])
    strict_metadata = os.getenv("CASEPREP_POCKET_PIMP_METADATA_READY", "").lower() in {
        "1", "true", "yes", "on",
    }
    proposed = [
        ("pocket_pimped", _and_filter([pocket_pimp, scoped or region or specialty])),
        ("exact_scope", _and_filter([procedure, diagnosis, subregion, region, specialty])),
        ("procedure_focus", _and_filter([procedure, region])),
        ("regional_backup", _and_filter([region, specialty])),
    ]
    if strict_metadata:
        proposed = [
            (name, _and_filter([pocket_pimp, filter_value]))
            for name, filter_value in proposed[1:]
        ]
    branches: List[Tuple[str, Optional[Dict[str, Any]]]] = []
    seen: set[str] = set()
    for name, filter_value in proposed:
        if filter_value is None:
            continue
        key = repr(filter_value)
        if key not in seen:
            seen.add(key)
            branches.append((name, filter_value))
    # Always include a semantic branch: legacy vectors predate the metadata
    # backfill (empty `procedures`, no `source_collection`), so scoped branches
    # alone can return nothing for well-covered procedures. The reranker's
    # metadata boosts and `_scope_compatible` guard keep cross-procedure
    # contamination out of the final set. Once the backfill is live (strict
    # mode) the fallback stays source-filtered to Pocket Pimped Q/A.
    fallback_filter = pocket_pimp if strict_metadata else None
    if repr(fallback_filter) not in seen:
        branches.append(("semantic_fallback", fallback_filter))
    return branches


def _response_matches(response: Any) -> Iterable[Any]:
    if isinstance(response, dict):
        return response.get("matches") or []
    return getattr(response, "matches", None) or []


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return {
        "id": getattr(value, "id", None),
        "score": getattr(value, "score", None),
        "metadata": getattr(value, "metadata", None),
    }


def _qa_from_text(text: str) -> Tuple[str, str, str]:
    match = re.search(
        r"(?:^|\s)Q:\s*(.*?)\s+A:\s*(.*?)(?:\s+(?:Note|Specialty|Region|Subregion|Diagnosis|Procedure):|$)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return "", "", ""
    question = _clean(match.group(1))
    answer = _clean(match.group(2))
    note_match = re.search(r"\bNote:\s*(.*?)(?:\s+(?:Specialty|Region|Subregion|Diagnosis|Procedure):|$)", text, re.I)
    return question, answer, _clean(note_match.group(1)) if note_match else ""


def normalize_match(match: Any, branch: str) -> Optional[Dict[str, Any]]:
    row = _as_dict(match)
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    score = float(row.get("score") or 0.0)
    if score < MIN_VECTOR_SCORE:
        return None
    text = _clean(metadata.get("text") or metadata.get("fact") or row.get("text"))
    parsed_q, parsed_a, parsed_note = _qa_from_text(text)
    question = _clean(metadata.get("question") or parsed_q)
    answer = _clean(metadata.get("answer") or parsed_a)
    if not question or not answer:
        return None
    additional = _clean(metadata.get("additional_info") or metadata.get("note") or parsed_note)
    record_id = _clean(row.get("id")) or hashlib.sha1(
        f"{question}\0{answer}".encode("utf-8")
    ).hexdigest()[:16]
    source = _clean(metadata.get("source"))
    source_collection = _slug(metadata.get("source_collection"))
    if not source_collection and "pocketpimp" in _slug(source).replace("_", ""):
        source_collection = POCKET_PIMP_SOURCE_COLLECTION
    return {
        "record_id": record_id,
        "question": question,
        "answer": answer,
        "additional_info": additional,
        "source": source,
        "source_collection": source_collection,
        "content_type": _slug(metadata.get("content_type")) or "qa",
        "specialties": _strings(metadata.get("specialties") or metadata.get("specialty")),
        "region": _slug(metadata.get("region")),
        "subregion": _slug(metadata.get("subregion")),
        "diagnoses": _strings(metadata.get("diagnoses") or metadata.get("diagnosis")),
        "procedures": _strings(metadata.get("procedures") or metadata.get("procedure")),
        "approaches": _strings(metadata.get("approaches") or metadata.get("approach")),
        "vector_score": score,
        "retrieval_branch": branch,
    }


def _overlap(expected: Sequence[str], actual: Sequence[str]) -> float:
    if not expected or not actual:
        return 0.0
    return len(set(expected) & set(actual)) / max(1, len(set(expected)))


_BIGRAM_STOP = {
    "a", "an", "and", "are", "for", "how", "in", "is", "of", "on", "the",
    "to", "what", "when", "which", "with",
}


def _bigrams(text: str) -> set[str]:
    tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", str(text or "").lower())
        if token not in _BIGRAM_STOP
    ]
    return {f"{left} {right}" for left, right in zip(tokens, tokens[1:])}


def score_candidate(candidate: Dict[str, Any], query: Dict[str, Any]) -> float:
    score = candidate["vector_score"] * 0.55
    score += _overlap(query["procedures"], candidate["procedures"]) * 0.20
    score += _overlap(query["diagnoses"], candidate["diagnoses"]) * 0.10
    score += _overlap(query["approaches"], candidate["approaches"]) * 0.05
    if query["region"] and candidate["region"] == query["region"]:
        score += 0.07
    if query["subregion"] and candidate["subregion"] == query["subregion"]:
        score += 0.03
    if candidate["retrieval_branch"] == "exact_scope":
        score += 0.03
    if candidate.get("source_collection") == POCKET_PIMP_SOURCE_COLLECTION:
        score += 0.08
    if candidate.get("content_type") == "qa":
        score += 0.02
    if len(candidate["answer"]) >= 3:
        score += 0.02
    # Lexical anchor: legacy vectors carry no procedure metadata, so shared
    # clinical bigrams ("distal radius", "carpal tunnel") separate on-procedure
    # Q/A from generic same-technique content ("...ORIF of the clavicle").
    query_bigrams = _bigrams(query["search_text"])
    if query_bigrams:
        candidate_bigrams = _bigrams(f"{candidate['question']} {candidate['answer']}")
        score += min(0.15, 0.05 * len(query_bigrams & candidate_bigrams))
    return round(score, 6)


_ANCHOR_STOP = _BIGRAM_STOP | {
    "about", "all", "approach", "case", "common", "do", "does", "fracture", "have",
    "help", "i", "know", "me", "my", "need", "open", "orif", "patient", "prep",
    "prepare", "primary", "procedure", "questions", "repair", "steps", "surgery",
    "surgical", "that", "tomorrow", "you", "your",
}


def _anchor_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", str(text or "").lower())
        if len(token) > 3 and token not in _ANCHOR_STOP
    }


def _approach_anchor_tokens() -> set[str]:
    """Approach/laterality words, from the resolver's single source of truth.

    An approach word ("volar", "henry", "posterior") is shared across many
    operations, so a Q/A that overlaps the case only on an approach word is not
    on-topic — that is how thumb/finger content ("volar-ulnar base fragment")
    leaked into a Galeazzi packet. Excluded from relevance anchoring, exactly as
    they are excluded from procedure identity in procedure_registry.
    """
    try:
        from procedure_registry import _APPROACH_TOKENS

        return set(_APPROACH_TOKENS)
    except Exception:
        return set()


def query_anchors(query: Dict[str, Any]) -> set[str]:
    """Vocabulary a Q/A must touch to plausibly be about this case."""
    anchors = _anchor_tokens(query["search_text"])
    for slug in query["procedures"]:
        anchors |= _anchor_tokens(slug.replace("_", " "))
    for key in ("region", "subregion"):
        anchors |= _anchor_tokens(query[key])
    for values in (query["diagnoses"], query["specialties"]):
        for value in values:
            anchors |= _anchor_tokens(value.replace("_", " "))
    return anchors - _approach_anchor_tokens()


def _scope_compatible(candidate: Dict[str, Any], query: Dict[str, Any]) -> bool:
    """Reject explicit cross-procedure/approach metadata before reranking."""
    if query["procedures"] and candidate["procedures"]:
        if not set(query["procedures"]) & set(candidate["procedures"]):
            return False
    if query["approaches"] and candidate["approaches"]:
        if not set(query["approaches"]) & set(candidate["approaches"]):
            return False
    if candidate["retrieval_branch"] == "semantic_fallback":
        # This branch is deliberately unfiltered, so vector similarity is the
        # only thing keeping it on-topic — and embeddings happily rank "portal
        # placement in elbow arthroscopy" against a biceps case. Require one
        # shared anchor word with the case before it can reach the packet.
        anchors = query_anchors(query)
        if anchors:
            candidate_text = f"{candidate['question']} {candidate['answer']} {candidate['additional_info']}"
            if not (anchors & _anchor_tokens(candidate_text)):
                return False
    text = _clean(" ".join((candidate["question"], candidate["answer"], candidate["additional_info"]))).lower()
    approaches = set(query["approaches"])
    if any("posterior" in item for item in approaches):
        if "lateral femoral cutaneous nerve" in text or "direct anterior interval" in text:
            return False
    return True


def _question_tokens(question: str) -> set[str]:
    stop = {"a", "an", "and", "are", "for", "in", "is", "of", "the", "to", "what", "which"}
    return {token for token in re.findall(r"[a-z0-9]+", question.lower()) if token not in stop}


def _near_duplicate(left: str, right: str) -> bool:
    a, b = _question_tokens(left), _question_tokens(right)
    if not a or not b:
        return _slug(left) == _slug(right)
    return len(a & b) / len(a | b) >= 0.78


def rerank_and_dedupe(
    candidates: Sequence[Dict[str, Any]], query: Dict[str, Any], limit: int = MAX_FINAL_QAS
) -> List[Dict[str, Any]]:
    ranked = []
    for candidate in candidates:
        if not _scope_compatible(candidate, query):
            continue
        item = dict(candidate)
        item["retrieval_score"] = score_candidate(item, query)
        ranked.append(item)
    ranked.sort(key=lambda item: (item["retrieval_score"], item["vector_score"]), reverse=True)

    selected: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in ranked:
        if item["record_id"] in seen_ids:
            continue
        if any(_near_duplicate(item["question"], kept["question"]) for kept in selected):
            continue
        seen_ids.add(item["record_id"])
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def _retrieval_cache_key(query: Dict[str, Any], top_k: int, limit: int) -> str:
    slug_scope = "+".join(sorted(query["procedures"])) or hashlib.sha1(
        query["search_text"].encode("utf-8")
    ).hexdigest()[:16]
    approach_scope = "+".join(sorted(query["approaches"]))
    return f"{slug_scope}|{approach_scope}|{top_k}|{limit}"


def retrieve_case_qas(
    refined: Any,
    *,
    embed_fn: Optional[Callable[[str], List[float]]] = None,
    index_obj: Any = None,
    top_k: int = BRANCH_TOP_K,
    limit: int = MAX_FINAL_QAS,
    diagnostics: Optional[Dict[str, Any]] = None,
    use_cache: bool = True,
) -> List[Dict[str, Any]]:
    from caseprep.services.ttl_cache import retrieval_cache

    query = normalize_query(refined)
    cache_key = _retrieval_cache_key(query, top_k, limit)
    if use_cache:
        cached = retrieval_cache.get(cache_key)
        if cached is not None:
            selected, cached_diagnostics = cached
            if diagnostics is not None:
                diagnostics.update(cached_diagnostics)
                diagnostics["cache_hit"] = True
            return [dict(item) for item in selected]
    if embed_fn is None or index_obj is None:
        import vector_search

        embed_fn = embed_fn or vector_search.embed_text
        index_obj = index_obj or vector_search.index

    embed_started = time.monotonic()
    vector = embed_fn(embedding_text(query))
    embed_ms = int((time.monotonic() - embed_started) * 1000)
    branches = build_query_branches(query)

    def run_branch(name: str, filter_value: Optional[Dict[str, Any]]) -> Tuple[str, Any]:
        kwargs: Dict[str, Any] = {
            "vector": vector,
            "top_k": top_k,
            "include_metadata": True,
        }
        if filter_value:
            kwargs["filter"] = filter_value
        return name, index_obj.query(**kwargs)

    raw: List[Dict[str, Any]] = []
    branch_counts: Dict[str, int] = {}
    failed_branches: List[str] = []
    query_started = time.monotonic()
    with ThreadPoolExecutor(max_workers=len(branches)) as pool:
        futures = {pool.submit(run_branch, name, filt): name for name, filt in branches}
        for future in as_completed(futures):
            try:
                branch, response = future.result()
            except Exception:
                # One Pinecone branch must not discard successful sibling branches.
                failed_branches.append(futures[future])
                continue
            branch_counts[branch] = 0
            for match in _response_matches(response):
                normalized = normalize_match(match, branch)
                if normalized:
                    raw.append(normalized)
                    branch_counts[branch] += 1
                if len(raw) >= top_k * len(branches):
                    break
    query_ms = int((time.monotonic() - query_started) * 1000)
    # Rescue-mode fallback: unfiltered semantic candidates participate only
    # when the metadata-scoped branches under-deliver, so cases with working
    # scope filters keep their zero-contamination behavior.
    scoped_raw = [c for c in raw if c["retrieval_branch"] != "semantic_fallback"]
    if len(scoped_raw) >= limit:
        raw = scoped_raw
    selected = rerank_and_dedupe(raw, query, limit=limit)
    run_diagnostics = {
        "embedding_count": 1,
        "embedding_ms": embed_ms,
        "pinecone_query_ms": query_ms,
        "branch_count": len(branches),
        "branch_candidate_counts": branch_counts,
        "failed_branches": sorted(failed_branches),
        "raw_candidate_count": len(raw),
        "selected_count": len(selected),
    }
    if diagnostics is not None:
        diagnostics.update(run_diagnostics)
        diagnostics["cache_hit"] = False
    if use_cache and selected and not failed_branches:
        retrieval_cache.set(cache_key, ([dict(item) for item in selected], run_diagnostics))
    return selected
