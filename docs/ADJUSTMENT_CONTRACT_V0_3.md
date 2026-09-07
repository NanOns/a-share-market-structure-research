# Adjustment Contract V0.3

Contract: `adjustment-contract-v0.3`. Engine remains `tdx-affine-qfq-v0.2`; no algorithm change.
Phase0.2C supersedes the release restrictions in V0.2 and earlier phase documents. Those files remain historical evidence.

```text
identity = TDX_NATIVE_AFFINE_QFQ
adjustment_name = TDX_NATIVE_QFQ
raw_source = LOCAL_TDX_DAY
corporate_action_source = LOCAL_TDX_GBBQ
price_formula = A*RAW+B
project_price_basis = FORWARD_ADJUSTED
adjustment_status = VERIFIED_REPRODUCIBLE_TDX_NATIVE
amount_basis = RAW
volume_basis = RAW
external_vendor_exact_match_required = FALSE
formal_trend_scanners_allowed = TRUE
```

Authority order: LOCAL TDX .day; LOCAL TDX gbbq; project adjustment contract; locked reference implementation; external providers = VALIDATION_REFERENCE_ONLY. External data cannot overwrite either local source.

Reference: https://github.com/injoyai/tdx at `7ec113c38bf62e8d04aabd8be04df09b9c94ac65`, for decoder, XRXD semantics, affine formula and regression. TDX-native here names this project's local-source contract; it does not claim independently verified pixel-for-pixel agreement with every TDX client version.

Category 1 only: C1=cash dividend per 10 shares, C2=rights price, C3=bonus/transfer per 10, C4=rights ratio per 10. Normalize parameters to 2 decimal places as required by the locked reference. Category 15 (91 observed records) stays retained but excluded from QFQ; no unknown category enters the engine.

```text
m = (10 + bonus_transfer_per_10 + rights_ratio_per_10) / 10
c = (cash_dividend_per_10 - rights_ratio_per_10 * rights_price) / 10
ex_price = (RAW-c)/m
QFQ = A*RAW+B
latest local trade-date anchor: A=1, B=0
backwards over an effective event: A_new=A/m; B_new=B-A_new*c
```

For bar d, compose d < ex_day <= latest local trade date at the dataset cutoff; future ex-days are excluded. Include every event in suspension gaps even without an ex-day bar. OHLC share A/B and use ROUND_HALF_UP to CNY 0.01 after the affine transform. Volume and amount remain raw. HFQ derivation from V0.2 is unchanged but is not the released price basis.

Release requires verified local RAW, decoder, XRXD, reproducible affine engine, unchanged consumed inputs, and no proven local systematic bug. A vendor QFQ mismatch alone cannot block release. Invalid local structure/identity/date/nonfinite parameters still require investigation; the new governance does not waive local data quality.

Authorized production purpose: CURRENT_MARKET_STRUCTURE_SCANNING, windows 5D/10D/20D/60D/120D and necessary 250D. Factor names authorized for Phase 1: RET5/10/20/60, MA5/10/20/60, SLOPE, TREND_R2, POS20/60/120, DIST_HIGH20/60, MDD20/60, VOLATILITY, RS5/10/20/60, AMOUNT_MA, AMOUNT_RATIO, RETURN_CONCENTRATION. Each still requires its explicit versioned Factor Contract; this list implements no factors.

See KNOWN_LIMITATIONS.md and ADJUSTED_DATASET_CONTRACT_V0_3.md. Relative-strength index price inputs retain their separate pending index contract; release does not approve unvalidated index OHLC.
