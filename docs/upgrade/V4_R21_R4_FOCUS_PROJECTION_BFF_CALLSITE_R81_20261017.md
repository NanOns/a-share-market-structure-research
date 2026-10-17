---
stage_id: V4_R21_R4_FOCUS_PROJECTION_BFF_CALLSITE_R81_20261017
branch: codex/v4-workspace-cleanup
status: FOCUS_PROJECTION_BFF_PG_READ_PATH_CONFIRMED_LIVE_HEAD_RECONCILIATION_PENDING
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 53
open_callsite_rows: 203
ingress_adapters_open: 10
remaining_open_or_ingress: 213
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# Focus projection BFF callsite reconciliation

The exact baseline callsite `V4-BCA-R2-f0873417056c47ed4f1e` maps to the current `v4_focus_projection_pg_closeout.read` and its Core Product BFF caller. `CoreProductBFFR1.focus_projection` requires the Head-bound PG product catalogue, validates the Focus manifest date/contract/head scope and ingress source binding, then calls the PG reader using that date and the bound Head token. The reader validates the embedded PostgreSQL descriptor and fact context, rehashes the full projection payload and rejects mismatched Head tokens. Missing catalogue/descriptor and changed payload fail closed without a business-file fallback.

Two focused consumer tests passed: BFF reads the Head-bound catalogue and PostgreSQL fact without config fallback; legacy Focus projection preparation upgrades into the typed Owner fact. Tests use controlled PG-shaped fixtures and do not establish live Head identity or business acceptance.

## Original 266-item accounting

This verifies one existing code path against one original stable ID; it closes no formal P1 item. Counts are now **53** code-level PG paths pending live reconciliation, **203 OPEN**, **10 ingress-open**, **213 open or ingress**, and **22 unmapped reference edges**. Owner: **49** code paths, **142 OPEN**, **9 ingress-open**. Other-business: **4**, **23**, **1**. Formal completion remains **0/266** and formal remaining remains **266/266**.

Live database identity, accepted Head, exact namespace/publication, T0 and source digest were not available for reconciliation. No live PG read/write, Head CAS or business acceptance occurred.
