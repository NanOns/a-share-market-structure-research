# Phase 0 data and factor contract

Version: `factor-contract-v0.3-phase0`

## Source and identity

- TDX is a read-only source.
- Security identity is `MARKET.CODE` (`SH`, `SZ`, or `BJ`).
- Current A-stock identity is primarily established from `tdxhy.cfg`, after explicitly removing the local Shanghai `900xxx` and Shenzhen `200xxx` B-share ranges; conservative code rules classify remaining daily files.
- `NORMAL_UNIVERSE` requires current `A_STOCK`, at least 120 records, and valid recent data.
- `expected_a_stock_count` includes every current A-share assignment even when its `.day` file is missing, so parse success is not circular.
- Current board membership is not point-in-time history. Historical replay must set `CURRENT_MEMBERSHIP_BIAS=true`.

## Daily record contract

The candidate record contract is little-endian `<IIIIIfII>`, 32 bytes:

```text
date, open, high, low, close, amount, volume, reserved
```

Date is an unsigned `YYYYMMDD` integer. OHLC values are stored as integers divided by 100. Amount is stored as float32 currency units and volume as uint32 shares for A stocks. The audit verifies these units across all usable A-stock records by checking that `amount / volume` is consistent with the stored daily low/high price interval (with a small tolerance). A direct UI comparison remains an additional manual acceptance check.

Every file is scanned for incomplete tails, invalid dates, duplicates, non-increasing dates, invalid OHLC relationships, non-finite/negative amount, and zero-price records.

## Window convention

`{t-N+1, ..., t}` explicitly includes date `t` and contains N observations.

- `MA_N` needs N valid prices.
- `RET_N(t) = Close(t) / Close(t-N) - 1` needs N+1 valid prices.
- `UP_DAY_RATIO_N` needs N comparisons and therefore N+1 valid prices.
- Missing history produces NULL; it is never filled or extrapolated.

## Price basis and dependencies

The Phase 0 executable price basis is `RAW`. Local `gbbq` is only an adjustment candidate until its binary format, date semantics, action coverage, OHLC rule, volume rule, and reproducibility are independently verified.

Every future factor/scanner must declare:

```text
requires_adjusted_price: true | false
```

While adjustment status is unverified, all multi-day price-structure results are `EXPERIMENTAL`.

## Frozen factor formulas

Each formula includes `t` unless explicitly stated.

```text
RET_N(t) = Close(t) / Close(t-N) - 1
MA_N(t) = mean(Close over {t-N+1, ..., t})
MA20_SLOPE_5D(t) = MA20(t) / MA20(t-5) - 1
POS_N(t) = (Close(t) - min(Low_N)) / (max(High_N) - min(Low_N))
DIST_HIGH_N(t) = Close(t) / max(High_N) - 1
MAX_DRAWDOWN_N(t) = min_j(Close(j) / max_{i<=j}(Close(i)) - 1)
UP_DAY_RATIO_N = positive close-to-close comparisons / N
VOLATILITY_N = sample_std(log_return_1d), ddof=1
TREND_SLOPE_N, TREND_R2_N = OLS(log(Close) ~ 0..N-1)
AMOUNT_RATIO20(t) = Amount(t) / mean(Amount over {t-19, ..., t})
RS_N(t) = RET_N(t) - median valid NORMAL_UNIVERSE RET_N(t)
RETURN_CONCENTRATION_20 = max positive 1d return / sum positive 1d returns
```

`POS_N` and `RETURN_CONCENTRATION_20` return NULL when their denominator is zero.

## Latest trade date

The scanner must not trust a simple maximum date. Phase 0 selects the latest date reached by at least 50% of expected A-stock files; if none exists, it uses the modal last date and reports the coverage failure. Index confirmation remains an additional acceptance check.
