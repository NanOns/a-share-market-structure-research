# V4 Next Round Execution Master R20｜2026-10-03

## 0. Baseline
Repository:
`NanOns/a-share-market-structure-research`

Branch:
`codex/v4-system-reform`

Execution baseline:
`2020234020e09020aca13fd84cdabde6fbb81f50`

## 1. External Audit Decision
```text
R19_EXTERNAL_AUDIT =
PARTIAL_PASS_CURRENT_STAGE_RUNTIME_ENTRY_REPAIR_REQUIRED

R19A_V4_14_ACCEPTED_HEAD = PASS_KEEP
R19B_RADAR_COHORT_CONTRACT_FREEZE = PASS_KEEP
R19C_SETTLEMENT_CONTRACT_FREEZE = PASS_KEEP
R19D_V4_15_CONTRACT_INTEGRATION = PASS_KEEP

V4_15_CONTRACT_PACKAGE =
EXTERNALLY_ACCEPTED_CONTRACT_SCOPE_RUNTIME_ENTRY_BLOCKED

R19_AUDIT_01_BYTE_IDENTITY_PORTABILITY = OPEN_P1
R19_AUDIT_02_CURRENT_STAGE_READER_COMPATIBILITY = FAIL_P0
```

## 2. Read These Files
- `V4_R19_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md`
- `V4_R20A_CURRENT_STAGE_AUTHORITY_READER_GOVERNANCE_REPAIR_TASK_20261003.md`
- `V4_R20B_HISTORICAL_BYTE_IDENTITY_PORTABILITY_CLOSURE_TASK_20261003.md`
- `V4_R20C_RADAR_COHORT_RUNTIME_TASK_20261003.md`
- `V4_R20D_SETTLEMENT_RUNTIME_TASK_20261003.md`
- `V4_R20E_FULL_PERSISTED_E2E_INDEPENDENT_ORACLE_SEAL_TASK_20261003.md`
- `V4_NEXT_ROUND_EXECUTION_MASTER_R20_20261003.md`

This master is the highest scheduler.

## 3. Execution Topology
```text
R20A [P0]
Current Stage Authority / Reader Governance Repair
        ↓ PASS_LOCAL
        ├──────────────→ R20C Radar/Cohort Runtime
        └──────────────→ R20D Settlement Runtime

R20B [P1]
Byte Identity Portability Closure
runs in parallel; does not block C/D

R20A + R20B + R20C + R20D PASS_LOCAL
        ↓
R20E Full Persisted E2E + Independent Oracle + Clean Seal
        ↓
unified commit + push
        ↓
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

## 4. R20A Is the Only Runtime Entry Blocker
Before R20A PASS_LOCAL:
```text
V4_15 runtime engineering = forbidden
```

After R20A PASS_LOCAL:
```text
R20C and R20D = authorized engineering work
```

R20B does not block R20C/R20D.

## 5. R20A Required Repair
Current Stage Head currently contradicts itself:
```text
accepted_stage_range = V4_00_TO_V4_14_ACCEPTED
v4_14_status = ALGORITHM_STATE_REPLAY_DEGRADED_PASS
v4_14_entry = CONTRACT_FREEZE_ONLY_NOT_REPLAY_PASS
```

Repair current Stage Head metadata and create a stage-aware current authority reader.

Current runtime authority must root at:
```text
data/v4/V4_14_ACCEPTED_HEAD.json
```

Do not run current V4-14/V4-15 runtime through historical V4-13 Stage assertions.

Historical validators remain frozen against historical archived Stage Heads.

## 6. R20B Parallel Governance Work
Close CRLF/LF byte portability explicitly.

Do not rewrite historical accepted artifacts.

Create a representation registry and a portable exact reader with explicit modes.

Do not normalize binary/LFS.

Future clean-tested source must be remotely addressable; bundle-only identity is no longer sufficient.

## 7. R20C Scope
Implement engineering:
```text
V4-14 accepted publication
→ Radar
→ complete daily ledger
→ logical event/observation
→ enrollment
→ Validation Cohort
```

No Focus/UI filtering.

No owner recomputation.

No future data at T0.

No V4-15 promotion.

## 8. R20D Scope
Implement engineering:
```text
enrollment
→ benchmark/controls T0 freeze
→ due planner
→ future accepted source
→ price path
→ competing outcomes
→ outcome revision
→ readback
```

Use exact accepted formulas.

No invented marked-estimate numeric threshold.

No production migration.

## 9. R20E Scope
Run one persisted full path:
```text
current V4-14 authority
→ Radar/Cohort
→ T0 freeze
→ due planner
→ future readback
→ settlement/revision/readback
```

Independent oracle must not call runtime evaluators to derive expected results.

R20E requires R20B closed before final seal.

## 10. Frozen Inputs
Do not rewrite:
- V4-08..V4-14 accepted business algorithms;
- V4-14 Accepted Head;
- full_dag_r5;
- V4-14 consumption/rollback evidence;
- R19 V4-15 frozen contract semantics;
- Data Head.

## 11. Global Forbidden
Until the next independent external audit:
```text
V4_15_ACCEPTED_HEAD
Stage Head > V4_00_TO_V4_14_ACCEPTED
Data Head advance
Production
Shadow
Focus
V4-16
FEP runtime
raw/provider fallback
business threshold redesign
formal production DB migration apply
rewriting historical accepted heads to fix line endings
```

## 12. Required End State
```text
R20A_CURRENT_STAGE_AUTHORITY = PASS_LOCAL
STAGE_HEAD_V4_14_ENTRY_COHERENCE = PASS
CURRENT_V4_14_READER = PASS
HISTORICAL_READER_ISOLATION = PASS

R20B_BYTE_IDENTITY_PORTABILITY = PASS_LOCAL
R19_AUDIT_01 = CLOSED_LOCAL

R20C_V4_15_RADAR_COHORT_RUNTIME = PASS_LOCAL
R20D_V4_15_SETTLEMENT_RUNTIME = PASS_LOCAL

R20E_V4_15_FULL_PERSISTED_E2E = PASS_LOCAL
R20E_INDEPENDENT_ORACLE = PASS_LOCAL

R19_AUDIT_02 = CLOSED_LOCAL

V4_15_RUNTIME_CANDIDATE =
READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

REAL_ACCEPTED_SOURCE_V4_15 =
PASS_CAPABILITY_SCOPED

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED

V4_15_ACCEPTED_HEAD = NOT_CREATED
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_14_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30

Production = false
Shadow = false
Focus = false
V4_16 = false

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

## 13. Next After External Audit
Only if R20 runtime candidate passes external audit may the following round:
- create V4-15 Accepted Head;
- advance Stage Head to V4-15;
- authorize V4-16 realtime shadow entry.

Historical PIT effectiveness must remain separately scoped unless new evidence actually closes it.
