# Ninth Batch: Source Isolation and Daily Increment Report

**Review status:** `INCOMPLETE_FAIL_CLOSED`  
**Branch/base:** `codex/v4-unified-development`, requested audit baseline `b5d6ba78cc32d5eb249e2fbd3626aa70b012c4b6`  
**Development candidate:** `G:\codex_tmp\v4_daily_candidate_chain_20261020`  
**PG:** `127.0.0.1:5432/market_research` (database OID `646711`)  
**Web ports:** 28766 is the existing prior-candidate server (PID 2968); 28765 was not listening and was not touched.

## Stage contract

Repair D0 SourceIngress readback so both producer and verifier use the exact candidate source binding. Keep historical NON_PIT and existing D0 three-state values unchanged. Use frozen real sources, then complete the 10/16, 10/19, 10/20, and 10/21 incremental Owner/PG/D0/Focus/Forward/Priority sequence, idempotency checks, independent numeric verification, and same-version 28766 readback. Do not use synthetic positive data and do not perform a 28765 production switch.

## Completed

- Fixed D0 verifier source isolation in commit `3dbbda499201e5829d5506fcc4f8def2af6d0a5d`. The PG readback scopes SourceIngress to one candidate token, date, R8 source freeze, D0 consumed-source publication, package/version token, artifact SHA-256 and byte count. Receipts outside that exact binding are diagnostic only. Zero, duplicate, conflicting, or replaced matches fail closed.
- Re-ran targeted tests: **23 passed**. `py_compile` and `git diff --check` passed.
- Read the historic 10/15 R15 publication from PG through the repaired verifier. It remains `POST_HOC_NON_PIT`; selected receipt count is one; the D0 tri-state remains FALSE 5,111 / TRUE 64 / UNKNOWN 51. No old publication was rewritten.
- Reused the frozen 10/16 TDX/BaoStock response without a new BaoStock login. Completed full Owner replay for 5,226 objects, including Core, Profile, Sector/Market, Focus and Forward outputs, and sealed candidate `cb85fcade6d610ca7ac58677ca2aacbb4118502d9047c6c912cac0f5bf3550bd`. The source was captured on 10/21 for 10/16; it remains NON_PIT. Candidate D0 values are UNKNOWN 5,136 / TRUE 90.
- Captured real BaoStock and TDX sources for 10/20 and 10/21 using the bounded project source pipeline. Each BaoStock response returned 5,224 daily rows and 25 (10/20) or 26 (10/21) adjustment-factor rows; each date produced a frozen source and `SOURCE_READY` record. Both were observed on 10/22 and remain NON_PIT. 10/19 also has a real freeze and `SOURCE_READY` record, captured after the session.
- Confirmed the R8 PG publication ledger has **zero candidate rows for 10/16–10/21**. Readback used the configured reader in a read-only transaction. No development Head or PG candidate publication was written during this partial run.

## Blocking findings

The full-universe independent check for 10/16 did not pass. It compared the sealed candidate's raw/adjusted/Core files against the frozen TDX native bars and read-only PG SourceIngress. It verified 5,215 affine QFQ rows and 5,214 ret1 rows, with two unresolved cases:

1. `SZ.002871`: Core ret1 is `0.01920529801324511`; recomputing from the sealed adjusted close and 10/15 adjusted close yields `0.015841584158415856`.
2. `SH.600825`: the candidate-to-source mapping could not be joined for the independent check.

The PG SourceIngress read exposed 5,567 rows, while this candidate and its matching TDX target artifact each contain 5,216 rows. This scope difference also needs reconciliation before numeric acceptance. The cross-source amount comparison found no differences among rows successfully joined.

The 10/16 candidate has not been published through R8 CAS. The publication bridge requires candidate-bound G1–G3 evidence and a candidate-specific CAS rollback drill. Those gates were not bypassed. The next-day Owner entry also correctly rejected 10/19 because 10/16 is still the immediate unpublished predecessor. Therefore 10/19–10/21 Owner/PG/D0/Focus/Forward/Priority and same-token 28766 verification remain incomplete. The 28766 server still serves the prior candidate token; it was not restarted for batch 9.

The 10/20 and 10/21 real source captures establish that real responses exist for those historical dates. Their availability on 10/22 cannot qualify them for a positive D0 as-of Seal. No synthetic positive sample was used.

## Acceptance and next stage

Code repair and historical PG preservation pass. 10/16 Owner computation and the 10/20–10/21 real source capture pass. Independent numeric verification is `FAIL_CLOSED`; R8/D0 candidate publication and the sequential 10/19–10/21 business chain are not complete. This batch is not ready for independent acceptance as a completed increment.

Next, resolve the 10/16 ret1 and source mapping discrepancies from immutable raw inputs and PG SourceIngress. Then create and verify real candidate-bound G1–G3 and rollback evidence, publish the 10/16 development candidate, and continue the remaining dates in strict order with PG idempotency/readback and same-version 28766 checks. Reconsider a positive Dev as-of Seal only if real source timestamps meet the frozen cutoff. 28765 remains out of scope.

See [`NINTH_BATCH_SOURCE_ISOLATION_DAILY_EVIDENCE.json`](NINTH_BATCH_SOURCE_ISOLATION_DAILY_EVIDENCE.json) for file bindings, hashes, PG identity, counts, and per-date source evidence.
