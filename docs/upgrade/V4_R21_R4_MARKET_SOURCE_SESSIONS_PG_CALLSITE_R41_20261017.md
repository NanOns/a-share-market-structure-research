---
stage_id: V4_R21_R4_MARKET_SOURCE_SESSIONS_PG_CALLSITE_R41_20261017
branch: codex/v4-workspace-cleanup
status: MARKET_SOURCE_SESSION_READER_HAS_EXPLICIT_PG_AUTHORITY_PATH
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 23
ingress_adapters_open: 8
other_callsite_rows_open: 235
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue actual read-path migration and reconcile additional exact-mapped business callsites
---

# V4 R21-R4 market source session PG callsite

Date: 2026-10-17 (Asia/Shanghai). The market-source acquisition calendar callsite had not been reconciled in the R21 matrix even though the current implementation contains an explicit PG reader route. The applicable PG calendar contract report and source acquisition contract were reviewed before reconciling this row.

## Implemented code path

- `market_source_acquisition.official_sessions()` selects the PG market calendar only when explicitly passed `source_mode='PG'` or `V4_MARKET_CALENDAR_SOURCE=PG`; it obtains `from_environment()` only in that mode and returns the PG reader's accepted ordered sessions.
- Unknown mode values fail closed. The file-based path remains explicitly selected for legacy callers; PG failure does not fall back to files.
- The PG reader binds sessions to the accepted publication Head, publication revision, registered approved calendar contract and calendar digest.
- Reconciled exact row `V4-BCA-R2-66c06ef7f4ecead04533` to code-implemented PG read path pending live database identity/readback and the caller's accepted publication mapping. Formal status remains open.

## Verification and limits

- `tests/test_v4_r21_pg_market_calendar.py` and `tests/test_market_source_acquisition_r4.py`: **15 passed**. These exercise the PG selection contract with controlled reader boundaries and the file/unsupported-mode behavior; they do not constitute a live database acceptance.
- No live PG read, source acquisition, network call, service, or Head mutation occurred.

## Accounting

Original P1 baseline is **266** (200 Owner, 28 other-business, 38 external-source). Formally complete **0 / 266**, remaining **266 / 266**. Code-level PG paths pending readback/reconciliation: **23**. Other open callsite rows: **235**; ingress adapters: **8**; unmapped reference edges: **22**. R41 closes no formal P1 row.

## Next stage

Continue exact-mapped business reader migrations and use the PG calendar only under an accepted publication identity. Do not lower the formal count until permitted same-T0 readback and exact baseline reconciliation.
