stage_id: V4_R21_R4_CANDIDATE_BFF_CALENDAR_CONTRACT_PG_R58_20261017
branch: codex/v4-workspace-cleanup
status: CANDIDATE_BFF_CUTOFF_CONTRACT_PG_BY_DEFAULT
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 47
open_callsite_rows: 211
ingress_adapters_open: 8
remaining_open_or_ingress: 219
unmapped_reference_edges: 22

# V4 R21-R4 candidate BFF calendar contract PG batch

Date: 2026-10-17 (Asia/Shanghai). Reviewed the official R21-R4 card, R57 calendar-default report, and the exact `derive_ready_sources` matrix caller before starting.

## Implemented

- `candidate_research_read_v2.capture_calendar_contract` now loads `V4_DM01_OFFICIAL_CALENDAR_BRIDGE_V1` version `1.0.0` through the approved PG contract registry by default. It uses the existing read-only repeatable-read Registry reader, expected database identity and model namespace configuration. Missing approval, identity or namespace fails closed without reading the local contract file.
- The local contract can only be selected with `V4_DAILY_CONTRACT_SOURCE=FILE`. The returned calendar-source evidence distinguishes PG Registry bytes from explicit file mode and records the exact contract SHA.
- Added focused tests for approved PG contract selection, fail-closed behavior without PG namespace and explicitly selected file mode. Added the test module to repository-policy CI.
- Corrected the R57 matrix blocker for `V4-BCA-R2-251b6859286f1bec50bc`: its exact inventory reference is the direct `producer_candidate_index_v2.json` read in `derive_ready_sources`. R55 persists that index entry downstream into the candidate PG Owner, after it is read; this does not migrate the active-day index producer/consumer chain. The row remains OPEN.
- Removed the stale R57 report wording that said the acquisition module remained in the CI command. That module is locally exercised; repository CI contains the PG calendar and DM-01 progress modules and does not require the BaoStock SDK metadata.

## Verification and limits

- Focused local selection: **35 passed** across the new BFF calendar contract tests, PG calendar, DM-01 progress, native research Owner and historical-candidate readers.
- The new BFF contract test uses a controlled PG boundary. No live PG query/import/write, registry registration, server start, Head update, or provider capture occurred. This is code-path evidence, not runtime business acceptance.
- R57 push and PR CI both passed on commit `3005822a3` (runs `39021551792`, `39021548214`). R58 CI will run on this batch's pushed commit.

## Accounting

Original denominator remains **266**: 200 Owner, 28 other-business and 38 external-market-source reads. R58 adds a real PG-backed BFF contract call but does not close one of the 266 inventoried business-read rows, so the reconciled counts remain **47** code-level PG paths pending inventory reconciliation, **211 OPEN**, **8 ACTIVE_INGRESS_ADAPTER_OPEN**, and **22 unmapped reference edges**. Formally complete **0/266**; formally remaining **266/266**. In the other-business group, **3** rows have code-level PG paths, **24** are OPEN and **1** is ingress.

## Next

Migrate the candidate-index writer/reader as one chain before crediting `derive_ready_sources`. Continue the remaining Owner and other-business readers and map DM-01 lifecycle/source report state to its real PG authority; `source_probe_state` is not that authority. Continue validating TDX and BaoStock at their actual entry points.
