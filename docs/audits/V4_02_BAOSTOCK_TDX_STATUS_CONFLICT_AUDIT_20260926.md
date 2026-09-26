# V4-02 BaoStock / TDX dated status discrepancy audit

- Audit ID: `V4-02-STATUS-CONFLICT-20240613-01`
- Status: `OPEN`
- Scope: provider `tradestatus` facts for four required-scope securities on 2024-06-13 where local source-selected TDX daily bars exist.
- Stage gate: tracked independently; local actual-bar status follows the V4-02 rule and remains `ACTUAL_TRADED`.

## Evidence

The dated-status build queried 982 gap-bearing securities once each through the anonymous BaoStock 0.9.3 route. The normalized status artifact records 88,011 provider status/ST facts across those query windows. Four dates conflict with local bar presence:

| Security | Date | BaoStock `tradestatus` | Local source record |
|---|---:|---:|---|
| SH.600647 | 2024-06-13 | 0 | Validated TDX daily OHLC, volume, amount |
| SH.600766 | 2024-06-13 | 0 | Validated TDX daily OHLC, volume, amount |
| SH.603133 | 2024-06-13 | 0 | Validated TDX daily OHLC, volume, amount |
| SZ.002087 | 2024-06-13 | 0 | Validated TDX daily OHLC, volume, amount |

The status artifact retains both the local `ACTUAL_TRADED` classification and the provider `provider_tradestatus` field for these rows. It does not overwrite the local bar or classify these dates as suspended. RAW source hash: `cdbc3e2b49bf16f59a6661d4641a3d9a3b498c5a9843974e934a7ab695f02313`. Dated-status artifact hash: `bb75f6cb9187616a272ff493b3fedfeaf9d0b2ac6c2a4aef4d3d74c550921119`.

## Acceptance

To close this audit, independently determine why the BaoStock field reports `0` on these four local actual-bar dates, verify the source field semantics for the affected records, and approve the precedence rule or any required correction. Until then, preserve the disagreement as a separate audit item. No broader status inference is made from these four rows.
