---
stage_id: R21-R4-contract-registry-sql-parser-ci-r62
branch: codex/v4-workspace-cleanup
status: POSTGRESQL_GRAMMAR_CHECK_ADDED_TO_CI
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 48
open_callsite_rows: 210
ingress_adapters_open: 8
remaining_open_or_ingress: 218
unmapped_reference_edges: 22
---

# Contract registry SQL parser in CI (R62)

Date: 2026-10-17 (Asia/Shanghai).

## Change

Added the pinned PostgreSQL grammar parser `pglast==8.6` to the repository-policy CI test environment and a regression test that parses all three contract-registry SQL artifacts: forward migration draft, guarded rollback draft, and read-only catalog preflight. This makes grammar compatibility regressions visible on push/PR.

## Evidence and limits

- Local focused verification: **22 passed** across the parser regression and contract registry behavior tests.
- Parser accepted forward draft (16 statements), rollback draft (19 statements), and read-only preflight (7 statements).
- Push CI [39023559420](https://github.com/NanOns/a-share-market-structure-research/actions/runs/39023559420) and PR CI [39023562326](https://github.com/NanOns/a-share-market-structure-research/actions/runs/39023562326) both completed successfully, including the V4 PG contract/candidate suite and business-code file-access audit.
- This confirms PostgreSQL grammar parsing only. No PG connection/catalog inspection, DDL/DML, registry import, or accepted Head readback occurred. It does not replace full business acceptance.

## Original 266-item accounting

The denominator remains **266** (200 Owner, 28 other-business, 38 external market-source). Formal completion remains **0/266**, formal remaining **266/266**. Implementation tracking remains **48** code paths pending live reconciliation, **210 OPEN**, **8 active ingress adapters**, **218** open or ingress, and **22 unmapped reference edges**. This SQL tooling batch maps to no original business read row and does not change those counts.

## Next

Continue actual contract, Head, Authority, descriptor, daily, BFF and DM-01 consumer wiring; check live PostgreSQL only under the configured Reader identity and keep all write-dependent acceptance open until separately authorized.
