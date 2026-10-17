# R90: DM-01 baseline acceptance facts read from PostgreSQL

## Scope

The continuous-maintenance entrypoint now obtains its Phase 0, V4-01 acceptance, V4-01 postcheck, and V4-02 acceptance facts through the date-bound `V4_DM01_STAGE_STATE_PG_R1` reader. The old report-file and local V4-02 Head reads were removed from this path. Missing or duplicate PG facts fail closed. Runtime receipts are written beneath `runtime/v4_dm01/<run-date>`.

The Head/bootstrap state still has a local JSON write/read path and is not migrated in this batch. No importer was run and no PG rows were written. The current environment has no configured `WORKBENCH_PG_DSN`, `V4_NATIVE_PG_READER_DSN`, or `V4_PG_EXPECTED_DATABASE_IDENTITY_JSON`, so live readback and business acceptance were not available.

## Verification

Focused unit tests cover exact date/stage dispatch, the PG-only bootstrap baseline path, and fail-closed behavior when a baseline fact is missing. These tests use controlled cursors and do not establish live PG or end-to-end business acceptance.

## Original 266-callsite accounting

- Formally completed: **0 / 266**.
- Formally remaining: **266 / 266**.
- Matrix remains: 53 code-level PG-only reads pending inventory reconciliation, 203 OPEN, and 10 active ingress adapters open; 22 reference edges remain unmapped.
- This baseline bootstrap change does not close an original stable callsite ID because the migration matrix contains no exact baseline row for this new reader path.

## Next

Migrate the local DM-01 Head/bootstrap state to a PG-backed authority and continue the 28 other-business consumers. Seed accepted baseline stage facts only through a separately authorized, auditable PG import; do not use report files as runtime fallback.
