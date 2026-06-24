"""
CLI entrypoint for CasePrep Content Factory.

  python -m caseprep.factory.compile --slug tka
  python -m caseprep.factory.generate --slug tha_lateral
  python -m caseprep.factory.batch_generate --limit 5 --dry-run
"""

from __future__ import annotations

import argparse
import sys
from typing import List

from caseprep.factory.compiler import CompilerError, compile_procedure
from caseprep.factory.orchestrator import generate_procedure_draft, list_batch_candidates
from caseprep.services.registry_read_service import (
    ProcedureNotFoundError,
    get_procedure_detail,
)
from caseprep.services.registry_write_service import (
    approve_procedure,
    certify_procedure,
    promote_to_runtime,
)


def _cmd_compile(args: argparse.Namespace) -> int:
    if args.promote and not args.actor:
        print("COMPILE FAILED: --actor is required when using --promote")
        return 1
    try:
        result = compile_procedure(
            args.slug,
            promote=args.promote,
            dry_run=args.dry_run,
            strict=not args.lenient,
            update_manifest_hash=args.update_hash,
            actor=args.actor,
            override_reason=args.override_reason,
        )
    except CompilerError as exc:
        print(f"COMPILE FAILED: {exc}")
        return 1

    print("=== Compile ===")
    print(f"slug: {result['slug']}")
    print(f"output: {result['output_path']}")
    print(f"promote: {result['promote']}")
    print(f"dry_run: {result['dry_run']}")
    print(f"payload_hash: {result['payload_hash']}")
    if result.get("override_used"):
        print("override_used: True")
    return 0


def _cmd_review(args: argparse.Namespace) -> int:
    """Read-only: show current status + validation warnings. No mutation."""
    try:
        detail = get_procedure_detail(args.slug, include_validation=True)
    except ProcedureNotFoundError as exc:
        print(f"REVIEW FAILED: {exc}")
        return 1

    print("=== Review ===")
    print(f"slug: {detail.slug}")
    print(f"content_status: {detail.content_status}")
    print(f"review_status: {detail.review_status}")
    print(f"runtime_enabled: {detail.runtime_enabled}")
    print(f"is_live: {detail.is_live}")
    print(f"coverage_score: {detail.coverage_score}")
    blocking = [w for w in detail.validation_warnings if w.severity == "blocking"]
    warning = [w for w in detail.validation_warnings if w.severity == "warning"]
    print(f"blocking_validation_warnings: {len(blocking)}")
    for w in blocking:
        print(f"  - {w.message}")
    print(f"warnings: {len(warning)}")
    for w in warning:
        print(f"  - {w.message}")
    return 0 if not blocking else 2


def _cmd_approve(args: argparse.Namespace) -> int:
    try:
        approve_procedure(args.slug, args.actor, notes=args.notes)
    except (ProcedureNotFoundError, ValueError) as exc:
        print(f"APPROVE FAILED: {exc}")
        return 1
    print("=== Approve ===")
    print(f"slug: {args.slug}")
    print(f"approved_by: {args.actor}")
    return 0


def _cmd_certify(args: argparse.Namespace) -> int:
    try:
        certify_procedure(args.slug, args.actor, notes=args.notes)
    except ProcedureNotFoundError as exc:
        print(f"CERTIFY FAILED: {exc}")
        return 1
    print("=== Certify ===")
    print(f"slug: {args.slug}")
    print(f"certified_by: {args.actor}")
    return 0


def _cmd_promote(args: argparse.Namespace) -> int:
    try:
        result = promote_to_runtime(
            args.slug,
            args.actor,
            override_reason=args.override_reason,
        )
    except (ProcedureNotFoundError, ValueError) as exc:
        print(f"PROMOTE FAILED: {exc}")
        return 1

    print("=== Promote ===")
    print(f"slug: {result['slug']}")
    print(f"previous_status: {result['previous_status']}")
    print(f"new_status: {result['new_status']}")
    print(f"runtime_enabled: {result['runtime_enabled']}")
    print(f"validation_result: {result['validation_result']}")
    print(f"override_used: {result['override_used']}")
    print(f"audit_entry_id: {result['audit_entry_id']}")
    print(f"audit_log_path: {result['audit_log_path']}")
    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    try:
        result = generate_procedure_draft(
            args.slug,
            dry_run=args.dry_run,
            use_llm=not args.no_llm,
            force=args.force,
        )
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"GENERATE FAILED: {exc}")
        return 1

    print("=== Generate ===")
    for key, value in result.items():
        if key != "modules_preview":
            print(f"{key}: {value}")
    if result.get("modules_preview"):
        print(f"modules_preview: {result['modules_preview']}")
    return 0 if not result.get("blocking_issues") else 2


def _cmd_batch_generate(args: argparse.Namespace) -> int:
    candidates = list_batch_candidates(
        limit=args.limit,
        min_coverage=args.min_coverage,
        max_coverage=args.max_coverage,
        include_certified=args.include_certified,
    )
    print("=== Batch Generate ===")
    print(f"candidates: {len(candidates)}")
    print(f"{'slug':<40} {'coverage':>8}  status")
    for row in candidates:
        print(f"{row['slug']:<40} {row['coverage_score']:>8}  {row['content_status']}")

    if args.dry_run:
        print("\nDry run — no procedures generated.")
        return 0

    failures: List[str] = []
    for row in candidates:
        slug = row["slug"]
        try:
            result = generate_procedure_draft(
                slug,
                dry_run=False,
                use_llm=not args.no_llm,
                force=args.force,
            )
            status = "OK" if not result.get("blocking_issues") else "BLOCKED"
            print(f"  {slug}: {status} (QA={result.get('overall_quality_score')})")
            if result.get("blocking_issues"):
                failures.append(slug)
        except Exception as exc:
            print(f"  {slug}: FAIL ({exc})")
            failures.append(slug)

    print(f"\nCompleted: {len(candidates) - len(failures)}/{len(candidates)}")
    if failures:
        print(f"Failures/blocked: {', '.join(failures)}")
        return 2
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="caseprep.factory")
    sub = parser.add_subparsers(dest="command", required=True)

    p_compile = sub.add_parser("compile", help="Compile modules.json to payload draft")
    p_compile.add_argument("--slug", required=True)
    p_compile.add_argument("--promote", action="store_true", help="Write certified_payload.json (still no runtime)")
    p_compile.add_argument("--dry-run", action="store_true")
    p_compile.add_argument("--lenient", action="store_true", help="Skip required-section strict check")
    p_compile.add_argument("--update-hash", action="store_true", help="Update manifest source_payload_hash")
    p_compile.add_argument("--actor", default=None, help="Human identifier; required with --promote")
    p_compile.add_argument(
        "--override-with-reason",
        dest="override_reason",
        default=None,
        help="Bypass promotion guards with a reason (persisted to the audit log)",
    )

    p_review = sub.add_parser("review", help="Show current status + validation warnings (read-only)")
    p_review.add_argument("--slug", required=True)

    p_approve = sub.add_parser("approve", help="Mark a procedure approved (requires no blocking QA issues)")
    p_approve.add_argument("--slug", required=True)
    p_approve.add_argument("--actor", required=True, help="Human identifier performing the approval")
    p_approve.add_argument("--notes", default=None)

    p_certify = sub.add_parser("certify", help="Mark a procedure certified in manifest.json")
    p_certify.add_argument("--slug", required=True)
    p_certify.add_argument("--actor", required=True, help="Human identifier performing certification")
    p_certify.add_argument("--notes", default=None)

    p_promote = sub.add_parser("promote", help="Flip runtime_enabled=true for a certified procedure")
    p_promote.add_argument("--slug", required=True)
    p_promote.add_argument("--actor", required=True, help="Human identifier performing the promotion")
    p_promote.add_argument(
        "--override-with-reason",
        dest="override_reason",
        default=None,
        help="Bypass promotion guards with a reason (persisted to the audit log)",
    )

    p_gen = sub.add_parser("generate", help="Generate draft modules for one procedure")
    p_gen.add_argument("--slug", required=True)
    p_gen.add_argument("--dry-run", action="store_true")
    p_gen.add_argument("--no-llm", action="store_true", help="Rule-based synthesis only")
    p_gen.add_argument("--force", action="store_true", help="Allow draft on certified slug")

    p_batch = sub.add_parser("batch_generate", help="Generate drafts for low-coverage procedures")
    p_batch.add_argument("--limit", type=int, default=5)
    p_batch.add_argument("--min-coverage", type=int, default=0)
    p_batch.add_argument("--max-coverage", type=int, default=84)
    p_batch.add_argument("--dry-run", action="store_true")
    p_batch.add_argument("--no-llm", action="store_true")
    p_batch.add_argument("--force", action="store_true")
    p_batch.add_argument("--include-certified", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "compile":
        return _cmd_compile(args)
    if args.command == "review":
        return _cmd_review(args)
    if args.command == "approve":
        return _cmd_approve(args)
    if args.command == "certify":
        return _cmd_certify(args)
    if args.command == "promote":
        return _cmd_promote(args)
    if args.command == "generate":
        return _cmd_generate(args)
    if args.command == "batch_generate":
        return _cmd_batch_generate(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())