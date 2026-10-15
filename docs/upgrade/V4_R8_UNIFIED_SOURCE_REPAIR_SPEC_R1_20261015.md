# V4 R8 unified source repair — S2 design contract

- Contract: `V4-R8-UNIFIED-SOURCE-REPAIR-20261015/R1`
- Version: `R1.0.0`
- Scope: new-listing Profile conservation, Forward due-source states, and after-close first-freeze timing.

## P0-A: target lifecycle conservation

The target-dated, versioned lifecycle identity binding is authoritative for the current daily Owner run. Its active IDs are added only to the target-day universe; historical dates retain their own dated universes. Identity absence is a hard failure. Active entities with no calculable history remain in Core/Profile outputs with null values and explicit `UNKNOWN`/`INSUFFICIENT_HISTORY`; raw bars and returns are never fabricated. `config/v4_dynamic_profile_lifecycle_conservation_r1.json` binds these rules into the generation scope.

## P0-B: settlement source states

The Forward schedule distinguishes `PENDING_FUTURE_SESSION`, `DUE_SOURCE_NOT_ACCEPTED`, `SOURCE_GAP`, security-fact-backed `NO_QUOTE`/`SUSPENDED`, and `SETTLED`. Accepted target-day lifecycle facts may classify a missing security quote only when they explicitly state `NO_QUOTE` or `SUSPENDED`. Missing due-source days and generic gaps never enter the quote-failure count or return denominator. Only `SETTLED` results enter return aggregates; nominal unadjusted close-to-close values remain research descriptions.

## P0-C: after-close timing

An after-close T0 signal is `AFTER_CLOSE_FIRST_OBSERVED`. The first available source time, accepted Head time, first processing time, and immutable freeze time have distinct fields and must be timezone-aware and ordered. The signal is valid from the next official session. A first freeze at or after that session's 09:30 Asia/Shanghai open is `LATE_OBSERVED_NOT_PIT`; it remains an observation but is never backdated. `executable_from` marks a research reference boundary and does not claim a trade occurred. No machine-clock changes are allowed.

## Stage evidence

Targeted tests cover set conservation/unknown history, all due-source states, settlement denominators, and synthetic next-session timing boundaries. Real production sources were read only; the detailed counts and SHA-256 bindings are recorded in `reports/audits/v4_unified_r8/CRITICAL_BUG_REPAIR_EVIDENCE.json`. Full isolated Owner/PG readback is reserved for S4 and is not inferred from unit tests or the single-security real-source replay.
