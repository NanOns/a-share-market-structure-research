# V4 Next Round Execution Master R18R1R1｜2026-10-03

## 0. Baseline
Repository: `NanOns/a-share-market-structure-research`
Branch: `codex/v4-system-reform`
Execution baseline:
`e07da98989fc9fa30ef2015d6ac4cd3d6e47b798`

## 1. External Audit State
```text
R18R1_EDGE_SET_CLOSURE = PASS_KEEP
R18R1_CROSS_PROCESS_R4 = PASS_KEEP
R18R1_CANONICAL_GATE = PASS_KEEP
R18R1_EXPECTED_EDGE_ORACLE = PASS_KEEP

R18R1_RUNTIME_EDGE_CONSUMPTION = FAIL_P0
R18R1_EDGE_RECEIPT_EXECUTION_TRUTH = FAIL_P0
```

No rollback and no promotion.

## 2. Read
- `V4_R18R1_INDEPENDENT_EXTERNAL_AUDIT_R2_20261003.md`
- `V4_14_R18R1R1A_PREEXEC_EDGE_BINDING_REPAIR_TASK_20261003.md`
- `V4_14_R18R1R1B_CROSS_PROCESS_FULL_DAG_R5_TASK_20261003.md`
- `V4_14_R18R1R1C_INDEPENDENT_CONSUMPTION_ORACLE_TASK_20261003.md`
- this master

This master is highest scheduler.

## 3. Strict Sequence
```text
R18R1R1A
pre-execution exact field edge binding
↓
R18R1R1B
full_dag_r5 cross-process replay
↓
R18R1R1C
independent consumption oracle + clean seal
↓
unified commit + push
↓
STOP
```

## 4. Exact Defect
R18R1 successfully accounts for all 30 frozen edges, but the runtime currently adds generic `consumer.edge_inputs[edge_id]` after owner outputs have already been computed.

Therefore edge-set closure does not equal execution-consumption truth.

At least these claims are not currently proven:
```text
F0 -> D1 core_facts = EXECUTED
D0 -> EVENT_DIFF confirmation_facts = EXECUTED
```

Several other receipts bind whole-node outputs instead of exact fields consumed.

## 5. Required Invariant
For every EXECUTED edge:
```text
producer exact field payload
==
pre-call consumer argument payload
```

The pre-call invocation envelope must be frozen before output generation.

Receipt must be derived from this envelope, not create it after the fact.

## 6. KEEP
Do not reopen:
- expected 30-edge set;
- active authority;
- owner business algorithms;
- 60 vectors / 17 dimensions;
- cross-process machinery;
- r1/r2 rule;
- determinism;
- real scoped evidence boundary;
- formal heads.

## 7. New Candidate
Preserve r4 immutable.

Create:
`full_dag_r5`

Only r5 may be canonical for R18R1R1.

## 8. Forbidden
- V4_14_ACCEPTED_HEAD
- Stage/Data advance
- ALGORITHM_STATE_REPLAY_PASS formal grant
- Production/Shadow/Focus
- V4-15
- raw/provider fallback
- business algorithm or threshold redesign
- rewriting r4 evidence

## 9. Required End State
```text
R18R1R1A_PREEXEC_EDGE_BINDING = PASS_LOCAL
EXECUTED_EDGE_CONSUMPTION_TRUTH = PASS_LOCAL

R18R1R1B_CROSS_PROCESS_FULL_DAG_R5 = PASS_LOCAL
CANONICAL_FULL_DAG_GATE_R5 = CREATED

R18R1R1C_INDEPENDENT_CONSUMPTION_ORACLE = PASS_LOCAL
EDGE_CONSUMPTION_TRUTH = PASS

R18_REAL_ACCEPTED_SOURCE_REPLAY = PASS_CAPABILITY_SCOPED
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED

V4_14_RUNTIME_CANDIDATE = READY_FOR_EXTERNAL_AUDIT_R18R1R1

V4_14_ACCEPTED_HEAD = NOT_CREATED
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_13_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
ALGORITHM_STATE_REPLAY_PASS = NOT_GRANTED_PENDING_EXTERNAL_AUDIT

NEXT = STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```
