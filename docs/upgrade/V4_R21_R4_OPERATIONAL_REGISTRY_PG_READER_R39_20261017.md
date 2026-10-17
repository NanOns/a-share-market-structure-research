---
stage_id: V4_R21_R4_OPERATIONAL_REGISTRY_PG_READER_R39_20261017
branch: codex/v4-workspace-cleanup
status: HEAD_BOUND_BUILDER_REGISTRY_PG_READER_AND_SERVICE_ROUTE_WIRED
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 22
ingress_adapters_open: 8
other_callsite_rows_open: 236
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: migrate additional exact-mapped Owner and other-business consumers through their Head-bound authorities
---

# V4 R21-R4 operational registry PG reader

Date: 2026-10-17 (Asia/Shanghai). R38 fixed the service cache's treatment of PG locators, but both Reader admission and the daily service still opened the builder registry as a workspace JSON file. The current contract registry schema report, Owner authority reader contract and R38 service report were reviewed before this migration.

## Implemented

- Added a versioned `V4_OPERATIONAL_BUILDER_REGISTRY_PG_R1` authority that stores the exact builder-registry payload in the existing append-only Owner fact store. Its manifest binds the source file identity, accepted trade date, PG descriptor and fact token.
- The candidate preparation function first checks the exact source bytes and owner binding, appends and reads back the PG fact, then replaces the candidate's registry locator with the inline PG descriptor. The function was not invoked against the configured database.
- Added a PG reader that checks Head T0, descriptor equality, source-binding token and Owner payload scope. When the new authority key is present it has no registry-file fallback; candidates without that key retain the legacy exact-file path.
- Operational successor admission and both daily-service registry consumers (cache source collection and compatibility asset lookup) now call the shared reader.
- Reconciled the exact service registry callsite `V4-BCA-R2-6e494c31ad6b9871ea87` to implemented PG-read code pending accepted-Head and inventory evidence. It remains formally open.

## Verification and limits

- Focused selection: **14 passed** across operational registry authority, daily service Reader routes and embedded Owner Reader integration.
- Python compilation and `git diff --check` passed.
- The tests exercise authority selection and fail-closed behavior with controlled Owner-reader boundaries; they do not simulate a successful database write as business acceptance. No PG write, live PG readback, service startup, or accepted Head update occurred. Current operational Head does not carry `native_operational_registry`.

## Accounting

Original P1 baseline is **266**: 200 Owner, 28 other-business and 38 external-source reads. Formally complete **0 / 266**; remaining **266 / 266**. Code-level PG paths pending live readback/reconciliation increase from 21 to **22**. Open other callsite rows decrease from 237 to **236**; 8 ingress adapters and 22 unmapped reference edges remain. The single code-level status change is not a formal P1 closure.

## Next stage

Continue actual Head-bound migrations for exact-mapped Owner and other-business readers, then obtain authorized read-only PG identity and same-T0 evidence before closing any formal P1 item. Keep the current Head, database and live service unchanged in this source-only batch.
