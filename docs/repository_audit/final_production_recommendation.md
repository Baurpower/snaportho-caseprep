# Final Production Recommendation

## 1. Is the current pipeline production-grade?

**No.**

It has one narrow, high-quality path (the resolver → certified payload short-circuit for the 24 procedures) that is the result of good recent cleanup work. Everything else — the fallback for non-certified cases, approach selection for anything that isn't a perfect certified hit, Miller retrieval, hybrid builders, and the old legacy catalog path — is still a collection of partial, weak, or fake quality gates sitting on top of legacy code and mixed historical data.

For the specific 24 certified cases with good resolver matches, the experience can be excellent. For almost everything else (the majority of real-world inputs once you leave the certified set), the system is still "it works sometimes" with significant risk of wrong-approach, wrong-region, poorly-cited, or outright unsupported anatomy reaching the user.

## 2. What is the biggest architectural risk?

The **resolver is the only real gate**, and the certified short-circuit is the only strong output path. The entire rest of the system (which is still very large and reachable) was designed under a different model ("generate reasonable anatomy from whatever we can retrieve and the old playbooks").

As long as the fallback paths remain large, complex, and only lightly constrained by the resolved `procedure_id` + `approach`, adding more procedures will not increase overall quality — it will mostly increase the number of ways bad content can be generated and the difficulty of noticing regressions.

Secondary risk: `approach_router.py` + the data under `data/approach_playbook/` still carry a lot of historical logic and are called even on paths that went through the modern resolver. This creates a subtle but real chance of approach contamination.

## 3. What should be fixed before adding more cases?

Before certifying the 25th procedure (or before treating non-certified cases as first-class), the following must be in place:

- The resolver must be the single, trusted text-to-procedure component (Phases 1–2 in the roadmap). Legacy trigger scoring in `approach_router.py` should be heavily guarded or removed for any path that cares about anatomy quality.
- A minimum confidence gate + explicit ambiguity handling must exist before a slug is allowed to trigger the certified short-circuit or drive downstream retrieval.
- Certified payloads must have a real contract test + schema that runs in CI (Phase 3).
- The Miller / hybrid / playbook retrieval paths used for fallback must be modified to accept and *enforce* `procedure_id` + `approach_ids` from the resolver (Phase 4). "Just search the prompt" should no longer be the default.
- A real evaluation harness (resolver golden tests + approach contamination tests + payload contracts + E2E for the current certified set) must exist and run on every relevant change (core of Phase 5).

Until these are done, "adding more cases" is mostly theater. The new cases will either (a) only be high-quality when the resolver is perfect, or (b) fall into the same weak fallback system that already exists for the other 36.

## 4. What can wait?

- Building the full certification workflow UI and reviewer queue (Phase 6) can start in parallel, but it only becomes critical after the quality gates and harness exist. You can certify a few more cases manually with good discipline while the harness is being built.
- Advanced operational tooling (dashboards, per-procedure canaries, automatic fallback rate alerts) is valuable but secondary to having the core gates and tests.
- Full namespace separation in the vector index and multi-corpus scaling (parts of the scaling plan) can be done incrementally as you add the 50th–100th procedure. The immediate need is discipline on the existing corpora, not a brand new indexing architecture.

## 5. What should never be used in production?

- The old legacy catalog path (`not ENABLE_LOCAL_ANATOMY_RAG` branch that calls `run_pipeline_fast` with the old `CATALOG` from upper/lower extremity files).
- Any path that reaches `run_pipeline_fast` (anatomy_gpt) or the oldest hybrid logic for a case that a user would reasonably expect to be "prepared" (i.e., anything that looks like a common orthopedic procedure).
- Unconstrained Miller retrieval (no `procedure_id` / approach filter) for anything except pure exploratory RAG.
- The current fallback behavior for the 36 "not_certified" procedures if you are presenting the output as authoritative BroBot case prep. Those should be clearly labeled "limited / in progress" with very little generated anatomy, or the certification effort should be accelerated for the common ones.

## 6. What is the clean target architecture?

See `target_architecture.md`. In one sentence:

A strict pipeline where a **Case Resolver** (data-driven, high-confidence only) produces a canonical `procedure_id`, which is then used to look up either a **Certified Payload** (the only rich output) or a heavily constrained **Anatomy Retrieval** layer that is told the exact procedure + approach and is forbidden from emitting unsupported facts. All other behavior is explicitly "limited."

The current `procedure_registry.py` + `data/anatomy/` work is the right shape for the Resolver + Certified Payload Store. The rest of the system needs to be bent (or parts of the legacy paths removed) until they respect the same constraints.

## 7. What is the next concrete PR?

Do **Phase 1 + the confidence gate from Phase 2** as a single small, reviewable set of changes:

1. Add the top-level `ARCHITECTURE.md` (or update `README`) that clearly labels the certified short-circuit as the production path for BroBot and the rest as guarded fallback / legacy.
2. In `main.py`, introduce and enforce a `MIN_RESOLVER_CONFIDENCE_FOR_CERTIFIED` constant in the short-circuit condition. Log (and optionally reject) any certified short-circuit that came from a low-confidence resolver decision.
3. In `procedure_registry.py` (and the call site in `approach_router.py`), make sure the resolver return value always includes an explicit `confidence` (even for the alias/contains/fuzzy stages) and that `approach_router.get_supported_case` treats a low-confidence or missing slug as "unknown" rather than falling straight into legacy trigger scoring.
4. Expand the existing smoke + validate scripts with 20–30 additional resolver test cases (the ones from the user query + common variants + a few deliberate ambiguities and garbage inputs). These tests must assert the four log lines and the presence/absence of `suggested_matches`.
5. Add a clear comment block in `main.py` (near the certified if) and in `approach_router.py` (in the legacy scoring fallback) saying "This path is legacy and should not be used for new certified or high-volume procedures. See docs/repository_audit/ for the target direction."

This PR is small, changes almost no behavior for the current 24 certified cases (it only makes the guardrails explicit), dramatically improves understandability, and gives you a foundation on which the rest of the roadmap can be built without making the mess worse.

After that PR, the next most valuable work is Phase 3 (real contract tests on the payloads) + the core of Phase 5 (a real harness that includes approach contamination tests). Those two together will let you start certifying additional common procedures with confidence that you won't silently regress the existing ones.

Everything else (full scaling plan, advanced dashboards, multi-corpus namespaces, etc.) is important for the long term but will be built on sand if the above is not done first.

**Bottom line**: The cleanup work created a good island (the certified path). The job now is to stop the rest of the system from being a swamp that leaks into the island, and to make the island the default experience for the cases that matter. The concrete next PR above is the first real step in that direction.