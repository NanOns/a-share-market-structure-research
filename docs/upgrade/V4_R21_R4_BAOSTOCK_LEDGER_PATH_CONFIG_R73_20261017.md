---
stage_id: V4_R21_R4_BAOSTOCK_LEDGER_PATH_CONFIG_R73_20261017
branch: codex/v4-workspace-cleanup
baseline_head: fca4eed3a2405b2fab596171ab08d3750c437a8a
status: BAOSTOCK_REQUEST_BUDGET_PATH_EXPLICITLY_CONFIGURED
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 50
open_callsite_rows: 208
ingress_adapters_open: 8
remaining_open_or_ingress: 216
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# BaoStock request ledger path configuration

The shared request-budget ledger resolver now follows the same explicit > environment > `config/paths.yaml` precedence as the TDX and BaoStock data roots. It no longer discovers `reports/v4_baostock/request_ledger.json` as an implicit legacy fallback. The project config explicitly points to the existing ledger, preserving its current path and contents; no file was moved, copied, or rewritten. If the path is not configured, acquisition fails with `BAOSTOCK_REQUEST_LEDGER_NOT_CONFIGURED` rather than silently starting a second budget ledger.

52 focused configured-path, TDX path, BaoStock request-budget, and BaoStock client tests passed, including absent configuration with a legacy file and preservation of the legacy bytes. The existing BaoStock capture adapter continues to call the central resolver. This changes path resolution only; it does not claim PG persistence of request-budget state or provider acceptance.

Original 266 accounting is unchanged: **0 formally complete; 266 remaining**. Implemented PG-only paths pending live reconciliation: 50; OPEN: 208; ingress adapters open: 8; remaining open or ingress: 216; unmapped reference edges: 22. No stable P1 callsite ID is closed by this path-only batch.

Next: reconcile the request ledger's long-term storage contract separately, continue PG stage consumption in the continuous-maintenance orchestrator, and resume exact mapped Owner/BFF migrations.
