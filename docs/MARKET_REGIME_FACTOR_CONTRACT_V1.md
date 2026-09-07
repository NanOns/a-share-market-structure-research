# Market Regime Factor Contract V1

Version: market-regime-factor-v1.0

Current snapshot only; source date is the Phase1 cutoff. No historical membership backfill, future factor rows, external data, index OHLC, composite score or scanner label.
Numeric finite values only; NULL never becomes zero. Quantiles use linear interpolation. Every numeric aggregate has __valid_count and __valid_ratio. Metadata fields describe date, version, identities, validity and provenance, are not ranked and have no numeric denominator.
Derived above_maN = aligned_close - MA_N with both inputs finite. Derived amount_ratio_5_20 = AMOUNT_MA5/AMOUNT_MA20, denominator>0, otherwise NULL. This is not Phase1 AMOUNT_RATIO20 (today/20D). amount_expansion = amount_ratio_5_20-1. Calendar: MASTER_TRADING_CALENDAR as inherited from Phase1; no new rolling-window calculation.

Membership/denominator: same-day NORMAL_UNIVERSE valid stock rows, then field-specific finite count. __valid_ratio divides by full NORMAL_UNIVERSE. No R2 threshold is invented; publish raw R2 medians and slope>0 breadth. RS quartiles describe dispersion, not a direction score. Amount means trading activity, never net inflow.

| Field | Input | Formula | Denominator | Null rule | Ranking |
|---|---|---|---|---|---|
| market_ret5_median | RET5 | median of finite inputs | finite input count | empty -> NULL | none |
| market_ret10_median | RET10 | median of finite inputs | finite input count | empty -> NULL | none |
| market_ret20_median | RET20 | median of finite inputs | finite input count | empty -> NULL | none |
| market_ret60_median | RET60 | median of finite inputs | finite input count | empty -> NULL | none |
| breadth_ret5_pos | RET5 | positive of finite inputs (>0 count / valid count) | finite input count | empty -> NULL | none |
| breadth_ret20_pos | RET20 | positive of finite inputs (>0 count / valid count) | finite input count | empty -> NULL | none |
| breadth_ret60_pos | RET60 | positive of finite inputs (>0 count / valid count) | finite input count | empty -> NULL | none |
| breadth_above_ma20 | above_ma20 | positive of finite inputs (>0 count / valid count) | finite input count | empty -> NULL | none |
| trend_r2_20_median | TREND_R2_20 | median of finite inputs | finite input count | empty -> NULL | none |
| mdd20_median | MDD20 | median of finite inputs | finite input count | empty -> NULL | none |
| breadth_above_ma60 | above_ma60 | positive of finite inputs (>0 count / valid count) | finite input count | empty -> NULL | none |
| trend_r2_60_median | TREND_R2_60 | median of finite inputs | finite input count | empty -> NULL | none |
| mdd60_median | MDD60 | median of finite inputs | finite input count | empty -> NULL | none |
| pos60_median | POS60 | median of finite inputs | finite input count | empty -> NULL | none |
| breadth_trend20_pos | TREND_SLOPE_20 | positive of finite inputs (>0 count / valid count) | finite input count | empty -> NULL | none |
| breadth_trend60_pos | TREND_SLOPE_60 | positive of finite inputs (>0 count / valid count) | finite input count | empty -> NULL | none |
| market_rs20_p75 | RS20 | p75 of finite inputs | finite input count | empty -> NULL | none |
| market_rs20_p25 | RS20 | p25 of finite inputs | finite input count | empty -> NULL | none |
| mdd20_p10 | MDD20 | p10 of finite inputs | finite input count | empty -> NULL | none |
| amount_ratio_5_20_median | amount_ratio_5_20 | median of finite inputs | finite input count | empty -> NULL | none |
| active_amount_expansion_ratio | amount_expansion | positive of finite inputs (>0 count / valid count) | finite input count | empty -> NULL | none |