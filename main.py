from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from vector_search import get_case_snippets
from gpt_refiner import refine_case_snippets

app = FastAPI()

# ── CORS (adjust for production) ─────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this in prod!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request Schema ───────────────────────────
class CasePrepRequest(BaseModel):
    prompt: str

# ── Endpoint ─────────────────────────────────
@app.post("/case-prep")
async def case_prep(request: CasePrepRequest):
    prompt = request.prompt.strip()
    if not prompt:
        return {
            "pimpQuestions": [],
            "otherUsefulFacts": ["❌ No prompt provided"]
        }

    snippets = get_case_snippets(prompt)
    if not snippets:
        return {
            "pimpQuestions": [],
            "otherUsefulFacts": ["❌ No relevant content found."]
        }

    return refine_case_snippets(prompt, snippets)
