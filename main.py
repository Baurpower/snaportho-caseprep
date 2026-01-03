import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from vector_search import get_case_snippets
from gpt_refiner import refine_case_snippets
from query_refiner import refine_query

# ✅ import your anatomy pipeline
from anatomy_gpt import load_catalog_from_jsonl_file, run_pipeline

from openai import OpenAI

app = FastAPI()

# ── CORS (adjust in production) ───────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────
# Global singletons (loaded once)
# ─────────────────────────────────────────────────────
CATALOG: List[Dict[str, Any]] = []
OPENAI_CLIENT: Optional[OpenAI] = None

#from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

APPROACH_CATALOG_PATHS = [
    os.getenv(
        "UPPER_APPROACH_CATALOG_PATH",
        str(BASE_DIR / "data" / "upper_extremity" / "approaches" / "upper_extremity_approaches.jsonl"),
    ),
    os.getenv(
        "LOWER_APPROACH_CATALOG_PATH",
        str(BASE_DIR / "data" / "lower_extremity" / "approaches" / "lower_extremity_approaches.jsonl"),
    ),
]

@app.on_event("startup")
def _startup():
    global CATALOG, OPENAI_CLIENT

    # ✅ Load both catalogs
    CATALOG = []
    for p in APPROACH_CATALOG_PATHS:
        CATALOG.extend(load_catalog_from_jsonl_file(p))

    print(f"✅ Loaded approach catalog: {len(CATALOG)} items")
    for p in APPROACH_CATALOG_PATHS:
        print(f"   - {p}")

    # ✅ Reuse one OpenAI client
    OPENAI_CLIENT = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        project=os.getenv("OPENAI_PROJECT_ID"),  # optional
    )
    print("✅ OpenAI client initialized")


# ── Request Schema ─────────────────────────────────────
class CasePrepRequest(BaseModel):
    prompt: str


# ── Root Sanity Check ──────────────────────────────────
@app.get("/")
def read_root():
    return {"message": "SnapOrtho CasePrep API is live."}


# ── Case Prep Endpoint ────────────────────────────────
@app.post("/case-prep")
async def case_prep(request: CasePrepRequest):
    prompt = (request.prompt or "").strip()
    if not prompt:
        return {"pimpQuestions": [], "otherUsefulFacts": ["❌ No prompt provided"], "anatomy": None}

    # 1) Refine prompt (blocking)
    refined_prompt = await run_in_threadpool(refine_query, prompt)
    print(f"🧠 Refined Prompt: {refined_prompt}")

    # 2) Pinecone search (blocking)
    snippets = await run_in_threadpool(get_case_snippets, refined_prompt)
    if not snippets:
        return {"pimpQuestions": [], "otherUsefulFacts": ["❌ No relevant content found."], "anatomy": None}

    # 3) Kick off BOTH tasks in parallel (blocking -> threadpool)
    caseprep_task = run_in_threadpool(refine_case_snippets, prompt, snippets)

    anatomy_task = run_in_threadpool(
        run_pipeline,
        case_prompt=prompt,
        catalog=CATALOG,
        snippets=snippets,
        client=OPENAI_CLIENT,
    )

    # 4) Await both together
    caseprep_result, anatomy_result = await asyncio.gather(caseprep_task, anatomy_task)

    # 5) Merge
    return {**caseprep_result, "anatomy": anatomy_result}

# ✅ Optional: dedicated anatomy-only endpoint
@app.post("/anatomy")
async def anatomy_only(request: CasePrepRequest):
    prompt = (request.prompt or "").strip()
    if not prompt:
        return {"error": "No prompt provided"}

    if not CATALOG:
        return {"error": "Approach catalog not loaded"}

    result = await run_in_threadpool(
        run_pipeline,
        case_prompt=prompt,
        catalog=CATALOG,
        client=OPENAI_CLIENT,
    )
    return result
