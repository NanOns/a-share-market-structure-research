# V4 Functional R8 — third-batch scoped repair report

- Task card: `V4_FUNCTIONAL_R8_SECOND_BATCH_EXTERNAL_AUDIT_R1_NEXT_TASK_R3_20261021.md` (Google Drive ID `1dsUKoiv_8h0hMtlOerf2XLbZf2yMP54y`).
- Branch: `codex/v4-unified-development`; exact starting HEAD: `da2a026793ca28e996c0e05a90849aa798b3dd09`.
- Candidate: T0 `2026-10-14`, token `2e3a2dd57284e2f8566c265a7c1f112dbc50e7dab3a473f73873d9d02a88b0df`, NON_PIT. Formal Head readback remained `2026-10-09`.
- Contract sources read before implementation: R2 final repair plan, R8 unified source repair spec, runtime performance repair R1, increment identity parity amendment R1.1, exact daily continuation R1, and Phase 0 R5 receipt. Phase 0 inherited `DEGRADED_PASS`; this task did not invoke a scanner.
- Final status: **`THIRD_BATCH_CODE_PARTIAL / S02_PARTIAL / S04_PARTIAL / PERFORMANCE_PARTIAL / PG_OPEN / PRODUCTION_NOT_AUTHORIZED`**.
- Detailed machine evidence: [`THIRD_BATCH_EVIDENCE.json`](THIRD_BATCH_EVIDENCE.json).

## Scope and boundary

Work used the original `G:/codex work/大A交易` checkout on the designated development branch. The existing 28766 preview was restarted to load the branch code; the preview reused `127.0.0.1:5432/market_research` with `transaction_read_only=on`. At final readback, 28766 was listening, 28765 had no listener, and PostgreSQL remained on 5432. No DDL/DML, collector, scheduler, production Head, formal publication, deployment, or D2 producer was run. Candidate-derived snapshots were written atomically below the existing G-drive candidate root; no TDX source files were changed.

## Findings and results

| Area | Status | Result and remaining boundary |
|---|---|---|
| S02 width | `PARTIAL` | Added versioned side-by-side SIGN and positive-indicator results while retaining the existing positive-indicator candidate output. The current governing algorithm contract still does not rule the business meaning; the recommendation and alternative with observed value impact are recorded in `S02_BREADTH_SEMANTIC_ADJUDICATION_R1.md`. The record explicitly awaits a business ruling. |
| S02 trend | `PARTIAL` | Added a same-date reference adapter requiring close, MA20, MA20-minus-five, one series and price basis, source clock, cutoff, publication, time role, digest, and a structurally bound permission chain. The 10/12–14 candidate has no bound legal reference path, so those trend values remain `UNKNOWN`; no alternate index, equity breadth, or four-axis vote is substituted. Home now exposes `candidate_trend_review=UNKNOWN` and the UI uses it while preserving the recorded source value (`WEAK`) for inspection. Composite regime remains `UNKNOWN` / `NOT_PUBLISHED_V4_03`. |
| S04 D0 | `PARTIAL` | Seal state now derives from explicit availability time, knowledge cutoff, input publication, time role, source digest, and a permission-chain record tied to the source and publication. Existing 10/14 scenario evidence contains predicates and producer digest but no such seal chain; both `LAUNCH_CONFIRM` and `RECOVERY_TURN` report `HISTORICAL_SEAL_NOT_PROVEN`. Their predicate results remain candidate diagnostics. `STRONG_PULLBACK` and `TREND_CONTINUE` remain `DIAGNOSTIC_ONLY`, UNKNOWN for all 5,225 securities, and excluded from formal aggregation. |
| Priority cold path | `PARTIAL` | Added atomic content-addressed lifecycle and market-stress snapshots under the candidate root, bound to candidate metadata, exact source identity, producer SHA, and parameter SHA. Repeated persisted-cache cold requests fell from a cache-miss first build of 105.47 s to 11.63–11.96 s; three hot requests were 0.296–0.302 s. First build remains over the 20 s task-card limit, so this is not a complete first-ever-use fix. Projection/rank construction remains about 11.3–11.8 s and is the largest remaining persisted-cold stage. |
| S06-P | `PASS_ENGINEERING_VECTORS` | Added an executable offline G1–G4 comparator. The no-revision APPEND vector passes all four gates; revision and replay vectors fail closed. A candidate predecessor is explicitly NON_PIT and is never substituted for a formal accepted predecessor. These are engineering vectors, not a real APPEND or formal G2/G4 acceptance. |
| S07 research paths | `PASS_SCOPED_API_AND_UI_CONSUMER_WIRING` | Real 28766 readback covered explainable ranked candidates, excluded candidates with all available reasons, and D0/source-seal UNKNOWN. Home/market → sector → stock → Focus → Forward routes returned the same candidate T0; denominators remained 400 sectors, 5,225 stocks, and 3,247 Focus rows. Full S07 and production acceptance remain open. |
| S05-D / S05-I | `OPEN` / `NOT_IMPLEMENTED` | No D2 threshold generation or producer was implemented. The 875 historical episodes are not backfilled. |

### Breadth semantics proposal

The versioned proposal recommends keeping `I(r>0)` as the candidate breadth definition because it measures change in advancing share and matches the current producer; SIGN remains a separate diagnostic sensitivity series. It does **not** claim the business owner has ruled. With the existing ±0.05 threshold, candidate inputs produce:

| T0 | Evaluable / 5,224 | SIGN | Positive indicator | SIGN minus positive | Classes |
|---|---:|---:|---:|---:|---|
| 2026-10-12 | 5,204 | -0.491929 | -0.237317 | -0.254612 | both DETERIORATING |
| 2026-10-13 | 5,206 | +0.451978 | +0.221667 | +0.230311 | both IMPROVING |
| 2026-10-14 | 5,206 | -0.802920 | -0.398579 | -0.404341 | both DETERIORATING |

Matching class labels do not make the values interchangeable. These historical candidate rows remain NON_PIT.

### Actual 28766 path evidence

- `/api/v4/home`: HTTP 200, T0 `2026-10-14`, formal Head `2026-10-09`; recorded trend `WEAK` is preserved, candidate trend review is `UNKNOWN` / `TREND_REFERENCE_NOT_BOUND`, composite is `UNKNOWN`, and publication remains `FACT_AXES_OBSERVED_COMPOSITE_UNACCEPTED`.
- `/api/v4/radar/priority` (stocks): HTTP 200, 5,225 total = 967 rankable + 4,258 excluded. The exclusion path returned primary and overlapping reasons (example: `RELATIVE_STRENGTH_NOT_IMPROVING` and `FIVE_SESSION_RETURN_NOT_POSITIVE`). Sector scope returned 400 total = 141 rankable + 259 excluded.
- `/api/v4/focus`: HTTP 200, 3,247 Focus rows; D0 attribution covered all 5,225 securities. Overall D0 was TRUE 145 / UNKNOWN 5,080; LAUNCH_CONFIRM FALSE 5,055 / TRUE 118 / UNKNOWN 52; RECOVERY_TURN FALSE 5,138 / TRUE 35 / UNKNOWN 52. Both candidate scenario seals are `HISTORICAL_SEAL_NOT_PROVEN`; diagnostic scenarios are UNKNOWN 5,225 each.
- `/api/v4/forward/statistics`: HTTP 200. No new future outcome was manufactured; the capture plan remains `WAIT_SOURCE_READY`.
- Negative controls: stale context returned HTTP 409; page limit 201 returned HTTP 400. Candidate responses kept `production_accepted=false` and `formal_head_modified=false`.
- Priority transport reported `Server-Timing: response_encode;dur=0.374` ms on the final read. Full external request wall time includes query, construction, encoding, and transfer.

### Priority timing

Same branch source, candidate T0/token, stock scope, page and summary SHA (`25ce170665429175757f3b1f377d4b43da9985d73973bb3d0e1d85fb97eecbba`):

| Run | Cache state | API wall ms | Stage timings ms (index / lifecycle / source SHA / projection+rank / market stress / digest+page) |
|---|---|---:|---|
| First snapshot generation | Market snapshot miss | 105,472.64 | 1.687 / 41.212 / 56.731 / 11,561.786 / 93,627.670 / 22.246 |
| Persisted-cache cold 1 | New process | 11,746.55 | 0.548 / 44.618 / 53.126 / 11,354.838 / 66.987 / 16.641 |
| Persisted-cache cold 2 | New process | 11,963.76 | 1.824 / 40.994 / 52.232 / 11,614.074 / 54.530 / 16.876 |
| Persisted-cache cold 3 | New process | 11,633.49 | 1.795 / 41.412 / 54.049 / 11,307.922 / 52.971 / 16.517 |
| Persisted-cache hot 1 | Same process as cold 1 | 296.73 | 0.077 / 24.370 / 52.176 / 0 / 51.101 / 16.570 |
| Persisted-cache hot 2 | Same process as cold 2 | 302.34 | 0.074 / 24.080 / 54.857 / 0 / 50.923 / 17.641 |
| Persisted-cache hot 3 | Same process as cold 3 | 295.58 | 0.092 / 22.973 / 52.496 / 0 / 51.485 / 16.890 |

The server starts and passes readiness before the measured request; startup/source-wait was not included in the API wall figure. Source-byte verification remains about 52–55 ms. On the cold ranking request, projection and ranking remain about 11.3 s. Cache identity changed when the trend adapter source changed; the older snapshot was not reused.

## Tests and engineering vectors

- Targeted command: `python -m pytest tests/test_v4_functional_r8_third_batch.py tests/test_v4_functional_r8_s01_s03.py tests/test_v4_r6_risk_priority.py -q --basetemp=G:\codex_tmp\test_temp\third_batch` — **44 passed**.
- `py_compile` passed for the changed Python modules; `node --check src/workbench_service/static/core-product-r1/app.js` passed; `git diff --check` passed.
- G1–G4 offline vector: no-revision APPEND `PASS` across G1/G2/G3/G4; revision detected `FAIL_CLOSED` with `REVISION_REQUIRES_RANGE_REPAIR`; multi-session replay rejected with `G4_APPEND_SCOPE_INVALID`. All vector results say `writes_performed=false`, `head_modified=false`, and `production_admission=false`.
- No GitHub CI run or external acceptance is claimed.

## Next stage

Obtain the business ruling for breadth semantics and a legal same-series trend reference for future T0s; connect real source-clock/publication/permission facts at the S04 upstream producer. Further reduce the remaining ~11.3 s projection/rank stage and keep first snapshot-generation cost visible. Keep formal/candidate PG operations, D2 threshold production, accepted Head/CAS, 28765, and production release outside this task until separately authorized. S06-P is executable for candidate offline vectors; it does not authorize PG writes or a real append.

## Commit and push receipt

- Starting HEAD: `da2a026793ca28e996c0e05a90849aa798b3dd09`.
- Implementation commit: `bd010445476a6cfb1fec25de6cf4b6121ee699c1` (`Implement scoped R8 third batch repairs`).
- Unrelated pre-existing `.githooks/`, `config_back/`, and `script_back/` workspace items were preserved and excluded from the commit.
- Push is recorded after delivery; it is a code delivery receipt only. Independent external review remains pending.
