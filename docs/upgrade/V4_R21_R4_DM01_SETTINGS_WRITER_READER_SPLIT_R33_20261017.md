---
stage_id: V4_R21_R4_DM01_SETTINGS_WRITER_READER_SPLIT_R33_20261017
branch: codex/v4-workspace-cleanup
status: HTTP_SETTINGS_MUTATION_AND_READBACK_SPLIT; LIVE_PG_NOT_RUN
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 21
ingress_adapters_open: 8
other_callsite_rows_open: 237
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue daily Head/Authority/descriptor and Owner/BFF actual call chains
---

# V4 R21-R4 DM-01 settings Writer/Reader split

Date: 2026-10-17 (Asia/Shanghai). This batch closes a remaining edge in R30's daily HTTP status route wiring.

## Implemented

- Added `DailyJobs.set_settings(enabled)` as a mutation-only operation through the Writer connection.
- `settings()` delegates its optional update to `set_settings`, then reads the persisted value through the Reader connection.
- The HTTP settings PUT calls `set_settings` and obtains its response from the separate `DailyJobsReadOnly` client.
- `DailyJobsReadOnly` rejects `set_settings` along with other mutations.

## Verification and limits

- Daily HTTP route and DM-01 state tests: **13 passed**, including a handler-level check that PUT performs one Writer mutation then one Reader readback and never invokes the Writer object's settings read.
- Python compilation and `git diff --check` passed.
- No live PG session, scheduler mutation, service startup or accepted business readback occurred.

## Accounting

Original P1 baseline **266**. Formally complete **0 / 266**; formally remaining **266**. Code-level PG read paths remain **21** pending inventory reconciliation and live readback; **8** ingress adapters remain open; **237** other callsite rows remain open. **22** reference edges remain unmapped. This is a DM-01 service wiring correction, not a reconciled baseline row.

## Next stage

Continue operational Head, Authority, descriptor, daily and BFF call chains. Keep formal counts unchanged until approved PG readback and per-ID inventory reconciliation.
