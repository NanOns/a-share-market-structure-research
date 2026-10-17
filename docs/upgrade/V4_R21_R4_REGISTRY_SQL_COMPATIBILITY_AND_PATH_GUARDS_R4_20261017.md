---
stage_id: V4_R21_R4_REGISTRY_SQL_COMPATIBILITY_AND_PATH_GUARDS_R4_20261017
baseline_sha: 2343c1bad65fb5ac80737aae4f94195421ef763c
branch: codex/v4-workspace-cleanup
status: SQL_AND_PATH_GUARD_CODE_COMPLETE_LIVE_PG_RECONCILIATION_OPEN
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
live_pg_catalog_or_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue exact daily accepted Head/source and Owner/other-business consumer migrations
---

# V4 R21-R4 registry SQL compatibility and path guards

Date: 2026-10-17 (Asia/Shanghai). This batch continues the Drive R21-R4 execution card and the R2/R3 implementation batches.

## Registry approval and SQL changes

- The publication reader now validates the Reader role and database identity before fetching contract bytes, while keeping Head, contracts, approval events, source bindings and Owner reads inside the same read-only repeatable-read transaction.
- Contract lookup is pinned to both opaque publication id and the final schema's `revision_no`. Approval state resolution orders by business `occurred_at`, database-assigned `recorded_at`, then event id to make same-time decisions deterministic.
- The draft migration now stamps registry `recorded_at` in a database trigger on insert, so a caller cannot backdate a version or approval event into an accepted publication's historical interval.
- Added `BEFORE TRUNCATE` guards for both append-only registry relations. UPDATE/DELETE guards remain in force. These remain unexecuted SQL proposals pending separately authorized migration and catalog checks.

## TDX/BaoStock configuration regression guard

- Added a repository-config test that clears path overrides, verifies TDX input, TDX snapshot output and BaoStock cache all resolve through `config/paths.yaml`, and confirms both output/cache paths are outside the read-only TDX source root.
- Test fixtures keep provider source and cache paths under G-backed pytest temporary directories.

## Batch accounting

Original P1 baseline: **266**. Formal completion remains **0 / 266**, with **266** formally remaining. Matrix counts remain OPEN 237, ingress adapters open 8, PG code paths pending live-PG/inventory reconciliation 21; unmapped reference edges remain 22. The PG calendar source callsite remains OPEN because runtime mode is still opt-in and no live publication mapping was read. This batch adds compatibility and regression guards without claiming an inventory item closed.

## Verification

- Consolidated focused offline selection: **108 passed** covering publication/contract/Owner, DM-01 PG progress, PG market calendar, TDX paths and BaoStock acquisition.
- `compileall`, staged repository policy, and `git diff --check` passed. Tests use PG-shaped fakes; live catalog/readback and complete business acceptance remain unavailable.
- No PG DDL/DML, contract import, Head switch, source acquisition, service start, or production deployment occurred.

## Next stage

Continue replacing active daily accepted-source/Head reads and migrate mapped Owner and other-business callsites against exact PG relation, namespace and publication bindings. Do not reduce formal remaining counts without live readback and per-callsite reconciliation.
