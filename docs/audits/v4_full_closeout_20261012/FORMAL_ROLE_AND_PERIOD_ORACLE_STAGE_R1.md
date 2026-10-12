# Formal role readiness and dated independent arithmetic

Contracts: V4_FORMAL_PG_ADDITIVE_ROLE_PREPARATION_R1 and V4_FULL_DATED_PERIOD_AGGREGATION_INDEPENDENT_ORACLE_R1. User amendment defers performance and rollback testing; functional/data checks and authorized controlled cutover remain in scope.

The actually configured formal cluster at 127.0.0.1:5432 / market_research / system_identifier 7688198230782699460 admitted two newly created LOGIN roles. Both have no superuser, database-creation, role-creation, replication, bypass-RLS or elevated membership privileges. The producer is explicitly granted CREATE on the existing database for new V4 schemas; the reader is not. Both verified their real login, cluster identity and identity-function EXECUTE. Existing roles, business schemas and the original Data/Research Heads were not changed. Credentials are encrypted with Windows user DPAPI and stored only under the new G-local production workspace; no password or DSN secret enters evidence or Git.

Evidence: `G:/codex_tmp/v4_full_closeout_20261012/formal_pg_roles/RESULT.json`. Acceptance: role identity and granted privilege checks PASS. Formal business-schema migration, runtime use, same-T0/token native readback and production cutover remain next-stage work; role creation alone is not production deployment.

Independent 2026-09-28 period oracle: all 5,222 source securities, both RAW and QFQ weekly/monthly period domains, 18,320,512 field comparisons, zero differences. The oracle reads the actual PG owners and separately groups the immutable daily source using Python calendar dates and Decimal arithmetic. It verifies OHLC, amount, volume, calendar/actual/unknown/gap/suspension counts, basis, statuses, reconstructed lineage and absent production/PIT permission. It does not call the period kernels or infer suspension from absence.

Evidence: `G:/codex_tmp/v4_full_closeout_20261012/period_oracle/R1/2026-09-28/RESULT.json`. Acceptance: complete dated aggregation-only oracle PASS. Exact adjustment-factor transport and the other four dates remain separately required. This does not establish full V4 PASS.
