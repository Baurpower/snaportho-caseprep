"""
Internal API key guard for server-to-server CasePrep registry routes.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import Header, HTTPException, status

logger = logging.getLogger(__name__)

ENV_KEY_NAME = "CASEPREP_INTERNAL_API_KEY"
ENV_NAME = "CASEPREP_ENV"
HEADER_NAME = "x-caseprep-internal-api-key"

# Environments where running without a configured key is a deliberate local
# convenience, not a misconfiguration. Anything else (including an unset or
# unrecognized CASEPREP_ENV) is treated as non-local and must fail closed.
_LOCAL_ENVS = frozenset({"local", "dev", "development", "test"})


def _configured_api_key() -> str:
    return (os.getenv(ENV_KEY_NAME) or "").strip()


def _current_env() -> str:
    return (os.getenv(ENV_NAME) or "local").strip().lower()


async def require_internal_api_key(
    x_caseprep_internal_api_key: Optional[str] = Header(default=None, alias=HEADER_NAME),
) -> None:
    configured = _configured_api_key()
    if not configured:
        env = _current_env()
        if env in _LOCAL_ENVS:
            logger.warning(
                "%s is not set; allowing unauthenticated access to /caseprep/registry/* "
                "because %s=%s is treated as local development.",
                ENV_KEY_NAME,
                ENV_NAME,
                env,
            )
            return

        # Fail closed outside local/dev/test: never allow unauthenticated
        # access just because the key is unset. Never log header/key values.
        logger.error(
            "%s is not set while %s=%s; rejecting all /caseprep/registry/* requests.",
            ENV_KEY_NAME,
            ENV_NAME,
            env,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal API key is not configured for this environment.",
        )

    provided = (x_caseprep_internal_api_key or "").strip()
    if not provided or provided != configured:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal API key.",
        )