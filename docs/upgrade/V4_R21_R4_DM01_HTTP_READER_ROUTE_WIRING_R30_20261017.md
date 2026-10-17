---
stage_id: V4_R21_R4_DM01_HTTP_READER_ROUTE_WIRING_R30_20261017
branch: codex/v4-workspace-cleanup
status: STATUS_GET_ROUTES_WIRED_TO_READER; LIVE_PG_READBACK_NOT_RUN
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 21
ingress_adapters_open: 8
other_callsite_rows_open: 237
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue operational Head, Authority, descriptor, source-ingress and Owner callsite migrations
---

# V4 R21-R4 DM-01 HTTP Reader route wiring

Date: 2026-10-17 (Asia/Shanghai). This batch continues the official R21-R4 execution card and R28's writer-free status client.

## Implemented

- `make_daily_handler` now creates or accepts a `DailyJobsReadOnly` status client.
- HTTP GET routes for progress, status, settings, job details and events now use the Reader-only object. The operational status response's nested daily-update state uses it as well.
- A settings PUT still uses the Writer controller for the requested state change, then reads the committed state through the Reader-only client.
- No scheduler, service, PG connection or database mutation was started during this batch.

## Verification and limits

- `tests/test_v4_daily_server_reader_wiring_r30.py` and `tests/test_v4_r21_dm01_pg_progress.py`: **12 passed**. Route tests inject separate Reader and Writer objects and assert that GET paths never call the Writer controller.
- An additional run including `tests/test_v4_pg_runtime_consumers_r3.py` produced **6 failures** and 12 passes. Failures require `V4_NATIVE_PG_DSN` or a frozen default product source absent from this checkout; no live PG call occurred. These results are not treated as acceptance.
- GitHub Actions for R29 commit `0e07526ca0268e97a47c3882c400b5a7380bc8e4` completed successfully: both repository content policy and `v4-pg-publication-candidate` workflows passed, including the business-code file-access audit.
- No live job-state readback, PG schema/privilege validation, service startup, or business acceptance occurred.

## Accounting

Original P1 baseline **266**. Formally complete **0 / 266**; formally remaining **266**. Code-level PG read paths remain **21** pending inventory reconciliation and live readback; **8** ingress adapters remain open; **237** other callsite rows remain open. **22** reference edges remain unmapped. R30 wires the existing daily-state read client into HTTP handlers and does not close a baseline row.

## Next stage

Continue the actual operational Head, Authority, descriptor, source-ingress and Owner callsite migrations. Reconcile exact baseline IDs only after same-T0 PG readback and approved runtime identity are available.
