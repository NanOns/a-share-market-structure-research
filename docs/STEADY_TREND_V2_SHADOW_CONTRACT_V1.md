# STEADY_TREND V2 Shadow Contract v1.0

Ruleset: `steady-trend-v2-shadow-v1.0`  
Status: shadow only; `production_eligible = FALSE`.

## Frozen semantics

`LIMIT_UP_IS_NOT_AN_EXCLUSION = TRUE`. No limit-up existence/count field is an exclusion, penalty, or class input. `LIMIT_UP_DAY_COUNT_20` remains `NOT_AVAILABLE`.

The candidate universe is the current normal universe, but a V2 hit requires `v1_steady_trend = TRUE`. V1 rules and outputs are immutable comparison inputs. The V2 classifier uses only the R3-00 `UP_DAY_RATIO20` diagnostic and the existing V1 `RETURN_CONCENTRATION_20` factor; it does not redefine either factor.

Continuity is `STRONG` at `UP_DAY_RATIO20 >= 0.60`, `MODERATE` at `[0.50, 0.60)`, and `WEAK` below `0.50`, provided `valid_count >= 15` and `valid_ratio >= 0.75`; otherwise it is data-insufficient. Missing/gap observations are not treated as zero-return days.

Pulse dependence is `LOW` at concentration `<= 0.35`, `MODERATE` at `(0.35, 0.50]`, and `HIGH` above `0.50`; null is data-insufficient.

For V1 steady hits: strong continuity plus low/moderate pulse is `STEADY_CORE`; moderate continuity plus low/moderate pulse is `STEADY_ACCEPTABLE`; high pulse is `PULSE_DOMINATED`; weak continuity with non-high pulse is `CONTINUITY_WEAK`; either insufficient evidence produces `DATA_INSUFFICIENT`. Only core and acceptable set `v2_steady_hit = TRUE`.

These fixed thresholds are diagnostic hypotheses, not fitted thresholds, rankings, scores, recommendations, probabilities, or forward-performance claims. Other V1 pattern flags are context only and never classification inputs. No network data, external adjustment, index OHLC, future data, automated trading, or backtest is used.
