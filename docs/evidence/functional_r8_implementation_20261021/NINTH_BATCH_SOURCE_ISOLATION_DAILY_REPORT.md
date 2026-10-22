# Ninth Batch: Exact Source Isolation and Daily Increment Report

**Original ninth-batch status:** `DEV_INCREMENT_COMPLETE_WITH_10_16_READ_INDEX_LIMITATION`

**Annotation follow-up status:** `PARTIAL_MEMBERSHIP_SCOPE_REPAIRED_D0_REPUBLICATION_REQUIRED`
**Branch:** `codex/v4-unified-development`
**Requested baseline:** `b5d6ba78cc32d5eb249e2fbd3626aa70b012c4b6` (ancestor of the starting branch state)
**Development PG:** `127.0.0.1:5432/market_research`, OID `646711`
**Web ports:** candidate preview on `127.0.0.1:28766` serves 10/21 token `c8b6b32f…49d3c528`; `28765` was not listening and was not touched.

## Contract and changes

The D0 producer and independent verifier now resolve SourceIngress from the exact candidate source binding. Candidate token, trade date, R8 freeze, consumed package identity, artifact SHA-256 and byte length determine the receipt. Other same-day receipts are diagnostic only. Missing, ambiguous, conflicting or replaced exact matches fail closed. The verifier no longer lets unrelated same-day receipts make a valid candidate `POST_HOC_NON_PIT`.

The exact-binding repair and regression tests are in commit `3dbbda499201e5829d5506fcc4f8def2af6d0a5d`. This batch also fixes the successor transaction receipt to persist its candidate token and fixes R8 receipt assembly to bind the post-CAS Head digest. Four focused test modules pass (**28 passed**); affected modules compile and `git diff --check` passes.

Historical NON_PIT classifications and existing D0 three-state results were preserved. The real frozen sources were reused; no synthetic positive source or sample was used. Each D0 publication is development-only and marks `production_admission=false`.

## Sequential candidate results

| Date | Candidate token | Owner rows / D0 TRUE, UNKNOWN | Numeric verification | R8 / D0 |
|---|---|---:|---|---|
| 10/16 | `33cf6cdb…b5fc440` | 5,226 / 90, 5,136 | independent PG/native full-universe PASS: 5,216 source matches, 5,216 QFQ checks, 5,215 observed ret1 checks, zero amount differences and zero mismatches; period oracle 219,464 checks | G1–G4 PASS; D0 published and idempotent retry passed |
| 10/19 | `f9c4fa37…e136862` | 5,224 / 152, 5,072 | independent period oracle PASS, 292,516 checks | G1–G4 PASS; D0 published and idempotent retry passed |
| 10/20 | `dba3131d…d9aad` | 5,224 / 115, 5,109 | independent period oracle PASS, 292,516 checks | G1–G4 PASS; D0 published and idempotent retry passed |
| 10/21 | `c8b6b32f…49d3c528` | 5,224 / 99, 5,125 | independent period oracle PASS, 292,516 checks | G1–G4 PASS; D0 published and idempotent retry passed |

Each day was applied in order from the previous development Head. The first 10/20 publication token (`38507df2…b6697c`) was rolled back after its readback returned 10/19; the predecessor Head was restored exactly, and retry attempt 2 published the final 10/20 token. For 10/19, a receipt-assembly NameError surfaced after the transaction and PG row were committed; independent PG/transaction readback verified the committed event and G1–G4, and the source fix prevents recurrence. R8 receipts independently verify the candidate-only PG append, transaction, Head, same-token readback and rollback evidence. The D0 restricted reader verified the fact digest and full input/derived closure; each exact SourceIngress lookup returned one matching artifact. Its transaction was `READ ONLY`. The evidence JSON records per-date hashes, source identity, closure fingerprints, timestamps, candidate receipts and priority snapshots.

All four D0 publications are `PUBLISHED_DEV_RECONSTRUCTED_NON_PIT`. Their source captures were late relative to the historical session. Exact candidate isolation fixes incorrect cross-receipt classification; it does not convert those late real captures into point-in-time sources.

D0 records its source snapshot cutoff separately from contract freeze, computation, publication and usable timestamps. For 10/21, the cutoff was `2026-10-22 09:42:55.284169+08`, code/parameters froze at `09:43:01.489638+08`, computation completed at `09:43:01.731667+08`, and publication/usable time was `09:43:02.078690+08`. The exact ingress artifact became available at `2026-10-21 17:35:26+08` after that session closed. The Seal therefore stays NON_PIT while retaining a valid, ordered time chain.

## Read index, Priority and 28766

For 10/19, 10/20 and 10/21, Focus, Forward, Priority and Stocks read indexes were rebuilt from the exact published candidate token. The candidate-only Priority precompute passed. Their 28766 same-version checks passed for status, context, home, Focus, Forward, Priority and Stocks; all routes returned HTTP 200 with the same candidate token.

The 10/16 candidate had already been published and its D0 closure independently verifies. Its immutable `native_membership_reference` is scoped to `T0=2026-10-15` although the candidate is `T0=2026-10-16`. This blocks full 10/16 read-index and Focus/Priority/Stocks route closure with `NATIVE_MEMBERSHIP_REFERENCE_SCOPE_MISMATCH`; status and Forward were verified. The historical identity was not rewritten. This is the remaining boundary on the four-date downstream route claim and is recorded in the evidence JSON.

## Acceptance and handoff

Code, sequential development R8/D0 publication, exact source readback, idempotency, full closure and independent numerical checks are complete. 10/19–10/21 have complete same-token downstream 28766 validation. The 10/16 historical read-index boundary remains fail closed pending a separate correction or superseding candidate. Independent review can inspect the linked JSON evidence and the pushed source/test changes.

No 28765 production switch, production Head update or final packaging was performed. This development push is not external acceptance.

See [`NINTH_BATCH_SOURCE_ISOLATION_DAILY_EVIDENCE.json`](NINTH_BATCH_SOURCE_ISOLATION_DAILY_EVIDENCE.json) for machine-readable bindings and results.

## Follow-up after reviewer annotation (2026-10-22)

The reviewer called out the remaining 10/16 membership failure and the high D0 `UNKNOWN` counts. The findings below use the real frozen candidate files and readback from the authorized development PG.

### D0 `UNKNOWN` root cause and source-bound recomputation

The 10/16, 10/19, 10/20 and 10/21 prewatch files were generated before formal D0 aggregation stopped counting `STRONG_PULLBACK` and `TREND_CONTINUE`. Both are explicitly diagnostic-only in `V4_D0_SOURCE_SEAL_SUCCESSOR_R2`; each is `UNKNOWN` for every security in these files. That made an unrelated diagnostic unknown override otherwise determinate formal FALSE rows.

Using the real frozen `target_values` and the current formal aggregator, I wrote separate recompute-only owner files under `G:/codex_tmp/v4_daily_candidate_chain_20261020/.../owner_v3_d0_formal_recompute_r1/`. No old owner file or publication was overwritten. Counts changed as follows:

| Date | Previously published TRUE / FALSE / UNKNOWN | Formal recomputation TRUE / FALSE / UNKNOWN |
|---|---:|---:|
| 10/16 | 90 / 0 / 5,136 | 90 / 5,084 / 52 |
| 10/19 | 152 / 0 / 5,072 | 152 / 5,018 / 54 |
| 10/20 | 115 / 0 / 5,109 | 115 / 2,736 / 2,373 |
| 10/21 | 99 / 0 / 5,125 | 99 / 5,076 / 49 |

This is a source-bound recomputation, not a corrected PG publication or 28766 readback. The D0 owner bytes are part of the R8 candidate token, so publishing corrected rows requires a superseding candidate token and the corresponding append-only R8/D0 chain.

The per-date source hashes, owner output bindings, scenario counts and unresolved formal reasons are in [`D0_FORMAL_RECOMPUTE_DIAGNOSTIC_R1.json`](D0_FORMAL_RECOMPUTE_DIAGNOSTIC_R1.json).

The remaining 10/20 formal `UNKNOWN` is not caused by those diagnostics. Its `RECOVERY_TURN` has 2,420 unknown rows, including 2,399 `RPS5_DELTA3` values with `EXACT_DATED_RPS_ENDPOINT_UNKNOWN` at prior endpoint 10/15. The old 10/15 Owner happens to contain a value for 2,381 of those securities, but that endpoint is not interchangeable: among the 2,825 rows with a stored 10/20 delta, only one equals current RPS5 minus the old 10/15 RPS5; 2,824 differ. I did not backfill from the mismatched snapshot. The 10/20 RPS endpoint producer/source scope remains open for a separate exact-source repair, and those true unknowns stay unknown.

### 10/16 Membership authority repair

The 10/16 candidate inherited a `native_membership_reference` authority with `T0=2026-10-15`. Although its membership bytes matched the 10/16 snapshot, the PG authority was date-scoped to 10/15 and correctly failed closed. I appended a new 10/16-scoped membership, identity and search-identity authority in development PG, read all three back (55,136 membership rows, 5,226 current identity rows and 6,055 search rows), and saved a superseding candidate file under the G-drive candidate root. Its token is `ab13eb13456fcf2d725137d5404ef55e10a4b6496203da5ecb50faff7c694ea6`; the prior token and its files remain unchanged.

The successor validator now rejects a carried-forward membership authority whose `T0` or snapshot binding differs from the candidate. This prevents publication of the same mismatch in future candidates. The superseding membership candidate has not yet been R8/D0-published, and 28766 still serves the prior 10/21 token; therefore the 10/16 full-route limitation is not yet closed.

### Follow-up validation and remaining work

The membership-scope and formal-aggregation regressions pass with the existing D0 source-isolation regressions (**28 passed**). Historical 10/15 NON_PIT and its three-state results remain unchanged. The development database and only 28766 were used; no 28765 production action occurred.

Remaining work: create and independently verify superseding R8/D0 publications for the corrected formal aggregates, rebase later candidate dates in order where tokens depend on the corrected 10/16 candidate, and repeat the same-token read-index/28766 checks. Independently repair the 10/20 exact 10/15 RPS5 endpoint binding before claiming that portion's `UNKNOWN` population has been resolved.


## Annotation follow-up 2: exact RPS5 endpoint and UNKNOWN reduction

The earlier open 10/20 RPS5 endpoint was recomputed from frozen TDX source after fixing candidate-membership precedence and computing the 10/15 endpoint in the 10/20 price coordinate. Independent row-level verification now matches 5,202 observed deltas exactly, retains 22 exact endpoint UNKNOWNs, and finds zero mismatches. The formal D0 development-only recomputation is TRUE/FALSE/UNKNOWN = 137/5,015/72; the frozen scanner comparison passes. Two security IDs without a matching core identity row remain UNKNOWN.

This supersedes the earlier statement that the 2,399 endpoint UNKNOWNs remain open. The revised Owner is not yet rebound into a superseding R8 candidate, appended to PG, or served from 28766. Details: [`NINTH_BATCH_RPS5_ENDPOINT_REPAIR_R1_REPORT.md`](NINTH_BATCH_RPS5_ENDPOINT_REPAIR_R1_REPORT.md) and its evidence JSON.


## Annotation follow-up R2 supersedes R1 endpoint counts

The exact candidate identity source key was also missing for two newly listed current members. The core replay now reads the bound candidate Identity authority and includes the complete 5,226 current membership rows. Independent numeric comparison across the full core owner confirms 5,202 exact RPS5 deltas, 24 matching endpoint UNKNOWNs, zero mismatches, and zero current-RPS5 mismatches. All 5,224 existing formal D0 rows now join to the corrected core and recompute to TRUE/FALSE/UNKNOWN = 137/5,015/72 with frozen scanner PASS. Two candidate members still lack formal D0 rows, so the full candidate D0/Focus/Priority owner has not been published. See [`NINTH_BATCH_RPS5_ENDPOINT_REPAIR_R2_REPORT.md`](NINTH_BATCH_RPS5_ENDPOINT_REPAIR_R2_REPORT.md).
