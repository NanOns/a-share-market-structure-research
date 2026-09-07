# Adjusted Daily Dataset Contract V0.3

Version: `adjusted-daily-contract-v0.3`.
Phase 1 is authorized to generate `data/normalized/adjusted_daily.parquet` after a FULL_PASS_TDX_NATIVE release seal. Phase0.2C emits no adjusted dataset.

## Row schema

| Fields | Type / meaning |
|---|---|
| security_id | string MARKET.CODE |
| date | date32 trading date; unique with security_id |
| raw_open, raw_high, raw_low, raw_close | exact cent-valued local .day prices |
| adj_open, adj_high, adj_low, adj_close | decimal cent-valued ROUND_HALF_UP(A*RAW+B) |
| raw_volume | int64 raw shares, unchanged |
| raw_amount | float64 decoded local raw amount, unchanged |
| qfq_mul, qfq_add | decimal values, retained without cent-rounding; Phase1 physical schema must preserve the engine precision |
| price_basis | FORWARD_ADJUSTED |
| adjustment_status | VERIFIED_REPRODUCIBLE_TDX_NATIVE |
| adjustment_version | tdx-affine-qfq-v0.2 |
| tradable | bool; true on eligible real trading rows |
| is_synthetic_fill | bool; false for real .day rows |
| data_quality_flag | explicit string/enum, including original missing-state provenance |

Actual rows preserve raw inputs. No price interpolation, duplicate security/date, external-source replacement, amount adjustment or volume adjustment is allowed. A/B are calculated at a consistent snapshot cutoff, with category-1 effective events only. Data manifest must include cutoff/anchor dates, source hashes, contract version, adjustment identity TDX_NATIVE_AFFINE_QFQ and release seal provenance. If per-security latest bar differs, record it; do not silently mix anchors. Source updates require recomputing affected factors before publication.

PRICE = QFQ; VOLUME = RAW; AMOUNT = RAW. Persist the table atomically outside TDX. Permissions are separate from artifact existence: the release seal permits Phase1 creation but does not imply it already exists.

## Suspension alignment

Inherit MASTER_TRADING_CALENDAR (`master-trading-calendar-v0.1`) and the Phase0.1 NORMAL_UNIVERSE contract: minimum 120 raw bars, latest-session raw bar present, >=75% raw coverage over the latest 20 master sessions.

The normalized actual-bar table and the derived aligned view are distinct. Only a proven SUSPENDED state may create a synthetic aligned row:

```text
aligned_close = previous close (same QFQ snapshot basis)
aligned_return = 0
aligned_volume = 0
aligned_amount = 0
tradable = false
is_synthetic_fill = true
```

Never write these values into raw OHLC/volume/amount; on synthetic rows raw fields are null. Do not fabricate adj_open/high/low without a later explicit contract. MISSING_DATA, NOT_LISTED_YET, DELISTED_OR_INACTIVE and FILE_MISSING receive no suspension fill. Carry the state in data_quality_flag. These are analytical alignment semantics, not executable trades or future information for backtests.

Formal trend defaults to aligned calendar windows; each Phase1 factor must declare calendar_window or valid_bar_window and its treatment of synthetic rows, unavailable prices and nonpositive adjusted values. Release of adjusted prices does not invent factor formulas.
