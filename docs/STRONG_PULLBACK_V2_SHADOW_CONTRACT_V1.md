# STRONG_PULLBACK V2 Shadow Contract v1.1

Ruleset: `strong-pullback-v2-shadow-v1.1-latest-peak-exclusive-segments`. Status: shadow only; `production_eligible = FALSE`.

V2 classification eligibility requires the immutable V1 `STRONG_PULLBACK = TRUE`. The recent peak is the latest occurrence of the maximum adjusted close within the last 20 valid observations available at cutoff; future observations are prohibited. Peak date, depth, duration and amount segmentation use that same anchor. The advance segment includes the peak and requires at least two observations; the pullback segment starts after the peak and requires at least one. The peak amount is never counted twice.

Segment status is `NO_PULLBACK_SEGMENT` at zero days since peak, `EARLY_PULLBACK` at one day, and `ESTABLISHED_PULLBACK` at two or more days. Actual peak depth is in-band on `[-0.18, -0.03]`, too shallow above `-0.03`, and too deep below `-0.18`. Volume is contracted only when the reused ratio is below `1.00`; otherwise it is not contracted. Missing critical peak, duration, depth, advance amount, pullback amount, or ratio evidence is data-insufficient and is never zero-filled.

An established, in-band, contracted structure is `PULLBACK_CORE`; an established, in-band, non-contracted structure is `PULLBACK_STRUCTURE_ONLY`. The latter remains a structure hit: `VOLUME_NOT_CONTRACTED != BAD STOCK != AUTOMATIC EXCLUSION`. One-day in-band structures are `EARLY_PULLBACK`; actual depth outside the V1 band is `DEPTH_MISMATCH`; unreliable inputs are `DATA_INSUFFICIENT`. Only core and structure-only set `v2_pullback_structure_hit = TRUE`; only core confirms volume.

No composite score, fitted threshold, recommendation, probability, forward outcome, backtest, external/network data, index OHLC, automated trading, or production publication is permitted. STEADY_TREND V2 and other structures may be attached as context only and never participate in classification.
