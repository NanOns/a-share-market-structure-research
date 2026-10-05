# V4 FEP Execution Master｜V4-15E2 R1R2 ENTRY Event Repair｜2026-10-05

## Baseline

`f8708c34063238547127cab4baefb17c2e5825ac`

## Execute Only

`V4_15E2_R1R2_ENTRY_EVENT_STRATIFICATION_AND_OWNER_GAP_REPAIR_TASK_20261005.md`

## PASS_KEEP

```text
historical real-source scan
historical window
feature replay
RPS replay
V4-15 label adapter
conditional mechanics
policy applicability engine
representativeness semantics
artifact registry
regression accounting
```

## Repair Topology

```text
split ENTRY event strata
        ↓
FIRST_PREWATCH complete population
        ↓
NEW_CONFIRMED exact-owner gate
        ↓
REENTRY exact-owner gate
        ↓
supersede pooled ENTRY baseline
        ↓
event-specific support policy
        ↓
FIRST_PREWATCH:T1 baseline
        ↓
full regression
        ↓
STOP external audit
```

## Forbidden

```text
no fake frozen_invalidation
no raw-bar reimplementation of episode invalidation
no pooled ENTRY statistics
no deletion of old R1R1 evidence
no E3
no model fitting
no production/shadow/priority permission
```

## Exit

```text
V4_15E2_R1R2_REPAIR =
PASS_LOCAL_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

ADMITTED_ENTRY_EVENT_SCOPE =
FIRST_PREWATCH:T1

REENTRY =
UNSET_OWNER_INPUT_NOT_AVAILABLE

NEXT =
STOP_WAIT_V4_15E2_R1R2_INDEPENDENT_EXTERNAL_AUDIT
```
