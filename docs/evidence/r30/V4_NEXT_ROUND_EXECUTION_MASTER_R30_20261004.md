# V4 Next Round Execution Master R30｜V4-21 Continued Forward Observation Contract Design｜2026-10-04

## 0. Baseline

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`  
Execution baseline: `c38c25dd189b3996f53e85dc64bbc142db1c188e`

## 1. Current External State

```text
R29_EXTERNAL_AUDIT =
PASS_FINAL_V4_20_DEFAULT_UI_CUTOVER_CONTRACT_DESIGN_SCOPED

V4_20_CONTRACT_DESIGN =
EXTERNALLY_ACCEPTED

V4_20_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_PRODUCTION_PERMISSION

DEFAULT_UI_CUTOVER =
false

R28_P2_TRANSITIVE_ROLLBACK_VECTOR_COVERAGE =
CLOSED
```

## 2. Execute

Execute:

`V4_21_R30_CONTINUED_FORWARD_OBSERVATION_CONTRACT_DESIGN_TASK_20261004.md`

This is CONTRACT_DESIGN_ONLY.

## 3. Topology

```text
evidence-lane registry
        ↓
accepted-session ledger
        ↓
event/cohort ledger
        ↓
due/outcome ledger
        ↓
right-censor policy
        ↓
stratification
        ↓
Shadow/Production continuity
        ↓
gate readback
        ↓
observation receipt
        ↓
F21-01 through F21-20
        ↓
current zero-real-evidence gate
        ↓
protected-state verification
        ↓
clean regression
        ↓
contract candidate seal
        ↓
STOP_WAIT_R30_INDEPENDENT_EXTERNAL_AUDIT
```

## 4. Hard Boundary

Do not:

```text
create a new settlement engine
write real forward observations
change production permission
change Focus source
change default UI source
create V4_21_ACCEPTED_HEAD
```

## 5. Exit

```text
V4_21_CONTRACT_DESIGN =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

V4_21_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_REAL_OBSERVATION

REAL_CONTINUED_FORWARD_OBSERVATION =
NOT_STARTED

NEXT =
STOP_WAIT_R30_INDEPENDENT_EXTERNAL_AUDIT
```
