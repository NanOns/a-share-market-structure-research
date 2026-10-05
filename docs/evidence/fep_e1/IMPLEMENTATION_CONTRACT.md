# FEP E1 implementation and readback contract V1

Authority: V4_15E1_FEP_DATASET_AND_POSTGRESQL_FOUNDATION_IMPLEMENTATION_TASK_R1_20261005.md, copied to reports/fep_e1/TASK_AUTHORITY.md. Baseline: ce44488ae972cf0f4d9f4af34cb03d81be436387. The task authorizes implementation and states external design acceptance; the separately named external acceptance original was not located. Frozen R2 module/schema bytes are preserved alongside this document. Older pending-review headers retain their historical meaning.

## Implementation surfaces

| Design planned surface | Actual surface |
|---|---|
| src/v4/expectancy/observation.py | src/workbench_analysis/fep_e1/observation.py |
| snapshots.py | src/workbench_analysis/fep_e1/snapshots.py |
| labels.py | src/workbench_analysis/fep_e1/labels.py |
| datasets.py | src/workbench_analysis/fep_e1/datasets.py |
| contracts.py / db.py | src/workbench_analysis/fep_e1/contracts.py / db.py |
| Dataset transaction writer | src/workbench_analysis/fep_e1/repository.py |
| PostgreSQL migration | src/workbench_db/migrations/v4_postgres/028..031_fep_*.sql |
| Registries/policy | config/fep_*_v1.json |
| Real database tests | tests/fep/ |
| Acceptance runner | scripts/run_fep_e1_acceptance.py |

All 33 R2 table/domain/primary/composite-key declarations are installed. Migration 029 installs 32 explicit guards. Migration 030 implements R2 reference validation/CAS plus E1 observation, snapshot, feature, exact-source and denominator validators. CAS serializes both request identity and head key before readback, so concurrent identical replays return the original receipt. Model-set remains head payload. Migration 031 seals NOLOGIN roles, a dedicated CAS owner, fixed search_path, revoked PUBLIC execution and restricted application writes. Model/priority tables receive no application writer grant.

`db.apply(..., bootstrap=False)` applies only FEP migrations to an already installed V4 schema. `bootstrap=True` is for isolated engineering fixtures. It retains known legacy migration versions; 014..027 lacking registration in the historical service receive explicit fixture-only ledger names. The frozen historical service is not edited. Migration identity mismatches raise and roll back.

## Capability limits

Database relations, constraints, roles, concurrency and transactional dataset persistence are engineering implementations. No live Core call path imports FEP or waits for FEP acceptance. No actual model, real deployment grant, inference, calibration or Priority V2 output is produced.

The feature registry verifies 47 accepted V4-03 producer registry entries but marks their current ENTRY field mapping NOT_IMPLEMENTED until exact publication value paths, quality and UTC availability are proven. The accepted 2026-09-24 profile sample has primitive quality metadata, with no direct primitive value collection; it cannot be silently reused as a 2026-09-30 ENTRY snapshot. Slot deadline remains UNSET. `FEP_E1_DATASET_COMPLETE=false`.

Five existing real V4-15 pending outcomes are exact-read back by registered file reference, outcome key, evaluation revision and source digest. They lack the three independent authority timestamps required by E1. The adapter never computes forward prices, benchmarks or path metrics. It returns a nontrainable result for those rows. A caller-supplied maturity/time dictionary cannot enable real training. Reopening this capability requires separately accepted owner interface repair. Synthetic mature examples are explicitly ENGINEERING_FIXTURE and stay inside disposable PostgreSQL databases.

Dataset assembly preserves the full expected denominator, partition cutoffs, selected revision/digest, pending/missing reasons and date weights; its digest includes all four components. Dataset persistence writes all components in one FEP-only transaction. DB deferred triggers check manifest/ledger completeness; row composite FKs and advisory-locked fold guards reject object mixing. This is engineered scope completeness; real observation cohort admission remains blocked pending formal event/slot/feature authority.

The additive FEP namespace contract enumerates all 33 tables. It does not amend the frozen V4-18 namespace matrix. Its current global-inventory regression failure remains an open cross-cutting blocker and is not deselected.

## Reproduce actual database evidence

Use installed PostgreSQL 18.6 binaries from E:/Postgres/bin. Initialize two new empty clusters on E:/codex_tmp/fep_e1_* (or the allowed F: equivalent), UTF8, locale C, engineering-only fep_e1_admin, loopback host. Fresh and Upgrade require separate clusters because historical migration 024 creates a cluster role; the original SQL is neither patched nor skipped. No existing database is reset by the runner.

Start each with `pg_ctl -D <isolated-directory> -l <E-or-F-log> -o "-p <unused-port> -h 127.0.0.1 -c timezone=UTC -c max_connections=16 -c shared_buffers=128MB" -w start`. Configure inherited PYTHONPATH with the repository root and src. Set FEP_E1_ADMIN_DSN and FEP_E1_UPGRADE_ADMIN_DSN explicitly to the corresponding loopback instances, user fep_e1_admin, dbname postgres. Run `python -B -m scripts.run_fep_e1_acceptance`. The runner refuses nonengineering users, nonloopback addresses and data directories outside the prescribed roots. No production .env credentials are read.

Fresh: empty database -> unmodified migrations 001..027 -> FEP -> checksum replay -> tests. Upgrade: separately commit 001..027 -> clone pre-FEP core template -> FEP -> replay -> tests. Each cluster also retains a template for isolated CAS sessions. The upgrade template supports applying all four FEP migrations, injecting invalid DDL and proving that schema and ledger completely roll back. Local fixture databases/failed states are retained and servers are stopped after delivery.

Final evidence records actual version, locale, timezone, directories, ports, ledger checksums, schema before/after, constraints, trigger definitions, grants, function owners/proconfig, transaction IDs, SQL exceptions, concurrent session results and row counts. JSON and raw logs are stored atomically and preserve their bytes in Git via directory-local attributes.

## Acceptance and stop

The local result is BLOCKED, despite passing isolated database tests. Real feature/observation lineage, label-time authority and the V4-18 inventory integration require owner repair disposition. Regression distinguishes the previous 43 debts, nine failures independently reproduced in newly added baseline scopes, and one true introduced namespace failure. All remain visible.

No FEP_E1_ACCEPTED_HEAD or V4_16_ACCEPTED_HEAD is created. Production, Shadow, Focus, MODEL_DISPLAY and PRIORITY_USE remain ungranted. Next: STOP_WAIT_EXTERNAL_REPAIR_DISPOSITION. Commit/push delivers implementation and evidence, not external acceptance or authorization for E2.
