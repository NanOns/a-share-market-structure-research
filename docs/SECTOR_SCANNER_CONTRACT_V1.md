# Formal Sector Scanner Contract V1

Contract `sector-scanner-contract-v1.2-evidence-binding`; rules `sector-scanner-ruleset-v1.2-evidence-binding`. Economic thresholds are unchanged. Scanner authorization additionally follows `sector-statistical-validity-v1.1-branch-bound`; cross-horizon breadth uses the common finite RET5/RET20 member set. Data insufficiency is distinct from a valid non-hit. Every alternative prior-damage or pullback branch must satisfy its own value condition, valid-member minimum, and coverage minimum; evidence from different branches cannot be combined to authorize a hit.

Input is one Phase 2 current snapshot bound by its receipt, generation, SHA-256 and cutoff. The market vector is attached as context only and never changes thresholds or hits. Membership is `CURRENT_TDX_MEMBERSHIP`; `pit_membership=false`; `historical_backtest_safe=false`. Historical and future snapshots are rejected. No external data or index OHLC is used.

The main Parquet contains all and only valid, allowed sectors. Every scanner first requires `sector_valid=true`, `coverage>=0.70`, `valid_member_count>=5`, and role other than `EXCLUDE_FROM_THEME_RANK`. A required NULL fails that condition; it is never treated as zero. Industry, theme, and style percentile ranks are calculated separately using finite, valid, allowed sectors with `pandas.rank(pct=True, method="average", ascending=True)`. Phase 3 derives RS5/RS60 percentiles from Phase 2 atomic RS5/RS60 and independently reproduces the published RS20 percentile.

## Rules

`CURRENT_STRENGTH` requires all: RET20 median > 0; same-type RS20 percentile >= .80; breadth RET20 positive >= .60; POS60 median >= .60; MDD20 median > -.15.

`STABILIZATION` requires all: .35 <= RS20 percentile < .75; RET5 median > 0; RS5 percentile >= .60; breadth RET5 positive >= .55; breadth5-breadth20 >= .10; amount ratio median >= .90; plus at least one prior-damage condition: RET20 median <= 0, MDD20 median <= -.08, or POS60 median < .50. It means current cross-horizon stabilization evidence, not confirmed reversal.

`REACCELERATION` requires all: RS60 percentile >= .65; RS20 percentile >= .70; RET20 and RET5 medians > 0; RS5 percentile >= .75; breadth RET5 positive >= .60; breadth5-breadth20 >= .08; amount ratio median >= 1; plus MDD20 <= -.03 or DIST_HIGH20 <= -.03. Its formal meaning is `CROSS_HORIZON_REACCELERATION_PATTERN`, not an observed PIT state transition.

Multiple hits are retained in `scanner_hits`. `primary_pattern` precedence is REACCELERATION, STABILIZATION, CURRENT_STRENGTH. A stabilization/current-strength overlap emits `RULE_OVERLAP_STABILIZATION_CURRENT_STRENGTH`; it is never silently removed.

## Tags and evidence

`LOW_COVERAGE` is `.70 <= coverage < .85`; coverage below .70 is invalid and absent from the main scanner output. `BREADTH_EXPANSION` requires breadth5 >= breadth20+.10 and breadth5 >= .55. `HIGH_CONCENTRATION` requires finite Phase 2 TOP3 concentration >= .60. Missing concentration gives false plus `concentration_tag_status=UNAVAILABLE`. The two warning tags do not veto hits.

The output retains the required atomic return, same-type percentile, breadth, position, distance-high, drawdown, amount-ratio, concentration and coverage values. It contains no score. `reason_codes` records passed conditions for hits and quality warnings; compact `failed_conditions` records failed conditions. Full condition values/operators/thresholds are stored in the audit artifact.

Display rank affects presentation only. Primary CURRENT_STRENGTH sorts RS20 percentile then breadth20 descending; STABILIZATION sorts RS5 percentile then breadth delta descending; REACCELERATION sorts RS5 then RS20 percentile descending. Sector type and ID are deterministic tie breakers. Main data retains every valid sector; CSV report is not Top-N filtered and remains split-ready by sector type.

Daily publication is append-only by cutoff. A rerun replaces only the same date after rebinding that date's Phase 2 snapshot. An existing future scanner snapshot blocks publication. Staging, validation, fsync, atomic replace and receipt-last apply. Consumers must validate output hash/generation against the receipt.
