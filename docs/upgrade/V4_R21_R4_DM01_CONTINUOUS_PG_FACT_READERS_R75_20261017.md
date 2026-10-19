---
stage_id: V4_R21_R4_DM01_CONTINUOUS_PG_FACT_READERS_R75_20261017
branch: codex/v4-workspace-cleanup
baseline_head: 5ed1accb2a9be4237b824843f4cd92df040c2b2e
status: CONTINUOUS_MAINTENANCE_PG_FACT_AND_CONFIGURED_SOURCE_READS
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 50
open_callsite_rows: 208
ingress_adapters_open: 8
remaining_open_or_ingress: 216
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# DM-01 continuous-maintenance PG facts and configured source reads

Read the current R74 BaoStock path stage and R72 DM-01 PG handoff stage before this batch. The continuous-maintenance caller now reads its GBBQ probe, lifecycle snapshot, special-phase manifest, source freeze, and BaoStock runtime acceptance from exact date-bound PG facts. Source-freeze diagnostic evidence is derived from the PG payload digest and no longer reopens the report copy. PG lookup selects at most two records and fails closed unless the date/stage fact is unique, its database identity matches, and both the stored record and payload digests validate.

The same caller now discovers official TDX capture files through `tdx.snapshot_root` and BaoStock snapshots through `baostock.cache_root`. The BaoStock runtime-smoke writer resolves the TDX read-only root from central configuration before writing its receipts. The TDX and BaoStock read paths were exercised using custom temporary roots distinct from the repository defaults.

Verification: **71 focused tests passed** across configured source paths, continuous-maintenance stage reads, DM-01 special-phase bindings, BaoStock capture contracts, and official daily source manifests. One initial test invocation stopped in the repository isolation plugin before test collection because its disposable root was not registered; rerunning with the registered `G:/codex_tmp/test_temp` root passed. No live PG read/write or DM-01 business acceptance is claimed. The V4-02 accepted PG ingress binding and exact live Head mapping remain unresolved.

Original 266 stable-ID accounting is unchanged: **0 formally complete; 266 remaining**. Code-level PG paths pending live reconciliation: 50; OPEN: 208; ingress adapters open: 8; remaining open or ingress: 216; unmapped reference edges: 22. Owner remains 46 code-level, 147 OPEN, 7 ingress-open; other business remains 4 code-level, 23 OPEN, 1 ingress-open. These caller improvements close no P1 row without stable-ID reconciliation and live evidence.

Next: migrate the remaining DM-01 runtime state and source consumers away from filesystem authority; then continue exact mapped other-business and Owner/BFF consumers. Reconcile the 266 stable IDs per batch and do not substitute controlled-boundary tests for live business acceptance.
