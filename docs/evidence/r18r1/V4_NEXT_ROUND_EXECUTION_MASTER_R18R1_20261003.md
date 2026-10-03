# V4 Next Round Execution Master R18R1｜2026-10-03

## 0. Baseline
Repository:
`NanOns/a-share-market-structure-research`

Branch:
`codex/v4-system-reform`

Execution baseline:
`70fc9b050497e798d077480d0ae4adf97e9824c6`

## 1. Audit Disposition
```text
R18A_RUNTIME_HARNESS = PASS_KEEP

R18B_CROSS_PROCESS_MECHANICS = PASS_KEEP
R18B_SAME_DAY_REVISION_ISOLATION = PASS_KEEP
R18B_DETERMINISTIC_REPLAY = PASS_KEEP

R18B_FULL_DAG_OWNER_EDGE_COVERAGE = FAIL_P0

R18C_VECTOR_ORACLE = PASS_KEEP
R18C_REAL_SCOPED_REPLAY = PASS_KEEP_CAPABILITY_SCOPED
R18C_FULL_DAG_ORACLE_COMPLETENESS = FAIL_P0
```

No Stage rollback.
No V4-14 promotion.

## 2. Read These Files
- `V4_R18_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md`
- `V4_14_R18R1A_OWNER_EDGE_COMPLETE_REPLAY_HARNESS_TASK_20261003.md`
- `V4_14_R18R1B_CROSS_PROCESS_FULL_DAG_R4_CANONICAL_EVIDENCE_TASK_20261003.md`
- `V4_14_R18R1C_INDEPENDENT_EDGE_ORACLE_REAL_RECHECK_SEAL_TASK_20261003.md`
- `V4_NEXT_ROUND_EXECUTION_MASTER_R18R1_20261003.md`

This master is the highest scheduler.

## 3. Strict Sequence
```text
R18R1A
Owner-edge Complete Replay Harness
↓
R18R1B
full_dag_r4 cross-process replay
+ canonical evidence authority
↓
R18R1C
independent edge oracle
+ real scoped recheck
+ clean seal
↓
unified commit + push
↓
STOP
```

## 4. Exact Defect
Current R18 proves a coarse 10-node trace, but not the complete frozen owner-edge DAG.

Examples:
```text
B0 not separately executed
B2 not separately executed
B0 -> B1 not edge-proven
B0 -> B2 not edge-proven
Context dependency set not fully edge-proven
C -> D0 lineage not edge-proven
```

The current oracle validates node names and therefore cannot detect these omissions.

## 5. Required Repair Model
Every applicable frozen edge must have one machine-readable status:
```text
EXECUTED
DEGRADED_ACCEPTED_CAPABILITY
NOT_APPLICABLE_BY_FROZEN_CONTRACT
```

Required invariant:
```text
EXPECTED_EDGE_SET
==
EXECUTED ∪ DEGRADED ∪ NOT_APPLICABLE
```

No missing edge.
No unexpected edge.
No hard-coded downstream substitute without producer evidence.

## 6. Evidence Governance
Preserve:
```text
full_dag
full_dag_r2
full_dag_r3
```
as immutable historical attempts.

Create:
```text
full_dag_r4
```
as the repaired candidate.

Only one canonical R18R1B final Full-DAG gate may be consumed by the R18R1C oracle and final seal.

## 7. KEEP
Do not reopen:
- R18A 60-vector / 17-dimension runtime;
- real OS cross-process launcher;
- T r1/r2 exact T-1 rule;
- deterministic replay;
- R17R1 active authority;
- V4-13 promotion;
- accepted V4-08..V4-13 business algorithms;
- real scoped evidence-class boundaries.

## 8. Forbidden
Entire round:
```text
V4_14_ACCEPTED_HEAD
Stage Head advance
Data Head advance
ALGORITHM_STATE_REPLAY_PASS formal grant
Production
Shadow
Focus
V4-15
Radar/Cohort/Settlement
formal DB migration
raw/provider fallback
business threshold redesign
```

## 9. Required End State
```text
R18R1A_OWNER_EDGE_COMPLETE_HARNESS = PASS_LOCAL

R18R1B_CROSS_PROCESS_FULL_DAG_R4 = PASS_LOCAL
OWNER_EDGE_COMPLETENESS = PASS
CANONICAL_FULL_DAG_GATE = CREATED

R18R1C_INDEPENDENT_EDGE_ORACLE = PASS_LOCAL

R18_REAL_ACCEPTED_SOURCE_REPLAY = PASS_CAPABILITY_SCOPED
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED

V4_14_RUNTIME_CANDIDATE = READY_FOR_EXTERNAL_AUDIT_R18R1

V4_14_ACCEPTED_HEAD = NOT_CREATED
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_13_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30

ALGORITHM_STATE_REPLAY_PASS = NOT_GRANTED_PENDING_EXTERNAL_AUDIT

NEXT = STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```
