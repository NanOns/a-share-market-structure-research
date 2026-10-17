---
stage_id: V4_R21_R4_BAOSTOCK_RUNTIME_ACCEPTANCE_CONFIG_PATHS_R32_20261017
branch: codex/v4-workspace-cleanup
status: LIVE_ACCEPTANCE_PATH_GUARDS_CONFIGURED; LIVE_ACQUISITION_NOT_RUN
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 21
ingress_adapters_open: 8
other_callsite_rows_open: 237
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue approved source-ingress contract and PG append/readback wiring
---

# V4 R21-R4 BaoStock runtime-acceptance configured paths

Date: 2026-10-17 (Asia/Shanghai). This batch continues R31's BaoStock budget-path work and the R8 source-capture configuration migration.

## Implemented

- Added a shared `resolve_baostock_request_ledger` resolver in `common.paths`. It honors an explicit path, otherwise uses the legacy ledger when present, the configured cache when no legacy ledger exists, and fails closed if both copies exist.
- `operational_new_listing_r1` now delegates budget-path resolution to that shared helper.
- The live BaoStock runtime-acceptance adapter now resolves the TDX source root and uses it for every output path guard; it no longer pins the guard to `D:/new_tdx`.
- The same runtime-acceptance adapter resolves the request-budget ledger through the shared helper.
- Repaired the isolated source-readiness fixture to configure the newly required TDX source and snapshot roots. Fixture setup did not read or write a TDX source root.

## Verification and limits

- `tests/test_operational_new_listing_r1.py`, `tests/r4_repair/test_configured_tdx_path.py`, and `tests/test_next_t0_old_identity_preflight.py`: **52 passed**.
- Python compilation and `git diff --check` passed.
- The adapter path contract is verified offline; no BaoStock login/query, TDX capture, runtime-acceptance receipt, PG connection, or worker was run.

## Accounting

Original P1 baseline **266**. Formally complete **0 / 266**; formally remaining **266**. Code-level PG read paths remain **21** pending inventory reconciliation and live readback; **8** ingress adapters remain open; **237** other callsite rows remain open. **22** reference edges remain unmapped. The runtime-acceptance script is not an exact row in the baseline matrix; this batch adds no synthetic callsite ID or count.

## Next stage

Continue the exact source-ingress contract, approved PG append, and same-T0 consumer/publication readback. Do not run the live acceptance adapter without an explicit operational capture window and its accepted runtime conditions.
