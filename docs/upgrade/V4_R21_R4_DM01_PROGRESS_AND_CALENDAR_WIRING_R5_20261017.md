---
stage_id: V4_R21_R4_DM01_PROGRESS_AND_CALENDAR_WIRING_R5_20261017
baseline_sha: 8055b9f21fbb719ea1637de582ea754f4435188c
branch: codex/v4-workspace-cleanup
status: PG_PROGRESS_AND_CALENDAR_CODE_WIRED_LIVE_PG_OPEN
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
live_pg_catalog_or_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue replacing active daily Head/source inputs and batch exact Owner/other-business callsites
---

# V4 R21-R4 DM-01 progress and calendar wiring

Date: 2026-10-17 (Asia/Shanghai). This batch continues the R21-R4 Drive task card and the preceding R2-R4 batches.

## Implemented

- Added a partial index on `update_job_days(trade_date)` for `state='PUBLISHED'`, matching the read path used by the daily status projection.
- Added a runtime-mode test proving all existing `official_sessions(root)` callers select the PG reader when `V4_MARKET_CALENDAR_SOURCE=PG`; the PG branch does not inspect a file Head. Missing PG selectors still fail closed.
- Daily status now has a bounded PG query path to report latest published day and the query has a matching index. This only migrates the DM-01 progress field; the execution planner and accepted Head/source artifact inputs still include filesystem reads.

## Batch accounting

The baseline remains 266 P1 items: formally complete **0**, remaining **266**. Inventory migration statuses remain OPEN 237, ingress 8 and PG-code-pending-live-read/inventory 21; 22 reference edges remain unmapped. No row is closed by this batch. The market calendar callsite remains OPEN pending default runtime selection and live PG identity/namespace reconciliation.

## Verification

- Consolidated focused selection: **110 passed** across publication/contract/Owner, DM-01 progress, PG calendar runtime selection, TDX paths and BaoStock collection tests.
- Compile checks and `git diff --check` passed. The PG SQL paths are exercised with fakes; no live PG catalog/readback was available.
- No PG DDL/DML or operational worker/service was run.

## Next stage

Continue the daily accepted Head and source-artifact conversion and migrate mapped Owner/other-business callers in exact-ID batches. Keep formal counts unchanged until live accepted publication and Owner readback confirm per-ID reconciliation.
