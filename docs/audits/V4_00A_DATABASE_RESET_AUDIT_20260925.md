# V4-00A Clean PostgreSQL Baseline Reset Audit (2026-09-25)

| Field | Record |
|---|---|
| audit_id | `V4-00A-DATABASE-RESET-01` |
| status | `CLOSED / CLEAN_V4_BASELINE_REBUILT` |
| database | PostgreSQL `market_research`, `127.0.0.1:5432`, PostgreSQL 18.6, system identifier `7688198230782699460` |
| authorization | User explicitly directed a physical backup followed by deletion of the current project database. Scope was verified as `market_research`; cluster system/template databases were not changed. |
| backup | `runtime/v4_phase0/backups/postgres_physical_20260925_114550`; `pg_verifybackup` passed; manifest SHA-256 `2cbe45327884a096b9ef7824f6df0ec7b27ba98c8b14f981161587a788712727`. |
| reset | `DROP DATABASE market_research WITH (FORCE)` followed by recreation with original owner, UTF8 encoding, and locale. System database set remained `market_research`, `postgres`, `template0`, `template1`. |
| old row counts | Exact counts for 244 tables were read from a disposable clone of the verified physical backup; 146 tables held 5,308,402 rows. See `reports/v4_phase0/V4_DATABASE_RESET_ROW_COUNTS_BEFORE.json`. |
| schema rebuild | Applied `V4_PHASE0_FOUNDATION_V1` and `V4_PHASE0_NAMESPACE_INTEGRITY_V1` from hash-checked PostgreSQL migrations. 13 V4 tables, required indexes and constraints are present. |
| acceptance | All old legacy/workbench schemas and data were removed. Old publication heads = 0; old Focus heads = 0; all V4 runtime rows = 0. PostgreSQL foreign keys are validated; clean schema rebuild and append-only/namespace cases pass. |
| TDX boundary | No writes below `D:/new_tdx` or any configured TDX input root. The local read-only snapshot digest matched before/after the overlap run. |

The physical backup is retained outside TDX and outside Git. It is not a V4 data migration input. No old publication, Focus, runtime, or history row was restored into the clean V4 database.
