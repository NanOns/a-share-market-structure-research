---
stage_id: V4_R21_R4_BFF_CACHE_PG_DESCRIPTOR_PATH_GUARD_R38_20261017
branch: codex/v4-workspace-cleanup
status: SERVICE_CACHE_NO_LONGER_STATS_PG_ONLY_LOCATORS
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 21
ingress_adapters_open: 8
other_callsite_rows_open: 237
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue moving the remaining accepted Head and service registry reads onto their mapped PG authorities
---

# V4 R21-R4 BFF cache PG descriptor path guard

Date: 2026-10-17 (Asia/Shanghai). R36/R37 introduced a Head-bound PG membership descriptor into the daily service's Reader snapshot. The daily service cache invalidator still treated every `{path, sha256}` object as a workspace file and called `stat()` on it. The R36 descriptor report and active Reader integration constraints were reviewed before this repair.

## Implemented

- Added a service-level source-path collector that tracks local exact-file bindings while excluding `pg_descriptor` locators, whose `path` is logical lineage metadata and not a local filesystem path.
- The successor Reader cache now uses that collector for the Head candidate, Reader snapshot and existing registry document. It still invalidates on local source changes and the Head digest.
- Paths resolving outside the workspace are excluded from the cache set.
- Added a service regression with an absent PG locator path and an outside-root binding; only the existing local file is returned for cache tracking.

## Verification and limits

- `tests/test_v4_daily_server_reader_wiring_r30.py`: **3 passed**.
- Python compilation and `git diff --check` passed.
- No service was started, and no PG connection or business request was made. The current operational Head has no PG membership/Owner authority, so this is runtime path preparation, not live BFF acceptance.

## Accounting

Original P1 baseline: **266** (200 Owner, 28 other-business, 38 external-source). Formally complete **0 / 266** and remaining **266 / 266**. Existing inventory counts remain 21 code-level PG paths awaiting live readback/reconciliation, 8 ingress adapters, 237 other open rows and 22 unmapped reference edges. R38 closes no original P1 item.

## Next stage

Continue replacing direct accepted registry and Head reads only where a versioned PG authority and exact callsite mapping exist. Do not mark service or P1 acceptance from this helper test; require permitted same-T0 readback against the current Head.
