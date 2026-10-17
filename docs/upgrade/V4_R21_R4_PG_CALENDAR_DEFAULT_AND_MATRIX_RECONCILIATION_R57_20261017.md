stage_id: V4_R21_R4_PG_CALENDAR_DEFAULT_AND_MATRIX_RECONCILIATION_R57_20261017
branch: codex/v4-workspace-cleanup
status: PG_CALENDAR_DEFAULT_WIRED; ONE_PREVIOUS_CALLSITE_STATUS_REOPENED
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 47
open_callsite_rows: 211
ingress_adapters_open: 8
remaining_open_or_ingress: 219
unmapped_reference_edges: 22

# V4 R21-R4 PG calendar default and matrix reconciliation

Date: 2026-10-17 (Asia/Shanghai). Reviewed the R21-R4 execution card and the latest R56 runtime-contract/PG-reader report before starting this batch.

## Implemented

- The shared `market_source_acquisition.official_sessions` call now defaults to the accepted PG market calendar. `FILE` remains available only by explicit mode. The existing executor and PG DailyJobs calendar selectors also default to PG; PG failures do not fall back to local calendar files.
- Updated the file-backed acquisition test and legacy full-executor fixture to select `FILE` explicitly. Added default-PG assertions and put the market-calendar and DM-01 progress test modules into repository-policy CI. The BaoStock-SDK-dependent acquisition module is locally tested but excluded from CI.
- Re-audited the exact R56 source lines for `V4-BCA-R2-251b6859286f1bec50bc`. `derive_ready_sources` calls `verify_source_gate`, which still reads the operational Head and its lifecycle and identity sidecars. R56's runtime-contract reader does not replace those authorities. Reopened this row as `OPEN` and documented the actual missing PG relation mapping. It receives no migration credit.
- Updated `V4-BCA-R2-66c06ef7f4ecead04533` with the selected default-path evidence. Its formal status remains open pending live identity, approved calendar contract and accepted-publication reconciliation.

## Verification and limits

- Focused local selection: **51 passed** across PG calendar, DM-01 progress, source acquisition, executor-chain and contract-registry tests. The exact repository-policy pytest selection after excluding the Baostock-SDK-dependent acquisition module passed locally: **293 passed**.
- The PG path was exercised with controlled fake boundaries. No live catalog read, Registry import, database write, server start, accepted Head update, or provider capture occurred. These tests are not business acceptance.
- R56 CI initially failed in two legacy executor-chain tests because those fixtures had not explicitly selected file-contract mode; R57 makes that test boundary explicit. The first R57 CI attempt then showed that the acquisition module requires Baostock package metadata that repository CI does not install. The module was removed from the CI command; the PG calendar and DM-01 regression modules remain included. Current pushed CI is authoritative.

## Accounting

Original denominator remains **266**: 200 Owner, 28 other-business and 38 external-market-source rows. Formally complete **0/266**; formally remaining **266/266**. Reconciled current matrix: **47** code-level PG paths pending live readback/reconciliation, **211 OPEN**, **8 ACTIVE_INGRESS_ADAPTER_OPEN**, and **22 unmapped reference edges**. In the other-business group, **3** rows have code-level PG paths, **24** are OPEN and **1** is an ingress adapter. Reopening the derive-ready row corrects the previous R56 overcount; only exact source evidence changes the row count.

## Next

Continue the active `derive_ready_sources` accepted Head and dated Owner identity/lifecycle migration, then batch the remaining business and Owner readers. Solve DM-01 report-state ownership through a real PG relation mapping; the existing scheduler progress tables are not a substitute for source/lifecycle state. Verify TDX and BaoStock configuration on their actual entry points. No live PG write permission is required for independent source, test and CI work.
