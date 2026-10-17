---
stage_id: V4_R21_R4_REGISTRY_ROLLBACK_BATCH_R9_20261017
baseline_sha: adf763d48a51331aff36c23187e37cbe7bd9777f
branch: codex/v4-workspace-cleanup
status: GUARDED_ROLLBACK_DRAFT_SYNTAX_VALID_LIVE_SCHEMA_OPEN
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
live_pg_catalog_or_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue exact current consumers and full registry approval lifecycle tests
---

# V4 R21-R4 contract registry rollback batch

Date: 2026-10-17 (Asia/Shanghai). This batch closes a missing engineering deliverable in the registry migration draft.

## Implemented

- Added `R21R4_V4_CONTRACT_REGISTRY_ROLLBACK_DRAFT_20261017.sql`. It checks that the contract-version table, approval-event table, and all publication contract bindings are empty before dropping the R21-R4 registry objects or the additive publication column. It raises a stable exception and rolls back the transaction if any registry history or binding exists.
- Added an offline regression assertion for the rollback refusal conditions. The forward migration remains the source of append-only version bytes, append-only approval/revocation events, database-assigned recording timestamps, compatibility with legacy unbound accepted rows, and acceptance-trigger enforcement.

## Verification and limits

- **66 passed** across contract registry, PG publication candidate, and BFF candidate HTTP tests.
- PostgreSQL parser syntax check: forward migration **17 statements**, rollback draft **19 statements**. `git diff --check` passed.
- Parser success is syntax evidence only. No live catalog alignment, DDL/DML, history replay, role grant, or live approval/revocation round trip occurred. These require a compliant read identity and separately authorized writes.

## Accounting

Original P1 baseline **266**; formal completed **0 / 266**, remaining **266**. Inventory status counts remain OPEN 237, ingress-open 8, PG code pending live-read/inventory reconciliation 21; 22 reference edges remain unmapped. No business callsite is closed by this SQL rollback batch.

## Next stage

Continue direct production consumer integration and full approval, revoke, version-upgrade, and historical replay verification when the live schema/authorization is available. Keep all 266 formal items open until exact per-ID reconciliation.
