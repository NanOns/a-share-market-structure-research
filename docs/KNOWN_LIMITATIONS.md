# Known Limitations

Version: `known-limitations-v0.3`, frozen by Phase0.2C.

1. CROSS_VENDOR_QFQ_EXACT_EQUALITY_NOT_GUARANTEED = TRUE. Vendors may differ in historical corporate-action revisions, effective cash adjustment basis, stock-reform handling, rounding and anchor conventions. These are possible mechanisms, not a claim that every unresolved sample has a proven cause.
2. Deep historical corporate-action bases may diverge. SH.600519 in 2006 and SZ.000651 in 2000 are PROVIDER_BASIS_SENSITIVE_DEEP_HISTORY. They are not current production scanner blockers under this release. The old Gree sample has too little intraday price spread for reliable A/B separation; Eastmoney old Moutai has a multiplicative discrepancy still not uniquely attributed.
3. TDX-native adjustment is authoritative for this project: local .day + local gbbq + project affine contract + locked reference. Historical vendor differences never justify hardcoded B patches or source replacement.
4. Historical cross-provider backtests require separate HISTORICAL_ADJUSTMENT_GOVERNANCE and PROVIDER_BASIS_SENSITIVE = TRUE, especially horizons above 10/20 years, 1990s and stock reform history. No such backtest/governance implementation is included here.
5. Category 15 gbbq remains excluded from QFQ (91 retained records in the sealed input). Only category 1 has the released XRXD semantics.

Known examples (snapshot anchor 2026-09-04):

- SH.600519 2025-06-25: local B=-79.654; Tencent B=-79.581, Eastmoney B=-79.58. The 2025-06-26 Tencent effective cash adjustment is 276.00/10 versus local gbbq and Eastmoney dividend record 276.73/10. EXTERNAL_PROVIDER_EFFECTIVE_CASH_BASIS_DIFFERENCE explains Tencent's 0.073/share offset. The inferred 276.00 is not a claim about actual dividend paid.
- SZ.000651 2015-07-02: local A=0.5, Tencent A=0.5; local B=-25.480, Tencent B=-25.087. MULTIPLICATIVE_CHAIN_ALIGNED and CASH_ADJUSTMENT_HISTORY_DIVERGENT describe this snapshot. The remaining 0.393 offset was not uniquely assigned to a historical event.
- Local parameter rounding to 2 decimals follows the locked reference. Moutai's 2026 cash value 280.2423/10 becomes 280.24/10, a 0.00023/share precision difference. No algorithm patch is warranted by this fact alone.

Phase0.2B's scientific root cause remains ROOT_CAUSE_UNRESOLVED for the complete sample set. Phase0.2C changes production release authority, not the historical findings. Desktop UI equality remains unverified and is no longer a user manual prerequisite. Negative deep-history affine prices can occur; future factor contracts must define nonpositive denominator/log-price behavior rather than silently clipping or treating it as a decoder failure.

Inherited limits remain: current membership is not point-in-time history; index OHLC needs its separate contract. Source revisions require fresh input provenance and consistent factors at a shared cutoff; never mix rows from different QFQ anchors.
