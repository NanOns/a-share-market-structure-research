stage_id: V4_R21_R4_OPERATIONAL_REGISTRY_PG_ONLY_CONSUMER_R54_20261017
branch: codex/v4-workspace-cleanup
status: CODE_PATH_FAIL_CLOSED_NO_LEGACY_READ_FALLBACK
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 39
open_callsite_rows: 219
ingress_adapters_open: 8
remaining_open_or_ingress: 227
unmapped_reference_edges: 22

# V4 R21-R4 operational registry PG-only consumers

Date: 2026-10-17 (Asia/Shanghai). Reviewed the latest R21-R4 migration task, R39 registry mapping, R52 product-catalog BFF migration, R53 configured GBBQ path report and current callsite matrix before this batch.

## Changes

- `v4_operational_registry_pg_v1.read_registry` now requires the candidate's `native_operational_registry` authority and delegates to the exact Head/T0-scoped PG fact reader. It no longer falls back to the legacy registry file. The prepare function remains the explicit ingress boundary that validates and copies source bytes into the Owner fact store.
- Operational successor validation and both daily-service registry routes already share this reader; missing authority now causes a fail-closed result before any registry file open. The current accepted Head lacks this authority, so these routes remain unavailable until an approved successor Head is published.
- Fixed the GBBQ path contract test to validate its fixed `T0002/hq_cache/gbbq` suffix and resolved absolute path on Windows and Linux. This repairs the Linux-only assertion failure in the two R53 CI runs.
- Updated the exact 266-row callsite matrix with this batch's evidence. The registry callsite stays in the existing implemented-code-pending-reconciliation category.

## Verification and limits

- Selected repository-CI suite: **247 passed** (including the original CI selection, the registry authority/preparation tests and daily-service reader wiring).
- R53 CI had failed on the Windows-only path assertion; the corrected assertion passed locally in this selection. CI for this batch is pending push.
- No live PG read, PG write, database migration, Head update, service startup, provider capture or business acceptance occurred. Current Head does not carry `native_operational_registry`.

## Accounting

The original denominator remains **266**: 200 Owner, 28 other-business, 38 external-source reads. Formally complete **0/266**; formally remaining **266/266**. The matrix records **39** code-level PG paths pending live readback and inventory reconciliation, **219 OPEN** rows, **8 ACTIVE_INGRESS_ADAPTER_OPEN** rows, and **22** reference edges without exact callsite mapping. The 39 are implementation paths, not completed formal items.

## Next stage

Continue actual Head-bound migrations for the remaining exact-mapped Owner and other-business consumers, and continue DM-01 PG state work independently of live write permission. Obtain compliant read identity and same-T0 evidence before any formal item is closed.
