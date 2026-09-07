# Master Trading Calendar Contract

Version: `master-trading-calendar-v0.1`

## Local source and fields

The calendar uses the union of local `SH.000001` and `SZ.399001` date records plus current A-stock date evidence. Every civil date in the observed range is stored with:

```text
calendar_date
is_market_open
source_basis
confirmation_count
index_confirmation_count
confirming_indices
a_stock_confirmation_count
eligible_a_stock_count
a_stock_confirmation_ratio
```

A date is open when at least one primary index contains it, or when at least 20 locally eligible A stocks contain it and coverage is at least 50%. Index OHLC is not consumed; `INDEX_DATA_CONTRACT_PENDING=true`.

## Missing-state semantics

- `SUSPENDED`: a bar is absent inside a security's observed interval and a later local bar proves trading resumed.
- `MISSING_DATA`: evidence is absent or a current security has a trailing gap that cannot be proven to be suspension.
- `NOT_LISTED_YET`: calendar session precedes the first local bar.
- `DELISTED_OR_INACTIVE`: session follows the last bar for a security not in the current membership master.
- `FILE_MISSING`: the current master references a security but its daily file is absent.

Only `SUSPENDED` may receive a derived alignment fill: previous valid close, return 0, volume 0, amount 0, `is_synthetic_fill=true`, `tradable=false`. Raw bars are never changed. Other missing states are not synthetically filled.

## Window and Universe

The recent window is the latest 20 open master sessions. `NORMAL_UNIVERSE` requires at least 120 raw bars, latest-session raw bar present, and at least 75% raw-bar coverage in that window. Short proven suspensions do not automatically exclude a security if these requirements remain satisfied.

Future factors must declare `calendar_window` or `valid_bar_window`; formal trend defaults to aligned calendar windows.
