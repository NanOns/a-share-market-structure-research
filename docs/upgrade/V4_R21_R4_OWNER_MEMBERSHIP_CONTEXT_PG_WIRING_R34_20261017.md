---
stage_id: V4_R21_R4_OWNER_MEMBERSHIP_CONTEXT_PG_WIRING_R34_20261017
branch: codex/v4-workspace-cleanup
status: PG_MEMBERSHIP_CONTEXT_METADATA_WIRED; CURRENT_HEAD_NOT_MAPPED
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 21
ingress_adapters_open: 8
other_callsite_rows_open: 237
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue actual operational Head and membership/Owner descriptor runtime wiring
---

# V4 R21-R4 Owner membership context PG wiring

Date: 2026-10-17 (Asia/Shanghai). This batch advances the existing PG membership reference from a helper into the current operational Reader context path.

## Implemented

- Membership reference preparation now pins the source snapshot's context metadata in the same authority manifest as the dated membership descriptor under `V4_NATIVE_MEMBERSHIP_CONTEXT_METADATA_R1` version `1.0.0`.
- Added a PG authority reader for that metadata. It verifies exact snapshot binding, membership snapshot ID, required metadata shape, and non-PIT lineage; it does not consult the snapshot file as a fallback.
- When the accepted operational candidate carries `native_membership_reference`, `OperationalSuccessorReaderV1` obtains context metadata through that PG authority and retains it for HTTP context responses. The legacy file path remains available only for candidates without the PG binding.
- Startup `validate()` still performs its existing source/candidate validation, including the snapshot binding. The accepted operational Head in this checkout contains neither `native_pg_owner_authority` nor `native_membership_reference`, so this PG branch cannot be exercised against the current Head.

## Verification and limits

- Four focused tests passed for PG context metadata scope/lineage, authority metadata preparation, operational Reader context routing, and Owner PG validation without opening Owner payload files.
- Python compilation and `git diff --check` passed.
- No compliant PG Reader DSN, current Head authority mapping, live metadata query, publication readback, service or business acceptance was available.

## Accounting

Original P1 baseline **266**. Formally complete **0 / 266**; formally remaining **266**. Code-level PG read paths remain **21** pending full inventory reconciliation and live readback; **8** ingress adapters remain open; **237** other callsite rows remain open. **22** reference edges remain unmapped. R34 adds a PG metadata path but does not claim a baseline row closed.

## Next stage

Continue wiring the accepted operational Head, membership and Owner descriptors through the runtime and BFF. Keep the formal baseline unchanged until a compliant Reader identity and same-T0 accepted PG readback exist.
