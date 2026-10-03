# V4 Next Round Execution Master R17｜2026-10-03

## 0. Only Baseline

```text
Repository: NanOns/a-share-market-structure-research
Branch: codex/v4-system-reform
Execution baseline: f12315bf8e3142aa44e9068c5895004c35c4e23c
```

R16R1 external audit:

```text
R16R1_EXTERNAL_AUDIT = PASS_SCOPED_ENGINEERING
```

Current formal heads before R17:

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_12_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_13_ACCEPTED_HEAD = NOT_CREATED
```

## 1. Read These Files

```text
V4_R16R1_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md
V4_R17A_CROSS_STAGE_ACCEPTED_CHAIN_HISTORICAL_VALIDATOR_REPAIR_TASK_20261003.md
V4_R17B_V4_13_ACCEPTED_HEAD_PROMOTION_TASK_20261003.md
V4_R17C_V4_14_REPLAY_GATE_B_CONTRACT_FREEZE_ENTRY_TASK_20261003.md
```

This master is the highest execution scheduler for the round.

## 2. Execution Order

Strict sequence:

```text
R17A
Cross-stage Accepted-Chain / Historical Validator Repair
↓
R17A clean gate PASS

R17B
V4-13 Accepted Head Promotion
↓
Stage Head = V4_00_TO_V4_13_ACCEPTED
↓
R17B promotion gate PASS

R17C
V4-14 Replay Gate B Contract Freeze / Stage Entry
↓
V4_14_CONTRACT_COMPLETENESS = PASS_READY_FOR_EXTERNAL_AUDIT
↓
unified commit + push
↓
STOP
```

R17A and R17B are not optional.

R17C begins immediately after R17B local promotion gate passes; do not wait for forward samples.

## 3. KEEP

Do not reopen:

```text
R15 C01-C04
R15R1 lineage cleanup
R16 accepted input binder
R16 target-excluded LOO
R16 append-only publication
R16 fresh-process readback
R16R1 projection v1.2 semantics
R16R1 component provenance
R16R1 O01-O10 oracle
R16R1 numeric revision ordering
R16R1 publication hardening
V4-12 accepted algorithms
```

## 4. R17A Gate

Required:

```text
DM01_HISTORICAL_STAGE_BINDING = PASS
HISTORICAL_STAGE_VALIDATOR_MAINTENANCE = PASS
EXPANDED_CURRENT_REGRESSION = PASS
```

No Stage Head mutation in R17A.

## 5. R17B Gate

Only after R17A PASS:

Create:

```text
data/v4/V4_13_ACCEPTED_HEAD.json
```

Promote exact R16R1 r6 candidate and exact v1.2 projection contract.

Advance:

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_13_ACCEPTED
```

Keep:

```text
V4_DATA_ACCEPTED_HEAD = 2026-09-30
```

Permissions remain false.

## 6. R17C Gate

Only after R17B PASS:

Freeze V4-14 Replay Gate B contracts/vectors.

Do not claim:

```text
ALGORITHM_STATE_REPLAY_PASS
```

R17C is contract freeze / implementation-entry authorization only.

## 7. Global Forbidden

Throughout R17:

```text
Production
Shadow
Focus
Radar/Cohort/Settlement
formal DB migration
Data Head advance
raw/provider fallback
historical PIT overclaim
algorithm threshold redesign
V4-14 Accepted Head
V4-15 work
```

## 8. Required Final State

The only allowed end-of-round state is:

```text
R17A_CROSS_STAGE_GOVERNANCE_REPAIR = PASS

R17B_V4_13_ACCEPTED_HEAD_PROMOTION = PASS

V4_13_ACCEPTED_HEAD = CREATED_EXTERNALLY_AUTHORIZED_ENGINEERING_SCOPE

V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_13_ACCEPTED

V4_DATA_ACCEPTED_HEAD = 2026-09-30

R17C_V4_14_CONTRACT_FREEZE_ENTRY = PASS_LOCAL

V4_14_CONTRACT_COMPLETENESS = PASS_READY_FOR_EXTERNAL_AUDIT

V4_14_RUNTIME = NOT_IMPLEMENTED

ALGORITHM_STATE_REPLAY_PASS = NOT_GRANTED

NEXT = STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

After unified commit + push, STOP.
