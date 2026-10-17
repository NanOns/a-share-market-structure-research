stage_id: V4_R21_R4_CANDIDATE_INDEX_INPUT_HEAD_PG_READ_R55_20261017
branch: codex/v4-workspace-cleanup
status: EXACT_DAILY_CANDIDATE_INDEX_AND_INPUT_HEAD_READ_FROM_PG_OWNER
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 46
open_callsite_rows: 212
ingress_adapters_open: 8
remaining_open_or_ingress: 220
unmapped_reference_edges: 22

# V4 R21-R4 exact-daily candidate index and input Head PG read

Date: 2026-10-17 (Asia/Shanghai). Reviewed the official R21-R4 task card, current 266-row migration matrix, membership-reference PG authority contract, R54 registry-reader batch and current candidate BFF path.

## Implemented

- `prepare_research` now stores the exact accepted input-candidate Head as an append-only Owner fact and binds it, with its exact dated producer-index entry, into the existing native membership-reference PG authority. It validates input owner conservation and performs exact Owner fact readback before embedding the authority in the candidate. The function is source code only in this batch; it was not run against live PG.
- For an exact-daily Head at its accepted T0, candidate display obtains its index entry and accepted input Head from the Head-bound PG authority. It no longer reads `data/v4/producer_candidate_index_v2.json` or the input-candidate JSON for that T0. Historical dates and non-exact daily Heads retain their existing file-backed chain and remain open migration work.
- Exact-daily research sidecar documents continue to load through `read_research` from the same authority. Frozen computation dependencies must be present at the exact bound source path; missing bytes fail closed rather than loading a historical evidence archive.
- Added a regression test that deletes the exact-daily local index and input-candidate JSON before display and still verifies the PG-backed candidate result. Test fixtures replace PG boundaries, so the suite performs no actual PG write. The PG-only path applies to the latest accepted T0; historical candidate entries are not included in the 7 path count.
- Updated seven exact source-read rows in the original matrix; no baseline rows were added or removed.

## Verification and limits

- Focused membership-reference/candidate-read tests: **10 passed**. Tests verify authority scopes and PG payload boundaries using controlled fakes; they do not prove a live database write or business acceptance.
- No PG write/readback, schema migration, service startup, accepted Head update, provider capture, or live business acceptance occurred.
- R54 commit `00989c566` has both repository-policy CI runs green.

## Accounting

Original P1 denominator remains **266**: 200 Owner, 28 other-business, 38 external-source reads. Formally complete **0/266**; formally remaining **266/266**. The matrix now records **46** code-level PG paths pending live readback and inventory reconciliation, **212 OPEN** rows, **8 ACTIVE_INGRESS_ADAPTER_OPEN** rows, and **22** reference edges without exact callsite mapping. Implemented code paths remain open formal items until Head/T0, compliant Reader identity, same-T0 PG readback and inventory reconciliation are accepted.

## Next stage

Continue actual migrations for exact-mapped daily and Owner consumers, including remaining Head, Authority, descriptor, daily and BFF dependencies. Continue DM-01 PostgreSQL state work without waiting for live write permission.
