# Production Pipeline Diagrams

## A. Happy Path: Certified Case (Recommended Modern Path)

```
User input (e.g. "72 yo undergoing posterior THA tomorrow" or "direct anterior hip replacement")
          │
          ▼
main.py (/case-prep or /anatomy)
          │
          ▼
refine_query (query_refiner.py) + get_case_snippets (vector_search.py)
          │
          ▼
refine_case_snippets (gpt_refiner.py)   ← produces pimp/caseprep facts
          │
          ▼
resolve_procedure(prompt)   ← procedure_registry.py
          │
          ├─ Stage A: Exact alias (normalized)
          ├─ Stage B: Contains match
          ├─ Stage C: rapidfuzz fuzzy (>=85)
          └─ Stage D: GPT classifier (confidence >= 0.8)   [only if A/B/C fail]
          │
          ▼
canonical_slug (e.g. "tha_posterior" or "tha_anterior")
          │
          ▼
if slug in CERTIFIED_PAYLOADS:     ← loaded at startup from
                                    data/anatomy/case_prep/certified_case_prep_payloads.jsonl
          │
          ▼
**SHORT-CIRCUIT**
Return:
{
  ...caseprep facts...,
  "anatomy": {
    "mode": "certified_case_prep_payload",
    "procedure_id": "tha_posterior",
    ...
  },
  "brobot_case_prep": <full pre-built payload>
}
```

**Source files involved**:
- `main.py` (the if `slug and slug in CERTIFIED_PAYLOADS` block)
- `procedure_registry.py` (`resolve_procedure`, `_load_procedure_aliases` reading `data/anatomy/registry/procedure_aliases.jsonl`)
- `data/anatomy/case_prep/certified_case_prep_payloads.jsonl` (the 24 trusted payloads)
- `data/anatomy/registry/certification_registry.jsonl`

No old playbook, no Miller, no GPT anatomy generation, no `approach_router` legacy scoring.

## B. Fallback Path: Non-Certified / Low-Confidence Case

```
User input
          │
          ▼
refine + snippets (same as above)
          │
          ▼
resolve_procedure(...)  → returns slug or None + suggested_matches
          │
          ▼
get_supported_case(prompt)   ← approach_router.py
          │
          ├─ Calls resolve_procedure again (for canonical slug)
          ├─ Exact lookup in data/approach_playbook/procedure_to_approach_map_v1.jsonl
          └─ (if no slug match) legacy _score_match on raw normalized prompt against old triggers
          │
          ▼
if supported or allow_unsupported:
          │
          ├─ run_anatomy_legacy() → run_pipeline_fast (anatomy_gpt.py)   [legacy GPT approach/quiz]
          ├─ run_anatomy_miller_only(prompt)   [main.py]
          │     └─ anatomy_context_builder.get_miller_anatomy_context(..., backend=ANATOMY_BACKEND)
          │         (tries pinecone → local; sets retrievalMode)
          │
          ├─ (try) playbook_anatomy_builder.build_playbook_anatomy
          │   + anatomy_curator.curate_playbook_anatomy
          │
          └─ (fallback) build_hybrid_anatomy(legacy, miller)
          │
          ▼
Combined response (caseprep facts + hybrid/legacy/miller anatomy)
```

**Key files**:
- `approach_router.py` (`get_supported_case`, `_load_playbook` from `data/approach_playbook/...`, legacy trigger scoring)
- `main.py` (`run_anatomy_miller_only`, `run_anatomy_legacy`, hybrid assembly, `_unsupported_miller_payload`)
- `anatomy_gpt.py`, `hybrid_anatomy_builder.py`, `playbook_anatomy_builder.py`, `anatomy_curator.py`
- `anatomy_context_builder.py` (Miller retrieval)
- Old playbook data under `data/approach_playbook/`

## C. Failure / Bad Content Paths (Current Risks)

Several paths allow low-quality or incorrect content to reach the user:

1. **Weak alias / contains match in resolver** (`procedure_registry.py`)
   - A prompt containing "hip" or "THA" can match `tha_posterior` even if the user meant something else.
   - No strong disambiguation for "anterior THA" vs generic "THA" in some edge cases (ordering of aliases matters).

2. **Legacy trigger scoring fallback** (`approach_router.py`)
   - When resolver returns no slug, it falls back to old `_score_match` + `_normalize` against the v1 map triggers.
   - This path can still pick an entry based on weak word overlap.

3. **Non-certified path always runs heavy generation**
   - For the 36 non-certified procedures, the full legacy + Miller + GPT stack runs.
   - `run_pipeline_fast` (anatomy_gpt) and the hybrid builders can synthesize anatomy with limited source backing.

4. **Miller retrieval has no strong procedure/approach filter in the fallback**
   - `run_anatomy_miller_only` does general retrieval on the prompt.
   - It can return chunks from the wrong body region or wrong approach if the index metadata is weak.

5. **Hybrid / playbook builder still reachable**
   - Even after the v1 cleanup, `build_playbook_anatomy` + `curate_playbook_anatomy` are called for supported non-certified cases.
   - These can mix content from old playbooks.

6. **Old catalog path still exists**
   - When `ENABLE_LOCAL_ANATOMY_RAG` is false (or in some error paths), it completely bypasses the resolver and certified logic and calls the oldest `run_pipeline_fast` + `CATALOG` (loaded from upper/lower extremity + approach_router mappings).

7. **Unsupported case still returns limited but not zero anatomy**
   - `_unsupported_miller_payload` returns a payload with `limitedAnatomyContext: True` and empty arrays + a warning, but the client may still display partial results.

8. **No hard citation or "source_quote" requirement enforced at response time for fallback paths**
   - The certified payloads have good source_urls, but the generated fallback anatomy can include statements without strong per-fact provenance in some hybrid paths.

9. **Approach contamination risk**
   - Because `approach_router.py` still does mapping based on the old v1 map (even when using the resolver slug), a mismatch between what the resolver thought the procedure was and what approach IDs are recommended can occur for edge cases.

10. **Sparse metadata / old data still in the system**
    - Many modules and sources under the old `data/anatomy_modules/`, `data/anatomy_sources/`, and archived reports still exist and could be accidentally referenced by any script that walks `data/` recursively.

These paths explain why "irrelevant anatomy/playbook matches" and low-quality content can still appear for non-certified or ambiguous inputs.

**Recommended principle**: The certified short-circuit (resolver → data/anatomy/case_prep payload) should be the *only* path that returns rich anatomy for production BroBot use. All other paths should be explicitly marked "limited" or "experimental" and heavily guarded by thresholds + logging.