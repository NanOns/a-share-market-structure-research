# Runtime resume — return to R25

Baseline: `6f05278f50ee58bc904f5949c503de9223835463`. R31R2 external authority is archived byte-for-byte and grants `V4_22_CONTRACT_DESIGN = EXTERNALLY_ACCEPTED_SCOPED` only. The design repair chain is closed for its accepted scope. Historical seals and the canonical design contract are preserved.

Current explicit accepted Data Head remains 2026-09-30, with RECONSTRUCTED_CORRECTED lineage and no proven first availability at a target session. Existing R25 exact daily input authority, daily input digest, target-session selection and activation packet digest remain null. Therefore `R25 = WAIT_ACCEPTED_DAILY_INPUT` is the valid exit. No upstream capture, scanner, R25 retry, database or real Shadow execution was invoked.

The task names 2026-10-08 as the earliest calendar opportunity; the date alone does not provide target-session authority. First use the existing accepted incremental/data-owner pipeline to produce and externally accept the exact target package. Then retry the existing R25 packet/preflight, stop for independent external audit, and await separate first Real Shadow authorization against the exact accepted packet/digest.

R26-A01 and the two external P2 observations are carried as three separate nonblocking audit entries with independent scope, evidence and disposition. They do not reopen the design chain or block a valid R25 retry.

Verification: exact baseline byte comparison of protected heads, runtime authority, design contract and R25 records; absent V4-16..22 accepted heads; frozen zero real observations and false permissions. No business code changed, so no regression rerun was needed.

NEXT: `WAIT_EXACT_ACCEPTED_TARGET_SESSION_INPUT`. V4-22 final PASS and production permissions remain NOT_GRANTED. Commit/push is evidence synchronization only.
