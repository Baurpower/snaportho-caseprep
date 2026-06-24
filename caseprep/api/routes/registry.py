"""
CasePrep registry routes: read-only reads + Phase 2 write endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from caseprep.api.deps.internal_auth import require_internal_api_key
from caseprep.registry.dto import (
    CertificationRequestDTO,
    ProcedureDetailDTO,
    RegistryHealthDTO,
    RegistryIndexDTO,
    SectionEditRequestDTO,
    SectionEditResponseDTO,
)
from caseprep.services.registry_read_service import (
    ProcedureNotFoundError,
    get_health,
    get_index,
    get_procedure_detail,
)
from caseprep.services.registry_write_service import (
    certify_procedure,
    update_section,
)

router = APIRouter(
    prefix="/caseprep/registry",
    tags=["caseprep-registry"],
    dependencies=[Depends(require_internal_api_key)],
)


# ── Read routes ───────────────────────────────────────────────────────────────

@router.get("/health", response_model=RegistryHealthDTO)
def registry_health() -> RegistryHealthDTO:
    return get_health()


@router.get("/index", response_model=RegistryIndexDTO)
def registry_index() -> RegistryIndexDTO:
    return get_index()


@router.get("/procedures/{slug}", response_model=ProcedureDetailDTO)
def registry_procedure_detail(
    slug: str,
    include_validation: bool = Query(default=False),
) -> ProcedureDetailDTO:
    try:
        return get_procedure_detail(slug, include_validation=include_validation)
    except ProcedureNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Procedure '{slug}' was not found.",
        ) from exc


# ── Write routes (Phase 2) ────────────────────────────────────────────────────

@router.patch(
    "/procedures/{slug}/sections/{section_key}",
    response_model=SectionEditResponseDTO,
)
def registry_update_section(
    slug: str,
    section_key: str,
    body: SectionEditRequestDTO,
) -> SectionEditResponseDTO:
    """
    Replace one section in modules.json with the provided items.
    Recalculates coverage score and re-runs validation.
    Only called by the snaportho-web server proxy — never exposed to the browser.
    """
    try:
        result = update_section(slug, section_key, body.items)
    except ProcedureNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Procedure '{slug}' was not found.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return SectionEditResponseDTO(
        section=result["section"],
        validation_warnings=result["validation_warnings"],
        coverage_score=result["coverage_score"],
    )


@router.post(
    "/procedures/{slug}/certify",
    response_model=ProcedureDetailDTO,
)
def registry_certify_procedure(
    slug: str,
    body: CertificationRequestDTO,
) -> ProcedureDetailDTO:
    """
    Mark a procedure certified in manifest.json.
    Does NOT set runtime_enabled or regenerate certified_payload.json.
    Certification is a review marker only — export is a separate step.
    """
    try:
        return certify_procedure(slug, body.certified_by, body.notes)
    except ProcedureNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Procedure '{slug}' was not found.",
        ) from exc
