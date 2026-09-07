# BREAKOUT_PREP V2 Shadow Contract v1.0

Ruleset: `breakout-prep-v2-shadow-v1.0`. Status: shadow only; `production_eligible = FALSE`.

Eligibility requires immutable V1 `BREAKOUT_PREP = TRUE`, which retains the V1 near-high definition including `DIST_HIGH20 >= -0.05`. `DIST_HIGH20` is also the upper-bound/distance context; no duplicate high/close upper-bound metric is introduced. `LATE_EXTENSION_WARNING` remains context only and never cancels a V2 hit.

The classifier reuses R3-00 diagnostics unchanged. `recent_range_10` and `prior_range_10` are non-overlapping ten-valid-observation windows, each normalized as `(max(high)-min(low))/window-start close`; range is contracted only when their ratio is below `1.00`. Realized volatility uses two non-overlapping ten-log-return windows with `ddof=1` and is contracted only when its ratio is below `1.00`. Range and volatility remain separate evidence dimensions. Missing or invalid critical window inputs produce `DATA_INSUFFICIENT` and are never zero-filled.

Both contractions produce `BREAKOUT_CORE`; range-only produces `BREAKOUT_RANGE_ONLY`; volatility-only produces `BREAKOUT_VOL_ONLY`; neither produces `NEAR_HIGH_NO_CONTRACTION`. Only core and range-only set `v2_breakout_structure_hit = TRUE`, because a range contraction is the minimum shadow hypothesis for a breakout-preparation structure.

No stable `narrow_range_days` definition is introduced. Consolidation persistence remains descriptive through the fixed non-overlapping-window comparison and is not a separate gate. No score, fitted threshold, future confirmation, external/network data, index OHLC, backtest, forward outcome, recommendation, probability claim, automated trading, or production publication is permitted.
