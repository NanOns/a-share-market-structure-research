# V4 Phase 0 Final Acceptance — 2026-09-25

## Decision

- **Phase 0:** `FULL_PASS`
- **V4-01 entry:** `AUTHORIZED`
- **Scanner:** `NOT_APPLICABLE_UNTIL_V4_05`
- **Remaining Phase 0 blockers:** `NONE`
- **Acceptance payload implementation commit:** `8506cf9265275750f1bcb0950fa8fd2935f0d52a`
- **Task card SHA-256:** `e1ec6350b56c4db201efa7968ebfe701bb17110875ec65c6e05f162ed3be4494`
- **V4.2.2 REV2 SHA-256:** `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`

## Stage results

| Stage | Result | Scope / evidence |
|---|---|---|
| V4-00A | FULL_PASS | Old PostgreSQL project data was physically backed up and verified, then only `market_research` was reset and rebuilt from hash-checked migrations. Old 5,308,402 rows are not restored. |
| V4-00B | DEGRADED_PASS | Lifecycle and PIT membership semantics frozen; unavailable historical PIT membership is explicitly nonblocking and transferred to V4-01. |
| V4-00C | FULL_PASS | Fresh V4 schema, publication/revision/namespace integrity and rollback behavior verified. |
| V4-00D | FULL_PASS | A_STOCK TDX source package accepted: 265,993 comparable rows, 0 unexplained mismatches, 0 identity mismatches. Non-A residuals remain diagnostic and outside this core gate. |
| V4-00E | DEGRADED_PASS | RAW path is ready; unsupported adjusted event categories fail closed. Adjusted coverage work transfers to V4-01/02. |
| V4-00F | DEGRADED_PASS | BaoStock supplemental source is unavailable and optional; it does not block the local flow. |
| V4-00G | FULL_PASS | Versioned algorithm framework and required contract vectors machine-validated; tests passed 25/25. |
| V4-00H | FULL_PASS | Final capability gate grants V4-01 entry and keeps Scanner deferred until V4-05. |

## Database and source evidence

- Physical backup: `PHYSICAL_BACKUP_VERIFIED`, `pg_verifybackup` passed, system identifier matched; manifest SHA-256 `2cbe45327884a096b9ef7824f6df0ec7b27ba98c8b14f981161587a788712727`.
- Reset: old database row count `5,308,402`; current V4 runtime rows `0`; old publication/focus heads `0`.
- TDX root unchanged: `true`; before/after snapshot SHA-256 `a0e219048f025a9b8fa5998a8a2108535e9cee4b9f8a25573adf1019e97831ff`.
- Tests: `py -3 -m pytest -q tests\v4_phase0` — **25 passed**.

## Nonblocking limitations and transfers

Historical PIT membership and two-year RAW history begin in V4-01. Adjusted Canonical empirical coverage is owned by V4-01/02, BaoStock remains optional, 73 INDEX overlap mismatches remain a separate non-core diagnostic, and actual V4 performance measurement remains with its future capability stages. The legacy PG recovery audit is retired under the clean-empty V4 baseline decision. No scanner or production cutover permission is granted by this receipt.

Canonical machine-readable receipt: [`reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT.json`](../reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT.json). Stage evidence: [`reports/v4_phase0/V4_PHASE0_STAGE_RECEIPTS.json`](../reports/v4_phase0/V4_PHASE0_STAGE_RECEIPTS.json).

## Superseded by the R2 final re-audit

The prior `FULL_PASS` determination is withdrawn under R2 `f51e71ec8a3c02a5551bf07f66366856cf146182a76729b549871a680dcd0fe0`. The current canonical acceptance is [V4_PHASE0_FINAL_ACCEPTANCE_R2_20260925.md](V4_PHASE0_FINAL_ACCEPTANCE_R2_20260925.md); it records `DEGRADED_PASS`, a scope-limited RAW Bootstrap authorization, and the marked-relative benchmark block.
