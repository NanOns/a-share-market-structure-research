---
stage_id: V4_R21_R4_TDX_BAOSTOCK_CAPTURE_PATHS_BATCH_R8_20261017
baseline_sha: cbe844ca7cb28ac4f961d135c3a1979394d78a6f
branch: codex/v4-workspace-cleanup
status: CAPTURE_PATHS_CONFIG_WIRED_LIVE_INGRESS_OPEN
callsite_id: V4-BCA-R2-78d61b55d2259e7f1c21
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
live_capture: NOT_RUN
live_pg_catalog_or_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue exact PG consumer migration and source-to-accepted-candidate-to-publication wiring
---

# V4 R21-R4 TDX and BaoStock capture paths batch

Date: 2026-10-17 (Asia/Shanghai). This batch continues source-path implementation after the DM-01 PG Head code batches.

## Implemented code

- `scripts/capture_dm01_a01_r3_tdx_package.py` now resolves the TDX read-only source root and writable package snapshot root through `common.paths` and `config/paths.yaml` / environment overrides. Its capture outputs and summary are written under that configured snapshot root.
- `dm01_corrected_source_capture_v2.py` now uses the central TDX source and BaoStock cache roots for writes, source-boundary validation, and immutable BaoStock snapshots. Its request budget ledger is under the configured BaoStock cache instead of a reports directory.
- The shared path resolver already enforces explicit argument, environment, then central YAML precedence. No new resolver or absolute-drive fallback was added.

## Exact callsite and accounting

- Matrix ID `V4-BCA-R2-78d61b55d2259e7f1c21` now records the actual source path code and tests. The row remains OPEN: no source package was captured, no full contract was approved/imported, and no accepted PG fact/publication readback occurred. Other source capture and market-data IDs remain unmigrated.
- Original 266-item baseline: formally closed **0**, remaining **266**. Matrix status totals remain OPEN 237, ingress-open 8, PG code pending live read 21; unmapped reference edges remain 22.

## Verification

- **31 passed** in focused path configuration, BaoStock client, market calendar and PG calendar tests. `compileall` and `git diff --check` passed. Tests did not call external providers or PostgreSQL.
- The executable TDX/BaoStock capture paths were not run; no files were written under configured source or cache roots.

## Next stage

Continue with exact publication-bound PG consumer wiring and contract/source receipt binding. Do not reduce formal counts until source and consumer identities are reconciled and accepted by live readback.
