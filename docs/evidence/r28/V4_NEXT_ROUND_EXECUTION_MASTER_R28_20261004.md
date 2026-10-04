# V4 Next Round Execution Master R28｜V4-19 Focus Source Cutover Contract Design｜2026-10-04

## 0. Baseline

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`  
Execution baseline: `94635fa369c60b3f8182cb4d813751a453682d88`

## 1. Current External State

```text
R27_EXTERNAL_AUDIT =
PASS_FINAL_V4_18_MIGRATION_REPLAY_CONTRACT_DESIGN_SCOPED

V4_18_CONTRACT_DESIGN =
EXTERNALLY_ACCEPTED

V4_18_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_REAL_SHADOW_GATE

MIGRATION_REPLAY_PASS =
NOT_GRANTED

R25 =
WAIT_ACCEPTED_DAILY_INPUT
```

## 2. Execute

Execute:

`V4_19_R28_FOCUS_SOURCE_CUTOVER_CONTRACT_DESIGN_TASK_20261004.md`

This is CONTRACT_DESIGN_ONLY.

## 3. Topology

```text
CUTOVER_V2 machine contract
        ↓
capability registry
        ↓
permission formula
        ↓
dependency permission matrix
        ↓
Focus source routing
        ↓
mixed production/shadow UI policy
        ↓
cutover receipt schema
        ↓
cutover CAS
        ↓
capability rollback
        ↓
C01-C20 design vectors
        ↓
current all-permissions-false gate
        ↓
protected-state verification
        ↓
clean regression
        ↓
contract candidate seal
        ↓
STOP_WAIT_R28_INDEPENDENT_EXTERNAL_AUDIT
```

## 4. Hard Boundary

Do not:

```text
grant production_permission
switch Focus source
write production routing
count replay as real Shadow
create V4_19_ACCEPTED_HEAD
claim any capability cut over
```

## 5. Exit

```text
V4_19_CONTRACT_DESIGN =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

V4_19_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_REAL_GATES

production_permission[*] =
false

Focus source cutover =
false

NEXT =
STOP_WAIT_R28_INDEPENDENT_EXTERNAL_AUDIT
```
