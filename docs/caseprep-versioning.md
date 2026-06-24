# CasePrep Versioning (v1 / v2)

SnapOrtho CasePrep exposes two engines behind separate routes. **v1 is production default.** **v2 is opt-in for web staging.**

## v1 — Legacy RAG + GPT (production)

| Property | Value |
|----------|-------|
| Engine | `legacy_rag_gpt` |
| Route | `POST /case-prep` (default) |
| Flow | `refine_query` → Pinecone RAG → GPT pimp reformat → `anatomy_gpt` legacy catalog |
| Curated store | **Not used** |
| v2-only modules | **Not imported** by `caseprep/engines/v1_legacy.py` |

iOS and existing clients should keep calling `POST /case-prep` without changes.

## v2 — Curated-first hybrid (staging)

| Property | Value |
|----------|-------|
| Engine | `curated_hybrid` |
| Route | `POST /case-prep/v2` |
| Flow | Resolve procedure → certified JSONL payload if match → controlled fallback otherwise |
| GPT for core content | **Only when explicitly enabled** via fallback flags |
| Certified path | Returns `attending_pimp_questions` from payload (no GPT pimp) |

Web staging should call **`POST /case-prep/v2`** explicitly. Do not change iOS to v2 until certified coverage and client UX are ready.

## Routes

| Method | Path | Engine |
|--------|------|--------|
| `GET` | `/health` | Reports `v1_available`, `v2_available`, flags, curated store status |
| `POST` | `/case-prep` | **v1** unless `CASEPREP_DEFAULT_VERSION=v2` **and** `ENABLE_CASEPREP_V2=true` |
| `POST` | `/case-prep/v2` | **v2** (controlled disabled response when flag off) |
| `POST` | `/anatomy` | Legacy anatomy only; experimental hybrid behind `ENABLE_LOCAL_ANATOMY_RAG` |

## Environment flags

| Variable | Default | Purpose |
|----------|---------|---------|
| `CASEPREP_DEFAULT_VERSION` | `v1` | Default engine for `POST /case-prep` |
| `ENABLE_CASEPREP_V2` | `false` | Master switch for v2 engine |
| `ENABLE_CASEPREP_V2_AI_FALLBACK` | `false` | GPT pimp/anatomy on v2 non-certified fallback |
| `ENABLE_CASEPREP_V2_RAG_FALLBACK` | `true` | Pinecone snippets on v2 non-certified fallback (if deps exist) |
| `ENABLE_LOCAL_ANATOMY_RAG` | `false` | `/anatomy` experimental path only (not CasePrep v1) |

### Staging example

```bash
CASEPREP_DEFAULT_VERSION=v1
ENABLE_CASEPREP_V2=true
ENABLE_CASEPREP_V2_AI_FALLBACK=false
ENABLE_CASEPREP_V2_RAG_FALLBACK=false
```

Production should leave `ENABLE_CASEPREP_V2=false` until v2 is promoted.

## Response envelope

Both versions add metadata fields **in addition to** legacy top-level keys (`pimpQuestions`, `otherUsefulFacts`, `anatomy`).

```json
{
  "caseprep_version": "v2",
  "engine": "curated_hybrid",
  "procedure_slug": "tha_posterior",
  "content_status": "certified",
  "match_method": "contains",
  "fallback_reason": null,
  "ai_used": false,
  "rag_used": false,
  "warnings": [],
  "user_visible_warning": null,
  "payload": { },
  "pimpQuestions": [],
  "otherUsefulFacts": [],
  "anatomy": {}
}
```

### Detecting certified vs fallback

| `content_status` | Meaning |
|------------------|---------|
| `legacy` | v1 RAG/GPT pipeline |
| `certified` | v2 returned curated `brobot_case_prep` payload |
| `fallback` | v2 resolved procedure but no certified payload; optional RAG/AI per flags |
| `unsupported` | v2 disabled, unresolved procedure, or empty prompt |

Always check:

1. `caseprep_version` — `v1` vs `v2`
2. `content_status`
3. `ai_used` — `false`, or explicit list e.g. `["resolver_classifier"]`
4. `user_visible_warning` — present on fallback/unsupported/disabled

## Web integration

```javascript
// Staging only
const res = await fetch(`${CASEPREP_API}/case-prep/v2`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ prompt: userInput }),
});
const data = await res.json();

if (data.content_status === "certified") {
  renderCurated(data.brobot_case_prep);
} else if (data.user_visible_warning) {
  showWarning(data.user_visible_warning);
}
```

Show a **“Curated”** badge when `content_status === "certified"`. Show **“Preview / limited coverage”** when `fallback` or `unsupported`.

## Current limitations (before v2 default)

- Only **24** procedures have certified payloads (`data/anatomy/case_prep/certified_case_prep_payloads.jsonl`).
- Non-certified v2 cases return fallback unless AI/RAG flags are enabled.
- `hybrid_anatomy_builder` / Miller retrievers are v2-adjacent but not wired into `/case-prep/v2` yet.
- Content quality issues remain in some certified records (not fixed in this versioning pass).
- iOS should remain on v1 until web staging validates envelope handling.

## Validation

```bash
python3 scripts/anatomy/test_caseprep_v2_integration.py
python3 scripts/anatomy/smoke_test_anatomy_runtime.py
curl http://localhost:8000/health
```