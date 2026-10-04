# V4 Next Round Execution Master R30R1｜V4-21 Native Session Status Repair｜2026-10-04

## 0. Baseline

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`  
Execution baseline: `3f0663804bf104dd3e61e65d9927cb7f2081fa3b`

## 1. External Audit Decision

```text
R30_EXTERNAL_AUDIT =
PARTIAL_PASS_NATIVE_SESSION_STATUS_BINDING_REPAIR_REQUIRED

R30_CORE_FORWARD_OBSERVATION_DESIGN =
PASS_KEEP

R30_NATIVE_SESSION_STATUS_BINDING =
FAIL_P0

R30_SHADOW_SESSION_OWNER_BINDING =
FAIL_P0

R30_PRODUCTION_SESSION_AUTHORITY =
P1_REPAIR_SAME_ROUND
```

## 2. Execute

Execute only:

`V4_21_R30R1_NATIVE_SESSION_STATUS_AND_OWNER_BINDING_REPAIR_TASK_20261004.md`

## 3. Topology

```text
bind accepted V4-16 Observation Slot V2
        ↓
freeze native Shadow slot states
        ↓
separate native status from evaluability
        ↓
repair session count/streak semantics
        ↓
formalize future Production session authority
        ↓
repair observation receipt status semantics
        ↓
update F21-01 / F21-05 / F21-06
        ↓
add S21-01 through S21-08
        ↓
protected-state verification
        ↓
clean regression
        ↓
candidate seal
        ↓
STOP_WAIT_R30R1_INDEPENDENT_EXTERNAL_AUDIT
```

## 4. Hard Boundary

Do not:

```text
create real observation writer
create new settlement owner
write real Forward evidence
grant any capability gate
change Focus/default UI routing
create V4_21_ACCEPTED_HEAD
```

## 5. Exit

```text
R30R1_NATIVE_SESSION_STATUS_BINDING =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

V4_21_CONTRACT_DESIGN =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

V4_21_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_REAL_OBSERVATION

REAL_CONTINUED_FORWARD_OBSERVATION =
NOT_STARTED

NEXT =
STOP_WAIT_R30R1_INDEPENDENT_EXTERNAL_AUDIT
```
