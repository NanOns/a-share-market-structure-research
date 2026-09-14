# Adjustment Contract V0.1

Status: `SEMANTICS_UNVERIFIED`  
Executable project price basis: `RAW`  
Formal trend scanners allowed: `false`

## Local source

Only `D:/new_tdx/T0002/hq_cache/gbbq` and `gbbq.map` may provide event data. Record boundaries are structurally verified, but the payload remains encrypted/opaque. Unknown records are retained as `UNKNOWN_ACTION_TYPE`; none are silently ignored.

## Upstream source-code reference

- mootdx: `https://github.com/mootdx/mootdx` at `e99ae34382d970c68654c6d17c45512e728f130d`
- pytdx: `https://github.com/rainx/pytdx` at `14b1ad3534593952d1d698ffa706f4f13a4ed156`

The snapshots were explicitly user-authorized as source-code references only. They supply no external market data. Neither contains a local `gbbq` decoder. `mootdx/mootdx/tools/reversion.py` documents the per-10-share theoretical ex-price formula used below.

## Frozen mathematical candidate

For an event with cash dividend `D`, rights shares `R`, rights price `K`, and bonus/capitalization shares `S`, all quoted per 10 existing shares:

```text
price_mul = 10 / (10 + R + S)
price_add = (R*K - D) / (10 + R + S)
adjusted_price = price_mul * raw_price + price_add
```

The same positive affine transform applies to raw Open, High, Low, and Close for bars strictly before the event effective date. Multiple events compose in ascending effective-date order. This candidate is unit-tested but is not connected to local TDX records until `gbbq` event semantics are decoded.

## Operational rules

```text
price_basis = RAW
event_effective_date = apply event only to bars with date < effective_date
event_application_order = ascending effective_date
ohlc_adjustment_rule = same affine transform on OHLC
volume_adjustment_rule = KEEP_RAW_PENDING_LOCAL_UI_VERIFICATION
amount_basis = RAW_AMOUNT
missing_event_rule = mark adjustment incomplete; keep RAW; EXPERIMENTAL
unknown_event_rule = reject formal adjustment; keep record; EXPERIMENTAL
invalid_event_rule = reject affected security adjustment; preserve RAW
history_rebuild_rule = if gbbq or gbbq.map SHA-256 changes, rebuild all affected histories; while mapping is unknown rebuild all adjusted histories
price_abs_tolerance = 0.01
relative_tolerance = 0.0005
```

No `FORWARD_ADJUSTED` dataset may be emitted under this status.
