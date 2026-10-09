# R2.1 offline replay

Python 3.11+ standard library only. No network, account, provider login, database,
or repository is required for the numerical oracle.

```text
python oracle/independent_recompute.py --input . --output <separate_output_directory>
```

The script first verifies every SHA256SUMS entry. ZIP CRC must also be checked
with Python zipfile.ZipFile(...).testzip(). All sampling names were frozen
before reading factor values. Inputs include original daily and encrypted GBBQ
record excerpts with independent decoding and affine recomputation.
Core rolling formulas, full-cohort RPS ranks/ties, selected-sector medians and
breadth, selected target-excluded relative returns, Market participation,
period OHLCV/amount and real calendar views are reproducible. Six explicit
FIXTURE scenarios also verify period counts, nulls and status boundaries.
Selected real period states bind provider status, calendar and identity dates.
All-cohort antecedent returns, full Native/LOO/Market and unsampled historical
missing-day status accounting are NOT_VERIFIABLE.
Full market/Owner independent acceptance is NOT_GRANTED.

The repository tests need pytest and repository src; they are included for
review, separately from the standalone offline numerical oracle. Their source
and publication admission are explicitly ISOLATED_INJECTION; the real service
readback receipt is REAL_LOCAL; frozen-source gate replay is SOURCE_RECEIPT_REPLAY.
Windows machine reboot/pre-login was NOT_TESTED.
