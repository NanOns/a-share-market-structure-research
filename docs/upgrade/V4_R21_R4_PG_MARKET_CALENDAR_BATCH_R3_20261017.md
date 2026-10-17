---
stage_id: V4_R21_R4_PG_MARKET_CALENDAR_BATCH_R3_20261017
baseline_sha: 8346c7d4f0ce7d7b8fc749677d45e18f03e6c7f0
branch: codex/v4-workspace-cleanup
status: PG_CALENDAR_OPT_IN_CODE_COMPLETE_RUNTIME_RECONCILIATION_OPEN
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
live_pg_catalog_or_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue active daily Head/source consumer migration and mapped Owner batches
---

# V4 R21-R4 PG market calendar batch

Date: 2026-10-17 (Asia/Shanghai). This batch extends R2. The applicable R18/R20/R21 upgrade documents and the Drive execution card remain the stage scope.

## Code path

- Added `PgMarketCalendarReader` for the canonical `v4.market_calendar_sessions` relation. It selects the latest accepted publication Head for an explicit model namespace in a read-only repeatable-read transaction, verifies configured database identity and reader-role write capabilities, resolves all publication-pinned contract bytes and approval events, then reads the selected calendar's complete session sequence.
- The reader rejects missing publication/contract bindings, unapproved or revoked contract versions, wrong database identity, missing schema, gaps in session numbers, non-increasing dates, mixed/invalid calendar digests, and a Head date absent from that calendar.
- `market_source_acquisition.official_sessions` now accepts the explicit `V4_MARKET_CALENDAR_SOURCE=PG` mode and routes to the PG reader. PG mode does not fall back to local files. The existing `FILE` mode remains the default pending runtime mapping and live acceptance.

## Batch accounting

Original baseline: **266 P1 reads**. **Formally completed: 0 / 266; formally remaining: 266.** The exact inventory row `V4-BCA-R2-66c06ef7f4ecead04533` remains `OPEN`, because runtime still defaults to file mode and there is no compliant live Reader DSN or accepted namespace/calendar mapping. This row now has explicit PG candidate code evidence. Baseline status counts are unchanged: `OPEN=237`, ingress adapters open `8`, PG code paths pending live-PG/inventory reconciliation `21`; unmapped reference edges `22`.

## Verification

- Consolidated focused selection: **107 passed**, including R2 contract/publication/Owner/DM-01 tests, the new PG calendar reader and acquisition entrypoint, and TDX/BaoStock path tests.
- The new PG calendar tests use a PG-shaped fake and prove the SQL branch, fail-closed checks and route selection. They do not prove live data or full business acceptance.
- No PG DDL/DML, source acquisition, request-budget writes, Head switch, service, or production operation ran. No TDX source directory was written.
- `compileall` and `git diff --check` passed.

## Next stage

Continue the real daily accepted Head and source artifact migration and mapped Owner/other-business consumers. Keep `FILE` runtime selected until the canonical database identity, namespace and publication rows are reconciled through the authorized read-only connection. Do not reduce the 266 formal remaining count based on the fake-based test results.
