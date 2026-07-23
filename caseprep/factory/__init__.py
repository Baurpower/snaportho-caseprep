"""
BroBot CasePrep Content Factory — Phase 1.

CLI-driven pipeline: extract → synthesize → QA → human review.
Does not auto-certify or enable runtime.
"""

__all__ = ["compile_modules_to_payload", "compile_procedure", "generate_procedure_draft"]


def __getattr__(name: str):
    """Keep optional Pydantic/OpenAI dependencies lazy for review-only tooling."""
    if name in {"compile_modules_to_payload", "compile_procedure"}:
        from caseprep.factory.compiler import compile_modules_to_payload, compile_procedure

        return {
            "compile_modules_to_payload": compile_modules_to_payload,
            "compile_procedure": compile_procedure,
        }[name]
    if name == "generate_procedure_draft":
        from caseprep.factory.orchestrator import generate_procedure_draft

        return generate_procedure_draft
    raise AttributeError(name)
