---
stage_id: V4_R21_R4_DAILY_QA_EVIDENCE_PG_READER_R44_20261017
branch: codex/v4-workspace-cleanup
status: DAILY_RECEIPT_AND_ORACLE_VALIDATION_SUPPORTS_HEAD_BOUND_PG_EVIDENCE
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 32
ingress_adapters_open: 8
other_callsite_rows_open: 226
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: migrate remaining predecessor/period-source QA bindings and preserve Head lineage for authorized readback
---

# V4 R21-R4 daily QA evidence PG reader

Date: 2026-10-17 (Asia/Shanghai). R37/R39 connected membership and registry authority into successor validation. The daily receipt, core oracle, sector oracle, source freeze and period oracle were still local JSON reads. The applicable R37/R39/R43 reports and the embedded Owner fact contract were reviewed before implementing this evidence path.

## Implemented

- Added versioned `V4_OPERATIONAL_DAILY_EVIDENCE_PG_R1` preparation and read contracts for the exact day receipt, numeric core oracle, sector oracle, source freeze and period numeric oracle.
- Preparation checks the accepted trade date, receipt status and Owner bindings, reads each exact source binding, appends each document as an immutable PG Owner fact and verifies full payload readback before embedding the descriptors in a successor candidate.
- `OperationalSuccessorReader.validate()` now calls one evidence reader for those five documents. In PG mode the helper validates the candidate authority T0, document name, original source binding, fact token and inline PG descriptor; no source-file fallback occurs for those documents.
- The legacy exact-file route remains for candidates without `native_daily_evidence`. It still does not change a Head or publication pointer.
- Reconciled the five exact baseline callsites for day receipt, core oracle, sector oracle, source freeze and period oracle as PG-code implemented, pending current Head and live readback.

## Verification and limits

- Focused evidence/Reader selection: **13 passed** across daily evidence authority, embedded Owner integration and registry authority.
- Tests use controlled Owner-reader boundaries and prove the PG branch does not reopen source evidence. They do not establish a live PG write/read or business acceptance.
- No PG write/readback, service, source acquisition or Head update occurred. Current Head lacks `native_daily_evidence`.
- Period input history/verifier and additional source registry bindings remain separate exact inputs and have not been migrated by this batch.

## Accounting

Original P1 baseline: **266** (200 Owner, 28 other-business, 38 external-source). Formal completion remains **0 / 266**, remaining **266 / 266**. Code-level PG paths pending live reconciliation rise from 27 to **32**; other open callsite rows fall from 231 to **226**. The 8 ingress adapters and 22 unmapped reference edges remain. No formal P1 row closes.

## Next stage

Continue the daily validation chain by mapping period history/verifier and predecessor authority reads, then exercise the full chain under an approved Reader identity and same-T0 accepted Head readback.
