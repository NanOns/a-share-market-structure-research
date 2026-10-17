---
stage_id: V4_R21_R4_CONTRACT_REGISTRY_EXACT_MAP_R25_20261017
branch: codex/v4-workspace-cleanup
status: EXACT_PUBLICATION_BINDING_SET_ENFORCED_OFFLINE_LIVE_PG_OPEN
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 21
ingress_adapters_open: 8
other_callsite_rows_open: 237
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue exact publication and Owner consumer wiring; keep formal counts unchanged until live per-ID reconciliation
---

# V4 R21-R4 contract registry exact binding set

Date: 2026-10-17 (Asia/Shanghai). This batch hardens the publication contract consumer used by the PG publication reader and PG market-calendar reader.

## Implemented

- `load_publication_contracts` now requires a positive integer publication revision and the same read-only `REPEATABLE READ` transaction used by the individual contract reader.
- Before returning a set, it reads the exact accepted publication row by opaque publication ID and revision, then compares the caller's contract map to the complete persisted `contract_bindings` object. Missing, extra, partial, or altered version/digest entries fail closed with `V4_PUBLICATION_CONTRACT_BINDINGS_MISMATCH`.
- The existing per-contract reader still validates approval/revocation state, approval timestamps, namespace, stored digest, and exact raw bytes. The new check prevents consumers from silently receiving only a subset of a publication's contracts.
- Updated the PG market-calendar cursor fixture to model the additional exact-publication and transaction-scope reads made by the shared registry helper.

## Verification and limits

- `tests/test_v4_contract_registry_pg_v1.py` and `tests/test_v4_r21_pg_market_calendar.py`: **23 passed**. New cases cover missing/extra/substituted contract map entries and non-repeatable-read sessions; the calendar reader exercises the complete helper chain with a PG-shaped cursor.
- This is controlled-cursor verification of query selection and failure behavior. It does not establish live PG schema compatibility, approval lifecycle, catalog state, or business acceptance.
- No PG connection, DDL/DML, contract import, Head switch, source acquisition, service, or worker ran.

## Accounting

Original P1 baseline **266**. Formally complete **0 / 266**; formally remaining **266**. Code-level PG read paths remain **21** pending live readback/reconciliation; **8** ingress adapters remain open; **237** other callsite rows remain open. **22** reference edges remain unmapped. This batch changes no callsite status or completion count.

## Next stage

Continue the active daily contract/Head/Authority/descriptor chain and exact Owner/other-business consumer migrations. Do not close any row or reduce the 266 formal count without accepted Head and same-T0 Owner/source readback plus per-ID reconciliation.
