# TDX Market Structure Scanner — implementation baseline

Adopted baseline: `TDX_Market_Structure_Scanner_V0.3_FINAL_Implementation_Baseline.md`, dated 2026-09-04.

The canonical design supplied by the user is located at:

```text
E:/codex work/大A交易/requirementTDX_Market_Structure_Scanner_V0.3_FINAL_Implementation_Baseline.md
```

This workspace implements Phase 0 through Phase 0.2C. The executable constraints are:

- local TongdaXin files are read-only inputs;
- the resolved source root is `D:/new_tdx`;
- no network or external adjustment source is permitted;
- Phase 0 output controls whether later scanners are formal or experimental;
- current sector membership is not point-in-time history;
- every artifact is written atomically outside the TDX root.

See `docs/DATA_FACTOR_SPEC.md`, `docs/ADJUSTMENT_CONTRACT_V0_3.md`, and `reports/phase0_2c/PHASE0_2C_RELEASE_SEAL.json` for the implemented contracts and current decision. Older phase receipts are historical evidence.

Phase 0.1 added the master trading calendar, recent-window Universe rule, minimal sector roles, and initial adjustment audit. Phase 0.2 independently implements the local GBBQ decoder and affine QFQ/HFQ engine and validates three complete local histories. Its historical final status was `DEGRADED_PASS` because the required TongdaXin desktop QFQ comparison is still pending; project price basis therefore remains `RAW` and formal trend scanners stay disabled.

Phase 0.2A temporarily permitted public QFQ data strictly as validation references.
Its historical gate superseded Phase 0.2: `BLOCKED_FOR_FORMAL_ADJUSTMENT`, due to four
fixed-point mismatches and incomplete retained batch evidence. The root cause
is unresolved; no formal factor/scanner phase is allowed. RAW and LOCAL_TDX_ONLY
remain in force. Request-limit and evidence-overwrite defects are disclosed in
the Phase 0.2A report and repaired in the validation layer.

## Current release status — Phase 0.2C

This section supersedes the historical RAW/manual-UI/external-exact-match release restrictions above and in earlier phase documents. Historical scientific findings remain unchanged. Production inputs remain LOCAL_TDX_ONLY; earlier authorized provider snapshots are validation references only.

```text
CURRENT_DATA_STATUS = TDX_NATIVE_ADJUSTMENT_RELEASED
PHASE_0_STATUS = FULL_PASS
PHASE_0_CLOSED = TRUE
ADJUSTMENT_IDENTITY = TDX_NATIVE_AFFINE_QFQ
PROJECT_PRICE_BASIS = FORWARD_ADJUSTED
ADJUSTMENT_STATUS = VERIFIED_REPRODUCIBLE_TDX_NATIVE
FORMAL_TREND_SCANNERS_ALLOWED = TRUE
NEXT_PHASE = PHASE_1_NORMALIZATION_AND_FORMAL_FACTOR_ENGINE
```

The current release authority is Phase0.2C, adjustment-contract-v0.3, adjusted-daily-contract-v0.3, and known-limitations-v0.3. Phase 1 may generate adjusted_daily.parquet and formal factors under their individual contracts. Neither data generation, factors nor scanners were implemented by this release seal. Cross-vendor QFQ discrepancies and provider-sensitive deep history are known limitations, not current production blockers.

## Current production status — Phase 1

PHASE1_STATUS = PASS
PROJECT_PRICE_BASIS = FORWARD_ADJUSTED
ADJUSTMENT_IDENTITY = TDX_NATIVE_AFFINE_QFQ
NORMAL_UNIVERSE_COUNT = 5461
NEXT_PHASE = PHASE_2_MARKET_REGIME_AND_SYNTHETIC_SECTOR_FACTOR

This current status supersedes the prior Phase0.2C next-phase pointer. See docs/PHASE1_REPORT.md and reports/phase1/PHASE1_FINAL_RECEIPT.json.

## Current production status — Phase 2

PHASE2_STATUS = PASS
SNAPSHOT_BASIS = CURRENT_SNAPSHOT_ONLY
SECTOR_MEMBERSHIP_BASIS = CURRENT_TDX_MEMBERSHIP
NEXT_PHASE = PHASE_3_SECTOR_SCANNER

This section supersedes earlier next-phase pointers. No Phase3 scanner is implemented.

## Current production status — Phase 3

PHASE3_STATUS = PASS
SCANNER_RULE_VERSION = sector-scanner-ruleset-v1.2-evidence-binding
SNAPSHOT_BASIS = CURRENT_SNAPSHOT_ONLY
SECTOR_MEMBERSHIP_BASIS = CURRENT_TDX_MEMBERSHIP
NEXT_PHASE = PHASE_4_FORMAL_STOCK_SCANNER

## Current production status — Phase 4

PHASE4_STATUS = PASS
RULE_VERSION = stock-scanner-ruleset-v1.0
NEXT_PHASE = PHASE_5_CANDIDATE_POOL_AND_RESEARCH_PRIORITY

## Current production status — Phase 5

PHASE5_STATUS = PASS
RULE_VERSION = research-priority-ruleset-v1.1-correctness
NEXT_PHASE = PHASE_6_DAILY_PRODUCTION_CLOSURE_REPORTING_SMOKE_TEST
