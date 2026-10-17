---
stage_id: V4_R21_R4_BAOSTOCK_DOWNLOAD_PATH_CONFIG_R74_20261017
branch: codex/v4-workspace-cleanup
baseline_head: da9f06e25f79334edc2a160ef876fe780822b905
status: BAOSTOCK_RUNTIME_NATIVE_RESPONSE_PATH_CONFIGURED
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 50
open_callsite_rows: 208
ingress_adapters_open: 8
remaining_open_or_ingress: 216
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# BaoStock runtime response path configuration

Read the current R73 BaoStock path stage before this change. The runtime acceptance entrypoint now resolves native response output through `baostock.download_root` using the shared explicit argument > environment > `config/paths.yaml` path resolver. The project config points this root beneath `data/v4/source_snapshots/baostock_downloads`; the PG ingress contract requires this response path to stay inside the project root. The live smoke receipt and accepted manifest remain at their existing report paths. No provider request or PG write was performed.

Verification: **19 focused tests passed** across configured TDX/BaoStock paths and BaoStock runtime acceptance PG contracts. These are offline tests and do not establish live source acceptance or full DM-01 business acceptance.

Original 266 stable-ID accounting is unchanged: **0 formally complete; 266 remaining**. Code-level PG paths pending live reconciliation: 50; OPEN: 208; ingress adapters open: 8; remaining open or ingress: 216; unmapped reference edges: 22. Owner remains 46 code-level, 147 OPEN, 7 ingress-open; other business remains 4 code-level, 23 OPEN, 1 ingress-open. This path-only batch closes no P1 row.

Next: continue moving the continuous-maintenance DM-01 caller to exact PG stage facts, test its failure and identity paths, and migrate further mapped business consumers. Do not count a row formally complete without stable-ID reconciliation and live PG evidence.
