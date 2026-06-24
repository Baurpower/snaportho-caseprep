"""
Pydantic DTOs for the read-only CasePrep registry API.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from caseprep.registry.constants import REGISTRY_READ_SCHEMA_VERSION


class RegistryHealthDTO(BaseModel):
    status: Literal["ok", "degraded", "unavailable"]
    registry_available: bool
    procedure_count: int
    certified_count: int
    index_generated_at: Optional[str] = None
    schema_version: str = REGISTRY_READ_SCHEMA_VERSION


class ProcedureSummaryDTO(BaseModel):
    slug: str
    display_name: str
    specialty: str
    body_region: str
    procedure_family: str
    content_status: str
    review_status: str
    coverage_score: int
    is_live: bool
    deprecated: bool
    replacement_slug: Optional[str] = None
    has_modules: bool
    open_validation_count: int = 0


class RegistryIndexDTO(BaseModel):
    generated_at: Optional[str] = None
    counts_by_content_status: Dict[str, int] = Field(default_factory=dict)
    counts_by_review_status: Dict[str, int] = Field(default_factory=dict)
    procedures: List[ProcedureSummaryDTO] = Field(default_factory=list)


class BulletItemDTO(BaseModel):
    kind: Literal["bullet"] = "bullet"
    text: str
    source_urls: List[str] = Field(default_factory=list)


class TextItemDTO(BaseModel):
    kind: Literal["text"] = "text"
    text: str


class StructureAtRiskItemDTO(BaseModel):
    kind: Literal["structure_at_risk"] = "structure_at_risk"
    structure: str
    why_at_risk: str
    how_to_avoid_injury: str
    consequence_of_injury: str
    approach_context: Optional[str] = None
    source_urls: List[str] = Field(default_factory=list)


class SurgicalLayerItemDTO(BaseModel):
    kind: Literal["surgical_layer"] = "surgical_layer"
    layer_name: str
    what_user_should_know: str
    key_structures: List[str] = Field(default_factory=list)
    structures_at_risk: List[str] = Field(default_factory=list)
    surgical_relevance: str
    source_urls: List[str] = Field(default_factory=list)


class PimpQuestionItemDTO(BaseModel):
    kind: Literal["pimp_question"] = "pimp_question"
    question: str
    answer: str


class SourceItemDTO(BaseModel):
    kind: Literal["source"] = "source"
    source_type: str
    title: Optional[str] = None
    url: str
    consumed: bool = False


ClinicalSectionItemDTO = Union[
    BulletItemDTO,
    TextItemDTO,
    StructureAtRiskItemDTO,
    SurgicalLayerItemDTO,
    PimpQuestionItemDTO,
    SourceItemDTO,
]


class ClinicalSectionDTO(BaseModel):
    key: str
    label: str
    content_type: str
    is_required: bool
    is_empty: bool
    coverage_weight: int
    items: List[Dict[str, Any]] = Field(default_factory=list)


class SourceDTO(BaseModel):
    id: str
    source_type: str
    title: Optional[str] = None
    url: str
    consumed: bool
    linked_section_keys: List[str] = Field(default_factory=list)


class ValidationWarningDTO(BaseModel):
    code: str
    severity: Literal["info", "warning", "blocking"]
    section_key: Optional[str] = None
    message: str
    detail: Optional[str] = None


class SectionEditRequestDTO(BaseModel):
    items: List[Dict[str, Any]] = Field(default_factory=list)


class SectionEditResponseDTO(BaseModel):
    section: "ClinicalSectionDTO"
    validation_warnings: List[ValidationWarningDTO] = Field(default_factory=list)
    coverage_score: int


class CertificationRequestDTO(BaseModel):
    certified_by: str
    notes: Optional[str] = None


class PromotionRequestDTO(BaseModel):
    promoted_by: str
    override_reason: Optional[str] = None


class PromotionResponseDTO(BaseModel):
    slug: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    runtime_enabled: bool
    validation_result: Literal["passed", "blocked"]
    validation_warnings: List[ValidationWarningDTO] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    override_used: bool = False
    override_reason: Optional[str] = None
    registry_index_rebuilt: bool = False
    audit_entry_id: str
    audit_log_path: str


class ProcedureDetailDTO(BaseModel):
    slug: str
    display_name: str
    specialty: str
    body_region: str
    procedure_family: str
    content_status: str
    review_status: str
    version: str
    coverage_score: int
    is_live: bool
    deprecated: bool
    replacement_slug: Optional[str] = None
    reviewer: Optional[str] = None
    certified_at: Optional[str] = None
    last_reviewed_at: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    sections: List[ClinicalSectionDTO] = Field(default_factory=list)
    sources: List[SourceDTO] = Field(default_factory=list)
    validation_warnings: List[ValidationWarningDTO] = Field(default_factory=list)
    review_notes_excerpt: Optional[str] = None
    runtime_enabled: bool = False