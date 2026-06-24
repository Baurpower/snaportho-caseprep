"""Pydantic schemas for factory artifacts."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SourcedClaim(BaseModel):
    text: str
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    source_section: Optional[str] = None
    confidence: str = "medium"


class ExtractedKnowledge(BaseModel):
    procedure_id: str
    display_name: str
    extracted_at: str
    source_ids: List[str] = Field(default_factory=list)
    indications: List[SourcedClaim] = Field(default_factory=list)
    contraindications: List[SourcedClaim] = Field(default_factory=list)
    setup_positioning: List[SourcedClaim] = Field(default_factory=list)
    approach_landmarks: List[SourcedClaim] = Field(default_factory=list)
    surgical_layers: List[Dict[str, Any]] = Field(default_factory=list)
    structures_at_risk: List[Dict[str, Any]] = Field(default_factory=list)
    implant_strategy: List[SourcedClaim] = Field(default_factory=list)
    reduction_or_fluoro_checkpoints: List[SourcedClaim] = Field(default_factory=list)
    complications: List[SourcedClaim] = Field(default_factory=list)
    postop_protocol: List[SourcedClaim] = Field(default_factory=list)
    pimp_question_facts: List[SourcedClaim] = Field(default_factory=list)
    source_refs: List[str] = Field(default_factory=list)
    extraction_warnings: List[str] = Field(default_factory=list)
    confidence_score: float = 0.0


class GenerationMeta(BaseModel):
    procedure_id: str
    generated_at: str
    factory_version: str = "caseprep_factory_v1"
    model_used: Optional[str] = None
    source_grounding_score: float = 0.0
    structural_completeness_score: float = 0.0
    clinical_accuracy_score: float = 0.0
    or_preparedness_score: float = 0.0
    resident_utility_score: float = 0.0
    attending_relevance_score: float = 0.0
    hallucination_risk_score: float = 0.0
    overall_quality_score: float = 0.0
    coverage_score: int = 0
    blocking_issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggested_revision_actions: List[str] = Field(default_factory=list)
    review_status: str = "needs_review"
    runtime_promoted: bool = False
    certified: bool = False