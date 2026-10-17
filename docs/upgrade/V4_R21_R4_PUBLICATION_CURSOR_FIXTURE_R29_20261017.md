---
stage_id: V4_R21_R4_PUBLICATION_CURSOR_FIXTURE_R29_20261017
branch: codex/v4-workspace-cleanup
status: PUBLICATION_READER_FIXTURE_ALIGNED_CI_GREEN
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 21
ingress_adapters_open: 8
other_callsite_rows_open: 237
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: rerun full CI after the publication cursor fixture update and continue runtime migrations
---

# V4 R21-R4 publication reader cursor fixture

Date: 2026-10-17 (Asia/Shanghai). This batch repairs CI fixtures exposed by the R25 exact contract-set query.

## Implemented

- The `FakeConnection` in `tests/test_v4_pg_publication_candidate.py` now answers both the two-field transaction-scope query and the exact publication ID/revision `contract_bindings` query introduced in R25.
- The fake continues to return database/user identity for the full publication reader query. The fixture models query behavior; it does not bypass the production checks.

## Verification and limits

- `tests/test_v4_pg_publication_candidate.py`: **53 passed**.
- The R25/R26 pushed revisions' full workflow had 23 failures caused by the stale fake cursor returning the four-field identity tuple for the two-field scope query. The R29 fix passes the affected focused suite. GitHub Actions runs **39013839108** and **39013836479** both completed successfully, including repository content policy, PG publication candidate tests, and the current business-code file-access audit.
- No live PG connection, schema check, contract approval round trip, DDL/DML, Head mutation, service, or worker ran.

## Accounting

Original P1 baseline **266**. Formally complete **0 / 266**; formally remaining **266**. Code-level PG read paths remain **21** pending live readback/reconciliation; **8** ingress adapters remain open; **237** other callsite rows remain open. **22** reference edges remain unmapped. This fixture correction changes no migration count.

## Next stage

Wait for full CI on the updated fixture while continuing independent Owner, daily Head, descriptor, and source-ingress migrations. Do not interpret fixture pass or workflow success as live business acceptance.
