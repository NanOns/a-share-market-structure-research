---
stage_id: R21-R4-baostock-runtime-acceptance-pg-r64
branch: codex/v4-workspace-cleanup
status: DATE_BOUND_BAOSTOCK_RUNTIME_ACCEPTANCE_PG_READER_AND_INGRESS_ADAPTER_CODED
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 48
open_callsite_rows: 210
ingress_adapters_open: 8
remaining_open_or_ingress: 218
unmapped_reference_edges: 22
---

# BaoStock runtime acceptance PG path (R64)

Date: 2026-10-17 (Asia/Shanghai).

## Implemented

`src/workbench_db/v4_baostock_runtime_acceptance_pg_r1.py` adds a date-keyed append-only record for the BaoStock DailyUpdates V1 acceptance manifest and exact live-smoke receipt. The capture entrypoint defaults to this PG fact, reads under repeatable-read/read-only isolation, checks configured database identity and payload/manifest/receipt bindings, then checks target date, SDK fingerprint, auth mode and method contract. The local manifest path is retained only behind explicit `V4_BAOSTOCK_RUNTIME_ACCEPTANCE_SOURCE=FILE`.

The acceptance producer validates the current local ingress manifest/receipt and appends through `ForwardFactStore`, which requires explicit `V4_NATIVE_PG_DSN`. No actual write was attempted. The PG record can carry and validate the V2 zero-change proof plus exact per-code empty responses. The active operational daily executor is not yet switched to this PG fact and still follows its separate local runtime manifest/native response and source-freeze paths; those consumer rows remain open.

## Verification and limits

- Focused regression: **9 passed** across date-bound PG-shaped read, database identity and digest rejection, V1 capture default wiring, V2 zero-change evidence validation, contract registry, and operational executor behavior. The repository workflow's complete selected V4 PG/consumer suite also passed: **306 passed**.
- Current business file-access audit and validator: **PASS** (1,430 call sites scanned; 176 Owner-file reads and 238 P1 findings remain inventoried). The audit output is retained outside Git at `G:\codex_tmp\R64_business_file_access.json`.
- The PG boundary tests use controlled fakes. No live catalog/read/write, BaoStock network acquisition, runtime smoke, source-ingest promotion, Head CAS, or end-to-end business acceptance was run.
- Push and PR CI results for the preceding R63 commit are green: [push 39023921836](https://github.com/NanOns/a-share-market-structure-research/actions/runs/39023921836), [PR 39023924531](https://github.com/NanOns/a-share-market-structure-research/actions/runs/39023924531). R64 CI will be recorded after its push.

## Original 266-item accounting

This R64 subpath has no independently matched baseline callsite ID, so formal completion remains **0/266** and formal remaining **266/266**. The crosswalk remains **48** code-level PG reads pending live reconciliation, **210 OPEN**, **8 ingress adapters open**, **218 open or ingress**, and **22 unmapped reference edges**. No original row is closed by the controlled-reader test evidence.

## Next

Wire the operational executor to the date-bound PG runtime fact and migrate its source-freeze/native response/accepted Head chain; reconcile the V2 embedded proof against the accepted PG source-fact contract. Keep all per-row formal counts open until exact source/row reconciliation and live approved PG readback.
