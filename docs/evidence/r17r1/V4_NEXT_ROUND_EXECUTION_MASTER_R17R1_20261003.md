# V4 Next Round Execution Master R17R1｜2026-10-03

## 0. Baseline
Repository: `NanOns/a-share-market-structure-research`
Branch: `codex/v4-system-reform`
Execution baseline: `204d799f26a7badbce3d6b09d3ceed722c522c91`

Read:
- `V4_R17_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md`
- `V4_13_R17R1A_ACCEPTED_PACKAGE_ACTIVE_BINDING_REPAIR_TASK_20261003.md`
- `V4_14_R17R1B_CONTRACT_REFREEZE_ACTIVE_AUTHORITY_TASK_20261003.md`
- `V4_NEXT_ROUND_EXECUTION_MASTER_R17R1_20261003.md`

This master is the highest scheduler.

## 1. Audit Disposition
```text
R17A = PASS_KEEP
R17B_PROMOTION_MECHANICS = PASS_KEEP
R17B_V4_13_ACTIVE_PACKAGE_BINDINGS = FAIL_P0_REPAIR_REQUIRED
R17C_V4_14_CONTRACT_FREEZE = FAIL_P0_ACTIVE_AUTHORITY_CLOSURE
```

Do not roll back Stage.

## 2. Sequence
```text
R17R1A
V4-13 Accepted Package Active-Binding Repair
↓
ACTIVE_CONTRACT_FAMILY_CLOSURE = PASS
↓
V4_13_ACCEPTED_HEAD_AMENDED_R1 created
↓
Stage remains V4_00_TO_V4_13_ACCEPTED
↓
R17R1B
V4-14 v1.1 Contract Re-freeze
↓
ACTIVE_CONTRACT_FAMILY_CLOSURE = PASS
↓
clean detached regression
↓
unified commit + push
↓
STOP
```

## 3. Exact P0 Defect
Two active V4-13 contract artifacts still use superseded projection v1.0:

```text
config/v4_13_dag_edge_registry_v1_1.json
  D1 -> PROFILE / structure_projection
  -> config/v4_13_projection_v1.json

config/v4_13_rotation_structure_enrichment_schema_v1_1.json
  structure_schema
  -> config/v4_13_projection_v1.json
```

Formal active projection is:
`config/v4_13_projection_v1_2.json`
SHA `567b498c9e0f828dc041d56ab56e79c8a4d34877fd09eef46a9c1f504396b19c`

R17C copied the stale edge and its validator does not detect active-family supersession.

## 4. R17R1A
Create versioned same-family amendments:
- `v4_13_dag_edge_registry_v1_2.json`
- `v4_13_rotation_structure_enrichment_schema_v1_2.json`
- `v4_13_accepted_entry_contract_v1_1.json`
- `V4_13_ACCEPTED_HEAD_AMENDED_R1.json`

Update moving Stage binding to amended head.

Keep:
`accepted_stage_range = V4_00_TO_V4_13_ACCEPTED`
`Data Head = 2026-09-30`

Original V4-13 Accepted Head stays immutable.

## 5. R17R1B
Create versioned V4-14 v1.1 contract-freeze package.

Do not overwrite R17C v1.0 contracts.

Add recursive:
`ACTIVE_CONTRACT_FAMILY_CLOSURE`

Exact old refs must be rejected as active bindings even if hash/bytes are valid.

## 6. KEEP
Do not reopen:
- R17A historical governance;
- R16/R16R1 runtime;
- r6;
- Projection v1.2 semantics;
- V4-10/11/12 owner algorithms;
- R17C Replay Gate B dimensions except authority-binding correction.

## 7. Forbidden
- V4-14 runtime
- V4-14 Accepted Head
- ALGORITHM_STATE_REPLAY_PASS
- Production / Shadow / Focus
- Radar / Cohort / Settlement
- V4-15
- Data Head advance
- DB migration
- raw/provider fallback
- business algorithm redesign

## 8. Required End State
```text
R17R1A_V4_13_ACTIVE_BINDING_REPAIR = PASS
V4_13_ACCEPTED_HEAD_AMENDED_R1 = CREATED
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_13_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
R17R1B_V4_14_CONTRACT_REFREEZE = PASS_LOCAL
ACTIVE_CONTRACT_FAMILY_CLOSURE = PASS
V4_14_CONTRACT_COMPLETENESS = PASS_READY_FOR_EXTERNAL_AUDIT
V4_14_RUNTIME = NOT_IMPLEMENTED
ALGORITHM_STATE_REPLAY_PASS = NOT_GRANTED
NEXT = STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```
