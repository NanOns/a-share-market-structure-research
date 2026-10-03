# V4 Next Round Execution Master R18R1R1R1｜2026-10-03

## 0. Baseline

Repository:
`NanOns/a-share-market-structure-research`

Branch:
`codex/v4-system-reform`

Execution baseline:
`f7b3402e4fbd5c98f4e76e3a56042a84960e120a`

## 1. External Audit Disposition

```text
R18R1R1_PRECALL_CONSUMPTION = PASS_KEEP
R18R1R1_EDGE_CONSUMPTION_TRUTH = PASS_KEEP
R18R1R1_CROSS_PROCESS_R5 = PASS_KEEP
R18R1R1_CANONICAL_R5_GATE = PASS_KEEP
R18R1R1_CONSUMPTION_ORACLE = PASS_KEEP
R18R1R1_CLEAN_REGRESSION = PASS_KEEP

REAL_ACCEPTED_SOURCE_REPLAY = PASS_KEEP_CAPABILITY_SCOPED
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED_KEEP

V4_14_ROLLBACK_RECEIPT = MISSING_P0
```

The only remaining V4-14 runtime-completion blocker is the explicit contract requirement:

```text
rollback_receipt
```

## 2. Read These Files

- `V4_R18R1R1_INDEPENDENT_EXTERNAL_AUDIT_R3_20261003.md`
- `V4_14_R18R1R1R1A_ROLLBACK_DRILL_RECEIPT_TASK_20261003.md`
- `V4_14_R18R1R1R1B_INDEPENDENT_ROLLBACK_ORACLE_SEAL_TASK_20261003.md`
- `V4_NEXT_ROUND_EXECUTION_MASTER_R18R1R1R1_20261003.md`

This master is the highest scheduler.

## 3. Strict Sequence

```text
R18R1R1R1A
V4-14 candidate rollback drill / receipt
↓
R18R1R1R1B
independent rollback oracle + clean seal
↓
unified commit + push
↓
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

## 4. Do Not Reopen R5

Do not regenerate or redesign:

```text
full_dag_r5
30-edge consumption mapping
pre-call invocation runtime
cross-process trajectory
same-day revision logic
deterministic replay
consumption oracle
real accepted-source readback
```

Use them as frozen inputs to rollback testing.

## 5. Correct Rollback Scope

V4-14 has no Accepted Head and no production permission.

Therefore rollback is a candidate-activation rollback drill, not a production cutover.

Use isolated Stage Head copy / sandbox and prove:

```text
exact V4-13 predecessor
→ simulated candidate activation
→ injected failure
→ exact predecessor restoration
```

Actual formal heads must never change.

## 6. Reuse Governance

Reuse existing accepted promotion semantics:

```text
exact predecessor binding
atomic write
compare-and-swap / stale predecessor rejection
parent Stage archive
append-only candidate evidence
fail closed
```

Do not invent a parallel “latest candidate” discovery mechanism.

## 7. Mandatory Rollback Scenarios

```text
failure before activation
failure after sandbox activation
stale predecessor CAS
candidate byte mutation
predecessor byte mutation
repeat rollback idempotency
candidate evidence preserved
real protected heads unchanged
```

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
V4-15 runtime
Radar
Cohort
Settlement
raw/provider fallback
business algorithm redesign
threshold redesign
rewriting full_dag_r5
deleting candidate evidence
```

## 9. Required End State

```text
R18R1R1R1A_V4_14_ROLLBACK_DRILL = PASS_LOCAL
V4_14_ROLLBACK_RECEIPT = CREATED
ROLLBACK_TO_EXACT_V4_13_PREDECESSOR = PASS
REAL_PROTECTED_HEADS_UNCHANGED = PASS

R18R1R1R1B_INDEPENDENT_ROLLBACK_ORACLE = PASS_LOCAL
V4_14_ROLLBACK_RECEIPT = PASS

EDGE_CONSUMPTION_TRUTH = PASS
R18_REAL_ACCEPTED_SOURCE_REPLAY = PASS_CAPABILITY_SCOPED
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED

V4_14_RUNTIME_CANDIDATE =
READY_FOR_FINAL_EXTERNAL_AUDIT_WITH_ROLLBACK

V4_14_ACCEPTED_HEAD = NOT_CREATED
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_13_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30

ALGORITHM_STATE_REPLAY_PASS =
NOT_GRANTED_PENDING_EXTERNAL_AUDIT

NEXT = STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

## 10. Next After External Audit

Only if the next independent audit passes may the following round be authorized:

```text
V4-14 Accepted Head Promotion
+ Stage Head advance to V4_00_TO_V4_14_ACCEPTED
+ scoped/degraded ALGORITHM_STATE_REPLAY_PASS
+ V4-15 contract-first entry
```

Historical PIT effectiveness must remain explicitly `NOT_GRANTED` unless separately evidenced.
