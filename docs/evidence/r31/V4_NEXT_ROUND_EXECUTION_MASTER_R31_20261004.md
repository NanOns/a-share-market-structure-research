# V4 Next Round Execution Master R31｜V4-22 Independent Audit Contract Design｜2026-10-04

## 0. Baseline

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`  
Execution baseline: `791543c3bdbd4b80b2679b447d257cc27dd504ad`

## 1. Current External State

```text
R30R1_EXTERNAL_AUDIT =
PASS_FINAL_NATIVE_SESSION_STATUS_AND_OWNER_BINDING_REPAIR

V4_21_CONTRACT_DESIGN =
EXTERNALLY_ACCEPTED_SCOPED

V4_21_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_REAL_OBSERVATION

R30R1_P2_LEDGER_REFERENTIAL_INTEGRITY_VECTOR =
OPEN_NONBLOCKING_CARRY_TO_V4_22
```

## 2. Execute

Execute:

`V4_22_R31_INDEPENDENT_AUDIT_CONTRACT_DESIGN_TASK_20261004.md`

This is CONTRACT_DESIGN_ONLY.

## 3. Topology

```text
audit status vocabulary
        ↓
domain registry
        ↓
data / algorithm / publication
        ↓
Shadow / UI / Forward
        ↓
migration / cutover / rollback
        ↓
open-item registry
        ↓
R30R1 referential-integrity audit vectors
        ↓
independent oracle rules
        ↓
tested-source governance
        ↓
final verdict formula
        ↓
current NOT_READY gate
        ↓
protected-state verification
        ↓
clean regression
        ↓
contract candidate seal
        ↓
STOP_WAIT_R31_INDEPENDENT_EXTERNAL_AUDIT
```

## 4. Hard Boundary

Do not:

```text
close current real-evidence open items
grant V4_17G
grant MIGRATION_REPLAY_PASS
grant production_permission
switch Focus/default UI
write real Forward evidence
create V4_22_ACCEPTED_HEAD
claim V4_22_FINAL_PASS
```

## 5. Exit

```text
V4_22_CONTRACT_DESIGN =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

V4_22_FINAL_AUDIT_ENTRY =
BLOCKED_WAIT_REAL_GATES

V4_22_FINAL_PASS =
NOT_GRANTED

NEXT =
STOP_WAIT_R31_INDEPENDENT_EXTERNAL_AUDIT
```
