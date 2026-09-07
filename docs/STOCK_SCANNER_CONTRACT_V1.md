# Stock Scanner Contract V1

Contract `stock-scanner-contract-v1.0`; rules `stock-scanner-ruleset-v1.0`. Formulas are unchanged. SECTOR_LEADER requires a valid CURRENT_STRENGTH or REACCELERATION sector and member RS20 percentile >=.80. Within one date and the identical finite member set, RS20=RET20-market_median_ret20, so RS20 and RET20 ranks are identical; RET20 rank is redundant evidence and is not described as independent confirmation. POS60 remains audit context, not a required Leader confirmation. This simplification does not claim the V1 Leader definition is optimal.

Membership is current-only; `pit_membership=false`; `historical_backtest_safe=false`. Invalid, excluded, or DATA_INSUFFICIENT sectors cannot supply strong context. No score, dynamic threshold, candidate rating, trade signal, external data, index OHLC or historical membership backfill.
