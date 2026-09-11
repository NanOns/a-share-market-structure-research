# Daily Operation Guide

## Normal daily run

After TongdaXin has finished downloading its local daily data, double-click:

`RUN_DAILY_SCANNER.cmd`

After the run finishes, double-click `OPEN_UNIFIED_WORKBENCH.cmd` to open the current Chinese V2 service workbench. `OPEN_RESEARCH_WORKBENCH.cmd` remains the legacy/static V1 report viewer and is not the V2 service entrypoint.

The launcher invokes the sole live entrypoint:

```powershell
E:\python\python.exe run_live_forward.py --date latest
```

The scanner resolves the latest valid cutoff from local TDX evidence. Do not replace `latest` with a fabricated or historical date.

## V1 and M1–M10 scope

`run_live_forward.py --date latest` is the V1 daily production entrypoint with the existing V2 shadow checks and static report publication. It currently runs the canonical V1 production stages and the registered shadow modules; it does not automatically invoke the separate M7–M10 reconstructed-preview builders.

Therefore, a successful V1 run must not be described as generating every M1–M10 artifact. M7–M10 preview data is only considered available when its versioned snapshot, date slices, basis metadata, and API checks are all present. The daily gate must stop with a nonzero `BLOCKED` result for `PARTIAL_UPDATE`, `INVALID_FUTURE_OUTLIER`, or `INPUT_NOT_READY`; do not publish a partial “today” result.

Before a live run, use the non-writing preflight:

```powershell
E:\python\python.exe .\run_daily.py --date latest --dry-run
```

Only `DRY_RUN_READY` indicates that the local TDX input is ready. `DRY_RUN_BLOCKED` preserves the prior release and identifies the input condition that must be corrected.

After V1 returns `PASS` and a new publication is current, generate the M7–M10 preview layers in dependency order. M7 is the history/semantic foundation consumed by the preview builders; the checked-in daily builders materialize M8/M9 first and then M10:

```powershell
E:\python\python.exe .\scripts\build_m8_m9_preview.py
E:\python\python.exe .\scripts\build_m10_mainline_preview.py
```

The first command creates or reuses the local reconstructed M8/M9 snapshot and binds it to the current publication. The second command creates or reuses the M10 mainline snapshot and binds it to the same publication. The optional amount-A audit report is generated with:

```powershell
E:\python\python.exe .\scripts\build_m10_amount_diff_preview.py
```

These preview builders use the current local publication and local parquet/TDX-derived artifacts; they do not accept an arbitrary target date and must not be run while the V1 readiness gate is blocked. Refreshing the V2 page is sufficient after the builders finish; no database-client session should hold the DuckDB writer lock.

The same entrypoint automatically refreshes the real Forward descriptive evaluation after sealed observations and due outcomes are processed. Its current pointer is `reports/forward_evaluation/CURRENT_FORWARD_EVALUATION.json`; no separate conversation or manual evaluation command is required. While samples are insufficient, the report shows accumulation progress and leaves return metrics empty.

## Result interpretation

- Exit code `0` with status `PASS`: a real new date or same-date source revision was processed and atomically published.
- Exit code `0` with status `VERIFIED_NO_NEW_FORWARD_OBSERVATION`: local TDX contains no accepted new trading date; the existing release remains current.
- Nonzero exit code with status `BLOCKED`: do not treat the day as published. Read the reported `stage` and `error`, and retain the prior current release.

Daily reports and immutable releases are written below `reports/`. Forward observations are written below `data/forward/`. The launcher never writes below `D:/new_tdx`.

## Command-line use

From PowerShell:

```powershell
Set-Location 'E:\codex work\大A交易'
E:\python\python.exe .\run_live_forward.py --date latest
```

Running the command again is supported. When there is no accepted new data, it performs verification and returns the currently published release rather than creating a false new release.

## Acceptance status

Current Phase 0 status is `FULL_PASS_TDX_NATIVE`; the approved integrated model identity is `cb3bdd356f01dfaad5990a393a44d10149cf81f9805c533219124d773aad8c94`. A live run remains subject to the local TDX readiness gate and must not be treated as published when that gate is blocked.
