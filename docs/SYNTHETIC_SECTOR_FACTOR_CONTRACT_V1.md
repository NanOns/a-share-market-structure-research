# Synthetic Sector Factor Contract V1

Version: sector-factor-contract-v1.1-correctness

Current snapshot only; source date is the Phase1 cutoff. No historical membership backfill, future factor rows, external data, index OHLC, composite score or scanner label.
Numeric finite values only; NULL never becomes zero. Quantiles use linear interpolation. Every numeric aggregate has __valid_count and __valid_ratio. Metadata fields describe date, version, identities, validity and provenance, are not ranked and have no numeric denominator.
Derived above_maN = aligned_close - MA_N with both inputs finite. Derived amount_ratio_5_20 = AMOUNT_MA5/AMOUNT_MA20, denominator>0, otherwise NULL. This is not Phase1 AMOUNT_RATIO20 (today/20D). amount_expansion = amount_ratio_5_20-1. Calendar: MASTER_TRADING_CALENDAR as inherited from Phase1; no new rolling-window calculation.

Membership basis=CURRENT_TDX_MEMBERSHIP, pit_membership=false, historical_backtest_safe=false. Reuse sector-role-v0.1 without alteration. total_member_count is all unique source member identities, including unresolved/non-A identities. Valid means current factor row with valid identity and a known latest normalized state other than FILE_MISSING or DELISTED_OR_INACTIVE. Per-factor denominator further excludes NULL. coverage=valid/total; tradable_coverage=tradable/total, never interchangeable. Factor valid ratio uses total source members, making poor coverage visible.
Validity: INDUSTRY>=5 total, THEME/STYLE>=8 total; valid>=5 and coverage>=0.70. Excluded theme roles remain visible but are never sector_valid or ranked. Invalid sectors retain descriptive raw aggregates, with sector_valid=false and reason; no formal percentile.
sector_rsN = median(valid member RET_N) - median(same-day NORMAL_UNIVERSE RET_N). Audit equivalence with median(member RS_N); unavailable benchmark yields NULL. Each RS count describes valid member returns.
TOP3_CONCENTRATION follows V0.3 section39, not the task's alternative amount suggestion: sum(top3 max(RET1,0))/sum(all max(RET1,0)); RET1=C_t/C_previous_master_session-1, both closes positive. Minimum8 finite RET1 members, zero positive sum -> NULL. No amount or market-cap substitution. Negative returns contribute zero to this explicitly defined positive-return sum, not to missing-value imputation.
Same-type percentiles: valid sectors with finite factor only; group sector_type; ascending=True, method=average, pct=True. Higher return/breadth/activity and less-negative MDD produce higher percentile. Tie denominator is finite valid sector count for that field/type, stored separately. EXCLUDE_FROM_THEME_RANK has no percentile. No threshold labels.


| Field | Input | Formula | Denominator | Null rule | Ranking |
|---|---|---|---|---|---|
| sector_ret5_median | RET5 | median of finite inputs | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_ret10_median | RET10 | median of finite inputs | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_ret20_median | RET20 | median of finite inputs | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_ret60_median | RET60 | median of finite inputs | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_breadth_ret5_pos | RET5 | positive of finite inputs (>0 count / valid count) | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_breadth_ret20_pos | RET20 | positive of finite inputs (>0 count / valid count) | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_breadth_ret60_pos | RET60 | positive of finite inputs (>0 count / valid count) | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_breadth_above_ma20 | above_ma20 | positive of finite inputs (>0 count / valid count) | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_trend_r2_20_median | TREND_R2_20 | median of finite inputs | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_mdd20_median | MDD20 | median of finite inputs | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_breadth_above_ma60 | above_ma60 | positive of finite inputs (>0 count / valid count) | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_trend_r2_60_median | TREND_R2_60 | median of finite inputs | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_mdd60_median | MDD60 | median of finite inputs | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_pos60_median | POS60 | median of finite inputs | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_ret20_mean | RET20 | mean of finite inputs | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_trend_slope20_median | TREND_SLOPE_20 | median of finite inputs | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_dist_high20_median | DIST_HIGH20 | median of finite inputs | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_trend_slope60_median | TREND_SLOPE_60 | median of finite inputs | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_dist_high60_median | DIST_HIGH60 | median of finite inputs | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_pos20_median | POS20 | median of finite inputs | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_pos120_median | POS120 | median of finite inputs | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_amount_ratio_median | amount_ratio_5_20 | median of finite inputs | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_amount_expansion_breadth | amount_expansion | positive of finite inputs (>0 count / valid count) | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_return_concentration20_median | RETURN_CONCENTRATION_20 | median of finite inputs | finite input count | empty -> NULL | only explicit same-type percentile fields |
| sector_rs5 | RET5, NORMAL_UNIVERSE | member median - market median | finite member returns | missing median -> NULL | RS20 only |
| sector_rs10 | RET10, NORMAL_UNIVERSE | member median - market median | finite member returns | missing median -> NULL | RS20 only |
| sector_rs20 | RET20, NORMAL_UNIVERSE | member median - market median | finite member returns | missing median -> NULL | RS20 only |
| sector_rs60 | RET60, NORMAL_UNIVERSE | member median - market median | finite member returns | missing median -> NULL | RS20 only |
| top3_concentration | positive RET1 | top3 sum / positive sum | positive sum; >=8 finite returns | zero sum or <8 -> NULL | none |
| sector_rs20_pct | sector_rs20 | average rank / count within type | valid finite sectors of same type | invalid -> NULL | ascending |
| sector_breadth20_pct | sector_breadth_ret20_pos | average rank / count within type | valid finite sectors of same type | invalid -> NULL | ascending |
| sector_mdd20_pct | sector_mdd20_median | average rank / count within type | valid finite sectors of same type | invalid -> NULL | ascending |
| sector_amount_ratio_pct | sector_amount_ratio_median | average rank / count within type | valid finite sectors of same type | invalid -> NULL | ascending |