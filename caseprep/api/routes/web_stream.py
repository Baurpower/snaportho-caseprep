"""Website-only CasePrep v1.1 packet SSE route.

Additive: legacy /case-prep (iOS) and /case-prep/v2 never dispatch here.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from caseprep.config import CasePrepConfig
from caseprep.engines.v1_1_web_stream import stream_caseprep_packet
from caseprep.engines.v1_2_web_stream import stream_caseprep_packet_v1_2
from caseprep.schemas import CasePrepRequest

router = APIRouter()


def _stream_response(stream) -> StreamingResponse:
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/case-prep/web/v1.1/stream")
async def case_prep_web_v1_1_stream(request: CasePrepRequest) -> StreamingResponse:
    cfg = CasePrepConfig.from_env()
    if not cfg.enable_web_v1_1_stream:
        raise HTTPException(status_code=404, detail="CasePrep web v1.1 stream is not enabled.")

    from main import OPENAI_CLIENT  # module-level singleton set at startup

    return _stream_response(
        stream_caseprep_packet(
            (request.prompt or "").strip(),
            openai_client=OPENAI_CLIENT,
            config=cfg,
        )
    )


@router.post("/case-prep/web/v1.2/stream")
async def case_prep_web_v1_2_stream(request: CasePrepRequest) -> StreamingResponse:
    cfg = CasePrepConfig.from_env()
    if not cfg.enable_web_v1_2_stream:
        raise HTTPException(status_code=404, detail="CasePrep web v1.2 is not enabled.")
    from main import OPENAI_CLIENT
    return _stream_response(
        stream_caseprep_packet_v1_2(
            (request.prompt or "").strip(), openai_client=OPENAI_CLIENT, config=cfg
        )
    )
