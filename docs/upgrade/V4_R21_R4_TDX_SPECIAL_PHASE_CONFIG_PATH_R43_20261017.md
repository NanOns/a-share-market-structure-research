---
stage_id: V4_R21_R4_TDX_SPECIAL_PHASE_CONFIG_PATH_R43_20261017
branch: codex/v4-workspace-cleanup
status: SPECIAL_PHASE_MANIFEST_USES_CENTRAL_TDX_ROOT_CONFIGURATION
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 39
other_callsite_rows_open: 219
ingress_adapters_open: 8
remaining_open_or_ingress: 227
unmapped_reference_edges: 22
live_provider_capture: NOT_RUN
live_pg_ingest: NOT_RUN_NO_WRITE_AUTHORIZATION
next_stage: continue exact Head/Authority/Owner consumer migration and identify the approved PG Owner relation for DM-01 source receipts
---

# V4 R21-R4 TDX special-phase path configuration

Date: 2026-10-17 (Asia/Shanghai). Reviewed the R42 TDX/BaoStock path verification and the central `config/paths.yaml` resolver contract.

## Implemented

- `build_special_phase_source_manifest` now resolves its default read-only TDX root via `common.paths.resolve_tdx_root(project_root)` rather than a hard-coded drive path.
- An explicit `tdx_root` remains supported for isolated callers and tests. Existing source-root write guards still protect the TDX tree.
- The change adds no alternate resolver and does not read or write a TDX source directory.

## Verification and limits

- `tests/v4_dm01/test_official_daily_sources_v2.py`: **51 passed**, including the no-argument resolver path through a temporary project config.
- `compileall` and `git diff --check` passed.
- No provider capture, PG read/write, source import, scheduler, or service run occurred.

## Accounting

The original P1 baseline remains **266** (200 Owner, 28 other-business, 38 external-source). Formally complete **0 / 266**; remaining **266 / 266**. The code-level PG read-path count is **39**, pending approved live readback and exact inventory reconciliation. There are **219** OPEN rows and **8** ingress rows (**227** remaining open/ingress), with **22** unmapped reference edges. This path configuration change closes no original P1 row.

## Next stage

Continue wiring publication-bound Head, Authority, descriptors and Owner consumers. DM-01's source-freeze, lifecycle, GBBQ revision and special-phase receipts need a matching approved PG Owner or publication contract before orchestration switches away from their current evidence source.
