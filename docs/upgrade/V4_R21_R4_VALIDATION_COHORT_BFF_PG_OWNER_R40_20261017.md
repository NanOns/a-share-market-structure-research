---
stage_id: V4_R21_R4_VALIDATION_COHORT_BFF_PG_OWNER_R40_20261017
branch: codex/v4-workspace-cleanup
status: COHORT_BFF_OWNER_READ_USES_EMBEDDED_PG_AUTHORITY
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 22
ingress_adapters_open: 8
other_callsite_rows_open: 235
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue exact-mapped Owner/BFF migrations and validate source evidence using accepted PG Head context
---

# V4 R21-R4 validation cohort BFF PG Owner

Date: 2026-10-17 (Asia/Shanghai). R39 made the operational builder registry available through the embedded PG authority. The validation-cohort statistics route still reloaded the accepted Head and source Owner independently, bypassing the main Reader's embedded PG authority. R39 and the validation-cohort read contract were reviewed before this change.

## Implemented

- `read_authorized_statistics` now accepts an already verified Head value and an injected Owner reader. When Head data is supplied, it verifies that its canonical digest matches the accepted Head token before using its cohort grant map.
- For Heads carrying `native_pg_owner_authority`, the statistics BFF obtains `validation_cohort` through `OperationalSuccessorReader.read()` and passes the resulting Owner payload into the existing frozen-cohort grant, T0, benchmark, and source receipt validations.
- The embedded-PG branch fails closed if the requested owner binding differs or the Reader response is not a READY mapping. It does not call the legacy cohort file loader. The existing legacy contract remains for Heads without embedded PG Owner authority.
- Reconciled `V4-BCA-R2-eb65b592463a23c11d8b` to implemented PG-read code pending accepted-Head and inventory evidence; it remains formally open.

## Verification and limits

- Focused test selection: **12 passed** across the cohort BFF route, registry PG reader and embedded operational Owner Reader.
- The test proves routing and identity checks around a controlled Owner-reader boundary. It does not simulate a real PG acceptance. No PG write/readback, live BFF request, service startup, or Head change occurred.
- The current operational Head has no embedded PG Owner authority or cohort grant evidence, so the route cannot yet be accepted against the current Head.

## Accounting

Original P1 baseline: **266** (200 Owner, 28 other-business, 38 external-source). Formally complete **0 / 266**; remaining **266 / 266**. The callsite had already been counted among the **22** code-level PG paths pending live reconciliation, so R40 changes no category totals: **236** other rows remain open, alongside 8 ingress adapters and 22 unmapped edges. R40 adds implementation evidence for the cohort Owner subpath but closes no formal row.

## Next stage

Continue Head-bound BFF and Owner migrations where the exact source and grant contracts are known. Reconcile formal counts only after approved Reader identity, same-T0 readback and full source-receipt validation.
