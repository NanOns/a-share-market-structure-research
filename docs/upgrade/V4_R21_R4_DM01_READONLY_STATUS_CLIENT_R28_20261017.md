---
stage_id: V4_R21_R4_DM01_READONLY_STATUS_CLIENT_R28_20261017
branch: codex/v4-workspace-cleanup
status: READONLY_STATUS_CLIENT_REQUIRES_NO_WRITER_DDL_LIVE_PG_OPEN
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 21
ingress_adapters_open: 8
other_callsite_rows_open: 237
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue accepted daily Head/source/Owner mapping and PG scheduler state readback
---

# V4 R21-R4 DM-01 read-only status client

Date: 2026-10-17 (Asia/Shanghai). This batch adds a scheduler-state query surface that can run without writer credentials or schema initialization.

## Implemented

- Added `DailyJobsReadOnly`, which initializes only local query metadata and never resolves `V4_NATIVE_PG_DSN`, opens a writer connection, creates a schema, or executes scheduler DDL.
- It inherits the state read methods, which use `read_connect()` and the configured Reader DSN in a read-only repeatable-read transaction.
- Worker start/tick, writer connection use, and worker-lock acquisition fail closed with `V4_PG_DAILY_JOBS_READ_ONLY`.
- This can be injected into the existing daily service handler for a read-only status surface. The existing worker-backed `DailyJobs` class remains the explicit write-capable scheduler.

## Verification and limits

- `tests/test_v4_r21_dm01_pg_progress.py`: **11 passed**. The new test proves the status client needs no writer DSN and refuses to start or write work.
- Verification used a PG-shaped read cursor. No PG connection, catalog inspection, DDL/DML, service, or worker ran.
- The client assumes the workspace scheduler schema already exists; it does not create or migrate it.

## Accounting

Original P1 baseline **266**. Formally complete **0 / 266**; formally remaining **266**. Code-level PG read paths remain **21** pending live readback/reconciliation; **8** ingress adapters remain open; **237** other callsite rows remain open. **22** reference edges remain unmapped. This adds a reader class but closes no baseline callsite.

## Next stage

Continue the accepted daily Head/source/Owner migration and exact PG scheduler readback. Do not treat this read-only client or cursor tests as live operational acceptance.
