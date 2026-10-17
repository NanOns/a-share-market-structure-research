---
stage_id: V4_R21_R4_BFF_PG_MEMBERSHIP_DESCRIPTOR_R36_20261017
branch: codex/v4-workspace-cleanup
status: PG_MEMBERSHIP_LOCATOR_REACHES_BFF_WITHOUT_FILE_FALLBACK
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 21
ingress_adapters_open: 8
other_callsite_rows_open: 237
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue accepted Head/Authority/descriptor and BFF runtime integration
---

# V4 R21-R4 BFF PG membership descriptor

Date: 2026-10-17 (Asia/Shanghai). This batch connects R34/R35's PG context snapshot to the Core Product BFF sector-exposure source field.

## Implemented

- Added a single BFF membership-source resolver. In PG membership mode it requires the exact `pg_descriptor` locator carried by the Reader's context snapshot and rejects a file-only locator.
- The sector-exposure response now obtains its membership source through that resolver. Legacy file locators remain available only for candidates without the PG authority binding.
- The operational Reader's PG context snapshot includes the descriptor from the Head-bound membership authority; the HTTP context projector still exposes only its established metadata fields.

## Verification and limits

- Six focused tests passed for metadata preparation, Reader context routing without a snapshot-file open, PG descriptor propagation/fail-closed behavior, and Owner validation without local payload access.
- Python compilation and `git diff --check` passed.
- No current accepted Head contains the membership authority; no live BFF request, PG read, service startup or business acceptance occurred.

## Accounting

Original P1 baseline **266**. Formally complete **0 / 266**; formally remaining **266**. Code-level PG read paths remain **21** pending inventory reconciliation and live readback; **8** ingress adapters remain open; **237** other callsite rows remain open. **22** reference edges remain unmapped. R36 closes no baseline row.

## Next stage

Continue the real accepted Head, membership/Owner descriptor and BFF invocation chain. Reconcile counts only after an approved Reader identity and same-T0 readback against the mapped current Head.
