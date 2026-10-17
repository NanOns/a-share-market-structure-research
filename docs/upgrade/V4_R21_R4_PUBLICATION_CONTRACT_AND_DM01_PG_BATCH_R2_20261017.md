---
stage_id: V4_R21_R4_PUBLICATION_CONTRACT_AND_DM01_PG_BATCH_R2_20261017
baseline_sha: 7ec58205b819cf524af4a692c0536c6e25aebeaa
branch: codex/v4-workspace-cleanup
status: CODE_BATCH_COMPLETE_LIVE_PG_AND_INVENTORY_RECONCILIATION_OPEN
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
live_pg_catalog_or_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
pg_ddl_dml_contract_import_head_switch_production_deploy: NOT_AUTHORIZED_AND_NOT_RUN
next_stage: continue exact daily source and Head migration plus Owner and other-business callsite batches
---

# V4 R21-R4 publication contract and DM-01 PG status batch

Date: 2026-10-17 (Asia/Shanghai). This is a continuation of the Drive execution card `V4_R21_R3外审后_R21_R4合同PG消费者批量迁移与日更接线持续执行卡_R1_20261017.md` and the previous R4 batch. Applicable R18/R20/R21 upgrade documents and the R3 independent audit were reviewed earlier in this execution.

## Implemented code

- Connected `PgPublicationReader` to `load_publication_contracts`. The publication's Head, contract binding, contract bytes and latest approval/revocation events, consumed sources, module descriptors and Owner readbacks are resolved in one read-only repeatable-read transaction. Missing or empty contract bindings fail closed. Exact publication revision is included in the contract lookup.
- Returned the verified contract version, digest, namespace, T0, acceptance time and approval identity in the publication context, so the BFF context token pins that evidence with Head and Owner descriptors.
- Extended the PG reader-role capability check to include contract registry and approval-event write privileges.
- Changed `DailyJobs.progress` to derive the latest published trade date from PG `update_job_days` receipts whose state is `PUBLISHED`; it no longer reopens the file Operational Head for this status field. This is PG orchestrator status code, not proof that the broader DM-01 accepted Head and source artifacts have moved to PG.
- Fixed acquisition test fixtures to configure isolated TDX source and BaoStock cache roots. The production `config/paths.yaml` remains the source of configured path defaults; tests do not access or write under the read-only TDX source root.

## Batch accounting

The original baseline remains **266 P1 items**: 200 Owner reads, 28 other-business reads and 38 market-source reads. **Formally completed: 0 / 266; formally remaining: 266.** Existing matrix implementation statuses remain 21 PG code paths pending live-PG/inventory reconciliation, 8 ingress adapters open and 237 open. This batch advances the connected publication contract consumer and the DM-01 PG progress consumer; it does not close a baseline item because there is no compliant PG read DSN or accepted per-ID live readback. The 22 unmapped reference edges remain open.

## Verification

- **86 passed**: focused publication candidate, contract registry, Owner manifest, native reader DSN and DM-01 PG progress tests.
- **15 passed**: TDX configured-path, BaoStock client, and TDX/BaoStock acquisition path tests.
- The broader `test_dynamic_daily_r21_repair.py` selection requires `V4_NATIVE_PG_DSN` and failed during setup because no writer DSN is configured. No DSN value was logged, and no PG write was attempted.
- These unit tests use PG-shaped fakes and do not establish full business acceptance or live database compatibility. Live catalog/readback was unavailable. No PG DDL/DML, contract import, Head switch, service start, or production deployment occurred.
- Focused `compileall` and `git diff --check` passed.

## Next stage

Continue replacing the real daily accepted-source/Head reads and DM-01 orchestration inputs with exact, typed PG publication/Owner bindings; then migrate mapped Owner and other-business callsites in batches. Preserve the 266 formal remaining count until exact callsite evidence, live PG readback and required business acceptance pass. The 28 other-business and 200 Owner cohorts have not been represented as complete by this batch.
