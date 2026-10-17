---
stage_id: V4_R21_R4_DM01_NEXT_SESSION_CAPTURE_PATHS_R77_20261017
branch: codex/v4-workspace-cleanup
baseline_head: 477e2b1046897f7badadda297d56859f9ba25b6b
status: NEXT_SESSION_TDX_AND_BAOSTOCK_CAPTURE_ROOTS_CONFIGURED
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 50
open_callsite_rows: 208
ingress_adapters_open: 8
remaining_open_or_ingress: 216
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# DM-01 next-session TDX and BaoStock capture paths

Read the current R76 source-path stage and the formal R21-R4 execution card before this batch. The active next-session source probe now resolves official TDX daily-package receipts under the configured `tdx.snapshot_root` and BaoStock daily snapshots under `baostock.cache_root`. The source roots still come from the existing central path resolver; no additional resolver or disk fallback was added.

Verification: **6 focused tests passed** across the custom TDX/BaoStock path roots, BaoStock capture adapter, and DM-01 special-phase PG input binding. These are controlled path and boundary tests; no live source acquisition, PG read/write, or full DM-01 acceptance is claimed.

The original 266 stable-ID accounting is unchanged: **0 formally complete; 266 remaining**. Code-level PG paths pending live reconciliation: 50; OPEN: 208; ingress adapters open: 8; remaining open or ingress: 216; unmapped reference edges: 22. This entrypoint path batch closes no P1 ID.

Next: continue auditing active TDX snapshot/delta and BaoStock runtime-acceptance paths, then migrate remaining Head/Authority/descriptor callers. The DM-01 continuous-maintenance orchestration change remains blocked from commit until the report and file-based Head authorities it reads are replaced with correctly mapped PG state; do not bypass repository policy.
