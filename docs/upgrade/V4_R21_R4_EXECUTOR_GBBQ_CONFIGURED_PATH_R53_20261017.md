---
stage_id: V4_R21_R4_EXECUTOR_GBBQ_CONFIGURED_PATH_R53_20261017
baseline_sha: 7aba9d769c4f659d9f54ccbb37c911d23ad3dbc0
branch: codex/v4-workspace-cleanup
status: EXECUTOR_GBBQ_PATH_RESOLVES_FROM_CENTRAL_TDX_ROOT
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
matrix_code_level_pg_paths_pending_live_reconciliation: 39
matrix_open_rows: 219
matrix_ingress_adapters_open: 8
matrix_remaining_open_or_ingress: 227
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
provider_capture: NOT_RUN
next_stage: continue exact-mapped publication/Head/Owner migrations and DM-01 state mapping; keep the executor source gate closed pending accepted PG evidence
---

# V4 R21-R4 executor GBBQ configured path (R53)

Date: 2026-10-17 (Asia/Shanghai). Reviewed R42 TDX/BaoStock path verification and R43's central TDX resolver integration before changing the daily executor's GBBQ path contract.

## Implemented

- Versioned `V4_DAILY_TDX_READONLY_SOURCE_R1` to 1.1.0 and replaced its absolute drive path with the constrained relative location `T0002/hq_cache/gbbq`.
- `_tdx_gbbq_source_path` resolves the source root using the existing `common.paths.resolve_tdx_root` and verifies the relative path is exact, non-absolute, and traversal-free.
- The daily source gate passes its project root explicitly, so a configured project root is used consistently. The TDX source remains read-only; output isolation checks are unchanged.

## Verification and limits

- `tests/test_v4_r8_real_daily_executor_pg_bridge.py` and `tests/test_operational_daily_executor_v1.py`: **9 passed**.
- A missing local `cryptography` package initially prevented test collection. Installed it under `G:/codex_tmp/test_temp/site-packages` and reran successfully; no project dependency files changed.
- `compileall` and `git diff --check` passed. No TDX file was read, no provider was called, and no PG read/write or service run occurred.

## Accounting

Original P1 baseline remains **266** (200 Owner, 28 other-business, 38 external-source). Formal completion **0 / 266**; formal remaining **266 / 266**. PG code paths pending live reconciliation: **39**; OPEN rows **219**; ingress rows **8**; remaining OPEN/ingress **227**; unmapped reference edges **22**. Path selection evidence does not satisfy PG publication/Owner reconciliation and closes no original P1 item.

## Next stage

Continue actual PG consumer migration. The executor's source freeze, accepted Head, source readiness and publication transitions remain open until an approved source package/Owner mapping and same-T0 PG readback are available.
