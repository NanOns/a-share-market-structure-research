# SECTOR_LEADER V2 Shadow Contract v1.1

Ruleset: `sector-leader-v2-shadow-v1.1-quality-coverage`. Status: shadow only; `production_eligible = FALSE`.

Eligibility requires immutable V1 `SECTOR_LEADER = TRUE`. V1 sector strength and member RS20 qualification are reused. Member RET20 rank is redundant with member RS20 rank and is not an independent input. Membership count and qualifying-sector count are descriptive only and never increase a class.

R3-00's exact within-sector percentile implementation supplies four separate quality dimensions on one selected qualifying sector: higher trend R², MDD nearer zero, higher POS60, and lower return concentration receive higher percentiles. Each dimension requires at least five finite members and 70% member coverage; otherwise it is data-insufficient. Percentiles at least `0.75` are strong support, `[0.50, 0.75)` moderate, and below `0.50` weak. No score or weights exist.

INDUSTRY and THEME are `ECONOMIC_SECTOR`. STYLE classes EVENT, STATUS, and OTHER are `NON_PRICE_STYLE`; PRICE_BEHAVIOR is `PRICE_BEHAVIOR_STYLE`; unresolved style semantics are `UNKNOWN_STYLE`. `PRICE_BEHAVIOR_STYLE_IS_NOT_INDEPENDENT_SECTOR_EVIDENCE = TRUE`, but these memberships and V1 leaders are not deleted.

One V2 primary qualifying sector carries qualification, all four quality percentiles, their sample evidence, and display context. A relation with sufficient quality evidence is preferred before semantic and strength ordering, preventing an insufficient preferred sector from hiding another usable relation. Remaining selection order is economic, non-price style, unknown style, price-behavior style; then REACCELERATION before CURRENT_STRENGTH, sector RS20 percentile descending, member RS20 percentile descending, and sector ID ascending only as deterministic tie-break. Security ID is never a selection or class input.

Economic/non-price primaries with at least two strong and three nonweak supports are `LEADER_CORE`; at least one strong and two nonweak are `LEADER_SUPPORTED`; lesser support is `RETURN_LEADER_ONLY`. A price-behavior-only primary is `STYLE_SELF_REINFORCED`; unknown-only or missing quality is `DATA_INSUFFICIENT`. Only core and supported set the shadow hit.

No future/forward evidence, external/network data, index OHLC, backtest, probability, recommendation, automated trading, fitted threshold, V1 priority change, or production publication is permitted.
