from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from vector_search import get_case_snippets
from gpt_refiner import refine_case_snippets
from query_refiner import refine_query

app = FastAPI()

# ── CORS (adjust in production) ───────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    prompt = request.prompt.strip()
    if not prompt:
        return {
            "pimpQuestions": [],
            "otherUsefulFacts": ["❌ No prompt provided"]
        }

    # Refine prompt using GPT
    refined_prompt = refine_query(prompt)
    print(f"🧠 Refined Prompt: {refined_prompt}")

    # Search Pinecone using the refined prompt
    snippets = get_case_snippets(refined_prompt)
    if not snippets:
        return {
            "pimpQuestions": [],
            "otherUsefulFacts": ["❌ No relevant content found."]
        }

    # Refine the results with GPT using the original prompt
    return refine_case_snippets(prompt, snippets)