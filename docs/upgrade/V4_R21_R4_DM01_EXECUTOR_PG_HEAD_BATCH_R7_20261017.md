---
stage_id: V4_R21_R4_DM01_EXECUTOR_PG_HEAD_BATCH_R7_20261017
baseline_sha: a056b009df751206a2ab4039c5b8d7362536bac7
branch: codex/v4-workspace-cleanup
status: EXECUTOR_HEAD_NOOP_PG_CODE_OPT_IN_LIVE_READBACK_OPEN
callsite_id: V4-BCA-R2-928e5423aa7c5ec455a8
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
live_pg_catalog_or_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: migrate daily executor dated identity Owner read and final Head publication/CAS
---

# V4 R21-R4 DM-01 executor Head read batch

Date: 2026-10-17 (Asia/Shanghai). This batch follows R6 and changes one exact baseline callsite.

## Code path

- The existing daily executor check for a date already covered by accepted state now calls `PgMarketCalendarReader.calendar()` in `V4_MARKET_CALENDAR_SOURCE=PG` mode and compares against its accepted publication trade date.
- Unsupported source modes fail closed. PG reader errors propagate; there is no file Head fallback on the PG branch. `FILE` remains the default while publication mapping and full business acceptance remain open.
- This change covers only the early NOOP check. Later daily derivation still reads the local Head and lifecycle/identity Owner, and publication still uses the file CAS path. Those are not counted as migrated.

## Exact callsite and accounting

- Matrix ID: `V4-BCA-R2-928e5423aa7c5ec455a8` (`operational_daily_executor_v1.py`, baseline line 111, `execute_sources`). Code-path evidence is attached to this row. Its formal migration status remains OPEN pending opt-in deployment, live PG identity/publication readback, and the rest of the executor chain.
- Original baseline remains **266 P1 items**. Formal closed **0 / 266**; formally remaining **266**. Status totals remain OPEN 237, ingress-open 8, PG-code-pending-live-read 21; 22 reference edges remain unmapped.

## Verification

- **128 passed** in focused R21-R4 regressions covering publication and contract validation, Owner manifest binding, DM-01 progress/planning and executor PG Head behavior, market calendar, TDX path guards and BaoStock collection.
- `compileall` and `git diff --check` passed. Fakes demonstrate positive and fail-closed code paths; live PG and complete business acceptance were not run.
- No PG DDL/DML, contract import, publication write/CAS, acquisition, worker, service or production operation ran.

## Next stage

Move the daily executor's dated identity Owner read and final Head/CAS onto the same accepted PG publication/Owner transaction, then continue exact Owner and other-business callsites. Keep all formal counts unchanged until per-ID live reconciliation.
