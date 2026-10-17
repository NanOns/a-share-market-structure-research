# R95：DM-01 V4 stage writer requires a pre-provisioned PG schema

## Scope

`v4_dm01_stage_state_pg_r1._store()` no longer constructs `ForwardFactStore`, whose initializer creates a schema, installs tables/triggers, and imports local JSON files. It now binds the G-drive workspace and derived schema, requires the explicit `V4_NATIVE_PG_DSN`, checks the database identity and the existing `forward_facts` relation, then returns an append-only store handle. Missing schema fails with `DM01_STAGE_STATE_SCHEMA_NOT_PROVISIONED`. `append_stage()` independently checks the expected database identity before invoking the append operation.

## Verification and limits

- `tests/test_v4_dm01_stage_state_pg_r1.py`, `tests/test_v4_dm01_daily_stage_consumer.py`, `tests/test_v4_r21_dm01_pg_progress.py`: **25 passed**.
- Tests cover that schema lookup performs no DDL, that no `ForwardFactStore` initializer runs, that missing schema fails closed, and that stage facts retain date/stage/digest checks.
- No PostgreSQL connection, DDL, DML, source import, Head write, or daily business acceptance was performed.

## Original 266 stable callsites

This batch closes no stable callsite: **0 / 266 formally complete; 266 / 266 remaining**. The local V4 Stage/Dev/Data bootstrap Head read/write chain remains open and requires a separately designed and authorized PG migration/import path; current controlled tests do not satisfy that requirement.

## Next

Continue V4-only work on the PG-backed bootstrap Head and current Head consumer chain, keeping catalog reads, DDL, and DML behind their respective explicit access boundaries. Continue migrating the remaining registry, Authority, descriptor, daily, and BFF business readers, and do not change R3.3 DM-01 modules as part of this scope.
