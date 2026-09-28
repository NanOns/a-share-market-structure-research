# V4-03 Legacy factor difference register V1

Stage contract: V4.2.2 REV2 §10A0, §49A.1, §78, §87A; V4-00G window framework 1.1.0. Input: immutable `V4_DEV_BASELINE_HEAD`, cutoff 2026-09-24. This register precedes any legacy helper reuse. Reuse decision for every row is **NO**; V4-03 imports no `src/factors` module.

| factor_id | legacy formula / window / universe / missing rule / unit | REV2 formula / window / universe / missing rule / unit | reason |
|---|---|---|---|
| VOLATILITY20 → vol20 | Sample standard deviation, `ddof=1`; 21 aligned rows; current normal universe; synthetic suspension rows admitted; log return | Population standard deviation, `ddof=0`; 21 consecutive market-session closes; PIT historical evaluable universe; any suspension interval or missing session makes UNKNOWN; log return | Denominator and suspension rules differ. |
| RS_N → RPS5/20 | `RET_N - same-date median(RET_N)`; aligned session rows; current normal universe, minimum 100; ratio | Midrank percentile; fixed session endpoints; historical PIT evaluable universe, minimum 2; unknown members excluded with count retained; 0–100 points | Different statistic, denominator, universe and unit. |
| RS_N → rel_market_1/3/5 | Same legacy RS formula and window | `retN - MARKET_RELATIVE_REFERENCE_V1`; fixed session endpoints and start-date historical universe; UNKNOWN when reference coverage gate fails; return fraction | Market reference is independent from RPS. |
| MA_N | Mean aligned closes including synthetic suspension rows; current normal universe; aligned rows | Mean latest N verified actual bars including t; confirmed suspension skipped, unexplained gap UNKNOWN; price unit | Window and missing semantics differ. |
| TREND_SLOPE_N → slope20/60 | OLS slope of log close over N aligned rows; log price/session | Difference of MA20 over five actual-bar offset or MA60 over ten, divided by ATR20; technical actual-bar windows; dimensionless | Formula, offset and unit differ. |
| POS60 | `(C-min L)/(max H-min L)` on aligned rows; current normal universe; zero range flagged | Same ratio over 60 verified actual bars, no epsilon; zero range UNKNOWN | Formula resembles legacy, but window and quality differ. |
| AMOUNT_RATIO20 | Current amount divided by mean of 20 aligned rows including current; synthetic suspensions possible | Current raw CNY amount divided by mean of 20 prior actual bars strictly before t; zero/unknown denominator UNKNOWN | Current-bar denominator inclusion and window differ. |
| RET_N | Aligned close endpoint ratio; current normal universe, synthetic suspension possible | Fixed market-session endpoints without moving them; endpoint suspension/missing/identity unknown makes UNKNOWN; intermediate confirmed suspension annotated | Endpoint and universe semantics differ. |
| HHV/LLV/prior extrema | Legacy `DIST_HIGH` uses aligned maximum and no separate prior/current contracts | HHV/LLV include current actual bar; prior_high/low exclude current; technical actual-bar windows | No equivalent prior/current split. |

Evidence: `src/factors/engine.py`, `src/factors/registry.py`, `config/factors.yaml`, `docs/FACTOR_CONTRACT_V1.md`, and `docs/MARKET_REGIME_FACTOR_CONTRACT_V1.md` are legacy comparison sources only. They are not V4-03 machine contracts.

Acceptance result: **REGISTERED / REUSE_DENIED**. Next stage: field-level scope and window mapping audit, then independent per-algorithm contracts and vectors.
