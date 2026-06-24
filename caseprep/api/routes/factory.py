"""
CasePrep factory control-plane routes: guarded runtime promotion.

This router never compiles or writes certified_payload.json — that remains
a CLI-only step (`python -m caseprep.factory compile --promote`). It only
flips runtime_enabled=true for a procedure that is already certified and
already has a certified_payload.json on disk, after re-validating it.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from caseprep.api.deps.internal_auth import require_internal_api_key
from caseprep.registry.dto import PromotionRequestDTO, PromotionResponseDTO
from caseprep.services.registry_read_service import ProcedureNotFoundError
from caseprep.services.registry_write_service import promote_to_runtime

router = APIRouter(
    prefix="/caseprep/factory",
    tags=["caseprep-factory"],
    dependencies=[Depends(require_internal_api_key)],
)


@router.post("/promote/{slug}", response_model=PromotionResponseDTO)
def factory_promote_procedure(
    slug: str,
    body: PromotionRequestDTO,
) -> PromotionResponseDTO:
    """
    Promote an already-certified procedure to live runtime.

    Requires: existing certified_payload.json, manifest content_status and
    review_status both 'certified', no blocking QA issues, no blocking
    validation warnings, and not deprecated. Any of those can be bypassed
    only by supplying override_reason, which is persisted to the audit log.
    """
    try:
        result = promote_to_runtime(
            slug,
            body.promoted_by,
            override_reason=body.override_reason,
        )
    except ProcedureNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Procedure '{slug}' was not found.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return PromotionResponseDTO(
        slug=result["slug"],
        previous_status=result["previous_status"],
        new_status=result["new_status"],
        runtime_enabled=result["runtime_enabled"],
        validation_result=result["validation_result"],
        validation_warnings=result["validation_warnings"],
        warnings=result["warnings"],
        override_used=result["override_used"],
        override_reason=result["override_reason"],
        registry_index_rebuilt=result["registry_index_rebuilt"],
        audit_entry_id=result["audit_entry_id"],
        audit_log_path=result["audit_log_path"],
    )
