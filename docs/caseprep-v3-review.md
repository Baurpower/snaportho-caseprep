# CasePrep v3: procedure cores, approach modules, and independent review

CasePrep v3 separates information shared by a procedure from the exposure used
to perform it. Legacy v2 packets are adapted at runtime; their useful content
is retained, but a migrated `certified` flag is displayed as **Curated · agent
review pending** until the v3 review gates pass.

## Packet contract

- `procedure_core`: indication, shared anatomy, reduction/implant principles,
  imaging checkpoints, and postoperative material that does not depend on an
  approach.
- `approaches[]`: independently sourced modules containing selection context,
  limitations, positioning, exposure, layers, landmarks, structures at risk,
  pitfalls, questions, and sources.
- `approach_coverage`: known, complete, and missing approach counts.
- `review`: content hash, evidence status, completed independent review roles,
  review artifacts, and the user-facing review label.

Catalog-only approach matches are deliberately emitted as `coverage_gap`.
They must not be presented as operative instructions or silently selected.

## Independent-agent review

Every review is append-only and bound to the SHA-256 hash of the reviewable
packet. A content change therefore invalidates prior passes automatically.
Use `caseprep.factory.agent_review_v3.record_review` to record a review.

Required independent roles:

1. `procedure_scope_reviewer`
2. `approach_anatomy_reviewer`
3. `operative_sequence_reviewer`
4. `evidence_reviewer`
5. `adversarial_safety_reviewer`
6. `educational_value_reviewer`

A passing review cannot include an unresolved high- or critical-severity
finding. The packet receives the **Independently agent reviewed** label only
when every role passes for the current content hash, every known approach has
complete coverage, and each approach has at least two linked sources.

## Evidence policy

- Bind technique claims to an approach-specific source.
- Prefer AO Surgery Reference or another authoritative operative reference for
  exposure and sequence.
- Use PubMed-indexed systematic reviews, guidelines, or high-quality studies
  for comparative claims.
- Orthobullets is acceptable as a high-yield educational source but should not
  be the sole basis for an independently reviewed packet.
- Qualify preference-sensitive or uncertain comparative evidence explicitly.
- Never infer a missing operative sequence from a catalog title.

## Audit

Run:

```bash
.venv/bin/python scripts/audit_packet_v3.py
```

The report identifies every live packet with approach gaps or missing review
roles. This is the queue for future content/review agents.
