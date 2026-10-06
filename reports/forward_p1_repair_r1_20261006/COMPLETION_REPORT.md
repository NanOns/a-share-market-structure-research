# Forward P1 Repair R1 completion

FORWARD_P1_REPAIR_R1=CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

IA-09=CANDIDATE_FIXED; IA-01=CANDIDATE_FIXED; IA-02=CANDIDATE_FIXED.

Entry: `0c78051c570bdd68ef98f1cb9fdcfcd315759ec2`. Completed evidence timestamp: 2026-10-06T23:55:07.335038+00:00.

- IA-09: 30 tests passed, 0 failed/error/skipped.
- Stock: 12 required vectors passed; Sector: 12 required vectors passed.
- Affected regression: 283 passed, 0 failed/error; 278 existing opt-in PG cases unexecuted. IA-06 remains OPEN.
- Safe collection retains the IA-05 retired-writer import error. No global pytest PASS is claimed.
- Final complete core runtime byte/mtime inventory equals the original baseline; all remaining runtime roots match the supplemental baseline. The supplemental database entry is reconciled against the earlier original core baseline in SUPPLEMENTAL_BASELINE_RECONCILIATION.json. All historical tracked objects are unchanged. Authority, Current Audit Head, accepted heads, old outcomes, FEP labels and migrations remain frozen. Real counters remain zero; later formal heads are absent.

An earlier regression was rejected by the protected-state gate because the live DuckDB storage bytes changed. Exhaustive comparison found identical rows in all 103 tables and identical views/indexes. Both versions and the failed fingerprints are retained; the original exact snapshot was restored with a separate incident receipt. The final regression uses a repository-wide test connection/recovery guard and is independently fingerprinted. The failed run is not claimed as zero-write or accepted.

Stock endpoint and path quality are independent. Sector uses dedicated frozen basket identities and member valuation, fixed original weights, no synthetic stock OHLC, and only close extrema. Successor outcomes/corrections append under FORWARD_PRICE_PATH_V1_1. Old M12 assertions and bytes remain intact; the new fixture isolates service/API writes and disposable recovery.

The new worker is simulation-only and rejects real delivery before source access. No active accepted dependency, UI permission or FEP owner allocation changes. IA-03/04 sentinels preserve current behavior; IA-05/06/07/08/10 remain OPEN.

Review IA01/IA02 vector matrices for inputs, expectations, old/new results and contract reasoning; IA09_TEST_ISOLATION_PROOF for actual guard attempts/recovery; PROTECTED_STATE_READBACK and both inventory pairs for preservation; AFFECTED_REGRESSION_SUMMARY for coverage limits.

Next: INDEPENDENT_EXTERNAL_AUDIT_REQUIRED. Git delivery is evidence transport, not external acceptance or permission for the next gated stage.
