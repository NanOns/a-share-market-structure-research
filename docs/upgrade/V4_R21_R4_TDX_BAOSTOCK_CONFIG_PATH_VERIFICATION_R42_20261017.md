---
stage_id: V4_R21_R4_TDX_BAOSTOCK_CONFIG_PATH_VERIFICATION_R42_20261017
branch: codex/v4-workspace-cleanup
status: TDX_AND_BAOSTOCK_CONFIGURED_PATH_REGRESSIONS_PASS
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 23
ingress_adapters_open: 8
other_callsite_rows_open: 235
unmapped_reference_edges: 22
live_provider_capture: NOT_RUN
live_pg_ingest: NOT_RUN_NO_WRITE_AUTHORIZATION
next_stage: continue PG consumer migrations and keep source ingress gated on an approved source manifest and authorized PG append
---

# V4 R21-R4 TDX and BaoStock configured path verification

Date: 2026-10-17 (Asia/Shanghai). Reviewed the R31 new-listing budget path and R32 central source-root path contracts before verifying their current consumers.

## Verification

- Focused path/configuration selection: **56 passed** across `tests/r4_repair/test_configured_tdx_path.py`, `tests/test_tdx_latest_daily_source_v2.py`, `tests/test_operational_new_listing_r1.py`, and `tests/test_operational_daily_executor_v1.py`.
- Evidence covers TDX read-only source-root resolution, separate snapshot-output root, BaoStock cache selection, configured request-ledger storage, new-listing request budget path, and DM-01 executor path selection.
- Test paths use temporary locations under `G:/codex_tmp/test_temp`. No network/provider acquisition, write under a TDX source root, PG ingestion, or service execution occurred.

## Accounting

The original P1 baseline remains **266** (200 Owner, 28 other-business, 38 external-source); formal completion **0 / 266**, remaining **266 / 266**. Code-level PG paths pending reconciliation: **23**; other open rows: **235**; ingress adapters: **8**; unmapped reference edges: **22**. Path-configuration tests do not close an external-source baseline item.

## Next stage

Continue the Reader/Head/Authority consumer batches. Source acquisition and PG ingestion remain open until an approved, versioned ingress manifest and authorized append/readback are available.
