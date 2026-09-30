# V4-08 R4 Closure

**Terminal:** `V4_08_R4_PIT_MEMBERSHIP_CANDIDATE_READY_FOR_FINAL_EXTERNAL_ACCEPTANCE`  
**AST terminal:** `ROTATION_AST_ENGINEERING_R4_PASS`  
**Implementation commit:** `0eb4669a673bad4694bfe2ac26fc67f2e8920935` on `codex/v4-system-reform`.  
**R4 implementation is complete; final external acceptance remains outstanding.**

## Promoted inputs

Identity promotion preserved all parent R7 rows and changed only acceptance metadata for the two target-active additions SZ.001246 and SZ.301716. Its accepted head SHA-256 is `496d537f7c6b9c78cac3a084330f09132814165d2967e8991ffa1d6319092214` and accepted artifact SHA-256 is `4c3445f7b1337fee09e942ac854d0cefcecfc8c90c0b7432d991cadc58818ecd`. The 9 `NOT_LISTED_AT_TARGET` outcomes remain excluded.

The accepted SSE/SZSE calendar head SHA-256 is `d0d453689261603a6ccd773f6383781178cb74d388087b72c652dc8afcb309f6` and the audited extension SHA-256 is `abb832c49e447996b33d7ebf4f233ccfbd4d7f4abc0722caa164d8e25a9ecfc3`. Coverage ends 2026-09-30; 9/25–9/27 remain closed and 9/28–9/30 are sessions.

## PIT candidate

Target date is 2026-09-30. Source revision ID is `sha256:190f9647cb8b6b610dd5336a76dc8b483e3a31439bdb0140bd95523c45905386` with source digest `2a66a6ce398ce64da48f6fd67ea9afd4fa8c7e7f7ce893a74c21b4ec6ec92508`, source bytes digest `2a66a6ce398ce64da48f6fd67ea9afd4fa8c7e7f7ce893a74c21b4ec6ec92508`, and temporal evidence digest `b69b37c4a3c64b3796a16a1d03865a6bb222a8cf9d28dfcddd232f2a9e42d17c`. Snapshot ID is `3dd77c68f3f29601b59d09853a70977bfab15f3fba3edeca6737f75ef9d7bcc0` with fact logical digest `f29596cd59d401fc4fe8d728b3bd32324a46cc116020d64ffb70609f03a9fbc6` and facts artifact SHA-256 `164142652bf5b3032f4e1a8ee54fe2817a3f3b5130635cf04fb641a6e819211d`.

Independent recomputation admitted 50162 facts from 85038 raw source rows, with zero logical mismatches. Counts are INDUSTRY 5224 / 110 sectors / 5224 unique members and THEME 44938 / 268 sectors / 5110 unique members. Combined distinct sector IDs: 378; combined distinct security IDs: 5224.

Exclusions total 34876: `{"BSE_OPTIONAL": 438, "NON_FORMAL_SECTOR_TYPE": 32862, "NOT_LISTED_AT_TARGET": 11, "OPTIONAL_BOARD_OUTSIDE_REQUIRED_SCOPE": 1565}`. Disposable PostgreSQL formal view returned 50162 rows, including INDUSTRY 5224 and THEME 44938; basis, quality, identity, as-of, availability, revision chain and negative STYLE exclusion checks passed. Determinism: `PASS_TWO_IDENTICAL_MATERIALIZATIONS`, logical digest `f29596cd59d401fc4fe8d728b3bd32324a46cc116020d64ffb70609f03a9fbc6`, fact bytes digest `164142652bf5b3032f4e1a8ee54fe2817a3f3b5130635cf04fb641a6e819211d`. Temporal gate: `PASS_NO_BACKDATING_NO_CARRY_FORWARD`; no 9/28 or 9/29 PIT reconstruction occurred.

## AST and regression

Canonical four-state truth table: `PASS` across 32 AND/OR rows plus 7 exact canonical early-retention OR vectors. TRUE OR N/A = TRUE; N/A OR TRUE = TRUE; FALSE OR N/A = FALSE; N/A OR N/A = UNKNOWN / `NO_USABLE_RETENTION_BRANCH`.

For `strong_prev=0`, mature retention evaluates to NOT_APPLICABLE / `STRONG_PREV_EMPTY`. With synthetic qualified premises, ROTATION_IN and ROTATION_ACCEPTED evaluate TRUE while ROTATION_EXPANDING and ROTATION_REACCELERATING evaluate NOT_APPLICABLE. Five retention parameters remain null and formal Rotation consumption stays disabled.

Clean detached checkout `0eb4669a673bad4694bfe2ac26fc67f2e8920935` ran migrations 001–019 on disposable PostgreSQL 18.6 and the required regression families plus governance P0 test: 626 total, 624 passed, 2 skipped, 0 failures/errors. Git status was empty before and after; no `.env` was read; the temporary cluster was destroyed.

## Governance and handoff

No final `data/v4/V4_08_ACCEPTED_HEAD.json` was created. The only V4-08 head is candidate-only, with formal consumers disabled. Phase 0 remains FULL_PASS. Prior-RPS remains OPEN; B2 Legacy Adapter and V4-10 production reducer/FSM remain NOT_IMPLEMENTED. `AUD-AMOUNT-A-06` and V4-01 listing-anchor reconciliation are independently tracked as open cross-cutting audits; neither is silently closed by R4.

**Next:** final independent external acceptance of the exact PIT candidate, source and evidence hashes. Stop here until that acceptance.
