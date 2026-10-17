---
stage_id: V4_R21_R4_DM01_BAOSTOCK_CACHE_CONSUMER_PATHS_R76_20261017
branch: codex/v4-workspace-cleanup
baseline_head: 5ed1accb2a9be4237b824843f4cd92df040c2b2e
status: DM01_BAOSTOCK_CACHE_CONSUMERS_USE_CENTRAL_PATH
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 50
open_callsite_rows: 208
ingress_adapters_open: 8
remaining_open_or_ingress: 216
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# DM-01 BaoStock cache consumer path configuration

Read the R74 BaoStock download-root stage and the formal R21-R4 execution card before this batch. The DM-01 lifecycle snapshot selector, daily source-freeze ingress, and daily increment capture readback now resolve BaoStock snapshots through the existing `baostock.cache_root` setting. The daily increment's live capture and subsequent file readback share the same resolved cache. A custom-root test exercises the lifecycle selector, and static consumer checks prevent these three current entrypoints from regressing to the repository's old fixed cache path.

Verification: **56 focused tests passed** across the configured DM-01 source-root checks, BaoStock PG capture adapter, special-phase PG input binding, and official daily source contracts. No live provider request, PG read/write, or full DM-01 business acceptance is claimed.

The execution card's 266 stable-ID baseline is unchanged: **0 formally complete; 266 remaining**. Code-level PG paths pending live reconciliation: 50; OPEN: 208; ingress adapters open: 8; remaining open or ingress: 216; unmapped reference edges: 22. No P1 ID is closed by this source-path batch.

Next: continue configuring all active TDX/BaoStock paths and move the remaining active Head/Authority/descriptor consumers to verified PG relations. The continuous-maintenance script still contains historical report and local Head reads; the repository policy correctly rejects committing that caller until its business-state authority is migrated. Live mapping of the canonical DM-01 Head remains `SOURCE_IDENTITY_PENDING` without a compliant PG catalog/read session.
