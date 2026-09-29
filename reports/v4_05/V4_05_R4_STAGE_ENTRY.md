# V4-05 Replay Gate A R4 Stage Entry

- **Stage contract:** `V4_05_REPLAY_GATE_A_R4_CONTRACT_IDENTITY_REPAIR`
- **R3 reviewed baseline:** `9864939068a633e650de232f2f285681592a6528`
- **R4 implementation commit:** `0e5b7585c5bd1e332ce6d11c6dfd1e4ff6cb6108`
- **Target:** `2026-09-28`; formal publication `2026-09-29T06:53:52+00:00`
- **Result:** `DEGRADED_PASS_CURRENT_FORWARD_STOCK_CORE_CANDIDATE_R4`; independent external acceptance is `PENDING`.
- **Next stage:** independent external audit of R4.

## Frozen scope

The accepted Sep-28 official TDX package and Sep-26 frozen GBBQ identities are preserved. The R3 source/adjustment/factor main chain and 5,222 target identities were reused. Historical AS_RECORDED remains `BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`. R4 does not promote either V4-05 or global Accepted Head and does not authorize V4-06/07/08.

## Repairs and evidence

- PERIOD_ASOF_V1 temporal enums restored; adjustment quality remains field-local in `period_status`, with unavailable QFQ OHLC null. P01/P02/P03 regressions pass.
- V4-01 start-universe identities for horizons 1/3/5 use the accepted row provenance tuple. Sep-28 target snapshot has 5,222 date-qualified identities from the accepted V4-02 go-forward target candidate. Per-horizon adjustment-basis identities bind each evaluable endpoint to T0 coordinate, frozen GBBQ, and raw package. Independent reference recalculation matches all identities, returns, counts, and coverage.
- R3 path policy is `UNKNOWN_SUFFIX_UNTIL_NEW_SERIES_VERSION`; R4 selects Option C. The target path row is not published and `trend_axis=UNKNOWN`. A 25-session fixed-target-cohort diagnostic is recorded separately and does not rewrite accepted V4-03 rows.
- A temporary SQLite contract-equivalent ledger exercised identical replay, changed source append/explicit accept, conflicting payload rejection, and transaction rollback. All counts are observed from actual queries; the temporary database was removed.
- Fresh-clone LFS recovery proof will be attached after the pushed artifact commit.
- Independent numeric samples cover all four boards and normal-ready, no-T0, adjustment-unknown, short-history, confirmed code-change, and boundary-like return-tail classes. No exchange price-limit claim is inferred from the latter.
- R3→R4 profile row set is unchanged at 5,222; business-value drift is zero. Changes are source/output digest rebinds, 27 weekly and 27 monthly temporal-view lineage repairs, and corrected market identity with fail-closed trend.
- The specified regression suite reports 423 passed and 2 skipped, bound to the implementation commit above. Two full R4 builds produced identical SHA256 for period, target snapshot, references, full-scope factors, market regime, and Core Profile.

## Gate state

Capability matrix is scoped: current-forward adjusted price and Market Reference are `FULL_PASS`; period, factors, Market Regime, and current-forward stock Core Profile are `DEGRADED_PASS`; historical AS_RECORDED is `BLOCKED`. `DATA_FACTOR_REPLAY_PASS` is scoped to `CURRENT_FORWARD_STOCK_CORE` and remains `DEGRADED_PASS`. The R4 candidate is not externally accepted.

## Protected heads

The V4_STAGE, V4-01, V4-02, go-forward V4-02, amended V4-03, and V4-04 Accepted Heads were hash-checked and left unchanged. A V4-05 Accepted Head was absent and remains uncreated.
