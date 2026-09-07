# Daily Operation Guide

## Normal daily run

After TongdaXin has finished downloading its local daily data, double-click:

`RUN_DAILY_SCANNER.cmd`

After the run finishes, double-click `OPEN_RESEARCH_WORKBENCH.cmd` to open the current Chinese V2 structure workbench.

The launcher invokes the sole live entrypoint:

```powershell
E:\python\python.exe run_live_forward.py --date latest
```

The scanner resolves the latest valid cutoff from local TDX evidence. Do not replace `latest` with a fabricated or historical date.

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

Current engineering status is `EXTERNAL_AUDIT_PASS / FORWARD_ENABLED`. The approved integrated model identity is `cb3bdd356f01dfaad5990a393a44d10149cf81f9805c533219124d773aad8c94`. The first real trading date after `20260904` remains the next live operational acceptance event.
