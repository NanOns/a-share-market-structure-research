# V4 R13 post-close PIT and Universe publication gate — R1

Date: 2026-10-16
Base: `codex/v4-workspace-cleanup` at `773cba98e900728500a888e678a3d0ea220bf0ce`
Applicable prior contracts: `V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md`, `V4_RUNTIME_PERFORMANCE_REPAIR_R1_20261013.md`, and the R12 stage report.

## Scope

Repair the post-close source clock, close new-T0 R2 manifest downgrade, bind full-market Universe completeness to publication eligibility, and reconcile only with evidence available without database writes or production service changes. Existing accepted R2 history stays readable as historical evidence. This contract does not authorize source issuers, PG DDL/DML, Head mutation, runtime scheduling, or deployment.

## Versioned acceptance and PIT clock

New independent acceptance uses `V4_DAILY_SOURCE_ACCEPTANCE_RECEIPT_R3` and `V4_DAILY_PIT_DECISION_CLOCK_R1`. The signed receipt identifies `decision_session`, the next exchange session, and the trading-calendar SHA-256. A valid receipt binds the exact T0, freeze, readiness, source facts, package digest, observed time, and calendar identity.

The causal order is:

`first complete source observation <= readiness observation <= acceptance <= signature <= decision cutoff`.

All timestamps must be timezone-aware and are compared as UTC instants; session windows are evaluated in `Asia/Shanghai`. `T0_AFTER_CLOSE` requires the T0 date and a cutoff at or after 15:00. `T1_PREOPEN` requires the signed `next_trade_date`, a later local date, and a cutoff before 09:30. The issuer's signed calendar digest and next-session date are required inputs; this repository has no approved independent issuer or calendar artifact to accept them as live authority. Missing or inconsistent clocks remain diagnostic.

The intended post-close example is: complete T0 K-line first observed 15:15, readiness observed 15:18, accepted 15:20, signed 15:25, then used only for a T0 evening or correctly attested next-session pre-open decision. A 14:30 decision is rejected because it precedes first observation. Information first available after the signed decision cutoff cannot be backfilled. Missing time, time-zone ambiguity, acceptance/signature before readiness, or an old T0 later signed remains rejected.

## R3 downgrade boundary

R2 remains a historical read contract. New source packages use R3 acceptance proof. The effective T0 boundary is 2026-10-16: Core readback rejects R2 at or after that date; Candidate rejects R2 at or after that date; migration 041 constrains future publication inserts to R3 at or after that date. No historical publication is rewritten.

## Universe publication gate

The existing `V4_MARKET_UNIVERSE_COMPLETENESS_R1` algorithm remains an independent denominator and reconciliation contract. Its PASS must be derived from exact snapshot bytes whose SHA-256 and canonical digest are bound to the independently signed `security_universe` source fact, same T0 and accepted package, Core row set, and publication namespace.

The current PG schema does not persist the snapshot rows and complete reconciliation as a verifiable Core readback. Therefore, beginning with the R13 effective T0, Core typed readback returns `BLOCKED_UNIVERSE_READBACK_NOT_PERSISTED`; Candidate and Head require a sealed PASS and matching digest and remain closed. This is a deliberate release block until a versioned persistence/readback path is built and verified. Caller-supplied PASS labels and the 5,100-row synthetic fixture cannot open it.

## Acceptance boundary and next stage

The stage report records fixture pass separately from live acceptance. Source-authority registry and Workspace/Owner mapping registry remain empty and closed. Migration 041 is inventoried and registered in the runner, but has not been compiled against PG or applied. No isolated/live PG write, production Head change, service deployment, 28765/28766 service start, or scheduling occurred. Next stage requires a read-only non-superuser database identity, approved independent issuer/calendar, exact PG ledger-to-catalog reconciliation, and persisted Universe proof/readback before any positive Head fixture can pass end to end.
