---
stage_id: V4_R21_R4_FOCUS_PROJECTION_POSTGRES_OWNER_R51_20261017
baseline_sha: 76539125103df2a36f48c609593b307d2c12006e
branch: codex/v4-workspace-cleanup
status: PG_OWNER_CONSUMER_CODE_COMPLETE_LIVE_READBACK_OPEN
callsite_id: V4-BCA-R2-40f9c0ebfaf3896f1ac5
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
matrix_code_level_pg_paths_pending_live_reconciliation: 39
matrix_open_rows: 219
matrix_ingress_adapters_open: 8
next_stage: continue Owner, daily executor/producer, DM-01 scheduler state and other-business consumer migrations
---

# V4 R21-R4 Focus projection PostgreSQL Owner consumer (R51)

Date: 2026-10-17 (Asia/Shanghai).

## Implementation

- Replaced the previous SQLite-backed Focus projection snapshot with an immutable fact in the native PostgreSQL operational Owner relation. The fact binds the source artifact, T0, Head scope token, full payload digest, and versioned contract; preparation reads the entire fact back and compares the complete payload.
- During native product catalog preparation, the exact Head-scoped R2 Focus projection is ingested once and the PG descriptor is embedded in the migrated R3 manifest before the manifest and scope are appended to the Head-bound catalog.
- `CoreProductBFFR1.focus_projection` now requires that Head-bound PG catalog, resolves the dated manifest through the PG catalog reader, and reads the inline Owner descriptor. The config authority, local manifest, and projection payload are not runtime fallbacks.
- Updated original row `V4-BCA-R2-40f9c0ebfaf3896f1ac5`; live evidence remains open.

## Original 266 accounting

- Original denominator: **266** (200 Owner, 28 other business, 38 external market-source reads).
- Formal completion: **0 / 266**; formal remaining: **266 / 266**.
- Matrix code paths pending live reconciliation: **39**; OPEN: **219**; ingress adapters OPEN: **8**. Therefore **227** rows remain OPEN or ingress-open; code paths are a separate implementation count and do not reduce the formal denominator.
- Reference edges remain **244 linked / 22 unmapped**.

## Verification and limits

- Focus projection and product catalog tests: **8 passed**.
- BFF Focus route and fail-closed focused regression selection: **12 passed, 16 deselected**. These use PG-shaped test doubles and establish code path behavior only.
- No live PostgreSQL write/readback, current accepted Head change, service start, market acquisition, or business acceptance was performed. The checked-in accepted Head does not yet embed `native_product_read_authority_pg`; consequently the formal item remains open pending authorized publication and same-T0 live reconciliation.

## Next

Continue exact-mapped Owner and daily executor/producer paths, DM-01 scheduler state, and other-business reads. Do not stop at this batch; retain the original 266 formally open until each has live accepted same-T0 evidence.
