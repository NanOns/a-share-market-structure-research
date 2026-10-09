# R2.1 offline replay

Python 3.11+ standard library only. No network, account, provider login, database,
or repository is required for the numerical oracle.

```text
python oracle/independent_recompute.py --input . --output <separate_output_directory>
```

The script first verifies every SHA256SUMS entry. ZIP CRC must also be checked
with Python zipfile.ZipFile(...).testzip(). All sampling names were frozen
before reading factor values. Numerical inputs are bounded excerpts from frozen
normalized Owner history, not independent copies of raw official ZIP bytes.
Core rolling formulas, full-cohort RPS ranks/ties, selected-sector medians and
breadth, and period OHLCV/amount are reproducible. Event-to-affine provenance,
all-cohort antecedent returns, full Native/LOO/Market and period calendar/status
closure are NOT_VERIFIABLE. Full market/Owner independent acceptance is NOT_GRANTED.

The repository tests need pytest and repository src; they are included for
review, separately from the standalone offline numerical oracle. Their source
and publication admission are explicitly ISOLATED_INJECTION; the real service
readback receipt is REAL_LOCAL; frozen-source gate replay is SOURCE_RECEIPT_REPLAY.
Windows machine reboot/pre-login was NOT_TESTED.
