"""CasePrep v1.3 unified grounded, RAG, and approach-library stream."""

from __future__ import annotations

from typing import Any, AsyncIterator

from caseprep.engines.v1_2_web_stream import stream_caseprep_packet_v1_2

VERSION = "v1.3"
ENGINE = "rag_approach_packet_stream"


async def stream_caseprep_packet_v1_3(
    prompt: str, *, openai_client: Any, config: Any
) -> AsyncIterator[bytes]:
    async for frame in stream_caseprep_packet_v1_2(
        prompt,
        openai_client=openai_client,
        config=config,
        version=VERSION,
        engine=ENGINE,
    ):
        yield frame
