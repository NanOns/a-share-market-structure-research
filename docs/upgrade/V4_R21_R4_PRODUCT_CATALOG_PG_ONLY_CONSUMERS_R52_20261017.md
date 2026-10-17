---
stage_id: V4_R21_R4_PRODUCT_CATALOG_PG_ONLY_CONSUMERS_R52_20261017
baseline_sha: f28e868519ad15436b5476aede881695e4d789d2
branch: codex/v4-workspace-cleanup
status: PRODUCT_PACK_AND_CHART_CONSUMERS_FAIL_CLOSED_WITHOUT_HEAD_PG_CATALOG
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
matrix_code_level_pg_paths_pending_live_reconciliation: 39
matrix_open_rows: 219
matrix_ingress_adapters_open: 8
matrix_remaining_open_or_ingress: 227
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue exact-mapped Owner and other-business consumer migrations; then bind the current accepted Head to its authorized PG product catalogue
---

# V4 R21-R4 product catalogue PG-only BFF consumers (R52)

Date: 2026-10-17 (Asia/Shanghai). Reviewed R50's product catalogue helper and R51's Focus projection PG Owner consumer before removing the remaining current-runtime file-authority branch in `pack` and `chart_history_pack`.

## Implemented

- Both product-history consumers now require `native_product_read_authority_pg` on the exact active candidate and resolve the dated manifest and scope through the PG Owner fact reader.
- Removed the runtime branches that opened `config/core_product_read_authority_r1.json`, local manifest files, or local scope artifacts when the PG catalogue is missing.
- A Head without the PG catalogue now fails closed with `PRODUCT_PG_CATALOG_REQUIRED_NO_FILE_FALLBACK`. Isolated engineering history remains an explicit separate reader path.
- Updated five stable matrix rows for the manifest/scope reads in `chart_history_pack` and `pack`; each remains formally OPEN pending accepted Head binding and live readback.

## Verification and limits

- Product catalogue and Focus-route selection: **9 passed**, 16 deselected from the combined route selection.
- `compileall` and `git diff --check` passed.
- These are PG-shaped unit tests. No live PG query, service request, Head update, source import, or business acceptance occurred. Current accepted Head lacks the required PG product catalogue.

## Accounting

Original P1 baseline: **266** (200 Owner, 28 other-business, 38 external-source). Formal completion **0 / 266**; formal remaining **266 / 266**. Code-level PG paths remain **39** pending live reconciliation; **219** rows remain OPEN and **8** ingress rows remain open (**227** open/ingress total). **22** reference edges remain unmapped. This batch improves five already code-mapped consumer rows and does not reduce formal completion.

## Next stage

Continue exact-mapped Owner and other-business callsites, including the candidate read's unresolved source contract. Keep the BFF closed until the authorized publication binds the exact PG catalogue and live same-T0 reconciliation is available.
