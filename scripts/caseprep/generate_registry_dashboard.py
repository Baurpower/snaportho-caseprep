#!/usr/bin/env python3
"""
Generate CasePrep registry dashboard markdown.

Run: python3 scripts/caseprep/generate_registry_dashboard.py
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from registry_lib import (  # noqa: E402
    REGISTRY_INDEX_PATH,
    collect_text_blobs,
    cross_region_warnings,
    list_procedure_folders,
    load_json,
    load_manifest,
    placeholder_hits,
    utc_now_iso,
)

DASHBOARD_PATH = Path(__file__).resolve().parents[2] / "docs" / "caseprep-registry-dashboard.md"


def main() -> int:
    folders = list_procedure_folders()
    index = load_json(REGISTRY_INDEX_PATH, {}) or {}

    by_content: Counter = Counter()
    by_specialty: Counter = Counter()
    uncertified: List[Dict[str, Any]] = []
    low_coverage: List[str] = []
    validation_warnings: List[str] = []

    for folder in folders:
        m = load_manifest(folder)
        if not m:
            continue
        slug = m.get("slug", folder.name)
        cs = m.get("content_status", "unknown")
        by_content[cs] += 1
        by_specialty[m.get("specialty", "unknown")] += 1

        if cs != "certified":
            uncertified.append(
                {
                    "slug": slug,
                    "display_name": m.get("display_name"),
                    "content_status": cs,
                    "coverage_score": m.get("coverage_score", 0),
                }
            )

        if cs == "certified" and (m.get("coverage_score") or 0) < 85:
            low_coverage.append(f"{slug} ({m.get('coverage_score')})")

        blob = collect_text_blobs(folder)
        if cs == "certified":
            ph = placeholder_hits(blob)
            if ph:
                validation_warnings.append(f"{slug}: placeholders {ph}")
            for w in cross_region_warnings(m.get("body_region", ""), blob):
                validation_warnings.append(f"{slug}: {w}")

    uncertified.sort(key=lambda x: -(x.get("coverage_score") or 0))
    next_targets = [u["slug"] for u in uncertified[:15]]

    lines = [
        "# CasePrep Registry Dashboard",
        "",
        f"**Generated:** {utc_now_iso()}",
        "",
        "## Summary",
        "",
        f"- **Total procedures:** {len(folders)}",
        f"- **Certified:** {by_content.get('certified', 0)}",
        f"- **Complete:** {by_content.get('complete', 0)}",
        f"- **Partial:** {by_content.get('partial', 0)}",
        f"- **Missing:** {by_content.get('missing', 0)}",
        f"- **Draft:** {by_content.get('draft', 0)}",
        f"- **Deprecated:** {by_content.get('deprecated', 0)}",
        "",
        "## By specialty",
        "",
    ]
    for spec, count in sorted(by_specialty.items(), key=lambda x: -x[1]):
        lines.append(f"- **{spec}:** {count}")

    lines.extend(["", "## Top uncertified procedures (by coverage_score)", ""])
    for u in uncertified[:20]:
        lines.append(
            f"- `{u['slug']}` — {u['display_name']} ({u['content_status']}, score={u['coverage_score']})"
        )

    lines.extend(["", "## Certified with low coverage (<85)", ""])
    if low_coverage:
        for item in low_coverage:
            lines.append(f"- `{item}`")
    else:
        lines.append("- None")

    lines.extend(["", "## Validation warnings", ""])
    if validation_warnings:
        for w in validation_warnings[:30]:
            lines.append(f"- {w}")
    else:
        lines.append("- None")

    lines.extend(["", "## Recommended next certification targets", ""])
    for slug in next_targets:
        lines.append(f"- `{slug}`")

    if index.get("alias_collisions"):
        lines.extend(["", "## Alias collisions", ""])
        for c in index["alias_collisions"][:10]:
            lines.append(f"- `{c.get('alias')}`: {c.get('existing')} vs {c.get('collision')}")

    DASHBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Dashboard written to {DASHBOARD_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())