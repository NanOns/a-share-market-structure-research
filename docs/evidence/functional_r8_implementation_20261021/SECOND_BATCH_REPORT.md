# V4 Functional R8 R2 — second batch report

- Task card: Google Drive `V4_FUNCTIONAL_R8_FIRST_BATCH_EXTERNAL_AUDIT_R1_AND_NEXT_REPAIR_20261021.md` (ID `1jLImTygYqbg2TmJrAExmCN_g-x-GKTZD`, read 2026-10-21).
- Branch / audit baseline: `codex/v4-unified-development` at `f0731224e58dbf65c50b5eacdc259abf07d83788`.
- Candidate: T0 `2026-10-14`, token `2e3a2dd57284e2f8566c265a7c1f112dbc50e7dab3a473f73873d9d02a88b0df`, `NON_PIT`; formal Head date `2026-10-09`.
- Worktree: `G:/codex work/大A交易`. All temporary calculations and API evidence are under `G:/codex_tmp`.

## Stage status

| Item | Status | Result |
|---|---|---|
| FR8-EA-01 | `PASS` | Project cache now binds candidate revision/token/date/domain and rechecks exact source bytes before a warm return. Tests cover same-token revision and same-binding byte tamper. |
| FR8-EA-02 | `PASS` | Lifecycle and Focus reason caches verify their exact bounded source closure on every use, including prior sector/rotation, current prewatch/focus/forward, and prior focus. Checks hash bound files; warm reads do not decompress or rescan history. |
| FR8-EA-03 | `PASS_WITH_EXPLICIT_EXCLUSIONS` | Priority requires dated, quality-qualified lifecycle facts with producer provenance. Close/prior-low use the exact per-security QFQ coordinate; different basis digests remain unequal. 5,214/5,214 ready adjusted rows match core `price_basis_id`; 11 core rows have no adjusted row and remain unproven. |
| FR8-EA-04 | `PASS_WITH_COLD_PATH_LIMIT` | Independent breadth calculator and real 28766 cold/hot measurement completed. Warm Priority is cached; cold path remains dominated by the bounded 10/12–14 full-source calculation. |
| S02 | `PARTIAL` | Both width definitions are calculated independently for 10/12–14 and have the same class under ±0.05. Formula semantics are not resolved by the bound primitive contract. The bound reference path lacks 10/12–14 raw values, so trend is `UNKNOWN`; regime publication remains locked. |
| S04 | `PARTIAL` | Real D0 predicates and three-state counts are preserved. The required source availability/cutoff/permission seal is absent, so `LAUNCH_CONFIRM` and `RECOVERY_TURN` remain open candidate diagnostics; `STRONG_PULLBACK` and `TREND_CONTINUE` remain diagnostic-only and are excluded from formal aggregation. |

## Implementation

`core_product_bff_r1.py` uses a versioned project cache key and verifies source hashes before returning warm project data. Lifecycle verification hashes the five-session sector/rotation window. Focus reason verification hashes current prewatch, focus, and forward plus the previous session's focus Owner. The Priority verification closure covers the current core/adjusted/sector/rotation/focus/prewatch/forward Owners plus the five-session lifecycle inputs, deduplicating repeated paths. These checks verify bytes and SHA; they do not decompress or replay history on warm requests.

For price provenance, `close` is derived from the adjusted Owner's basis namespace plus its adjustment revision. `prior_low20` is sourced from the T0 core Owner and receives that row's exact `price_basis_id`. The product field-registry pass now preserves these exact IDs instead of replacing them with `TDX_NATIVE_AFFINE_QFQ_T0_COORDINATE`. Maturity and health require T0 quality and lifecycle producer/input digests; RS fields are date-qualified. No score weights or caps changed.

The D0 source audit adds `V4_D0_CANDIDATE_GOVERNANCE_AUDIT_R1`. It checks the bound Owner digest and producer output digest but does not equate a digest or `r3a_sealed` flag with a source seal. Availability time, cutoff and permission chain are separately marked unproven. D0 input predicates and stored states are unchanged.

S02 reports both definitions without silently selecting one: signed `SIGN(r)` in {-1,0,1} and positive indicator `I(r>0)` in {0,1}; zero returns map to 0 in both. The existing candidate primitive retains its source-recorded positive-indicator calculation for parity and exposes the signed alternative beside it. The candidate stress result reports `NOT_PUBLISHED_V4_03`; it grants no composite-regime or Priority permission.

## Independent numeric evidence

The independent calculator streamed the bound QFQ `history.jsonl.gz` and dated core Owners directly; it did not call `build_candidate_market_stress`, `market_axis_primitives`, or `market_trend_axis`. Per-session comparison set: 5,224 securities (SHA-256 `73224ab52ab1ea3af61ded163aa058e67b8be3ad0df42adb0fd3442436c694ab`). Missing/invalid return pairs were excluded; the comparison universe is the prior third-session core set. Results use the source parameter threshold ±0.05:

Frozen comparison population is the prior third-session core set intersected with the current T0 core set. Listings after the comparison date are outside that population; securities absent at T0 are outside the intersection. Each leg is one-session QFQ close return (`close_d / close_previous_session - 1`), with the second leg dated T0 minus three sessions. The denominator is pairs with both legs available, positive finite closes and valid QFQ bars; no rounding is applied before the mean. A zero return is retained and maps to 0 in both formula definitions. There are 20 and 18 missing/invalid pairs on the three dates as shown below; the source does not distinguish every suspended versus missing-bar cause.

| T0 | Compare date | Evaluable / 5,224 | SIGN mean / class | Positive-indicator mean / class | Difference | Zero current / comparison |
|---|---|---:|---|---|---:|---:|
| 2026-10-12 | 2026-09-30 | 5,204 | -0.491929 / DETERIORATING | -0.237317 / DETERIORATING | -0.254612 | 63 / 153 |
| 2026-10-13 | 2026-10-08 | 5,206 | 0.451978 / IMPROVING | 0.221667 / IMPROVING | 0.230311 | 154 / 109 |
| 2026-10-14 | 2026-10-09 | 5,206 | -0.802920 / DETERIORATING | -0.398579 / DETERIORATING | -0.404341 | 83 / 113 |

All three independent evaluable counts match the dated market Owners' `breadth_evaluable` (5,204 / 5,206 / 5,206), and both formulas produce the recorded class. The `MARKET_REGIME_V1_PRIMITIVES` contract specifies thresholds but not which zero-return formula governs this breadth input; no semantic ruling was found. The bound `V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R3` ends at 2026-09-24, so the required 10/12–14 index close/MA20/MA20-minus-five values cannot be recomputed from it. The stored Owner label `WEAK` is therefore retained only as source data, not as independently validated trend. Exact raw rows, counts, set/source hashes are in the compact evidence JSON.

The independent S03 basis comparison read 5,225 T0 core rows and 5,214 adjusted rows. All 5,214 adjusted rows marked `READY` have `adjusted.price_basis + ':' + adjusted.adjustment_source_revision == core.price_basis_id`; zero mismatches. The remaining 11 core rows have no adjusted row and cannot establish a current close coordinate. Targeted tests also cover missing close, invalid quality/date/range, NaN/Infinity/bool, changed basis IDs, and candidate owner tampering.

## Tests, API readback, and performance

- Targeted command: `python -m pytest tests/test_v4_functional_r8_s01_s03.py tests/test_v4_r6_risk_priority.py -q --basetemp=G:\codex_tmp\test_temp\pytest` — **38 passed**. `py_compile` passed for the four changed Python modules; `git diff --check` passed.
- Targeted command (final): `python -m pytest tests/test_v4_functional_r8_s01_s03.py tests/test_v4_r6_risk_priority.py -q --basetemp=G:\codex_tmp\test_temp\pytest` — **39 passed**. `py_compile` passed for the four changed Python modules; `git diff --check` passed.
- Candidate Priority route: `GET /api/v4/radar/priority?view=candidate` on 28766 returned `HTTP 200`, candidate-only, `production_accepted=false`, `formal_head_modified=false`. It reconciles 5,225 stocks as **967 rankable / 4,258 excluded** and 400 sectors as **141 rankable / 259 excluded**. These semantic counts match the first-batch independent census/reconciliation; the new independent source-basis check adds zero basis mismatches across 5,214 READY adjusted rows.
- Focus API readback: `HTTP 200`, 3,247 Focus rows; D0 output `READY`, source binding SHA verified. At T0 10/14: overall `TRUE=145`, `UNKNOWN=5,080`; `LAUNCH_CONFIRM` false/true/unknown = 5,055/118/52; `RECOVERY_TURN` = 5,138/35/52; both diagnostic scenarios remain UNKNOWN on 5,225 rows. Governance reports seal metadata missing for the two candidate scenarios.
- 28766 negative cases: missing token `409 CONTEXT_TOKEN_MISMATCH`; stale token `409 CONTEXT_TOKEN_MISMATCH`; page limit 201 `400 INVALID_QUERY_BOUND` (repeated against the final running code; final evidence records the measured response times). No 28765 request was made.
- Measured API timings (2026-10-21, local candidate; not an SLA): Candidate Priority **168,103.61 / 1,267.40 ms cold/warm** (stocks view, same token and first-page request); Focus cold read **4,154.53 ms**. The cold path computes the bounded three-session stress/breadth comparison and five-session lifecycle; the warm response rechecks bound bytes without replaying those calculations. The measured cold latency is 168.1 s and warm latency 1.27 s on this candidate run; the source-closure checks and cold calculation remain a performance limitation, not an SLA pass.
- PostgreSQL identity was `127.0.0.1:5432/market_research`. The pre-existing preview process initially had default `transaction_read_only=off`; no SQL writes were made. It was stopped and restarted for final verification with `PGOPTIONS=-c default_transaction_read_only=on`; a new session read back `transaction_read_only=on`. No DDL, DML, migration, task runner or collector was launched. The active web preview is 28766; 28765 has no listener.

## Authorization boundary

No D2 freeze threshold was implemented. No production PG write, formal Head change, release/tag change, production deployment or 28765 operation occurred. S02 formula adjudication, trend raw inputs and S04 source sealing remain open; these are reported as partial rather than promoted by tests or API `READY` status.

Compact numerical, API, D0 and source-binding evidence is `SECOND_BATCH_EVIDENCE.json`. Large candidate source artifacts remain in the existing G: candidate root and were not copied into the repository.
