# Executive Summary — CasePrep Repository Audit & Cleanup

**Performed:** post clean v1 anatomy migration + resolver + hygiene passes.  
**Goal achieved:** Made the repo understandable without deleting history. Production behavior untouched.

## 1. How does the production CasePrep pipeline work?

See `current_pipeline.md` for full details + diagram.

**High level (modern certified path):**
- FastAPI in `main.py` (`/case-prep`, `/anatomy`).
- Query refine + vector snippets (miller local or pinecone) for pimp/caseprep facts.
- **Resolver first** (`procedure_registry.resolve_procedure` — loads aliases from `data/anatomy/registry/procedure_aliases.jsonl`).
- If resolver returns a slug that is in the 24 `CERTIFIED_PAYLOADS` (loaded at startup from `data/anatomy/case_prep/certified_case_prep_payloads.jsonl`): **direct return** of the full pre-baked BroBot payload (with resolver metadata). Old playbook paths bypassed.
- Else: fallback to approach_router gate + hybrid (anatomy_gpt + miller + playbook builders).

**Key innovation of recent work:** The dedicated resolver layer + data/anatomy/ canonical v1 makes wording variations (THA / total hip arthroplasty / 72yo ... THA etc.) robust, and certified case-prep no longer depends on exact playbook names or leaks legacy placeholders.

## 2. Which files are critical? (Source of Truth)

See `source_of_truth.md`.

- `main.py` + `procedure_registry.py` + `approach_router.py` + `vector_search.py` + `query_refiner.py` + `gpt_refiner.py` + hybrid/playbook builders + anatomy_gpt (for fallback).
- **Everything under `data/anatomy/`** (the clean v1: 24 certified payloads + router + 60 procedures + aliases + modules + sources).
- Active validation: `scripts/anatomy/validate_clean_anatomy_v1.py`, `smoke_test_anatomy_runtime.py`, `run_source_coverage_loop.py`.
- Supporting catalogs: data/approach_playbook/ (for approach selection), lower/upper extremity, spine.

## 3. Which files are obsolete? (Historical)

See `version_groups.md` and `archive_manifest.md`.

- All pre-v1 versioned anatomy data (`data/anatomy_*` dirs, old modules/sources/integration, miller gold v1).
- Root embedding experiment artifacts (dozens of `embed_*.txt`, `normalized_*`, `output_vectorversion_*`, `final_*`).
- Superseded reports (phase2/3, v1_1-v1_4 old, hybrid_miller, old playbook_v2 audits, most test_results).
- One-off historical test/audit/build scripts (most of `scripts/` outside `scripts/anatomy/`).
- Legacy pinecone tooling and many old `anatomy_*.py` / reformat scripts.
- ~120+ files moved into `archive/` (with subdirs: legacy_scripts, old_data, old_reports, old_embeddings, etc.). **No files were deleted.**

## 4. Which files still need review?

See `manual_review.md`.

- `data/approach_playbook/` (referenced for approach selection; old versions inside are historical but dir is live).
- Supporting anatomy catalogs (lower/upper/spine + approach_router/).
- A handful of side utilities (cpt_*, ortho_concepts, some remaining root .py and reports).
- Borderline reports / jsonl referenced by the still-active coverage loop script.
- Build artifacts (venv, pycache) — should be cleaned locally + gitignored.

**Nothing uncertain was archived.** ~10-15 items/groups listed for human review.

## 5. What folders should eventually be deleted?

After manual review of the queue + confirmation that no BroBot client or CI relies on them:
- `archive/` (once reviewed; or keep as git history + prune large binaries if needed).
- `data/anatomy_legacy_archive/` (merge or remove after confirming its README is sufficient).
- `venv/`, `__pycache__/` (never commit these).
- Remaining root historical artifacts if any left after this pass.
- Old versioned subdirs inside data/ that were not moved (if any).

Do **not** delete `data/approach_playbook/`, the extremity catalogs, or active scripts/reports without further audit.

## 6. What technical debt remains?

- Dual anatomy paths: clean certified v1 (preferred) vs. legacy hybrid + miller + old playbook (fallback). The resolver helps, but the old code paths are still exercised for non-certified.
- `approach_router.py` + `data/approach_playbook/` still carry v1/v2 history and are loaded even for modern flows (for non-certified or approach IDs).
- Pre-existing Python version issues in some test files (e.g. `dict | str` in query_refiner) that can cause import failures in <3.10 envs (unrelated to this audit).
- Many historical reports and scripts mixed with current ones (now separated by this audit + archive).
- No single "production config" file yet for all paths (hardcoded + env vars + data/anatomy/ as the v1 root).
- The miller gold index and old embedding artifacts are still present (used only in fallback).

## 7. Recommended final folder structure (after full review)

```
.
├── main.py, procedure_registry.py, approach_router.py, vector_search.py, ... (core active .py)
├── data/
│   ├── anatomy/                 # <-- THE canonical v1 source of truth (never version it again)
│   │   ├── registry/, case_prep/, modules/, sources/, reports/
│   ├── approach_playbook/       # (live for approach selection; consider pruning internal old v* later)
│   ├── lower_extremity/, upper_extremity/, spine/, approach_router/  # supporting catalogs
│   └── (optional) anatomy_legacy_archive/ or remove after review
├── scripts/
│   └── anatomy/                 # only the active validators + loop
├── reports/                     # only current/recent (anatomy_v1_*, key brobot post-cleanup, etc.)
├── docs/
│   └── repository_audit/        # this entire audit output (keep forever)
├── archive/                     # historical (review then prune or keep as git artifact)
├── requirements.txt
├── README.md (new top-level summary pointing to docs/repository_audit/executive_summary.md)
└── (venv, __pycache__, .git ignored)
```

**Immediate next actions recommended:**
1. Human review of `manual_review.md` + spot-check a few archived items.
2. Update any external BroBot client / deployment docs to point at `data/anatomy/` as the anatomy corpus.
3. Consider adding a top-level `ARCHITECTURE.md` symlink or include to `docs/repository_audit/current_pipeline.md` + `source_of_truth.md`.
4. Run the two validate/smoke scripts in CI against the clean v1.
5. (Later) prune `archive/` once confidence is high, or keep it and git-lfs the large jsonl if size is an issue.

This audit makes the repo navigable again while fully preserving history and production integrity.
