from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from cpt_suggester import suggest_cpt_codes

app = FastAPI(title="CPT Suggester API")


class CPTSuggestRequest(BaseModel):
    case_description: str


@app.post("/cpt/suggest")
def suggest_cpt(request: CPTSuggestRequest):
    try:
        result = suggest_cpt_codes(request.case_description)
        return {
            "case_description": request.case_description,
            **result
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/api/cpt/health")
def health_check():
    return {"status": "ok", "service": "cpt-suggester"}