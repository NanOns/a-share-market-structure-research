---
stage_id: V4_R21_R4_PRODUCT_CATALOG_BFF_MANIFEST_HELPER_R50_20261017
baseline_sha: e3f4ebec68ca7309990aeca5f6f94a499d11e699
branch: codex/v4-workspace-cleanup
status: PG_ONLY_BFF_MANIFEST_HELPER_CODE_COMPLETE_LIVE_READBACK_OPEN
callsite_id: V4-BCA-R2-3f5df8b949d86047ffb9
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
matrix_code_level_pg_paths_pending_live_reconciliation: 38
matrix_open_rows: 220
matrix_ingress_adapters_open: 8
next_stage: continue remaining exact-mapped BFF and Owner/other-business reads; DM-01 PG authority/state orchestration and source capture
---

# V4 R21-R4 product catalog BFF manifest helper (R50)

Date: 2026-10-17 (Asia/Shanghai).

## Scope and implementation

- Routed `CoreProductBFFR1.pack` and `chart_history_pack` through `dated_product_manifest` when the accepted Head embeds `native_product_read_authority_pg`.
- The helper now recognizes the versioned PG catalog, requires the exact candidate carrying that authority, reloads and validates the catalog through the read-only PG Owner fact reader, verifies the catalog owner digest/source binding, and returns the PG manifest without opening a local manifest path.
- Calls without the candidate fail closed in PG catalog mode. Existing R1/R2 file authority handling remains only on those legacy branches.
- Updated original matrix row `V4-BCA-R2-3f5df8b949d86047ffb9` (`dated_product_manifest`) with code-path evidence. No formal inventory row closes without live same-T0 readback.

## Original P1 accounting

- Original denominator: **266** (200 Owner, 28 other business, 38 external market-source reads).
- Formal completion: **0 / 266**; formal remaining: **266 / 266**.
- Matrix now records **38** PG-only code paths pending live reconciliation, **220** OPEN rows and **8** ingress adapters OPEN. The 38 code paths are not formal business completions.
- Reference edges: **244** linked, **22** unmapped.

## Verification and limits

- `tests/test_v4_product_catalog_pg_r48.py`: **2 passed**, including the BFF `pack` and `chart_history_pack` branches, no local manifest fallback, and missing-candidate failure.
- `compileall` passed for `core_product_bff_r1.py`.
- R49's full repository CI selection passed locally (169 tests); GitHub runs **39018371281** and **39018367584** passed after aligning its approval-source fixture.
- Tests cover code behavior only. No live PG catalog query, accepted Head readback, data migration, DDL/DML, or complete business acceptance was performed; no compliant Reader/Writer DSN is configured here.

## Next stage

Continue exact-mapped BFF and Owner/other-business consumers, then DM-01 authority/state orchestration and remaining source-ingress work. Keep all 266 formal items open pending accepted same-T0 PG evidence and per-ID reconciliation.
