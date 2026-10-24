"""Server-only, uncached approved graph retrieval; one immutable response per run."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from typing import Any, Literal
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class Approval(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["approved"]
    approving_party: str
    basis: str
    approved_at: str
    revoked: Literal[False]


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approach_id: str
    canonical_entity_id: UUID
    procedure_entity_id: UUID
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    packet: dict[str, Any]
    mappings: list[dict[str, Any]]
    approval: Approval

    @model_validator(mode="after")
    def validate_packet(self):
        if self.packet.get("approach_id") != self.approach_id:
            raise ValueError("packet identity mismatch")
        actual_hash = hashlib.sha256(json.dumps(self.packet, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        if actual_hash != self.content_hash:
            raise ValueError("packet hash mismatch")
        claims = self.packet.get("claims")
        sources = self.packet.get("sources")
        if not isinstance(claims, list) or not isinstance(sources, list):
            raise ValueError("missing claims/sources")
        source_ids = {s["source_id"] for s in sources}
        claim_ids = {c["claim_id"] for c in claims}
        if len(claim_ids) != len(claims) or len(source_ids) != len(sources):
            raise ValueError("duplicate provenance IDs")
        for claim in claims:
            if not set(claim.get("source_ids", [])) <= source_ids:
                raise ValueError("unknown source")
        for values in self.packet.values():
            if isinstance(values, list):
                for row in values:
                    if isinstance(row, dict) and not set(row.get("claim_ids", [])) <= claim_ids:
                        raise ValueError("unknown claim")
        return self


class GraphResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    procedure_slug: str
    status: Literal["available", "no_mapping", "no_approved_content"]
    candidates: list[Candidate]

    @model_validator(mode="after")
    def consistency(self):
        if (self.status == "available") != bool(self.candidates):
            raise ValueError("inconsistent availability")
        if len({c.approach_id for c in self.candidates}) != len(self.candidates):
            raise ValueError("duplicate candidates")
        return self


class ApproachGraphProvider:
    def __init__(self, url: str, key: str, *, client: httpx.AsyncClient | None = None):
        self.url, self.key = url.rstrip("/"), key
        self.client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(2.0, connect=1.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )

    async def fetch(self, procedure_slug: str, approach_id: str | None = None) -> dict:
        start = time.monotonic()
        result = {"status": "unavailable", "candidates": [], "procedure_slug": procedure_slug}
        try:
            if not self.url or not self.key:
                result["reason"] = "not_configured"
                return result
            async with asyncio.timeout(3.0):
                response = await self.client.post(
                    self.url + "/rest/v1/rpc/get_caseprep_approved_approaches",
                    headers={"apikey": self.key, "Authorization": f"Bearer {self.key}"},
                    json={"p_procedure_slug": procedure_slug, "p_approach_id": approach_id},
                )
                response.raise_for_status()
                parsed = GraphResponse.model_validate(response.json())
                if parsed.procedure_slug != procedure_slug or any(
                    approach_id and c.approach_id != approach_id for c in parsed.candidates
                ):
                    raise ValueError("response scope mismatch")
                result.update(parsed.model_dump(mode="json"))
        except (httpx.TimeoutException, TimeoutError):
            result["reason"] = "timeout"
        except httpx.HTTPStatusError:
            result["reason"] = "http_error"
        except (ValidationError, ValueError, KeyError, TypeError):
            result["reason"] = "invalid_response"
        except httpx.RequestError:
            result["reason"] = "transport_error"
        finally:
            result["duration_ms"] = int((time.monotonic() - start) * 1000)
        return result

    async def close(self):
        await self.client.aclose()


_provider: ApproachGraphProvider | None = None


def get_graph_provider() -> ApproachGraphProvider:
    global _provider
    if _provider is None:
        _provider = ApproachGraphProvider(os.getenv("CASEPREP_GRAPH_URL", ""), os.getenv("CASEPREP_GRAPH_SERVICE_KEY", ""))
    return _provider


async def close_graph_provider():
    global _provider
    if _provider is not None:
        await _provider.close()
        _provider = None
