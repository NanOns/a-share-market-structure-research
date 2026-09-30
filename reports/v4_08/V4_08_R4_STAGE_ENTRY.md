# V4-08 R4 Stage Entry and Acceptance Record

- Required starting HEAD: `097a22f3fd8f7be405eab6e64a4f513d2ec64413`; branch: `codex/v4-system-reform`.
- R4 implementation commit tested in a clean detached checkout: `0eb4669a673bad4694bfe2ac26fc67f2e8920935`.
- Stage contract: `V4_08_R4_INPUT_PROMOTION_FIRST_PIT_MATERIALIZATION_AND_NA_AST_REPAIR_TASK_20260930`.
- Latest applicable upgrade: REV4-FEP-R2, SHA-256 `203ff46075b4039d1e2d45d54fd76ce09509535739cd6aaef4dc394de1015205`; the R4 AST decision follows §§21A.4, 21A.4A, 72 and 78.
- Phase 0 inherited result: `FULL_PASS`, satisfying the scanner start gate.

## P0 runtime-logic gate

`NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC` = `PASS`; production/runtime-configuration symbol hits = 0; unclassified paths = 0. Every scanned file is bound by byte count and SHA-256. The lifecycle capture source contract is retained as audit-only input under `reports/v4_08/audit_inputs/`, and the R2 unresolved scope is derived from its frozen classification artifact.

## Authorized input promotion

- Identity only: the exact R3-authorized 2026-09-30 increment; 2 target-active additions, parent R7 rows preserved, 9 `NOT_LISTED_AT_TARGET` dispositions remain out of active identity. Accepted head: `496d537f7c6b9c78cac3a084330f09132814165d2967e8991ffa1d6319092214`; artifact: `4c3445f7b1337fee09e942ac854d0cefcecfc8c90c0b7432d991cadc58818ecd`.
- SSE/SZSE calendar only: accepted through 2026-09-30, exact audited extension reused, dates 2026-09-25–27 closed and 2026-09-28–30 sessions. Accepted head: `d0d453689261603a6ccd773f6383781178cb74d388087b72c652dc8afcb309f6`; extension: `abb832c49e447996b33d7ebf4f233ccfbd4d7f4abc0722caa164d8e25a9ecfc3`.
- Candidate inputs were not mutated. Scope remains the external R3 authorization; no whole-market lifecycle completeness claim is made.

## First PIT candidate

- Target: `2026-09-30` only. Source revision: `sha256:190f9647cb8b6b610dd5336a76dc8b483e3a31439bdb0140bd95523c45905386`; source bytes digest: `2a66a6ce398ce64da48f6fd67ea9afd4fa8c7e7f7ce893a74c21b4ec6ec92508`; temporal evidence digest: `b69b37c4a3c64b3796a16a1d03865a6bb222a8cf9d28dfcddd232f2a9e42d17c`.
- Snapshot: `3dd77c68f3f29601b59d09853a70977bfab15f3fba3edeca6737f75ef9d7bcc0`; fact logical digest: `f29596cd59d401fc4fe8d728b3bd32324a46cc116020d64ffb70609f03a9fbc6`; compressed facts SHA-256: `164142652bf5b3032f4e1a8ee54fe2817a3f3b5130635cf04fb641a6e819211d`.
- Independently recomputed rows: INDUSTRY 5224, THEME 44938, total 50162; expected R3 counts were not treated as oracle constants.
- Exclusions: `{"BSE_OPTIONAL": 438, "NON_FORMAL_SECTOR_TYPE": 32862, "NOT_LISTED_AT_TARGET": 11, "OPTIONAL_BOARD_OUTSIDE_REQUIRED_SCOPE": 1565}`. Formal PostgreSQL view readback: 50162 rows; all identity, target-date, source-chain and availability predicates passed.
- Repeated materialization: `PASS_TWO_IDENTICAL_MATERIALIZATIONS`; no backdating or historical carry-forward. The only V4-08 head is `V4_08_PIT_MEMBERSHIP_CANDIDATE_HEAD_R1`; final V4-08 Accepted Head is absent.

## AST acceptance

- Four-state evaluator and canonical early-retention OR: `PASS`; TRUE/FALSE/UNKNOWN/NOT_APPLICABLE preserved. REV4 §21A.4: one unavailable OR branch is skipped; FALSE OR N/A = FALSE; both N/A = UNKNOWN / `NO_USABLE_RETENTION_BRANCH`.
- `strong_prev=0`: mature retention = NOT_APPLICABLE / `STRONG_PREV_EMPTY`; IN and ACCEPTED remain TRUE under synthetic qualified premises; EXPANDING and REACCELERATING remain NOT_APPLICABLE. No `MATURE_RETENTION_FAILED` is emitted.
- Five retention parameters remain null; formal Rotation consumer remains disabled. AST engineering result: `ROTATION_AST_ENGINEERING_R4_PASS`.

## Clean-checkout acceptance and outstanding independent work

- Disposable PostgreSQL PostgreSQL 18.6, migrations 001–019: `PASS`; temporary cluster destroyed.
- Required-family regression plus P0 governance guard: 626 cases; 624 passed, 2 skipped, 0 failures/errors. Checkout was detached and git-clean before/after; no `.env` read.
- Independent open items remain separate: `AUD-AMOUNT-A-06` (`OPEN_EVIDENCE_REQUIRED`) and V4-01 listing-anchor reconciliation (`OPEN_SEPARATE_LIFECYCLE_ANCHOR_AUDIT`). Prior-RPS remains OPEN; B2 Legacy Adapter and V4-10 production reducer/FSM remain NOT_IMPLEMENTED.
- Acceptance result: `V4_08_R4_PIT_MEMBERSHIP_CANDIDATE_READY_FOR_FINAL_EXTERNAL_ACCEPTANCE`.
- Next stage: final independent external acceptance of the PIT membership candidate. Stop R4 implementation here; do not create a final V4-08 Accepted Head.
