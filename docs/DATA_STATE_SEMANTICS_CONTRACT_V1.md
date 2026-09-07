# Data State Semantics Contract V1

Version: `data-state-semantics-v1.0`  
Baseline: `V0.3_FINAL_IMPLEMENTATION_BASELINE`

## Missing-state values

| State | Meaning |
|---|---|
| `BAR` | An actual record exists in the local `.day` source for the date. |
| `CONFIRMED_SUSPENSION` | An audited local status source explicitly confirms suspension for the security/date. |
| `INFERRED_GAP` | The date is a market session inside the security's first/last bar interval, no local bar exists, and no audited local evidence confirms suspension. |
| `MISSING_DATA` | Expected data is unavailable but cannot be classified as an internal interval gap. |
| `NOT_LISTED_YET` | Date precedes the first local bar. |
| `DELISTED_OR_INACTIVE` | For a non-current member, date follows the last local bar. |
| `FILE_MISSING` | No local `.day` file is available. |

An internal gap is never proof of suspension.

## Confirmed suspension evidence

`CONFIRMED_SUSPENSION` requires a separately audited local status artifact that identifies both security and date. The normal production source set currently supplies no such reliable status feed, so production must use `INFERRED_GAP` unless an explicit audited evidence set is passed to normalization. Test fixtures may pass explicit dates to verify the contract; fixture evidence is not production evidence.

## Raw and derived fields

For `INFERRED_GAP`:

```text
raw_open/raw_high/raw_low/raw_close = NULL
raw_volume/raw_amount = NULL
adj_open/adj_high/adj_low/adj_close = NULL
aligned_close/aligned_volume/aligned_amount = NULL
is_synthetic_fill = FALSE
```

An inferred gap is not a confirmed flat price or a confirmed zero-volume/zero-amount observation.

For `CONFIRMED_SUSPENSION`, the compatibility normalization may carry the prior derived/reference close and use derived zero volume/amount. Raw OHLCV/amount remain `NULL`, `is_synthetic_fill=TRUE`, and the row remains visibly non-observed. Statistical treatment of inferred gaps is deferred to R2.

## Trade/data status separation

| Field | Meaning |
|---|---|
| `has_actual_bar` | Actual local `.day` record exists. |
| `data_observed` | Raw market-data record was observed locally. |
| `has_positive_amount` | Actual bar exists and its observed amount is positive. |
| `trade_status_known` | A reliable audited local trade-status source determines the status. |
| `tradable` | Compatibility field for the frozen Phase4 hard gate; currently equivalent to `has_actual_bar`, not proof of real-world executability. |

Having a bar does not establish legal/operational tradability. Without audited local status evidence, `trade_status_known=FALSE`.

## Compatibility and scope

R1 adds precise status fields without changing frozen Factor formulas, Scanner thresholds, Candidate logic or priority weights. Phase4's compatibility gate is not changed in R1. Any statistical decision about whether an `INFERRED_GAP` invalidates or permits a factor window belongs to R2.
