import json
import os
import re
import time
from collections import Counter
from html import unescape
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
from pydantic import BaseModel, Field


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX")

EMBED_MODEL = "text-embedding-3-small"
CLEANUP_MODEL = os.getenv("ANKI_ORTHO_CONTEXT_CLEANUP_MODEL") or os.getenv(
    "ANKI_ORTHO_CONTEXT_MODEL",
    "gpt-4o-mini",
)
FAST_TOP_K = 18
MAX_SOURCE_MATCHES = 10
MAX_BUCKET_ITEMS = 4
MAX_FLAT_RELATED_QUESTIONS = 10
MAX_HIGH_YIELD_CONCEPTS = 5
MAX_RAPID_ASSOCIATIONS = 5
MAX_RELATED_TOPICS = 8
CLEANUP_GPT_TIMEOUT_SECONDS = float(
    os.getenv("ANKI_ORTHO_CONTEXT_CLEANUP_TIMEOUT", "1.75")
)
MAX_CLEANUP_GPT_ITEMS = 4
RELEVANCE_DEBUG = os.getenv("ANKI_ORTHO_CONTEXT_RELEVANCE_DEBUG", "").lower() in {
    "1",
    "true",
    "yes",
}

# Only the curated pimp-question corpus should be used for the MVP.
# `Millers` is confirmed by the current QA ingestion script.
# The Pocket Pimped label is not confirmed in this repo yet, so keep the
# constant explicit and easy to update once the exact source label is known.
UNCONFIRMED_POCKET_PIMP_SOURCE_LABEL = "Pocket Pimped"
CURATED_PIMP_SOURCE_ALLOWLIST = (
    "Millers",
    UNCONFIRMED_POCKET_PIMP_SOURCE_LABEL,
)


class AnkiOrthoContextRequest(BaseModel):
    note_id: Optional[str] = None
    card_id: Optional[str] = None
    deck: Optional[str] = None
    front: str
    back: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    mode: str = "fast"


_OPENAI_CLIENT: Optional[OpenAI] = None
_PINECONE_INDEX = None


def _get_openai_client() -> OpenAI:
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT is None:
        if not OPENAI_API_KEY:
            raise ValueError("Missing OPENAI_API_KEY.")
        _OPENAI_CLIENT = OpenAI(
            api_key=OPENAI_API_KEY,
            project=OPENAI_PROJECT_ID,
            timeout=30.0,
        )
    return _OPENAI_CLIENT


def _get_pinecone_index():
    global _PINECONE_INDEX
    if _PINECONE_INDEX is None:
        if not PINECONE_API_KEY or not PINECONE_INDEX_NAME:
            raise ValueError("Missing PINECONE_API_KEY or PINECONE_INDEX.")
        pc = Pinecone(api_key=PINECONE_API_KEY)
        _PINECONE_INDEX = pc.Index(PINECONE_INDEX_NAME)
    return _PINECONE_INDEX


def _strip_html(value: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", value or "")
    return unescape(no_tags)


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _fix_mojibake(value: str) -> str:
    replacements = {
        "Ð": " • ",
        "�": " ",
        "Â°": "°",
        "Â": " ",
        "â": "-",
        "â": "-",
        "â": "'",
        "â": '"',
        "â": '"',
        "Â±": "±",
    }
    for bad, good in replacements.items():
        value = value.replace(bad, good)
    return value


def _remove_markdown_artifacts(value: str) -> str:
    value = re.sub(r"`{3}.*?`{3}", " ", value, flags=re.S)
    value = re.sub(r"(?m)^\s*#{1,6}\s*", "", value)
    value = re.sub(r"(?m)^\s*>+\s*", "", value)
    value = re.sub(r"(?m)^\s*[_*`~]+\s*", "", value)
    value = re.sub(r"(?m)\s*[_*`~]{2,}\s*", " ", value)
    value = re.sub(r"(?m)\b[_*`~]+([A-Za-z])", r"\1", value)
    value = re.sub(r"(?m)([A-Za-z])[_*`~]+\b", r"\1", value)
    return value


def _clean_text(value: str) -> str:
    value = _strip_html(value)
    value = _fix_mojibake(value)
    value = re.sub(r"`{3}.*?`{3}", " ", value, flags=re.S)
    value = re.sub(r"\{\{c\d+::", "", value)
    value = value.replace("}}", " ")
    value = re.sub(r"\[sound:[^\]]+\]", " ", value)
    return _normalize_space(value)


def _clean_display_text(value: str) -> str:
    value = _strip_html(value)
    value = _fix_mojibake(value)
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = _remove_markdown_artifacts(value)
    value = re.sub(r"\{\{c\d+::", "", value)
    value = value.replace("}}", " ")
    value = re.sub(r"\[sound:[^\]]+\]", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = re.sub(r"(?m)^[\s>*#]+", "", value)

    separator_re = re.compile(r"\s*(?:[•·▪◦●○Ð]+|\s[-–—]\s)\s*")
    bullet_like_count = len(re.findall(r"[•·▪◦●○Ð]", value)) + len(
        re.findall(r"\s[-–—]\s", value)
    )
    if bullet_like_count >= 2 or value.lstrip().startswith(("•", "Ð", "-", "–", "—", "_")):
        parts = [
            re.sub(r"\s+", " ", re.sub(r"^[\s_*\-–—•·▪◦●○`~]+", "", part)).strip(" ;,:")
            for part in separator_re.split(value)
        ]
        parts = [part for part in parts if part]
        if len(parts) >= 2:
            return "\n".join(f"- {part}" for part in parts)

    lines = []
    for raw_line in value.split("\n"):
        line = re.sub(r"^[\s_*\-–—•·▪◦●○`~]+", "", raw_line)
        line = re.sub(r"\s+", " ", line).strip(" ;,")
        if line:
            lines.append(line)
    if len(lines) >= 2:
        return "\n".join(lines)
    return _normalize_space(" ".join(lines))


def _safe_str(value: Any) -> str:
    return _clean_text(str(value)) if value is not None else ""


def _safe_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [_clean_text(str(item)) for item in value if _clean_text(str(item))]
    cleaned = _clean_text(str(value))
    return [cleaned] if cleaned else []


def _sanitize_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_metadata(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_metadata(item) for item in value]
    if isinstance(value, str):
        return _clean_text(value)
    return value


def _has_cleanup_artifacts(value: str) -> bool:
    if not value:
        return False
    artifact_patterns = [
        "Ð",
        "�",
        "â",
        "Â",
        "__",
        "**",
        "```",
    ]
    if any(pattern in value for pattern in artifact_patterns):
        return True
    if re.search(r"[•·▪◦●○Ð].{0,3}[A-Za-z]", value):
        return True
    if re.search(r"(^|[\s(])[_*`~]+(?=\S)", value):
        return True
    return False


def _needs_cleanup_gpt(raw_value: str, cleaned_value: str) -> bool:
    if _has_cleanup_artifacts(cleaned_value):
        return True
    if _has_cleanup_artifacts(raw_value) and cleaned_value == _normalize_space(cleaned_value):
        return False
    if raw_value.count(" Ð ") >= 2 and "\n- " not in cleaned_value:
        return True
    if len(cleaned_value) > 140 and cleaned_value.count("\n") == 0 and (
        cleaned_value.count(" - ") >= 2 or cleaned_value.count(" • ") >= 2
    ):
        return True
    return False


def _cleanup_answers_with_gpt(items: List[Dict[str, str]]) -> List[str]:
    client = _get_openai_client()
    payload = [
        {
            "question": _truncate(_safe_str(item.get("question") or ""), 220),
            "answer": _truncate(_safe_str(item.get("answer") or ""), 700),
        }
        for item in items[:MAX_CLEANUP_GPT_ITEMS]
    ]
    completion = client.with_options(
        timeout=CLEANUP_GPT_TIMEOUT_SECONDS
    ).chat.completions.create(
        model=CLEANUP_MODEL,
        temperature=0.0,
        max_tokens=320,
        messages=[
            {
                "role": "system",
                "content": (
                    "Clean formatting only. Do not add facts, explanations, or new meaning. "
                    "Return JSON only with one cleaned_answer per item. Preserve medical meaning. "
                    "Fix mojibake, bullets, markdown artifacts, and broken separators. "
                    "If an answer is a list, use concise bullet lines prefixed with '- '."
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "anki_cleanup_answers",
                "schema": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "cleaned_answer": {"type": "string"}
                                },
                                "required": ["cleaned_answer"],
                                "additionalProperties": False,
                            },
                        }
                    },
                    "required": ["items"],
                    "additionalProperties": False,
                },
            },
        },
    )
    content = completion.choices[0].message.content or ""
    parsed = json.loads(content)
    cleaned_items = parsed.get("items") if isinstance(parsed, dict) else None
    if not isinstance(cleaned_items, list):
        raise ValueError("Cleanup GPT returned invalid payload.")
    outputs: List[str] = []
    for index, item in enumerate(cleaned_items[: len(payload)]):
        if not isinstance(item, dict):
            raise ValueError("Cleanup GPT item payload was invalid.")
        outputs.append(_clean_display_text(str(item.get("cleaned_answer") or "")))
    if len(outputs) != len(payload):
        raise ValueError("Cleanup GPT returned the wrong number of answers.")
    return outputs


def _sanitize_response_payload(response: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    sanitized = dict(response)
    cleanup_targets: List[Tuple[Dict[str, Any], str, str, str]] = []

    related_questions = sanitized.get("related_pimp_questions")
    if isinstance(related_questions, list):
        for item in related_questions:
            if not isinstance(item, dict):
                continue
            raw_question = str(item.get("question") or "")
            raw_answer = str(item.get("answer") or "")
            cleaned_question = _clean_display_text(raw_question)
            cleaned_answer = _clean_display_text(raw_answer)
            item["question"] = cleaned_question
            item["answer"] = cleaned_answer
            if _needs_cleanup_gpt(raw_answer, cleaned_answer):
                cleanup_targets.append((item, "answer", cleaned_question, raw_answer))

    source_matches = sanitized.get("source_matches")
    if isinstance(source_matches, list):
        for item in source_matches:
            if not isinstance(item, dict):
                continue
            raw_question = str(item.get("question") or "")
            raw_answer = str(item.get("answer") or "")
            item["question"] = _clean_display_text(raw_question) if raw_question else None
            item["answer"] = _clean_display_text(raw_answer) if raw_answer else None

    cleanup_used = False
    if cleanup_targets:
        cleanup_used = True
        cleanup_started_at = time.perf_counter()
        batch = [
            {"question": question, "answer": raw_answer}
            for _, _, question, raw_answer in cleanup_targets[:MAX_CLEANUP_GPT_ITEMS]
        ]
        try:
            cleaned_outputs = _cleanup_answers_with_gpt(batch)
            for (item, field_name, _question, raw_answer), cleaned_answer in zip(
                cleanup_targets[:MAX_CLEANUP_GPT_ITEMS],
                cleaned_outputs,
            ):
                item[field_name] = cleaned_answer or _clean_display_text(raw_answer)
            for item, field_name, _question, raw_answer in cleanup_targets[MAX_CLEANUP_GPT_ITEMS:]:
                item[field_name] = _clean_display_text(raw_answer)
        except Exception:
            for item, field_name, _question, raw_answer in cleanup_targets:
                item[field_name] = _clean_display_text(raw_answer)
        _log_timing("cleanup_gpt", cleanup_started_at)

    return sanitized, cleanup_used


def _dedupe_strings(values: Iterable[str]) -> List[str]:
    seen = set()
    output: List[str] = []
    for raw in values:
        value = _normalize_space(raw)
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output


def _truncate(value: str, max_len: int) -> str:
    value = _clean_text(value)
    if len(value) <= max_len:
        return value
    return value[: max_len - 1].rstrip() + "…"


def _build_query_text(payload: AnkiOrthoContextRequest) -> str:
    parts: List[str] = []
    if payload.deck:
        parts.append(f"Deck: {_clean_text(payload.deck)}")
    if payload.tags:
        parts.append("Tags: " + ", ".join(_dedupe_strings(_clean_text(tag) for tag in payload.tags)))
    parts.append(f"Front: {_clean_text(payload.front)}")
    if payload.back:
        parts.append(f"Back: {_clean_text(payload.back)}")
    return "\n".join(part for part in parts if part.strip())


def _canonicalize_term(value: str) -> str:
    value = _clean_text(value).lower()
    value = value.replace("_", " ").replace("-", " ")
    value = re.sub(r"\bfx\b", "fracture", value)
    value = re.sub(r"\boa\b", "osteoarthritis", value)
    value = re.sub(r"\bavn\b", "avascular necrosis", value)
    value = re.sub(r"\btha\b", "total hip arthroplasty", value)
    value = re.sub(r"\btka\b", "total knee arthroplasty", value)
    value = re.sub(r"\borif\b", "open reduction internal fixation", value)
    value = re.sub(r"\bimn\b", "intramedullary nail", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _term_variants(value: str) -> Set[str]:
    canonical = _canonicalize_term(value)
    if not canonical:
        return set()

    variants = {canonical}
    if "fracture" in canonical:
        variants.add(canonical.replace("fracture", "fx").strip())
    if "fx" in canonical:
        variants.add(canonical.replace("fx", "fracture").strip())
    if "avascular necrosis" in canonical:
        variants.add(canonical.replace("avascular necrosis", "avn"))
    if "total hip arthroplasty" in canonical:
        variants.add(canonical.replace("total hip arthroplasty", "tha"))
    if "open reduction internal fixation" in canonical:
        variants.add(canonical.replace("open reduction internal fixation", "orif"))
    return {variant for variant in variants if variant}


def _phrase_variants(value: str) -> Set[str]:
    canonical = _canonicalize_term(value)
    if not canonical:
        return set()
    variants = {canonical}
    compact = canonical.replace(" ", "_")
    variants.add(compact)
    if "classification" in canonical:
        variants.add(canonical.replace("classification", "classif").strip())
    if "total hip arthroplasty" in canonical:
        variants.add(canonical.replace("total hip arthroplasty", "tha"))
    if "cementless fixation" in canonical:
        variants.add(canonical.replace("cementless fixation", "press fit fixation"))
        variants.add(canonical.replace("cementless fixation", "press fit"))
    if "femoral stem" in canonical:
        variants.add(canonical.replace("femoral stem", "stem"))
    return {variant for variant in variants if variant}


def _contains_variant(haystack: str, value: str) -> bool:
    normalized_haystack = f" {haystack} "
    for variant in _term_variants(value):
        if f" {variant} " in normalized_haystack:
            return True
    return False


def _count_variant_hits(haystack: str, value: str) -> int:
    count = 0
    normalized_haystack = f" {haystack} "
    for variant in _phrase_variants(value):
        if f" {variant} " in normalized_haystack:
            count += 1
    return count


def _extract_card_key_phrases(payload: AnkiOrthoContextRequest) -> Set[str]:
    raw_text = " ".join(
        part for part in [payload.deck or "", " ".join(payload.tags), payload.front or "", payload.back or ""] if part
    )
    text = _canonicalize_term(raw_text)
    if not text:
        return set()

    phrase_patterns = [
        r"\bdorr classification\b",
        r"\bdorr type [abc]\b",
        r"\bfemoral canal\b",
        r"\bcanal to calcar ratio\b",
        r"\bcanal calcar ratio\b",
        r"\bcortical thickness\b",
        r"\bstovepipe femur\b",
        r"\bchampagne flute\b",
        r"\bcemented fixation\b",
        r"\bcementless fixation\b",
        r"\bpress fit\b",
        r"\bpress fit stability\b",
        r"\btotal hip arthroplasty\b",
        r"\btha femoral stem\b",
        r"\bfemoral stem\b",
        r"\bfemoral morphology\b",
        r"\bbone quality\b",
        r"\bcalcar\b",
        r"\bfixation planning\b",
    ]
    phrases: Set[str] = set()
    for pattern in phrase_patterns:
        for match in re.finditer(pattern, text):
            phrases.add(match.group(0))

    if "dorr" in text:
        phrases.add("dorr")
    if "classification" in text:
        phrases.add("classification")
    if "cementless" in text:
        phrases.add("cementless fixation")
    if "cemented" in text:
        phrases.add("cemented fixation")
    if "press fit" in text:
        phrases.add("press fit")

    return phrases


def _extract_negative_guardrails(card_text: str, key_phrases: Set[str]) -> Set[str]:
    if "dorr" in card_text or "femoral stem" in card_text or "press fit" in card_text:
        return {
            "femoral neck fracture",
            "hip dislocation",
            "femoral head offset",
            "anteversion",
            "atypical femur fracture",
            "legg calve perthes",
            "acetabular version",
            "approach",
            "patellar tracking",
        }
    return set()


def _primary_key_phrases(key_phrases: Set[str]) -> Set[str]:
    generic = {
        "total hip arthroplasty",
        "tha",
        "classification",
        "bone quality",
    }
    return {phrase for phrase in key_phrases if phrase not in generic}


def _embed_text(text: str) -> List[float]:
    client = _get_openai_client()
    return client.embeddings.create(model=EMBED_MODEL, input=text).data[0].embedding


def _build_source_filter() -> Dict[str, Any]:
    return {"source": {"$in": list(CURATED_PIMP_SOURCE_ALLOWLIST)}}


def _normalize_match(match: Dict[str, Any]) -> Dict[str, Any]:
    metadata = match.get("metadata") or {}
    return {
        "id": _safe_str(match.get("id")),
        "score": float(match.get("score") or 0.0),
        "rerank_score": float(match.get("score") or 0.0),
        "question": _safe_str(metadata.get("question")) or None,
        "answer": _safe_str(metadata.get("answer")) or None,
        "metadata": metadata,
        "source": _safe_str(metadata.get("source")),
        "specialty": _safe_str(metadata.get("specialty")),
        "region": _safe_str(metadata.get("region")),
        "subregion": _safe_str(metadata.get("subregion")),
        "diagnoses": _safe_list(metadata.get("diagnoses")),
        "procedures": _safe_list(metadata.get("procedures")),
        "text": _safe_str(metadata.get("text")),
    }


def _query_curated_pimp_matches(query_text: str, top_k: int = FAST_TOP_K) -> List[Dict[str, Any]]:
    index = _get_pinecone_index()
    vector = _embed_text(query_text)
    response = index.query(
        vector=vector,
        top_k=top_k,
        include_metadata=True,
        filter=_build_source_filter(),
    )
    matches = response.get("matches", []) or []
    normalized = [_normalize_match(match) for match in matches]
    return [match for match in normalized if match["question"] or match["answer"]]


def _query_curated_pimp_matches_from_vector(
    vector: List[float],
    *,
    top_k: int = FAST_TOP_K,
) -> List[Dict[str, Any]]:
    index = _get_pinecone_index()
    response = index.query(
        vector=vector,
        top_k=top_k,
        include_metadata=True,
        filter=_build_source_filter(),
    )
    matches = response.get("matches", []) or []
    normalized = [_normalize_match(match) for match in matches]
    return [match for match in normalized if match["question"] or match["answer"]]


def _log_timing(stage: str, started_at: float) -> None:
    elapsed_ms = (time.perf_counter() - started_at) * 1000.0
    print(f"⏱️ Anki ortho-context {stage}: {elapsed_ms:.1f} ms")


def _build_card_signals(payload: AnkiOrthoContextRequest, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    deck = _canonicalize_term(payload.deck or "")
    front = _canonicalize_term(payload.front or "")
    back = _canonicalize_term(payload.back or "")
    tags = [_canonicalize_term(tag) for tag in payload.tags]
    tag_text = " ".join(tag for tag in tags if tag)
    card_text = " ".join(part for part in [deck, tag_text, front, back] if part).strip()
    key_phrases = _extract_card_key_phrases(payload)
    primary_key_phrases = _primary_key_phrases(key_phrases)
    negative_guardrails = _extract_negative_guardrails(card_text, key_phrases)

    explicit_diagnoses: Set[str] = set()
    explicit_procedures: Set[str] = set()
    explicit_subregions: Set[str] = set()
    explicit_regions: Set[str] = set()

    for match in matches:
        for diagnosis in match.get("diagnoses") or []:
            if _contains_variant(card_text, diagnosis):
                explicit_diagnoses.add(_canonicalize_term(diagnosis))
        for procedure in match.get("procedures") or []:
            if _contains_variant(card_text, procedure):
                explicit_procedures.add(_canonicalize_term(procedure))
        subregion = _safe_str(match.get("subregion"))
        if subregion and _contains_variant(card_text, subregion):
            explicit_subregions.add(_canonicalize_term(subregion))
        region = _safe_str(match.get("region"))
        if region and _contains_variant(card_text, region):
            explicit_regions.add(_canonicalize_term(region))

    return {
        "card_text": card_text,
        "deck": deck,
        "front": front,
        "back": back,
        "tags": tags,
        "key_phrases": key_phrases,
        "primary_key_phrases": primary_key_phrases,
        "negative_guardrails": negative_guardrails,
        "explicit_diagnoses": explicit_diagnoses,
        "explicit_procedures": explicit_procedures,
        "explicit_subregions": explicit_subregions,
        "explicit_regions": explicit_regions,
    }


def _strong_card_anchor(signals: Dict[str, Any]) -> bool:
    return bool(
        signals.get("key_phrases")
        or signals.get("explicit_diagnoses")
        or signals.get("explicit_procedures")
        or signals.get("explicit_subregions")
    )


def _strong_metadata_present(match: Dict[str, Any]) -> bool:
    return bool(match.get("diagnoses") or match.get("procedures") or match.get("subregion"))


def _relevance_score_match(match: Dict[str, Any], signals: Dict[str, Any]) -> Tuple[float, List[str], List[str], bool]:
    card_text = signals.get("card_text", "")
    key_phrases: Set[str] = signals.get("key_phrases", set())
    primary_key_phrases: Set[str] = signals.get("primary_key_phrases", set())
    negative_guardrails: Set[str] = signals.get("negative_guardrails", set())
    explicit_diagnoses: Set[str] = signals.get("explicit_diagnoses", set())
    explicit_procedures: Set[str] = signals.get("explicit_procedures", set())
    explicit_subregions: Set[str] = signals.get("explicit_subregions", set())
    explicit_regions: Set[str] = signals.get("explicit_regions", set())

    question_text = _canonicalize_term(match.get("question") or "")
    answer_text = _canonicalize_term(match.get("answer") or "")
    combined = " ".join(
        part
        for part in [
            question_text,
            answer_text,
            " ".join(_canonicalize_term(v) for v in match.get("diagnoses") or []),
            " ".join(_canonicalize_term(v) for v in match.get("procedures") or []),
            _canonicalize_term(match.get("subregion") or ""),
            _canonicalize_term(match.get("region") or ""),
        ]
        if part
    ).strip()

    score = float(match.get("rerank_score") or match.get("score") or 0.0)
    boosts: List[str] = []
    penalties: List[str] = []
    has_anchor = False
    has_thread_anchor = False
    guardrail_hit = False

    phrase_hits = 0
    for phrase in key_phrases:
        hits = _count_variant_hits(combined, phrase)
        if hits:
            has_anchor = True
            if phrase in primary_key_phrases:
                has_thread_anchor = True
            phrase_hits += hits
    if phrase_hits:
        delta = 0.22 * phrase_hits
        score += delta
        boosts.append(f"phrase_overlap:+{delta:.2f}")

    if "classification" in card_text and "classification" in combined:
        score += 0.16
        boosts.append("classification_thread:+0.16")
        has_anchor = True
        if not primary_key_phrases:
            has_thread_anchor = True

    if "dorr" in card_text and "dorr" in combined:
        score += 0.32
        boosts.append("dorr_thread:+0.32")
        has_anchor = True
        has_thread_anchor = True

    for value, explicit_values, label in (
        (match.get("diagnoses") or [], explicit_diagnoses, "diagnosis"),
        (match.get("procedures") or [], explicit_procedures, "procedure"),
        ([match.get("subregion") or ""], explicit_subregions, "subregion"),
        ([match.get("region") or ""], explicit_regions, "region"),
    ):
        normalized_values = [_canonicalize_term(v) for v in value if _canonicalize_term(v)]
        if explicit_values and normalized_values:
            if any(v in explicit_values for v in normalized_values):
                score += 0.18
                boosts.append(f"{label}_match:+0.18")
                has_anchor = True
            else:
                score -= 0.26
                penalties.append(f"{label}_conflict:-0.26")

    if any(_contains_variant(answer_text, phrase) for phrase in key_phrases):
        score += 0.10
        boosts.append("answer_overlap:+0.10")
        has_anchor = True
        if any(_contains_variant(answer_text, phrase) for phrase in primary_key_phrases):
            has_thread_anchor = True

    for off_topic in negative_guardrails:
        if _contains_variant(combined, off_topic):
            guardrail_hit = True
            score -= 0.35
            penalties.append(f"guardrail:{off_topic}:-0.35")

    if _strong_card_anchor(signals) and not has_anchor and _strong_metadata_present(match):
        score -= 0.30
        penalties.append("missing_anchor:-0.30")

    displayed = score >= 0.72
    if _strong_card_anchor(signals) and not has_anchor:
        displayed = False
    if primary_key_phrases and not has_thread_anchor:
        displayed = False
    if guardrail_hit and primary_key_phrases and not has_thread_anchor:
        displayed = False
    return round(score, 4), boosts, penalties, displayed


def _log_relevance_decision(match: Dict[str, Any], final_score: float, boosts: List[str], penalties: List[str], displayed: bool) -> None:
    if not RELEVANCE_DEBUG:
        return
    print(
        "🔎 Anki ortho-context relevance",
        {
            "question": _truncate(_safe_str(match.get("question")), 140),
            "score": round(float(match.get("score") or 0.0), 4),
            "rerank_score": round(float(match.get("rerank_score") or 0.0), 4),
            "final_relevance": final_score,
            "boosts": boosts,
            "penalties": penalties,
            "displayed": displayed,
        },
    )


def _field_alignment_score(
    values: Iterable[str],
    card_text: str,
    explicit_values: Set[str],
    *,
    exact_boost: float,
    conflict_penalty: float,
) -> Tuple[float, bool]:
    score = 0.0
    aligned = False
    normalized_values = [_canonicalize_term(value) for value in values if _canonicalize_term(value)]
    for value in normalized_values:
        if value in explicit_values or _contains_variant(card_text, value):
            score += exact_boost
            aligned = True
        elif explicit_values:
            score -= conflict_penalty
    return score, aligned


def _rerank_matches(matches: List[Dict[str, Any]], payload: AnkiOrthoContextRequest) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not matches:
        return [], {
            "card_text": "",
            "explicit_diagnoses": set(),
            "explicit_procedures": set(),
            "explicit_subregions": set(),
            "explicit_regions": set(),
        }

    signals = _build_card_signals(payload, matches)
    card_text = signals["card_text"]

    reranked: List[Dict[str, Any]] = []
    for match in matches:
        rerank_score = float(match.get("score") or 0.0)
        aligned = False

        dx_score, dx_aligned = _field_alignment_score(
            match.get("diagnoses") or [],
            card_text,
            signals["explicit_diagnoses"],
            exact_boost=0.28,
            conflict_penalty=0.06,
        )
        proc_score, proc_aligned = _field_alignment_score(
            match.get("procedures") or [],
            card_text,
            signals["explicit_procedures"],
            exact_boost=0.22,
            conflict_penalty=0.05,
        )
        subregion_score, subregion_aligned = _field_alignment_score(
            [match.get("subregion") or ""],
            card_text,
            signals["explicit_subregions"],
            exact_boost=0.20,
            conflict_penalty=0.05,
        )
        region_score, region_aligned = _field_alignment_score(
            [match.get("region") or ""],
            card_text,
            signals["explicit_regions"],
            exact_boost=0.10,
            conflict_penalty=0.02,
        )

        rerank_score += dx_score + proc_score + subregion_score + region_score
        aligned = dx_aligned or proc_aligned or subregion_aligned or region_aligned

        question = _canonicalize_term(match.get("question") or "")
        answer = _canonicalize_term(match.get("answer") or "")

        for important_phrase in signals["tags"]:
            if important_phrase and important_phrase in question:
                rerank_score += 0.04
                aligned = True
            if important_phrase and important_phrase in answer:
                rerank_score += 0.02

        best_match = dict(match)
        best_match["rerank_score"] = round(rerank_score, 4)
        best_match["aligned"] = aligned
        reranked.append(best_match)

    reranked.sort(
        key=lambda item: (
            item.get("aligned", False),
            float(item.get("rerank_score") or 0.0),
            float(item.get("score") or 0.0),
        ),
        reverse=True,
    )
    return reranked, signals


def _counter_choice(values: Iterable[str]) -> Optional[str]:
    counter = Counter()
    for value in values:
        cleaned = _normalize_space(value)
        if cleaned:
            counter[cleaned] += 1
    if not counter:
        return None
    return counter.most_common(1)[0][0]


def _preferred_metadata_value(values: Iterable[str], card_text: str) -> Optional[str]:
    cleaned_values = [_clean_text(value) for value in values if _clean_text(value)]
    if not cleaned_values:
        return None

    aligned = [value for value in cleaned_values if _contains_variant(card_text, value)]
    if aligned:
        return aligned[0]

    return _counter_choice(cleaned_values)


def _combined_text(match: Dict[str, Any]) -> str:
    return " ".join(
        part
        for part in [
            match.get("question") or "",
            match.get("answer") or "",
            " ".join(match.get("diagnoses") or []),
            " ".join(match.get("procedures") or []),
            match.get("specialty") or "",
            match.get("region") or "",
            match.get("subregion") or "",
        ]
        if part
    ).lower()


def _classify_concept_types(matches: List[Dict[str, Any]]) -> List[str]:
    concept_counters = Counter()
    for match in matches[:6]:
        text = _combined_text(match)
        if any(token in text for token in ["anatomy", "innervation", "blood supply", "origin", "insertion"]):
            concept_counters["Anatomy"] += 1
        if any(token in text for token in ["classif", "garden", "schatzker", "neer", "vancouver"]):
            concept_counters["Classification"] += 1
        if any(token in text for token in ["treat", "management", "indication", "contraindication"]):
            concept_counters["Management"] += 1
        if any(token in text for token in ["approach", "exposure", "positioning"]):
            concept_counters["Approach"] += 1
        if any(token in text for token in ["complication", "pitfall", "malunion", "nonunion", "avascular", "infection"]):
            concept_counters["Complications"] += 1
        if any(token in text for token in ["implant", "plate", "screw", "nail", "prosthesis"]):
            concept_counters["Implants"] += 1
        if any(token in text for token in ["biomechan", "force", "load", "stability", "compression"]):
            concept_counters["Biomechanics"] += 1
        if not any(
            token in text
            for token in [
                "anatomy",
                "innervation",
                "blood supply",
                "origin",
                "insertion",
                "classif",
                "garden",
                "schatzker",
                "neer",
                "vancouver",
                "treat",
                "management",
                "indication",
                "contraindication",
                "approach",
                "exposure",
                "positioning",
                "complication",
                "pitfall",
                "malunion",
                "nonunion",
                "avascular",
                "infection",
                "implant",
                "plate",
                "screw",
                "nail",
                "prosthesis",
                "biomechan",
                "force",
                "load",
                "stability",
                "compression",
            ]
        ):
            concept_counters["Diagnosis"] += 1

    if not concept_counters:
        return []
    return [name for name, _ in concept_counters.most_common(4)]


def _infer_level_and_yield(matches: List[Dict[str, Any]]) -> tuple[Optional[str], Optional[str]]:
    if not matches:
        return None, None

    text = " ".join(_combined_text(match) for match in matches[:5])

    if any(token in text for token in ["board", "oite", "most likely", "classic", "association"]):
        return "Boards", "High"

    if any(token in text for token in ["approach", "implant", "biomechan", "revision", "salvage", "fixation strategy", "controvers"]):
        return "Senior Resident", "High"

    if any(token in text for token in ["complication", "indication", "management", "treatment", "workup", "imaging"]):
        return "Junior Resident", "High"

    return "MS4", "Medium"


def _infer_card_level(matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not matches:
        return {
            "level": "MS4",
            "oite_yield": "Low",
            "why": "No curated orthopaedic follow-up questions were found for this card yet.",
        }

    level, oite_yield = _infer_level_and_yield(matches)
    level = level or "MS4"
    oite_yield = oite_yield or "Medium"
    text = " ".join(_combined_text(match) for match in matches[:5])

    if level == "Boards":
        why = "This card clusters around classic board-style orthopaedic associations and highly testable management pairings."
    elif level == "Senior Resident":
        why = "This card leans on surgical nuance, fixation strategy, or complication management beyond the basics."
    elif level == "Junior Resident":
        why = "This card emphasizes practical management decisions, indications, imaging, or complications expected early in residency."
    else:
        why = "This card focuses on common diagnoses, foundational trauma concepts, or management principles a sub-I should know."

    if "classification" in text or "garden" in text or "schatzker" in text:
        why = f"{why} Classification-based treatment thinking makes it especially testable."

    return {
        "level": level,
        "oite_yield": oite_yield,
        "why": _truncate(why, 180),
    }


def _build_badges(matches: List[Dict[str, Any]], card_text: str) -> Dict[str, Any]:
    top_matches = matches[:6]
    specialty = _preferred_metadata_value((match.get("specialty") for match in top_matches), card_text)
    region = _preferred_metadata_value((match.get("region") for match in top_matches), card_text)
    subregion = _preferred_metadata_value((match.get("subregion") for match in top_matches), card_text)
    diagnosis_values = [
        diagnosis
        for match in top_matches
        for diagnosis in (match.get("diagnoses") or [])
    ]
    procedure_values = [
        procedure
        for match in top_matches
        for procedure in (match.get("procedures") or [])
    ]
    diagnosis = _preferred_metadata_value(diagnosis_values, card_text)
    procedure = _preferred_metadata_value(procedure_values, card_text)
    concept_types = _classify_concept_types(top_matches)

    return {
        "specialty": specialty,
        "region": region,
        "subregion": subregion,
        "diagnosis": diagnosis,
        "procedure": procedure,
        "concept_types": concept_types,
    }


def _best_topic(badges: Dict[str, Any], matches: List[Dict[str, Any]]) -> str:
    for key in ("diagnosis", "procedure", "subregion", "region", "specialty"):
        value = badges.get(key)
        if isinstance(value, str) and value.strip():
            return value.replace("_", " ")

    top_question = _safe_str(matches[0].get("question")) if matches else ""
    if top_question:
        return _truncate(top_question, 72)

    return "orthopaedic context"


def _infer_title(badges: Dict[str, Any], matches: List[Dict[str, Any]]) -> str:
    topic = _best_topic(badges, matches)
    if topic.endswith("?"):
        return topic
    return f"{topic.title()} Context"


def _concept_prefix(question: str) -> str:
    lower = question.lower()
    if any(token in lower for token in ["classification", "classify", "garden", "neer", "schatzker", "vancouver"]):
        return "Classification pearl"
    if any(token in lower for token in ["indication", "treatment", "management"]):
        return "Management pearl"
    if any(token in lower for token in ["complication", "pitfall", "avoid"]):
        return "Complication pearl"
    if any(token in lower for token in ["approach", "exposure", "position"]):
        return "Approach pearl"
    if any(token in lower for token in ["what is", "define", "anatom", "blood supply", "innervation"]):
        return "Core fact"
    return "High-yield point"


def _build_high_yield_concepts(matches: List[Dict[str, Any]]) -> List[str]:
    concepts: List[str] = []
    seen = set()
    for match in matches[:MAX_HIGH_YIELD_CONCEPTS]:
        question = _safe_str(match.get("question"))
        answer = _truncate(_safe_str(match.get("answer")), 140)
        if not answer:
            continue
        prefix = _concept_prefix(question)
        concept = f"{prefix}: {answer}"
        key = concept.lower()
        if key in seen:
            continue
        seen.add(key)
        concepts.append(concept)
    return concepts


def _build_rapid_associations(badges: Dict[str, Any], matches: List[Dict[str, Any]]) -> List[str]:
    associations: List[str] = []

    for label, value in (
        ("Specialty", badges.get("specialty")),
        ("Region", badges.get("region")),
        ("Subregion", badges.get("subregion")),
        ("Diagnosis", badges.get("diagnosis")),
        ("Procedure", badges.get("procedure")),
    ):
        if value:
            associations.append(f"{label}: {str(value).replace('_', ' ')}")

    concept_types = badges.get("concept_types") or []
    for concept in concept_types[:2]:
        associations.append(f"Common angle: {concept}")

    deduped = _dedupe_strings(associations)
    return deduped[:MAX_RAPID_ASSOCIATIONS]


def _extract_topics(matches: List[Dict[str, Any]], badges: Dict[str, Any]) -> List[str]:
    topics: List[str] = []
    for match in matches[:8]:
        for key in ("specialty", "region", "subregion"):
            value = _safe_str(match.get(key))
            if value:
                topics.append(value.replace("_", " "))
        for diagnosis in match.get("diagnoses") or []:
            topics.append(diagnosis.replace("_", " "))
        for procedure in match.get("procedures") or []:
            topics.append(procedure.replace("_", " "))

    for concept in badges.get("concept_types") or []:
        topics.append(concept)

    return _dedupe_strings(topics)[:MAX_RELATED_TOPICS]


def _difficulty_bucket(match: Dict[str, Any]) -> str:
    text = _combined_text(match)
    if any(token in text for token in ["what is", "define", "anatom", "blood supply", "innervation", "most common"]):
        return "basic"
    if any(token in text for token in ["classification", "classify", "indication", "treatment", "management"]):
        return "intermediate"
    if any(token in text for token in ["complication", "pitfall", "approach", "biomechan", "implant", "controvers"]):
        return "advanced"
    return "intermediate"


def _build_flat_related_questions(matches: List[Dict[str, Any]], signals: Dict[str, Any]) -> List[Dict[str, str]]:
    questions: List[Dict[str, str]] = []
    seen = set()
    strong_anchor = _strong_card_anchor(signals)

    for match in matches:
        question = _safe_str(match.get("question"))
        answer = _safe_str(match.get("answer"))
        if not question or not answer:
            continue
        key = f"{question.lower()}::{answer.lower()}"
        if key in seen:
            continue
        final_score, boosts, penalties, displayed = _relevance_score_match(match, signals)
        _log_relevance_decision(match, final_score, boosts, penalties, displayed)
        if not displayed:
            continue
        if strong_anchor and final_score < 0.90 and len(questions) >= 5:
            continue
        seen.add(key)
        source = _safe_str(match.get("source"))
        questions.append(
            {
                "question": question,
                "answer": answer,
                "source_id": _safe_str(match.get("id")) or "",
                "source": source,
            }
        )
        if len(questions) >= MAX_FLAT_RELATED_QUESTIONS:
            break

    return questions


def _bucket_related_questions(matches: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, str]]]:
    buckets: Dict[str, List[Dict[str, str]]] = {
        "basic": [],
        "intermediate": [],
        "advanced": [],
    }
    seen = set()
    aligned_present = any(match.get("aligned") for match in matches[:8])
    for match in matches:
        question = _safe_str(match.get("question"))
        answer = _safe_str(match.get("answer"))
        if not question or not answer:
            continue
        if aligned_present and not match.get("aligned") and len(buckets["intermediate"]) + len(buckets["basic"]) >= 3:
            continue
        key = f"{question.lower()}::{answer.lower()}"
        if key in seen:
            continue
        seen.add(key)
        bucket = _difficulty_bucket(match)
        if len(buckets[bucket]) >= MAX_BUCKET_ITEMS:
            continue
        buckets[bucket].append({"question": question, "answer": answer})

    if not buckets["intermediate"]:
        for fallback in buckets["basic"][:1]:
            buckets["intermediate"].append(fallback)

    return buckets


def _compatibility_buckets_from_flat_questions(
    items: List[Dict[str, str]],
) -> Dict[str, List[Dict[str, str]]]:
    buckets: Dict[str, List[Dict[str, str]]] = {
        "basic": [],
        "intermediate": [],
        "advanced": [],
    }
    for item in items[:MAX_FLAT_RELATED_QUESTIONS]:
        question = _safe_str(item.get("question"))
        answer = _safe_str(item.get("answer"))
        if not question or not answer:
            continue
        text = f"{question} {answer}".lower()
        if any(token in text for token in ["what is", "define", "anatom", "blood supply", "innervation", "most common"]):
            bucket = "basic"
        elif any(token in text for token in ["complication", "pitfall", "approach", "biomechan", "implant", "controvers"]):
            bucket = "advanced"
        else:
            bucket = "intermediate"
        if len(buckets[bucket]) >= MAX_BUCKET_ITEMS:
            continue
        buckets[bucket].append({"question": question, "answer": answer})
    return buckets


def _build_source_matches(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for match in matches[:MAX_SOURCE_MATCHES]:
        metadata = _sanitize_metadata(dict(match.get("metadata") or {}))
        output.append(
            {
                "id": match.get("id") or "",
                "score": round(float(match.get("score") or 0.0), 4),
                "rerank_score": round(float(match.get("rerank_score") or 0.0), 4),
                "question": match.get("question"),
                "answer": match.get("answer"),
                "metadata": metadata,
            }
        )
    return output


def _compute_confidence(matches: List[Dict[str, Any]]) -> float:
    if not matches:
        return 0.0
    top_scores = [max(0.0, min(1.0, float(match.get("score") or 0.0))) for match in matches[:5]]
    base = sum(top_scores[:3]) / max(1, min(3, len(top_scores)))
    aligned_ratio = sum(1 for match in matches[:5] if match.get("aligned")) / max(1, min(5, len(matches)))
    mixed_penalty = 0.08 if aligned_ratio < 0.4 else 0.0
    rerank_bonus = 0.05 if matches[0].get("aligned") else 0.0
    confidence = base * 0.78 + aligned_ratio * 0.22 + rerank_bonus - mixed_penalty
    return round(max(0.0, min(0.98, confidence)), 3)


def _empty_response(mode: str, query_text: str = "") -> Dict[str, Any]:
    topic_hint = "SnapOrtho Context"
    if query_text:
        for line in query_text.splitlines():
            if line.startswith("Front: "):
                topic_hint = _truncate(line.replace("Front: ", ""), 72) or topic_hint
                break
    return {
        "badges": {
            "specialty": None,
            "region": None,
            "subregion": None,
            "diagnosis": None,
            "procedure": None,
            "concept_types": [],
        },
        "card_level": {
            "level": "MS4",
            "oite_yield": "Low",
            "why": "No curated orthopaedic follow-up questions were found for this card yet.",
        },
        "related_pimp_questions": [],
        "related_pimp_question_buckets": {
            "basic": [],
            "intermediate": [],
            "advanced": [],
        },
        "question_count": 0,
        "source_matches": [],
        "confidence": 0.0,
        "mode": mode,
        "formatter": "fallback-card-level",
    }


def _build_fast_response(payload: AnkiOrthoContextRequest, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    query_text = _build_query_text(payload)
    if not matches:
        return _empty_response(payload.mode, query_text=query_text)

    card_text = _canonicalize_term(query_text)
    signals = _build_card_signals(payload, matches)
    badges = _build_badges(matches, card_text)
    flat_questions = _build_flat_related_questions(matches, signals)
    compatibility_buckets = _compatibility_buckets_from_flat_questions(flat_questions)

    return {
        "badges": badges,
        "card_level": _infer_card_level(matches),
        "related_pimp_questions": flat_questions,
        "related_pimp_question_buckets": compatibility_buckets,
        "question_count": len(flat_questions),
        "source_matches": _build_source_matches(matches),
        "confidence": _compute_confidence(matches),
        "mode": payload.mode,
        "formatter": "fallback-card-level",
    }


def _sanitize_output_question_bucket(items: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    output: List[Dict[str, str]] = []
    seen = set()
    for item in items[:MAX_BUCKET_ITEMS]:
        if not isinstance(item, dict):
            continue
        question = _safe_str(item.get("question"))
        answer = _safe_str(item.get("answer"))
        if not question or not answer:
            continue
        key = f"{question.lower()}::{answer.lower()}"
        if key in seen:
            continue
        seen.add(key)
        output.append({"question": question, "answer": answer})
    return output


def _sanitize_output_question_list(items: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    output: List[Dict[str, str]] = []
    seen = set()
    for item in items[:MAX_FLAT_RELATED_QUESTIONS]:
        if not isinstance(item, dict):
            continue
        question = _safe_str(item.get("question"))
        answer = _safe_str(item.get("answer"))
        source_id = _safe_str(item.get("source_id"))
        source = _safe_str(item.get("source"))
        if not question or not answer:
            continue
        key = f"{question.lower()}::{answer.lower()}"
        if key in seen:
            continue
        seen.add(key)
        output.append(
            {
                "question": question,
                "answer": answer,
                "source_id": source_id,
                "source": source,
            }
        )
    return output


def build_anki_ortho_context_response(request_data: Dict[str, Any]) -> Dict[str, Any]:
    total_started_at = time.perf_counter()
    payload = AnkiOrthoContextRequest(**request_data)
    requested_mode = (payload.mode or "fast").strip().lower()
    payload.mode = "enhanced" if requested_mode == "enhanced" else "fast"

    print(
        "📝 Building Anki ortho context",
        {
            "note_id": payload.note_id or "",
            "card_id": payload.card_id or "",
            "mode": payload.mode,
            "has_deck": bool(payload.deck),
            "tag_count": len(payload.tags),
        },
    )

    query_text = _build_query_text(payload)

    started_at = time.perf_counter()
    query_vector = _embed_text(query_text)
    _log_timing("embedding", started_at)

    started_at = time.perf_counter()
    raw_matches = _query_curated_pimp_matches_from_vector(query_vector)
    _log_timing("pinecone_query", started_at)

    started_at = time.perf_counter()
    matches, _signals = _rerank_matches(raw_matches, payload)
    _log_timing("rerank", started_at)

    started_at = time.perf_counter()
    fallback_response = _build_fast_response(payload, matches)
    _log_timing("deterministic_formatting", started_at)

    started_at = time.perf_counter()
    final_response, cleanup_gpt_used = _sanitize_response_payload(fallback_response)
    _log_timing("sanitizer", started_at)
    print(f"🧼 Anki ortho-context cleanup_gpt_used: {cleanup_gpt_used}")

    _log_timing("total", total_started_at)
    return final_response


def example_curl_command() -> str:
    return (
        "curl -X POST http://127.0.0.1:8000/anki/ortho-context "
        "-H 'Content-Type: application/json' "
        "-d '{"
        "\"deck\":\"Trauma::Hip\","
        "\"front\":\"Displaced femoral neck fracture in an active older adult\","
        "\"back\":\"When should THA be considered?\","
        "\"tags\":[\"femoral_neck\",\"hip\",\"trauma\"],"
        "\"mode\":\"fast\""
        "}'"
    )


def debug_sample_payload() -> Dict[str, Any]:
    return {
        "deck": "Trauma::Hip",
        "front": "Displaced femoral neck fracture in an active older adult",
        "back": "When should THA be considered?",
        "tags": ["femoral_neck", "hip", "trauma"],
        "mode": "fast",
    }


def debug_expected_outcome() -> Dict[str, str]:
    return {
        "diagnosis": "femoral_neck_fx",
        "subregion": "femoral_neck",
        "title_contains": "Femoral Neck Fracture",
    }


if __name__ == "__main__":
    print("Anki ortho-context debug helper")
    print(example_curl_command())
    sample = "Ð _Deepens labrum and enhances stability Ð Facilitates load transmission Ð Maintains a vacuum seal Ð Regulates synovial fluid hydrodynamics Ð Aids in joint lubrication"
    print("Raw sample:")
    print(sample)
    print("Sanitized sample:")
    print(_clean_display_text(sample))
