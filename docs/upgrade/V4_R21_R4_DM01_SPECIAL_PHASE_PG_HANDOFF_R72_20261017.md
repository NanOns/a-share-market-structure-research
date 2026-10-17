---
stage_id: V4_R21_R4_DM01_SPECIAL_PHASE_PG_HANDOFF_R72_20261017
branch: codex/v4-workspace-cleanup
baseline_head: 7e154109d5f4f87a4063b3a9f757b6f6042ee674
status: SPECIAL_PHASE_AND_SOURCE_FREEZE_PG_STAGE_READS_CODE_LIVE_RECONCILIATION_BLOCKED
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 50
open_callsite_rows: 208
ingress_adapters_open: 8
remaining_open_or_ingress: 216
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# DM-01 special-phase and source-freeze handoffs

The special-phase producer requires exact, date-bound PG descriptors for the lifecycle snapshot and the accepted V4-02 ingress. It reads both facts through `read_stage`, and appends the complete special-phase manifest (or wait result) as an immutable PG stage fact. The shared manifest builder records the V4-02 and lifecycle PG locators and source digests, without opening the reports that were used by the previous runtime path.

The source-freeze producer now reads the exact GBBQ probe, lifecycle, and special-phase PG stage bindings. It validates the GBBQ snapshot and source bytes, builds the complete freeze payload, and appends it under `daily_source_freeze`. The main daily increment reads the exact returned freeze binding. The report copy may still be emitted for legacy diagnostics, but this migrated caller no longer uses it as business state. The separate continuous-maintenance orchestrator has not yet been switched to the PG binding.

The V4-02 PG ingress descriptor has no live accepted source binding in this workspace yet. The daily path requires `--v402-pg-stage-state`; absence leaves the special-phase input unavailable and blocks promotion. No filesystem fallback is retained for that runtime consumer. The explicit PG append path requires `V4_NATIVE_PG_DSN`; the reader requires the existing read DSN. No live PG operation was attempted.

Verification: **55 selected tests passed** across DM-01 stage consumers, special-phase PG input binding, BaoStock capture adapter, and official daily source manifest contracts. These are offline and controlled-boundary tests; no live PG or DM-01 business acceptance is claimed.

Original 266 accounting is unchanged: **0 formally complete; 266 remaining**. Implemented PG-only paths pending live reconciliation: 50; OPEN: 208; ingress adapters open: 8; remaining open or ingress: 216; unmapped reference edges: 22. Within the stable baseline, Owner is 46 code-level pending, 147 OPEN, 7 ingress; other business is 4 code-level pending, 23 OPEN, 1 ingress.

Next: provide a versioned accepted V4-02 PG ingress mapping, migrate the separate continuous-maintenance reader and remaining DM-01 lifecycle/source inputs, then continue exact mapped Owner/BFF consumers. Reconcile every 266-row count against stable IDs and live PG before marking a callsite formally complete.
