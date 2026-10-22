# Ninth Batch: Exact Source Isolation and Daily Increment Report

**Review status:** `DEV_INCREMENT_COMPLETE_WITH_10_16_READ_INDEX_LIMITATION`
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
