# TDX Market Structure Scanner

Phase 0 implementation for auditing a local TongdaXin installation without modifying it.

Run:

```powershell
python run_phase0.py --tdx-root "D:\new_tdx"
```

The primary Phase 0 result is `reports/phase0/TDX_DATA_AUDIT.json`.

Phase 0.1:

```powershell
python run_phase0_1.py
```

Its final receipt is `reports/phase0_1/PHASE0_1_FINAL_RECEIPT.json`. The current status is `DEGRADED_PASS`; adjustment-dependent results remain experimental.

Phase 0.2:

```powershell
python run_phase0_2.py
```

The local GBBQ decoder and affine QFQ engine now pass automated local and reference-style validation. The consolidated audit handoff is `docs/PHASE0_2_REPORT.md`; status remains `DEGRADED_PASS` only because the five-row TongdaXin desktop QFQ check is still `NOT_CHECKED`.

Phase 0.2A supersedes that gate decision: `BLOCKED_FOR_FORMAL_ADJUSTMENT`.
Four fixed external QFQ samples differ beyond tolerance; the root cause remains
unresolved. The latest report is `docs/PHASE0_2A_REPORT.md`. Production remains
`LOCAL_TDX_ONLY` with `RAW` prices and formal scanners disabled. Existing
network evidence must not be overwritten. Re-seal the retained evidence offline:

```powershell
python scripts/seal_phase0_2a_offline.py
```
