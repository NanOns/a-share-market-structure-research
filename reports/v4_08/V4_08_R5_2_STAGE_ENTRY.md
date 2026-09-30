# V4-08 R5.2 stage entry — 2026-09-30

Input HEAD c853f0ce1980d338d67fe0afb29d4ccaa95db648. Contract: V4_08_R5_2_FINAL_INPUT_AUTHORITY_AND_LEGACY_VALID_MEMBER_REPAIR_TASK_20260930.md plus latest REV4 FEP R2 §17, three-head contract and accepted canonical governance hash policy.

Scope limited to B04 authority abstraction/context validation and B05 capability classification. No parameter, Native formula, membership, B0/Rotation state machine, rank algorithm or migration changes. No Daily Lane rewrite, new scheduler/collector or fourth authority. No TDX writes.

B05 decision: option B. Accepted 47-field factors, Core profiles, canonical daily and Daily bootstrap bindings do not provide exact legacy missing_state provenance (FILE_MISSING/DELISTED_OR_INACTIVE distinction). Canonical identity/trading_status or membership presence cannot prove the old missing_state rule. Do not create a producer from guessed equivalences. B2_NON_AMOUNT_A is NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE; formal confirmed_raw stays UNKNOWN, B2_AMOUNT_A DIAGNOSTIC_AUDIT_OPEN. Independent Native/B0/B1 engineering scope excludes B2 confirmed/warm.

Evidence: daily head routing, T/T+1 independent contexts and frozen T digest, negative context vectors, injected-final-boolean rejection, capability downgrade, real 9/30 fail-closed, clean detached/disposable PostgreSQL regression and no-symbol.
Acceptance IN_PROGRESS. Next stage independent external reaudit; global heads unchanged; production permission false. Independent Prior-RPS, AUD-AMOUNT-A-06 and dated-roster audits remain OPEN in their existing scopes. Existing FEP untracked work preserved.
