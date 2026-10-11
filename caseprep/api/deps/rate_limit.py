"""
Best-effort per-client rate limit for the legacy public /case-prep route.

The shipped MyCases iOS and Android apps call /case-prep directly without the
internal key, so that route cannot require it yet (platform audit
CASEPREP-01). Until those clients move to the authenticated web proxy, cap
per-IP request rate here; nginx limit_req is the outer layer.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request, status

_WINDOW_SECONDS = 60.0
_HITS: Dict[str, Deque[float]] = defaultdict(deque)


def _limit() -> int:
    try:
        return max(1, int(os.getenv("CASEPREP_LEGACY_REQUESTS_PER_MINUTE", "6")))
    except ValueError:
        return 6


def _client_ip(request: Request) -> str:
    # nginx sets X-Real-IP to the connecting client; never trust a
    # client-supplied X-Forwarded-For chain for keying.
    real_ip = (request.headers.get("x-real-ip") or "").strip()
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"


async def limit_legacy_caseprep(request: Request) -> None:
    key = _client_ip(request)
    now = time.monotonic()
    hits = _HITS[key]
    while hits and now - hits[0] > _WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= _limit():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please wait a minute and try again.",
            headers={"Retry-After": str(int(_WINDOW_SECONDS))},
        )
    hits.append(now)
    if len(_HITS) > 50_000:
        _HITS.clear()
