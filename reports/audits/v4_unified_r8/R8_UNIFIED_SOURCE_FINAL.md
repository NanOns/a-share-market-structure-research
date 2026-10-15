# V4 R8 Unified Source Acceptance — Final

- Contract: `V4-R8-UNIFIED-SOURCE-REPAIR-20261015/R1`.
- Fixed branch: `codex/v4-unified-development`, created from R6 `e44a55609168344b820138efc01d53d76b7312df`; R7 source `bf285eef4a625daa2b0d0f147bd73fffbcb6710a` was integrated by scoped module/function changes.
- S4 code and isolated-PG evidence commit: `424486d87be5e5435afe0eb7fcf1101f55f4a1ea` (pushed). S5 final report and closeout note are committed on this branch; see containing commit in Git history.
- Read-only production checkpoints: the `127.0.0.1:28765` listener remained PID `48936`, executable `G:/codex work/大A交易_交付/windows_package_v1/versions/V4_PACKAGE_1.1.7_f3e4c68bc2d4/DaAV4/DaAV4.exe`; GET `/` returned 200. Accepted Head stayed at `2026-10-13`, SHA-256 `974c60e0095de0e37e2089edca710876d25f43de604fecafd115b675745375c3`. No package build, production write, Head change, or restart occurred.

## I-01–I-10 acceptance

| ID | Result | Evidence and limits |
|---|---|---|
| I-01 Unified branch | PASS | One fixed branch with R6 base provenance, R7 scoped migration, function-level preservation matrix, unique Forward route ownership, and pushed S0–S4 stage commits. Current branch contains the S5 closeout. |
| I-02 R6 preservation | PASS | R6 BFF/index, Sector Lifecycle, research priority, risk PG Owner, Focus/Market/Stocks and UI surfaces remain present. Targeted R6 risk/index and Forward e2e consumer checks passed; isolated risk Owner readback used the preserved R6 PG owner. No full browser re-scan was run. |
| I-03 R7 preservation | PASS | Forward statistics, cohort, observations, settlement and FEP handlers remain integrated. Targeted route/consumer tests passed; isolated PG readback returned source-backed observations, Lane data, settlements, paged totals and aggregate denominators. |
| I-04 New listing conservation | PASS | Real 2026-10-14 source replay returned 5,225 Core and Profile rows, each identity set equal to all 5,225 active lifecycle IDs, with 5,225/5,225 package coverage. `SZ.301660` is retained with `PARTIAL_UNKNOWN`/unknown history qualities; no raw source was edited. |
| I-05 Settlement states | PASS | Real accepted 10/08 H T+3 sample settled at -3.3632% nominal with denominator 1. Real 10/13 H T+1 remains `DUE_SOURCE_NOT_ACCEPTED` for 10/14; no false `NO_QUOTE`. An isolated accepted-source advancement vector appended settlement revision 2 and remained clearly fixture-only. |
| I-06 First-freeze clock | PASS | Separate source availability, Head acceptance, processing and frozen timestamps; synthetic tests cover after-close, before next-session open, late arrival and repeat idempotency. No real LIVE_OOS sample is claimed. |
| I-07 Ledger isolation | PASS | Disposable PG preserved exact hashes for seven seeded legacy dates; same T0 H/L observations and L revisions 1/2 coexist and read independently. Default read chooses latest revision. Lane L is only an isolated fixture. |
| I-08 Risk direction | PASS | Targeted direction vectors cover `NONE→WATCH`, `WATCH→WEAKENING` and first-observed denominators. R2 producer prepared/read back through the preserved R6 immutable PG Owner with matching payload SHA-256. Sector/market input gaps remain explicitly incomplete. |
| I-09 Execution efficiency | PASS | With 39,366 unrelated daily facts and 10,000 unrelated schedules in the disposable DB, date-scoped daily and settlement reads used `forward_facts_pkey` bitmap index scans, returning 2 and 1 rows; compact daily/settlement aggregate scans used the primary-key index. API readback confirmed universe total 2 with `limit=1`/`has_next=true`, settlement total 1 and denominator 1, seven dates and matured count 3. Timings are isolated-cluster measurements, not production latency claims. |
| I-10 No build or switch | PASS | Two read-only checks showed the same production process/package, successful root GET, accepted Head date and Head hash. No executable/package was produced; no production PG, Head, scheduler, TDX root or process was changed. |

## Current acceptance and future evidence

**`UNIFIED_SOURCE_ACCEPTANCE_PASS`** — all currently executable source, preservation, P0 repair, isolated-PG and targeted consumer checks in the task card passed. This status does not claim that future market sessions have occurred.

The accepted Head currently ends at 2026-10-13. A real 10/14 accepted source is not present, so 10/13 T+1 remains due-source-not-accepted. A true future `LIVE_OOS` observation and later horizon maturities remain `WAIT_FUTURE_REAL_SESSION`; this is the task card's allowed future-only limitation. The isolated Lane L records are engineering fixtures and must never be reported as out-of-sample results.

## Next single production-build entry

When the next build window is separately opened, build one candidate from the final `codex/v4-unified-development` SHA recorded in Git, verify it in isolation, and then use one planned production window for the single upgrade/restart check. This task did not run that build or switch production.

## Stage record

- Contract consulted: the R8 task card §5–§7 and `docs/upgrade/V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md`.
- Evidence: `CRITICAL_BUG_REPAIR_EVIDENCE.json`, `R6_R7_SOURCE_DIFF_AND_MERGE_MATRIX.md`, targeted test output (27 passed), syntax compilation, `git diff --check`, isolated PG/API readback and production read-only checkpoints.
- Acceptance: `UNIFIED_SOURCE_ACCEPTANCE_PASS`.
- Next stage: one same-SHA candidate build and isolated package proof in a separately authorized production window; no second source branch.
