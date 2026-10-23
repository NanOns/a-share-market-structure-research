# BATCH10-R4 Full Module Closeout Report

- Task: `BATCH10_R4_FORWARD_AND_FULL_MODULE_FUNCTIONAL_CLOSEOUT`
- Date: 2026-10-23 (Asia/Shanghai)
- Branch: `codex/v4-unified-development`; baseline `78ab4c898096c71a093b288258909e81f4ba5732` was checked against the remote before execution.
- Final disposition: **PARTIAL**. R4-A and R4-B passed for candidate lineage and retrospective accounting. Lane L conservation is repaired and PG-fixture verified; live first capture remains clock-gated. Six entry pages and chart integration work for the exact candidate, but market four-axis and several focus/forward subroutes lack exact Owner bindings. R4-E fault/performance coverage is incomplete.

## Contract, evidence, and decision

The latest applicable R4 upgrade/Forward contracts and Phase 0 result (`DEGRADED_PASS`) were checked before execution. Candidate Owner/read-index preparation used the existing development PG `127.0.0.1:5432/market_research`; the lifecycle fixture was a session-local TEMP table. Preview used only `127.0.0.1:28766`. Production `28765`, formal Head and production scheduling were not changed. Lane H remains `RETROSPECTIVE_RESEARCH`, `AS_RECORDED=false`, `PIT_ELIGIBLE=false`.

| Gate | Status | Evidence / decision | Next stage |
|---|---|---|---|
| FR8-R4-01 lineage | **PASS** | 10/19 semantic diff identified; 10/20 rebound to revised predecessor; full 10/21 replay, Owner readback and period oracle passed. | Independent review; no formal admission. |
| FR8-R4-02 Lane H | **PASS for historical NON_PIT accounting** | 13 daily bundles, 13 settlement bundles, 13 indexes, 39 settlement aggregates; no duplicate collapse or late rows. | Preserve retrospective scope; no return/win-rate interpretation. |
| FR8-R4-03 Lane L | **PASS with real-clock wait** | Identity conservation code and PG fixture pass; no actual bar invented. | Wait for genuine T0 first capture; do not backfill 10/22. |
| FR8-R4-04 six-entry integration | **PARTIAL** | All six pages render candidate data; stock search, pagination, detail and charts link correctly. Market four-axis and exact Owner-backed focus/forward subroutes fail closed. | Bind exact candidate Owners and test route/filter/export equality. |
| FR8-R4-05 incremental/fault/performance | **PARTIAL** | Streaming replay, 610,000 oracle checks and atomic-writer failure test pass. Invalidation, outage/LAST_GOOD and P95 remain untested. | Complete bounded fault and load drills with available source. |

The `BATCH10_R4_DEV_FUNCTIONAL_SCOPED_PASS_WITH_LIVE_WAIT` gate is **not met** because R4-D is partial and R4-E lacks required fault/performance evidence. This is candidate readiness evidence, not external acceptance or production approval.

## R4-A — 10/19 revision and downstream lineage

Old 10/19 token `f9c4fa37dcef3cb4d28cf2a4e6e41f448898947be9fb16240f67cfd8ee136862`; revised token `daeb6ed118605b9e1e0ed057e95ca6b84a6f2e4c25154bb71fbc70f42268a0ac`. RAW and QFQ each contain 5,213 rows, identical hashes and identity sets. Core has 5,224 rows on both; only `rps5_delta3` (79 identities) and `rps20_delta3` (72) differ. Base Profile and Profile derived values are unchanged. Prewatch signals/state are equal; confirmation changes for 5,224 identities and target values for 79. The candidates are not business-equivalent, so the downstream chain was rebuilt.

The 10/20 candidate now binds to revised 10/19 and has token `a5b169a8cde60cc6ba86f1efbb7714020e578264bfea33634532ab407df70b70`. Development Owner preparation read back all payloads (20 created, 208 reused), `FULL_OWNER_PAYLOAD_READBACK_ONLY`, publication false. The full 10/21 candidate token is `14ee0cf87a46f810b52295a8d42c4bbda391fd0fe49f4cb3457a1620067ad378`; Owner preparation read back all payloads (20 created, 228 reused), also without publication. 10/21 produced 5,224 Core/Profile rows, 5,216 RAW rows, 400 sectors, 5,133 sector facts and 3,975 focus rows. Period oracle checked 5,000 securities × 122 periods = 610,000 comparisons, with zero differences. The normalized predecessor pointer's content-addressed path has bytes/SHA matching the rebound 10/20 parent. `AS_RECORDED=false`, `PIT_ELIGIBLE=false`; formal Head unchanged.

The 10/20 Core/Profile difference remains explained: Core has 5,226 IDs and Profile 5,224. Core-only IDs are `SEC-11E54DE9C2693CFA40A4C091BCD5ABF9` (`SH.601059`) and `SEC-6054AE867A60481EDA16B0E02AF1DB09` (`SH.601198`). Source readiness marks both absent; that is not delisting evidence. Core identities remain preserved; no Profile history was fabricated.

## R4-B — Forward Lane H source, uniqueness, and settlement

Development schema `v4_r8_forward_0c2b84fb3e1a0c42` has 13 daily bundles and 73,115 logical history rows from 2026-09-28 through 2026-10-21. Per day, `MATCH + NO_MATCH + UNKNOWN` equals the row count; each date has one non-empty source SHA; rule contracts `SECTOR_STRENGTH_TRANSITION_R1` and `STOCK_RIGHT_STRUCTURE_EVENT_R1` are version `1.0.0`; `late=0`; latest-revision uniqueness collapses zero duplicates. Publication generations 1–13 are date ordered. Settlement has 13 bundles, 13 aggregate records and 39 T+1/T+3/T+5 aggregates; `FACT_ERRORS=[]`. `SOURCE_GAP`, `SUSPENDED`, `DUE_SOURCE_NOT_ACCEPTED`, `PENDING_FUTURE_SESSION` and `SETTLED` stay distinct. 10/21 T+1 is `DUE_SOURCE_NOT_ACCEPTED`, not an assumed settlement. The 3,260 UI aggregate is settled observations, not a performance claim. The evidence JSON includes per-date counts, hashes, indexes and the settlement matrix.

## R4-C — Lane L lifecycle conservation repair

The defect occurred because status rows were emitted only while iterating Core/Profile factor identities. A source-active identity without factor/history could be omitted and violate owner conservation. The converter now adds every source-active ID with lifecycle-derived status; unsupported statuses become `UNKNOWN`; only `ACTUAL_TRADED` sets `actual_bar_present=true`; duplicate, empty, or date-mismatched identities fail closed. History/Profile stages stream output rather than retaining the full large history payload.

For the rebuilt 2026-10-21 source, lifecycle/status/profile/Core each contain 5,224 rows, RAW 5,216, and lifecycle/status identity sets match. A PG TEMP fixture inserted the 5,224 actual projections plus one synthetic lifecycle-only `DATA_GAP` row. Readback returned 5,225 rows and IDs, zero false actual-bar claims; the synthetic row remained `DATA_GAP` with Core/Profile/RAW absent. The temp table is `ON COMMIT DROP`. This verifies converter and PG persistence shape, not a new LIVE_OOS capture. Operational state remains `WAIT_REAL_FIRST_CAPTURE`; no 10/22 event was backfilled.

## R4-D — six entry pages and actual research data

The exact 10/21 candidate was served on `127.0.0.1:28766`. Home showed 5,224 stocks, 400 sectors, 413 explicitly non-formal Radar changes, 73,115 Forward history rows, and 3,260 settled observations. All six routes—Home, Market, Sectors, Stocks, Focus and Forward—rendered candidate context and date selection. Sector list/detail loaded real objects with proxy/reconstructed provenance. Stocks returned 5,224 rows; search `三一重能` returned one result; offset 30 reached page 2; `三一重能 SH.688349` detail showed 10/21 facts. Focus loaded 3,975 reconstructed tracking rows and was not presented as a formal sample. Forward showed history and the first-capture wait.

After fixing the BFF constructor chart bindings, the stock detail displays the actual-trade candlestick, 10/21 close `13.58`, and candidate/non-PIT notice. Chart APIs return READY for D/W/M × RAW/QFQ (20 requested items; D=427, W=92, M=22; W/M tails are `FORMING_AS_OF`). Exact-candidate PG history index: 5,224 securities, 2,163,300 bars. Candidate R1/R2 read-index counts: 5,224 stocks, 400 sectors, 3,975 focus, and 413 Radar (R2).

Some capabilities remain unavailable because their exact Owners are not bound: market four-axis candidate binding is incomplete; Focus priority returns `NO_OPERATIONAL_FOCUS_SUBPAGE_OWNER`; Forward cohort returns `NO_AUTHORIZED_COHORT_OWNER`; settlement compatibility returns `NO_OPERATIONAL_COMPATIBILITY_OWNER_FOR_ROUTE`. Missing sector lifecycle/health fields remain UNKNOWN. No fallback date, formal regime or fabricated cohort was used. This keeps R4-D partial.

## R4-E — incremental, fault, and performance

The full 10/21 replay and 610,000 period checks pass. The gzip owner writer now streams deterministically to a same-parent temp file, fsyncs and atomically replaces only on success; a targeted failure test confirms an exception preserves the previous artifact and removes the temp. The 10/20 D0 baseline `141 TRUE / 5033 FALSE / 52 UNKNOWN` is retained from prior evidence, not recomputed from altered inputs. No 10/22 source was invented. Source replacement invalidation, PG/CAS outage and LAST_GOOD recovery, and API P95/load were not completed; R4-E remains partial.

## Verification and handoff

- Targeted tests: **14 passed** across BFF constructor bindings, atomic gzip streaming, R8 S2 repairs, lifecycle conservation, and RPS target-coordinate delta.
- `git diff --check`: passed before this documentation edit; rerun before commit. Full repository test suite/external CI not run.
- Runtime: dev UI `127.0.0.1:28766`; `28765` not used. Existing development PG `127.0.0.1:5432/market_research`; no permanent fixture objects. Formal Head and scheduler unchanged.
- Next: push this code/report/evidence for independent audit. Resolve missing exact Owner bindings and complete fault/load coverage before asking for scoped pass. Wait for a true first capture. Git push is not external acceptance.
