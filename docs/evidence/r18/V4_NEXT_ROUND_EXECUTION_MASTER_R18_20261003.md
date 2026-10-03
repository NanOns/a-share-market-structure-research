# V4 Next Round Execution Master R18｜2026-10-03

## 0. Baseline
Repository: `NanOns/a-share-market-structure-research`
Branch: `codex/v4-system-reform`
Execution baseline: `47b7f72f374c059f35a66bf2fe298a3ec5fe7efc`

R17R1 external decision:
```text
R17R1_EXTERNAL_AUDIT = PASS_FULL_CONTRACT_AUTHORITY_CLOSURE
V4_14_RUNTIME = AUTHORIZED_NEXT_SCOPED_ENGINEERING
```

Current formal heads:
```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_13_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_14_ACCEPTED_HEAD = NOT_CREATED
```

## 1. Read These Files
- `V4_R17R1_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md`
- `V4_14_R18A_REPLAY_AUTHORITY_RUNTIME_HARNESS_TASK_20261003.md`
- `V4_14_R18B_CROSS_PROCESS_FULL_DAG_REPLAY_E2E_TASK_20261003.md`
- `V4_14_R18C_INDEPENDENT_ORACLE_REAL_SCOPED_REPLAY_SEAL_TASK_20261003.md`

This master is the highest scheduler for R18.

## 2. Strict Order
```text
R18A
Replay Authority + Runtime Harness
↓
synthetic 17-dimension runtime gate

R18B
Cross-process Persisted Full-DAG Replay
+ same-day revision E2E
↓
persisted replay gate

R18C
Independent Oracle
+ capability-scoped real accepted-source replay
+ clean detached seal
↓
unified commit + push
↓
STOP
```

## 3. KEEP
Do not reopen:
- R17A historical governance;
- R17R1 active-family closure;
- V4-13 amended Accepted Head;
- V4-14 v1.1 contract freeze;
- all accepted V4-08 through V4-13 business algorithms;
- r6 V4-13 real candidate;
- Projection v1.2 semantics.

## 4. R18A Rules
Implement orchestration/replay, not a new business algorithm.

Must:
- bind exact active authority;
- call/read accepted owner logic;
- execute all 17 frozen dimensions;
- publish append-only replay revisions;
- fail closed on stale authority/ref mismatch.

## 5. R18B Rules
Must prove:
- true cross-process T-1 -> T continuity;
- exact previous market session;
- producer exit before consumer start;
- same-day r1/r2 use same T-1;
- no r1 -> r2 previous-session lineage;
- event/episode identity;
- hysteresis/expiry;
- structure lifecycle;
- deterministic replay.

## 6. R18C Rules
Must provide an independent oracle not implemented by calling V4-14 runtime functions for expected results.

Must run:
- frozen synthetic;
- real accepted-source capability-scoped;
- historical PIT only if all prerequisites are truly proven.

Missing historical PIT remains NOT_GRANTED.

## 7. Global Forbidden
Entire R18:
- `V4_14_ACCEPTED_HEAD`;
- Stage Head advance;
- Data Head advance;
- `ALGORITHM_STATE_REPLAY_PASS` formal grant;
- Production;
- Shadow;
- Focus;
- Radar/Cohort/Settlement;
- V4-15;
- formal DB migration;
- raw/provider fallback;
- algorithm threshold redesign.

## 8. Required End State
```text
R18A_V4_14_RUNTIME_HARNESS = PASS_LOCAL
R18B_CROSS_PROCESS_FULL_DAG_REPLAY = PASS_LOCAL
R18C_INDEPENDENT_ORACLE = PASS_LOCAL

R18_REAL_ACCEPTED_SOURCE_REPLAY = PASS_CAPABILITY_SCOPED

V4_14_RUNTIME_CANDIDATE =
READY_FOR_EXTERNAL_AUDIT

V4_14_ACCEPTED_HEAD =
NOT_CREATED

V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_13_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

ALGORITHM_STATE_REPLAY_PASS =
NOT_GRANTED_PENDING_EXTERNAL_AUDIT

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```
