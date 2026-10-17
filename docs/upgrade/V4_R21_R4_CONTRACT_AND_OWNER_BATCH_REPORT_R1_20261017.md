---
stage_id: V4_R21_R4_CONTRACT_AND_OWNER_BATCH_20261017_R1
baseline_sha: 49478ecd6fc0a0da2d3aca259ece0ce27bad4297
branch: codex/v4-workspace-cleanup
status: R21_R4_CODE_PARTIAL_CONTRACT_AND_OWNER_AUTHORITY
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_remaining_formal: 266
code_paths_pending_live_pg_or_inventory_reconciliation: 21
ingress_adapters_open: 8
unmapped_reference_edges: 22
live_pg_catalog_or_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
pg_ddl_dml_contract_import_head_switch_production_deploy: NOT_AUTHORIZED_AND_NOT_RUN
next_stage: wire the corrected contract registry into active contract and Head/Publication consumers; continue other-business callsites, daily contracts, descriptor and DM-01 paths
---

# V4 R21-R4 contract and Owner batch

Date: 2026-10-17 (Asia/Shanghai). The active execution contract is the user-provided Drive task card `V4_R21_R3外审后_R21_R4合同PG消费者批量迁移与日更接线持续执行卡_R1_20261017.md`. Applicable repository guidance reviewed before implementation: `V4_R18_INCREMENTAL_PERFORMANCE_RECOVERY_MATRIX_R1_20261016.md`, `V4_R20_BUSINESS_CODE_FILE_ACCESS_AUDIT_R1_20261017.md`, the R21-R3 progress and comprehensive reports, and the Drive R3 independent audit.

## Code batch delivered

- Reworked the unexecuted registry SQL draft. Contract bytes remain append-only; approval and revocation now use separate append-only events with actor, authorization reference, source revision, digest, occurrence time, and recording time. A publication binding only resolves to the latest approval event whose occurrence and recording timestamps are no later than acceptance.
- Changed `publications.contract_bindings` to a nullable staged column without an empty-object default. A `NOT VALID` constraint and a trigger that fires on every insert/update preserve historical accepted rows during reconciliation while validating new acceptance, binding, namespace, and acceptance-time changes. The proposed stage-two validation remains commented and requires row-by-row historical mapping.
- Hardened the contract byte reader to inspect the live transaction settings and require read-only `REPEATABLE READ`; returned contract evidence now carries its publication id, trade date, accepted timestamp, and database/user identity. Raw bytes are still independently SHA-256 checked; XML DTD/entity declarations remain rejected.
- Migrated the active `v4_operational_owner_authority_v2.load` path away from opening `AUTHORITY.json`. Owner authority manifests are now appended to the existing workspace `forward_facts` Owner relation and read by their inline PG descriptor; digest and database identity are checked, with no file-value fallback. Native read connections now establish read-only repeatable-read transactions.
- Updated the R21 callsite matrix evidence for `V4-BCA-R2-5fc637717724bb649d31`. This is code-path evidence only: it is not marked formally closed because the live database and full inventory reconciliation remain unavailable.
- Fixed the test isolation guard to accept the current `tdx.source_root` key as well as the legacy `tdx.root` form. The resolved TDX path remains protected as a read-only root.

## Counts and acceptance boundary

The R21 baseline remains 266 P1 business reads: 200 Owner, 28 other-business, and 38 external market-source reads. **Formally completed: 0; formally remaining: 266.** The existing matrix still records 21 code paths pending live-PG/inventory reconciliation, 8 ingress adapters open, and 237 untouched callsites; this batch strengthened one of the 21 paths but does not change the formal count. The 22 exact-reference edges remain unmapped.

The registry reader has not yet been wired into the active runtime contract/Head consumers. The 28 other-business paths, broad Owner domains, daily acceptance contracts, Head/Publication flow, BFF coverage, DM-01 orchestrators, and TDX/BaoStock ingress audit remain open. No live catalog query or PG read occurred because neither `WORKBENCH_PG_DSN` nor `V4_NATIVE_PG_READER_DSN` is configured. No DDL/DML, contract import, accepted Head change, real acquisition, scheduler, service, or production operation was performed.

## Verification

- Focused offline tests: **11 passed** (`test_v4_contract_registry_pg_v1.py`, `test_v4_r21_owner_manifest_pg_binding.py`), using `--confcutdir=tests` because the repository-wide legacy isolation plugin currently cannot initialize under the installed Python 3.13 environment (`psycopg` has no compatible PQ wrapper; the runtime package set also lacks `cryptography`). These are mocked PG-shaped positive and negative tests, not live-PG acceptance.
- `compileall` passed for modified Python files; `git diff --check` passed.
- The broader daily-executor/Owner selection did not collect: it is blocked by the incompatible local dependency environment, not reported as passing.
- GitHub CI and PR checks are pending the authorized commit/push of this batch.

## Next stage

Continue wiring the corrected registry into actual active contract and Head/Publication consumers, then migrate the other-business cohort and additional Owner domains with exact callsite evidence. Complete the real daily contract path, DM-01 PG status path, and TDX/BaoStock entrypoint coverage. Keep 266 as the formal open count until verified per-callsite migration and authorized live readback establish closure.
