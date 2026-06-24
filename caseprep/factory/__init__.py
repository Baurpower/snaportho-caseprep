"""
BroBot CasePrep Content Factory — Phase 1.

CLI-driven pipeline: extract → synthesize → QA → human review.
Does not auto-certify or enable runtime.
"""

from caseprep.factory.compiler import compile_modules_to_payload, compile_procedure
from caseprep.factory.orchestrator import generate_procedure_draft

__all__ = [
    "compile_modules_to_payload",
    "compile_procedure",
    "generate_procedure_draft",
]