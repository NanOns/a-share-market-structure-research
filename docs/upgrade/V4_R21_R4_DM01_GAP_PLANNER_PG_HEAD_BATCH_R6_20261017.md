---
stage_id: V4_R21_R4_DM01_GAP_PLANNER_PG_HEAD_BATCH_R6_20261017
baseline_sha: 14184363f5c2594e14057b5b7c704a9899927f96
branch: codex/v4-workspace-cleanup
status: PG_GAP_PLANNER_CODE_WIRED_LIVE_PG_OPEN
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
live_pg_catalog_or_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue daily executor source/accepted artifact migration and exact Owner/other-business callsite batches
---

# V4 R21-R4 DM-01 PG Head and gap-planner batch

Date: 2026-10-17 (Asia/Shanghai). This batch continues the R21-R4 execution card and R2-R5 code batches.

## Implemented code path

- Refactored the durable daily scheduler to call an overridable gap-planner boundary for enqueue, status and worker ticks.
- In `V4_MARKET_CALENDAR_SOURCE=PG` mode, the native PG scheduler obtains both the accepted trade date and session list from the accepted PG publication Head/calendar relation. It runs the same versioned gap planner against the returned calendar contract and never reads `V4_OPERATIONAL_RESEARCH_HEAD.json` for this scheduling state.
- Added the explicit `V4_OFFICIAL_MARKET_CALENDAR_V1` contract schema. PG scheduling requires the exact approved contract binding, venue agreement, exchange list, calendar relation/digest semantics, contiguous session numbers, ordered dates, exact database identity and read-only role. Missing data fails closed.
- File mode remains the default pending live reconciliation. Daily provider execution, its accepted source artifacts, and publication/Head write flow still have file-backed inputs and are not included as migrated by this batch. Scheduler source-revision calculation no longer reads the BaoStock runtime-acceptance report directory; it uses verified readiness freezes and the PG-backed probe state. The executor still verifies its dated source receipt before deriving or publishing.

## Batch accounting

Original baseline: **266 P1 items**. Formal completed remains **0 / 266**; formal remaining **266**. Inventory counts remain OPEN 237, ingress 8, and PG code paths pending live-PG/inventory reconciliation 21. The calendar callsite remains OPEN because its normal runtime selection is not PG and no live accepted publication was read. Unmapped reference edges remain 22.

## Verification

- **126 passed** in the consolidated focused selection: publication and contract validation, Owner manifest, DM-01 PG progress and gap planner, PG calendar, scheduler report-authority guard, TDX path guards and BaoStock collection.
- Compile checks, staged repository policy, and `git diff --check` passed. A broader legacy daily-jobs test selection was attempted; 16 tests stop during setup because `V4_NATIVE_PG_DSN` is not configured. No test connected to or wrote PG. PG behavior in the focused selection uses PG-shaped fakes; no live PG read or complete business acceptance occurred.
- No PG DDL/DML, source acquisition, scheduler, web service or production operation ran.

## Next stage

Continue migrating the daily executor's accepted source and artifact inputs. Then proceed through exact Owner and other-business P1 IDs. Keep all 266 formally open until live Head/source/Owner readback and per-ID reconciliation pass.
