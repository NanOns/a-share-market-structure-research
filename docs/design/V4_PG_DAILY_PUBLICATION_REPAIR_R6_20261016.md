# V4 PG 日发布 R6：发布资格与迁移前边界

- Contract: `V4-PG-DAILY-PUBLICATION-EXTERNAL-REPAIR-20261016/R6`
- Baseline: `2a51b12e096df3213a3fdcac0295bf5f7870524a`
- Scope: completeness judgment, typed Core readback binding, migration-runner compatibility, Owner/Workspace and seven-page consumer status.
- Boundary: repository code, tests and read-only PostgreSQL catalog/data checks only. No PG DDL/DML, isolated database, accepted Head update, server start, 28765 deployment, or physical cleanup.

## Versioned daily completeness rule

`V4_DAILY_COMPLETENESS_R1/1.0.0` is implemented in `src/workbench_db/v4_daily_core_result_r6.py`. It requires the actual Core row count to equal the positive `record_count` values for its exact TDX artifact bindings, zero missing close values, unique security IDs, complete OHLC for every `TRADING` row, and a source revision binding for every Core row. The artifact count must match both immutable PG `source_package_facts.record_count` and the same fact in the accepted package manifest. Migration `039_tdx_package_row_count_authority_r1.sql` enforces that equality on newly inserted TDX facts while leaving legacy facts unmodified. An unsupported or caller-modified rule is rejected. The plan computes the result from actual normalized producer rows; PG readback recomputes it from typed rows and independently proven source bindings, then requires equality with the stored status. A stored `PASS` alone cannot create verified status.

`read_daily_core_result()` returns publishable typed evidence only after all row hashes, aggregate hash, producer receipt, exact consumed-source manifest, accepted package facts, T0/effective windows, and package/source time cutoffs pass in the caller's repeatable-read, read-only transaction. `build_publication_candidate(..., verified_core_result=...)` binds that evidence and computes the publishable candidate state. The Head planner verifies the candidate digest and the same typed proof. Without the proof, metadata candidates remain blocked.

The contract measures completeness within the actual producer rowset; it does not claim that a producer supplied the full exchange/security universe. That universe denominator and a live canonical producer-to-PG feed are still external prerequisites and remain publication blockers.

## Migration runner and live schema compatibility

The runner previously globbed every migration file while registering only a subset, so unrelated SQL files stopped it at `UNREGISTERED_V4_MIGRATION`. It now iterates an explicit, hash-checked list and includes the source-manifest prerequisite plus `034`–`039` in dependency order. The R7 schema-compatibility and static migration tests pass. This verifies repository mapping only; it does not parse or apply DDL against a PostgreSQL server.

Read-only check at `market_research@127.0.0.1:5432` found 12 migration-ledger rows. The live `publications` table lacks `source_manifest_contract_id`; `source_revisions` lacks the new package provenance columns; `source_package_facts`, Core snapshots/rows, `publication_module_results`, and `sector_membership_facts` are absent. `publications` and `publication_heads` contain zero rows; `source_packages` exists and is empty. The connection role is `postgres` with superuser/role/database/replication/bypass-RLS privileges, so it is rejected by the Reader contract. No write was attempted. The live catalog therefore does not establish that the registered migration chain is safe to execute; the existing database has schema/ledger drift requiring an approved preflight and reconciliation plan.

## Existing Owner, Workspace and page consumers

The candidate adapter has opt-in routes for all seven current pages and reads one selected publication identity. Default `CurrentAcceptedV4Reader` behavior remains in place. Synthetic candidate HTTP and adapter tests verify identity selection and fail-closed behavior, not live page parity.

| Page | Verified candidate source path | Still unavailable |
|---|---|---|
| Summary | publication-scoped event rows; optional operational-risk Owner | replay, identity names, live accepted publication |
| Entity | publication-consumed source revision lifecycle facts; Core rows when bound | current live Core rows and identity-name relation |
| Radar | optional `research_priority` Owner | formal radar ledger, replay, names |
| Sector | optional `sector_lifecycle` supplement; membership facts only when publication-bound | live membership binding and PIT evidence |
| Cohort | explicit pending response | publication-bound cohort relation |
| Settlement | explicit pending response | publication-bound outcome/receipt relation |
| Health | operational-risk and sector-lifecycle supplements | replay/maturity completeness and live bindings |

The existing three Owner families remain optional capability supplements. The root-derived Workspace identity/capability check is implemented, but authoritative mapping from prior database namespace roots to the current workspace is absent. No Owner/Workspace evidence in this pass turns missing sources into accepted data.

## PG migration authorization plan (prepared, not approval to execute)

Before any migration execution, a separate authorization must identify the exact target and impact. Required preflight package:

1. Freeze the selected DB identity, role, current migration ledger checksums, relevant relation/constraint/index/function/trigger inventory, and row counts under a read-only repeatable-read transaction. Reconcile all ledger/catalog drift before choosing migrations; abort on checksum conflicts, duplicate objects, or unknown prior DDL.
2. Name the exact ordered migration set and hashes. Confirm prerequisites `010_source_manifest_contract_r1` then `034`–`039`, plus any required base migrations, against the target catalog. Do not infer applied state from filename or ledger alone.
3. Provide a verified backup/snapshot identifier, restore test, expected lock duration, table/constraint/trigger impact, rollback or forward-repair plan, and post-migration assertions. The append-only/source-authority changes may require forward repair rather than destructive rollback.
4. Use a separately configured least-privilege migration role and explicit `V4_NATIVE_PG_DSN`; do not reuse the current superuser Reader connection. State whether the target is a specifically approved isolated PG or production DB. No new database/port is presumed.
5. For an isolated PG, record source snapshot, G-drive data directory, port, startup/shutdown owner and cleanup authorization. For production, record maintenance window and independent restore/rollback acceptance.
6. Run the exact SQL once, capture migration ledger/catalog and immutability/trigger readback, then stop. This authorization cannot include accepted Head movement, production service deployment, or data cleanup unless separately listed.

Current execution readiness: `BLOCKED_PREFLIGHT_RECONCILIATION_AND_LEAST_PRIVILEGE_ROLE`. This plan does not authorize database writes.

## Acceptance and next stage

- Code: positive candidate-to-Head-plan path and paired fail-closed paths pass with deterministic PG-shaped fixtures; this is not a live PG publication.
- Focused suite: 94 passed before the migration-runner fix; final CI-scoped repository suite: 154 passed after Core, source-manifest, Owner, HTTP, daily executor and migration compatibility coverage.
- Live PG: read-only catalog/data evidence collected; Reader role rejected as superuser; no DDL/DML or isolated cluster used.
- Source/PIT: code independently reconstructs proof, but live accepted source package authority is absent; business eligibility remains blocked in actual runtime.
- Next: reconcile live migration/catalog drift under a separately approved least-privilege migration plan; provide an accepted source package and canonical daily producer feed; then perform live read-only Core and seven-page verification. Keep Head/production actions separately authorized.
