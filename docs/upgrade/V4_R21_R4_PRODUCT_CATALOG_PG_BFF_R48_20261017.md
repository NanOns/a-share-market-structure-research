---
stage_id: V4_R21_R4_PRODUCT_CATALOG_PG_BFF_R48_20261017
branch: codex/v4-workspace-cleanup
status: PRODUCT_MANIFEST_AND_SCOPE_READS_USE_HEAD_EMBEDDED_PG_CATALOG
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 37
ingress_adapters_open: 8
other_callsite_rows_open: 221
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_WRITE_DSN
next_stage: continue remaining Owner and other-business read callsites and confirm exact-candidate preparation with an authorized PG writer
---

# V4 R21-R4 product catalog PG BFF

Date: 2026-10-17 (Asia/Shanghai). R46 publisher preparation and the existing Head-embedded product catalog/history contracts were reviewed before connecting the product manifest to the PG BFF route.

## Implemented

- Added `V4_HEAD_EMBEDDED_PRODUCT_READ_CATALOG_PG_R1`. The existing exact-daily publisher now imports every dated product manifest and its referenced scope as immutable PG Owner facts, verifies full readback, and embeds the fact descriptors in the candidate Head. The catalog is scoped by accepted T0, complete published-session denominator, Owner digest, PIT flags, manifest date and source bindings.
- `native_product_catalog_v3.load()` reads the PG facts when the Head carries `native_product_read_authority_pg`; it does not open the catalog, manifest or scope source files on this path.
- `CoreProductBFFR1.chart_history_pack()` and `CoreProductBFFR1.pack()` now use that PG-first catalog and keep the existing local-file ingress only for candidates without the PG authority.
- Reconciled four exact baseline rows: `V4-BCA-R2-995651e4037bff37d345`, `V4-BCA-R2-cbc36584956420f6eec8`, `V4-BCA-R2-feeb0e7325d36faebd5a`, and `V4-BCA-R2-5d0aba48b88b7ddd66aa`. Their formal acceptance remains open pending current Head, live Reader and business reconciliation.

## Verification and limits

- Product catalog, BFF and preparation focused selection: **16 passed**. The new controlled-boundary tests verify manifest and scope reads avoid local-file fallback and reject an Owner binding substitution. These are code tests, not live business acceptance.
- Four existing `test_core_product_read_r1.py` cases attempted to create PG history schema and stopped at `V4_NATIVE_PG_DSN_REQUIRED_NO_FALLBACK`. No fake DSN or live write was used. Python compilation, source-policy inspection and `git diff --check` passed.
- No exact daily build, PG connection, market source capture, Head update, service startup or live BFF acceptance occurred. Current accepted Head does not yet carry `native_product_read_authority_pg`.

## Accounting

Original P1 baseline remains **266** (200 Owner, 28 other-business, 38 external-source). Formal completion remains **0 / 266**, remaining **266 / 266**. Code-level PG read paths pending reconciliation rise from **33 to 37**. The matrix now has **221 OPEN**, **8 ingress adapters open**, **37 implemented code rows pending reconciliation**, and **22 unmapped reference edges**. This closes four code-route rows only; it closes no formal P1 item.

## Next stage

Continue the remaining 221 OPEN rows in bounded functional batches. Run the complete exact daily publisher and BFF chain only after the approved PG writer is available, then reconcile the current Head and live same-T0 reads.
