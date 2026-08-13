# CasePrep v1.2 rollout

CasePrep v1.2 is additive. It leaves the legacy, v2, and v1.1 routes available and
adds `/case-prep/web/v1.2/stream`.

## Contract and quality policy

- Resolve the procedure before retrieval. Contradictory modifiers and ambiguous
  fracture-only prompts return a clarification packet rather than guessing.
- Prefer exact procedure evidence. Regional semantic fallback is admitted only
  above the stricter v1.2 threshold and is capped at 20% of selected questions.
- Every item carries `provenance`, `claim_support`, and `procedure_relevance`.
- Generated items never displace grounded items. Generated operative flow is
  withheld because an uncited procedural sequence is not a safe fallback.
- `core_done` and `done` expose grounded/generated counts, omitted sections,
  a grounded percentage, `coverage_status`, and a `quality_gate` result.
- Certified packets and packets with at least eight grounded questions skip the
  optional enrichment call, removing the major cold-path delay.

## Enablement order

1. Deploy the CasePrep service with `ENABLE_CASEPREP_WEB_V1_2_STREAM=false`.
2. Deploy the web migration `20260812_210000_caseprep_v12_packet_telemetry.sql`.
3. Set `ENABLE_CASEPREP_WEB_V1_2_STREAM=true` on the CasePrep service.
4. Set `CASEPREP_WEB_V1_2_STREAM_ENABLED=true` on the web service.
5. Set `NEXT_PUBLIC_CASEPREP_V1_2_ENABLED=true` and deploy the web client.
6. Release the iOS build, which requests contract v1.2 and rejects mismatched
   responses instead of rendering an unknown packet format.

Both web stream versions use the same server-side `getBroBotAccessGate`. The web
proxy resolves iOS bearer authentication before browser cookies or guest sessions,
so a signed-in subscriber cannot accidentally receive the guest daily cap.

## Monitoring and rollback

Monitor `caseprep_packet_events` by `coverage_status`, `quality_gate`, canonical
slug, and client surface. The table intentionally stores neither user prompts nor
clinical prose.

Rollback is flag-only: disable `NEXT_PUBLIC_CASEPREP_V1_2_ENABLED` for web clients,
then disable `CASEPREP_WEB_V1_2_STREAM_ENABLED` and
`ENABLE_CASEPREP_WEB_V1_2_STREAM`. Keep the telemetry migration; it is additive.

## Required verification

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
python3 -m compileall -q caseprep
```

For the web repository run `npx tsc --noEmit`. For iOS, run the Snap Ortho test
target; `BroBotModernContractTests` covers fragmented SSE, progressive reduction,
v1.2 provenance, and coverage state.
