---
stage_id: V4_R21_R4_DM01_READER_DSN_STATE_READS_R27_20261017
branch: codex/v4-workspace-cleanup
status: DM01_STATE_READS_USE_READONLY_DSN_LIVE_PG_OPEN
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 21
ingress_adapters_open: 8
other_callsite_rows_open: 237
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue the PG daily scheduler and accepted Head/source state migration
---

# V4 R21-R4 DM-01 Reader DSN state reads

Date: 2026-10-17 (Asia/Shanghai). This batch moves remaining native scheduler-state read methods off the Writer connection.

## Implemented

- Added a shared `read_connect()` boundary that always obtains `V4_NATIVE_PG_READER_DSN` or `WORKBENCH_PG_DSN` through `configured_reader_dsn()`, requests `REPEATABLE READ READ ONLY`, and applies the existing bounded transaction settings and Reader-role attestation.
- Routed `read_probe`, `progress`, `job`, `events`, `settings()` without an update, and `status()` through the Reader boundary.
- `settings(enabled=...)` still requires the explicit Writer connection for its state mutation and audit event, then reads the resulting state through the Reader connection.
- Worker/job writes, retries, cancellation, and enqueue remain in the explicit Writer-backed scheduler. This change does not alter daily publication or Head semantics.

## Verification and limits

- `tests/test_v4_r21_dm01_pg_progress.py`: **10 passed**. The new connection spy verifies `job()` and read-only `settings()` use the configured Reader DSN and read-only transaction.
- A broader selection including `tests/test_v4_pg_jobs_r4.py` had **8 failures** because that suite constructs the PG scheduler without a configured `V4_NATIVE_PG_DSN`; one guard assertion also depends on the database isolation plugin excluded by the targeted `--confcutdir=tests` run. It is not recorded as passing. No PG connection or write occurred.
- Compile and diff checks passed. No live status query, DDL/DML, Head switch, service, or worker ran.

## Accounting

Original P1 baseline **266**. Formally complete **0 / 266**; formally remaining **266**. Code-level PG read paths remain **21** pending live readback/reconciliation; **8** ingress adapters remain open; **237** other callsite rows remain open. **22** reference edges remain unmapped. This scheduler-state batch changes no baseline callsite status.

## Next stage

Continue the real PG scheduler state migration and the accepted daily Head/source/Owner chain. Keep file calendar mode and publication behavior open until the accepted publication mapping, Reader identity and same-T0 readback are proven.
