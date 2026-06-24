import os
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool

from anatomy_gpt import load_catalog_from_jsonl_file, run_pipeline_fast
from anki_ortho_context import (
    AnkiOrthoContextRequest,
    build_anki_ortho_context_response,
)
from openai import OpenAI

from caseprep.api.routes.registry import router as registry_router
from caseprep.api.routes.factory import router as factory_router
from caseprep.config import APPROACH_CATALOG_PATHS, CasePrepConfig
from caseprep.schemas import CasePrepRequest
from caseprep.engines import v1_legacy, v2_curated
from caseprep.services import curated_content_store, rag_context, procedure_resolver

# ── Legacy /anatomy experimental path (NOT used by CasePrep v1) ─────────────
ENABLE_LOCAL_ANATOMY_RAG = os.getenv("ENABLE_LOCAL_ANATOMY_RAG", "").lower() in (
    "1", "true", "yes", "on"
)
ANATOMY_BACKEND = (os.getenv("ANATOMY_BACKEND", "local") or "local").lower().strip()
ANATOMY_PINECONE_NAMESPACE = os.getenv("ANATOMY_PINECONE_NAMESPACE", "anatomy_miller_gold_v1")

BASE_DIR = Path(__file__).resolve().parent
ANATOMY_ROOT = BASE_DIR / "data" / "anatomy"
ANATOMY_CASE_PREP_DIR = ANATOMY_ROOT / "case_prep"

CASEPREP_CONFIG = CasePrepConfig.from_env()

app = FastAPI()
app.include_router(registry_router)
app.include_router(factory_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CATALOG: List[Dict[str, Any]] = []
OPENAI_CLIENT: Optional[OpenAI] = None


@app.on_event("startup")
def _startup():
    global CATALOG, OPENAI_CLIENT

    CATALOG = []
    for p in APPROACH_CATALOG_PATHS:
        CATALOG.extend(load_catalog_from_jsonl_file(p))

    print(f"✅ Loaded approach catalog: {len(CATALOG)} items")
    for p in APPROACH_CATALOG_PATHS:
        print(f"   - {p}")

    OPENAI_CLIENT = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        project=os.getenv("OPENAI_PROJECT_ID"),
    )
    print("✅ OpenAI client initialized")

    # Warm curated store for /health (non-fatal if missing)
    curated_content_store.store_status()

    print(
        f"📦 CasePrep: default={CASEPREP_CONFIG.default_version}, "
        f"v2_enabled={CASEPREP_CONFIG.enable_v2}, "
        f"v2_ai_fallback={CASEPREP_CONFIG.enable_v2_ai_fallback}, "
        f"v2_rag_fallback={CASEPREP_CONFIG.enable_v2_rag_fallback}"
    )


@app.get("/")
def read_root():
    return {"message": "SnapOrtho CasePrep API is live."}


@app.get("/health")
def health():
    cfg = CasePrepConfig.from_env()
    store = curated_content_store.store_status()
    return {
        "status": "ok",
        "v1_available": v1_legacy.is_v1_available(),
        "v2_available": v2_curated.is_v2_available(cfg),
        "v2_unavailable_reason": v2_curated.v2_unavailable_reason(cfg) or None,
        "caseprep_default_version": cfg.default_version,
        "enable_caseprep_v2": cfg.enable_v2,
        "enable_caseprep_v2_ai_fallback": cfg.enable_v2_ai_fallback,
        "enable_caseprep_v2_rag_fallback": cfg.enable_v2_rag_fallback,
        "rag_available": rag_context.is_rag_available(),
        "resolver_available": procedure_resolver.is_resolver_available(),
        "curated_store": store,
        "catalog_loaded": len(CATALOG),
    }


async def _dispatch_caseprep(prompt: str, *, version: str) -> Dict[str, Any]:
    if version == "v2":
        return await v2_curated.run_caseprep_v2(
            prompt,
            catalog=CATALOG,
            openai_client=OPENAI_CLIENT,
            config=CasePrepConfig.from_env(),
        )
    return await v1_legacy.run_caseprep_v1(
        prompt,
        catalog=CATALOG,
        openai_client=OPENAI_CLIENT,
    )


@app.post("/case-prep")
async def case_prep(request: CasePrepRequest):
    prompt = (request.prompt or "").strip()
    cfg = CasePrepConfig.from_env()

    version = (request.version or cfg.default_version or "v1").lower().strip()
    if version not in ("v1", "v2"):
        version = "v1"

    # v2 on default route only when explicitly enabled
    if version == "v2" and not cfg.enable_v2:
        version = "v1"

    return await _dispatch_caseprep(prompt, version=version)


@app.post("/case-prep/v2")
async def case_prep_v2(request: CasePrepRequest):
    prompt = (request.prompt or "").strip()
    return await v2_curated.run_caseprep_v2(
        prompt,
        catalog=CATALOG,
        openai_client=OPENAI_CLIENT,
        config=CasePrepConfig.from_env(),
    )


# ── /anatomy: legacy by default; experimental hybrid only when flag set ───────
@app.post("/anatomy")
async def anatomy_only(request: CasePrepRequest):
    prompt = (request.prompt or "").strip()
    if not prompt:
        return {"error": "No prompt provided"}

    if ENABLE_LOCAL_ANATOMY_RAG:
        return await _anatomy_experimental(prompt)

    if not CATALOG:
        return {"error": "Approach catalog not loaded"}

    result = await run_in_threadpool(
        run_pipeline_fast,
        case_prompt=prompt,
        catalog=CATALOG,
        client=OPENAI_CLIENT,
    )
    return result


async def _anatomy_experimental(prompt: str) -> Dict[str, Any]:
    """Isolated experimental anatomy path — lazy imports; failures do not affect v1."""
    resolved = await run_in_threadpool(
        procedure_resolver.resolve_procedure_safe, prompt, OPENAI_CLIENT
    )
    slug = resolved.get("procedure_slug")

    if slug:
        certified = curated_content_store.get_certified_payload(slug)
        if certified:
            return {
                "mode": "certified_case_prep_payload",
                "procedure_id": slug,
                "procedure_name": certified.get("procedure_name"),
                "case_prep_status": "certified",
                "payload": certified,
                "resolver": {
                    "match_method": resolved.get("match_method"),
                    "match_score": resolved.get("match_score"),
                },
                "brobot_case_prep": certified,
            }

    try:
        from approach_router import get_supported_case
    except Exception:
        get_supported_case = None

    sc = get_supported_case(prompt) if get_supported_case else {
        "supported": True,
        "case_family": slug or "unknown",
        "reason": "",
    }
    if slug:
        sc["case_family"] = slug

    supported = bool(sc.get("supported", True))
    if not supported:
        suggested = resolved.get("suggested_matches") or []
        return {
            "approachSelection": None,
            "anatomyQuiz": None,
            "retrievalMode": "not_run_unsupported_case",
            "limitedAnatomyContext": True,
            "suggestedMatches": suggested,
            "router": {
                "case_family": sc.get("case_family"),
                "selectionMode": "unsupported_case_no_approach_guessing",
                "supported": False,
                "reason": sc.get("reason", ""),
            },
        }

    legacy = await run_in_threadpool(
        run_pipeline_fast,
        case_prompt=prompt,
        catalog=CATALOG,
        client=OPENAI_CLIENT,
    )
    return legacy


@app.post("/anki/ortho-context")
async def anki_ortho_context(request: AnkiOrthoContextRequest):
    return await run_in_threadpool(
        build_anki_ortho_context_response,
        request.model_dump(),
    )