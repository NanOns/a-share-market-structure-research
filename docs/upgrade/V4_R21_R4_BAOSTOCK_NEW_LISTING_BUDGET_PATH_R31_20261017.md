---
stage_id: V4_R21_R4_BAOSTOCK_NEW_LISTING_BUDGET_PATH_R31_20261017
branch: codex/v4-workspace-cleanup
status: CONFIGURED_CACHE_PATH_WIRED_WITH_LEGACY_BUDGET_CONTINUITY
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 21
ingress_adapters_open: 8
other_callsite_rows_open: 237
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue exact source-ingress manifest and accepted PG append/readback wiring
---

# V4 R21-R4 BaoStock new-listing budget path

Date: 2026-10-17 (Asia/Shanghai). This batch continues source-path verification following the TDX/BaoStock capture-path batch.

## Implemented

- `operational_new_listing_r1` now resolves a new BaoStock request ledger under the configured cache root when no existing ledger is present.
- If the legacy `reports/v4_baostock/request_ledger.json` exists, the adapter continues using it so the daily budget history is not silently reset or copied.
- If both legacy and configured ledgers exist, the adapter fails closed with `BAOSTOCK_REQUEST_LEDGER_MIGRATION_CONFLICT` rather than choosing one budget history.
- The current checkout contains the legacy ledger path; only its existence was checked. The ledger contents were not read, copied, or changed.

## Verification and limits

- `tests/test_operational_new_listing_r1.py` and `tests/r4_repair/test_configured_tdx_path.py`: **46 passed**, including configured-cache selection, legacy-ledger continuity and dual-ledger conflict.
- No BaoStock login/query, TDX source access, PG connection, output capture, or background worker was run.
- This path change does not correspond to an exact P1 row in the current 266-row callsite matrix. No baseline callsite ID is inferred; the 22 unmapped reference edges remain unresolved.

## Accounting

Original P1 baseline **266**. Formally complete **0 / 266**; formally remaining **266**. Code-level PG read paths remain **21** pending inventory reconciliation and live readback; **8** ingress adapters remain open; **237** other callsite rows remain open. **22** reference edges remain unmapped. R31 changes no formal or code-level-PG migration count.

## Next stage

Continue the exact source-ingress manifest, accepted PG append and same-T0 downstream publication readback. Keep the existing request-budget history continuous until a separately governed migration reconciles any ledger copies.
