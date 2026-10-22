# BATCH10-R4 Full Module Closeout Report

- Task: `BATCH10_R4_FORWARD_AND_FULL_MODULE_FUNCTIONAL_CLOSEOUT`
- Date: 2026-10-23 (Asia/Shanghai)
- Branch / baseline: `codex/v4-unified-development` / `78ab4c898096c71a093b288258909e81f4ba5732` (remote matched before work)
- Disposition: **`BATCH10_R4_NOT_CLOSED / FULL_V4_RESEARCH_CHAIN_NOT_ACCEPTED`**. Lane H historical data accounting is verified, and the Lane L producer/conversion fix has targeted tests. R4-A requires a real rebase because the 10/19 revision is materially different; the downstream rebase was not performed. Six-entry GUI linkage is partial because market and focus subviews fail closed or remain unavailable.

## Phase contract, evidence, and decision

Read the current R4.3 upgrade plan and the applicable Forward source and observation contracts before execution. The implementation scope stayed on the development branch, the candidate preview at `127.0.0.1:28766`, and read-only transactions against `127.0.0.1:5432/market_research`. `28765` and the formal Head were not changed. Historical Lane H remained `RETROSPECTIVE_RESEARCH` / NON_PIT.

| Gate | Status | Evidence / decision | Next stage |
|---|---|---|---|
| FR8-R4-01 predecessor lineage | **FAIL — REBASE_REQUIRED** | 10/19 raw and adjusted values are equal, but Core RPS5 delta3 differs for 79 identities, RPS20 delta3 for 72; prewatch confirmation changes for 5,224 and target values for 79. 10/20 `283fec…` still names old 10/19 `f9c4…` as predecessor; 10/21 `f8c…` descends from `283fec…`. | Rebuild only affected 10/19→10/20→10/21 candidates from revised predecessor; read back new candidate publications before any further new release. |
| FR8-R4-02 Lane H | **PASS — historical accounting scope** | 13 PG bundles, 73,115 logical rows; per-day counts and source SHA in evidence; 0 duplicate revisions collapsed; latest unique key and settlement latest key checked. 3,260 settled records are not a win-rate claim. | Keep retrospective NON_PIT; repair/read-check Focus settlement widget and compare filtered/export UI values to PG. |
| FR8-R4-03 Lane L | **PARTIAL — code fixed, real clock wait** | Root cause was status projection sourced only from Core/profile factor IDs, which omitted source-active identities without profile history. New helper appends lifecycle-only status rows with explicit status and no fabricated bars. Targeted regression 2/2 passed. No qualifying 10/22 first capture or PG fixture readback was established. | Replay frozen capture through owner pipeline with PG fixture/readback; only promote future T0 first capture when source-ready/available/accepted timestamps prove eligibility. |
| FR8-R4-04 six entry GUI | **PARTIAL** | Visible DOM confirms Home, Sectors, Stocks and Forward populate. Home reports 5,224 stocks, 400 sectors, 413 non-formal Radar events, 73,115 history and 3,260 settlements. Market endpoints reject `CANDIDATE_PRODUCT_HEAD_BINDING_MISMATCH`; sectors preserve lifecycle maturity/health as UNKNOWN; Focus settlement/FEP subviews report connection errors. | Fix candidate product/head binding and Focus section service, then test date switching, search, pagination, CSV, details, D/W/M, RAW/QFQ, D0/D2 and Priority explanations. |
| FR8-R4-05 incremental/failure/performance | **PARTIAL** | No 10/22 source was synthesized. Existing 10/20 D0 `141/5033/52` evidence and immutable owners were retained. Source replacement, CAS/PG failure, LAST_GOOD, and P95 load scenarios were not run. | Execute only after R4-A rebase, using available source, and collect latency and fault-recovery evidence. |

The task’s `BATCH10_R4_DEV_FUNCTIONAL_SCOPED_PASS_WITH_LIVE_WAIT` gate is **not met** because R4-A is not rebased and R4-D is not fully accepted.

## R4-A — 10/19 revision and downstream lineage

Candidate tokens: old `f9c4fa37dcef3cb4d28cf2a4e6e41f448898947be9fb16240f67cfd8ee136862`; revised `daeb6ed118605b9e1e0ed057e95ca6b84a6f2e4c25154bb71fbc70f42268a0ac`. Raw and QFQ artifacts each have 5,213 rows, identical numeric/basis fields and identical IDs. Core has 5,224 rows on both branches and the semantic Core change is limited to RPS5 delta3 (79 identities) and RPS20 delta3 (72). Base Profile/Profile derived values are unchanged. Prewatch `signals` and `prewatch` stay the same; `confirmation` changes on 5,224 objects and `target_values` on 79. Therefore the branches are **not business equivalent**.

Dev PG contains both 10/19 publications as candidate-only `DEV_ASOF_SOURCE_VERIFIED` records, each 5,224 rows; both have `AS_RECORDED=false`, `PIT_ELIGIBLE=false`, `production_admission=false`. 10/20 token `283fec0eacc4035237a60f2c8dea77586be09dafa4b1b4df072e02c765ab7562` declares predecessor `f9c4fa37…e136862`, and 10/21 token `f8c09d96…6430` descends from 283fec. The immutable predecessor and downstream artifacts were preserved; no rebase writes were made in this turn.

The 10/20 R3 Core has 5,226 IDs and Profile has 5,224. Exact Core-only IDs are `SEC-11E54DE9C2693CFA40A4C091BCD5ABF9` (`SH.601059`) and `SEC-6054AE867A60481EDA16B0E02AF1DB09` (`SH.601198`); Profile-only is empty. The frozen readiness marks both codes absent and explicitly says absence is not delisting evidence. This evidence is insufficient to claim they are searchable in UI; the visible search/API proof remains open.

## R4-B — Forward Lane H

The 13 daily PG publications sum to 73,115 logical rows. Each per-day `MATCH + NO_MATCH + UNKNOWN` equals its row count; all rows bind to one non-empty source SHA per date; `late=0`; rule/version/entity types are present; latest-revision dedup produces no duplicates; publication generations 1–13 are date ordered. The evidence JSON carries the full 13-day source/hash/count matrix, publish indexes, and T+1/T+3/T+5 settlements. `DUE_SOURCE_NOT_ACCEPTED`, `PENDING_FUTURE_SESSION`, `SOURCE_GAP`, and `SUSPENDED` stay distinct. The 10/21 T+1 cohort is `DUE_SOURCE_NOT_ACCEPTED` rather than settled without an accepted source. API Home/Forward totals match 73,115, and historical entitlement remains NON_PIT; the separate 3,260 aggregate means settled observations only.

## R4-C — Lane L lifecycle conservation

`operational_daily_owner_v1.seal()` compares `set(statuses)` from the Profile status artifact with `set(lifecycle.active_security_ids)` and rejects any mismatch. Before this repair, `r43_structure_replay.materialize_profiles_structure()` emitted status only while iterating Core factor identities. An active source identity lacking a Core/profile factor row was therefore omitted from the status projection and caused `SOURCE_EXECUTION_FULL_OWNER_LIFECYCLE_CONSERVATION_FAILED`. The converter now retains source-active identities as lifecycle-only status rows, uses the source lifecycle state, uses `UNKNOWN` for unsupported values, and never claims an actual bar unless the source status is `ACTUAL_TRADED`. Duplicate/empty identities and date mismatch fail closed. The bar-count check remains unchanged.

The focused regression passed 2/2: lifecycle-only identity preservation without fabricated bars, and duplicate identity fail-closed. The actual frozen capture was not end-to-end replayed into PG; no qualified T0 first capture was observed for 2026-10-22, so no LIVE_OOS claim is made. State is `CODE_FIXED_REAL_CLOCK_WAIT`, pending the task-required PG fixture/readback.

## R4-D — visible UI and source limitations

Visible browser DOM was read on the six routes at `http://127.0.0.1:28766/v4/research/{home,market,sectors,stocks,focus,forward}`. Home rendered its current 2026-10-21 context (token `f8c09d96…6430`), with 5,224 stocks, 400 sectors, 413 event changes explicitly labeled non-formal Radar, 73,115 historical Forward rows, and 3,260 settled observations. Sectors and Stocks show actual rows but preserve unavailable lifecycle/qualification fields as UNKNOWN. Focus exposes missing 10/22 T0 capture and keeps the historical candidate out of the formal queue.

Market breadth/index/limits requests return HTTP 400 `INVALID_OPERATIONAL_QUERY / CANDIDATE_PRODUCT_HEAD_BINDING_MISMATCH`; no other date was substituted. Focus settlement/FEP cards show service interruption. Forward displays historical total and `WAIT_REAL_FIRST_CAPTURE`; its list filters and 10/21 page count of 5,624 are visible, but the Home/Focus/Forward filtered list/export equality matrix was not fully exercised. These are function/data linkage failures, so this gate remains partial.

## R4-E — incremental, fault, and performance

No new 10/22 bar/source was fabricated and no existing historical owner was overwritten. Existing 10/20 D0 status counts `141 TRUE / 5033 FALSE / 52 UNKNOWN` remain covered by stored R3 evidence, not recalculated in this closeout. No source replacement invalidation, CAS/PG failure injection, LAST_GOOD recovery drill, or API load/P95 was performed; this gate is partial.

## Verification and handoff

- Targeted regression: 2 passed. `git diff --check`: pass.
- Full test suite and successful GitHub workflow: not run / not verified.
- Database: existing dev PG only; audit queries used read-only transactions; no DDL/DML issued.
- Runtime: dev preview at 28766; production port 28765 was not used.
- Next phase: perform the mandatory R4-A downstream rebase, then complete the missing PG fixture and six-entry interactions before considering a scoped development pass. No production Head, scheduler, driver, or 28765 action is authorized by this report.
