from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from query_caseprep import case_prep_lookup

app = FastAPI(
    title="SnapOrtho Case Prep API",
    description="API to retrieve anatomy and pimp questions based on surgical case input.",
    version="1.0.0"
)

# Optional: Allow frontend apps (e.g., Next.js) to access this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request & response models
class CasePrepRequest(BaseModel):
    prompt: str

class CasePrepResponse(BaseModel):
    answer: str

# Main route
@app.post("/case-prep", response_model=CasePrepResponse, tags=["Case Preparation"])
async def run_case_prep(req: CasePrepRequest):
    answer = case_prep_lookup(req.prompt)
    return CasePrepResponse(answer=answer)
