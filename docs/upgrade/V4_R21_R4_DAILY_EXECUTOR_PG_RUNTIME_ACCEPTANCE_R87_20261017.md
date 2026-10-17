---
stage_id: V4_R21_R4_DAILY_EXECUTOR_PG_RUNTIME_ACCEPTANCE_R87_20261017
branch: codex/v4-workspace-cleanup
status: DAILY_RUNTIME_ACCEPTANCE_AND_SCHEMA_PG_ONLY_CODE_VERIFIED_LIVE_PG_PENDING
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 53
open_callsite_rows: 203
ingress_adapters_open: 10
remaining_open_or_ingress: 213
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# Daily runtime acceptance and SDK schema contract

The active executor no longer accepts `V4_BAOSTOCK_RUNTIME_ACCEPTANCE_SOURCE=FILE`; that mode fails closed. It reads the date-bound runtime acceptance bundle, smoke receipt and exact native response from the PG fact adapter. It also loads `BAOSTOCK_DM01_SDK_SCHEMA_ADAPTER_V2` version `2.0.0` through the approved contract registry instead of opening `config/baostock_dm01_sdk_schema_adapter_v2.json`.

The former `V4_DAILY_RUNTIME_ACCEPTANCE_PATH_R1` helper only selected a local report path for the removed file-authority flow. That helper is removed. Runtime materialization now uses the PG-derived ingress cache path; the old config file is retained, unmodified, and classified `RETIRED_WITH_PROOF` from this active executor call chain. No physical deletion occurred.

The exact original row `V4-BCA-R2-928e5423aa7c5ec455a8` now records the R83/R85/R87 active consumer chain. It remains code-level pending because approved contract registration, live DB identity, accepted publication/calendar T0 and business readback are not verified.

Verification: **27 passed** across the daily executor, date-bound PG acceptance bundle, calendar boundary and controlled executor call-chain tests. These fixtures do not prove live source capture or business acceptance.

Original accounting remains **0/266 formally complete; 266/266 remaining**. Code-level PG paths pending live reconciliation: **53**; OPEN: **203**; ingress-open: **10**; open or ingress: **213**; unmapped reference edges: **22**. No live PG read/write was attempted.

Next: continue the remaining BFF/Owner current Head and descriptor reads, and migrate the remaining 28 other-business plus 200 Owner consumers in stable-ID batches. Keep actual PG registration/readback blocked only at the missing runtime authorization boundary.
