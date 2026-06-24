"""
Durable append-only audit log for factory/registry promotion actions.

Every state-changing action in the compile -> review -> approve -> certify ->
promote workflow writes one JSONL line here. The log is additive only —
nothing in this module ever rewrites or deletes existing entries.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from caseprep.factory.paths import ROOT

AUDIT_LOG_PATH = ROOT / "data" / "caseprep" / "factory" / "audit_log.jsonl"

_write_lock = threading.Lock()

VALID_ACTIONS = frozenset(
    {
        "compile_draft",
        "approve",
        "certify",
        "promote_runtime",
        "override_certify",
        "override_promote",
    }
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git_commit_if_available() -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return None
    if result.returncode == 0:
        commit = result.stdout.strip()
        return commit or None
    return None


def record_audit_event(
    *,
    actor: str,
    action: str,
    slug: str,
    previous_status: Optional[str] = None,
    new_status: Optional[str] = None,
    previous_runtime_enabled: Optional[bool] = None,
    new_runtime_enabled: Optional[bool] = None,
    qa_score: Optional[float] = None,
    blocking_issues_count: Optional[int] = None,
    override_used: bool = False,
    override_reason: Optional[str] = None,
    changed_files: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Append one audit entry to data/caseprep/factory/audit_log.jsonl.

    Never accepts or persists secrets (API keys, tokens) — only identities,
    statuses, and review metadata. Returns the entry actually written,
    including a stable "id" derived from its own content for traceability.
    """
    if action not in VALID_ACTIONS:
        raise ValueError(f"Unknown audit action: {action}")

    entry: Dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "actor": (actor or "unknown").strip() or "unknown",
        "action": action,
        "slug": slug,
        "previous_status": previous_status,
        "new_status": new_status,
        "previous_runtime_enabled": previous_runtime_enabled,
        "new_runtime_enabled": new_runtime_enabled,
        "qa_score": qa_score,
        "blocking_issues_count": blocking_issues_count,
        "override_used": bool(override_used),
        "override_reason": override_reason,
        "changed_files": list(changed_files or []),
        "git_commit": _git_commit_if_available(),
    }
    entry["id"] = hashlib.sha256(
        json.dumps(entry, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:16]

    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _write_lock:
        with AUDIT_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry
