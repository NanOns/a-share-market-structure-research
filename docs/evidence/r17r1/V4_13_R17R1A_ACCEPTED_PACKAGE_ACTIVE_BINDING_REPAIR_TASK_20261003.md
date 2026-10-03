# R17R1A｜V4-13 Accepted Package Active-Binding Repair｜2026-10-03

## 0. Baseline
Use only current remote HEAD:
`204d799f26a7badbce3d6b09d3ceed722c522c91`

Read:
- `V4_R17_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md`
- `V4_13_R17R1A_ACCEPTED_PACKAGE_ACTIVE_BINDING_REPAIR_TASK_20261003.md`
- `V4_NEXT_ROUND_EXECUTION_MASTER_R17R1_20261003.md`

## 1. KEEP
Do not reopen R17A historical governance, R16/R16R1 runtime, r6, V4-13 business semantics, Projection v1.2 semantics, current Stage range, or Data Head.

Original `data/v4/V4_13_ACCEPTED_HEAD.json` is immutable historical evidence.

## 2. Repair DAG Registry
Create `config/v4_13_dag_edge_registry_v1_2.json`.

Requirements:
- same `contract_id = V4_13_DAG_INTEGRATION_INTERFACE_V1`;
- exact `supersedes` to v1.1;
- preserve all topology/time/quality semantics;
- only repair stale `D1 -> PROFILE / structure_projection` binding to exact `config/v4_13_projection_v1_2.json`;
- no threshold/owner/edge changes.

## 3. Repair Rotation/Structure Enrichment
Create `config/v4_13_rotation_structure_enrichment_schema_v1_2.json`.

Requirements:
- same `contract_id = ROTATION_STRUCTURE_ENRICHMENT_V1`;
- exact `supersedes` to v1.1;
- preserve rotation and V4-12 structure semantics;
- change only `structure_schema` to exact projection v1.2.

## 4. Active Contract Family Closure
Create machine-readable active-package closure for all V4-13 contract families.

At minimum:
- `PROFILE_ADVANCED_PROJECTION_V1 -> projection v1.2`
- `V4_13_DAG_INTEGRATION_INTERFACE_V1 -> DAG v1.2`
- `ROTATION_STRUCTURE_ENRICHMENT_V1 -> enrichment v1.2`

Each active member records exact path/hash/bytes/version/lineage.

## 5. New Accepted Contract Entry
Do not overwrite `config/v4_13_accepted_entry_contract_v1.json`.

Create a versioned amendment, recommended:
`config/v4_13_accepted_entry_contract_v1_1.json`

It must bind the corrected active package and independently recompute the package digest.

## 6. Amended V4-13 Accepted Head
Create:
`data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json`

It must preserve:
- exact r6 candidate;
- all capabilities;
- all permissions=false;
- real capability degradation.

It must bind:
- original V4-13 Accepted Head as predecessor/history;
- new accepted-entry contract;
- this external audit as amendment authority.

Do not modify original V4-13 Accepted Head bytes.

## 7. Stage Head Amendment
Archive current exact Stage Head first.

Update moving `data/v4/V4_STAGE_ACCEPTED_HEAD.json` only to bind the amended V4-13 head/package.

Keep exactly:
- `accepted_stage_range = V4_00_TO_V4_13_ACCEPTED`
- production=false
- shadow=false
- focus=false
- global mandatory adoption=false

`V4_DATA_ACCEPTED_HEAD.json` must remain byte-identical.

## 8. Active-Family Validator
Add an independent validator that rejects a superseded same-family contract when used in a current runtime/consumer binding.

Negative tests:
- DAG edge -> projection v1.0 => REJECT
- enrichment structure_schema -> projection v1.0 => REJECT
- exact old path/hash but superseded family member => REJECT
- active same-family v1.2 => ACCEPT
- historical `supersedes`/`derived_from` refs => ACCEPT only in lineage role

## 9. Protected
Must remain byte-identical:
- `AGENTS.md`
- `data/v4/V4_DATA_ACCEPTED_HEAD.json`
- `data/v4/V4_12_ACCEPTED_HEAD.json`
- `data/v4/V4_13_ACCEPTED_HEAD.json`
- `reports/v4_13_runtime_r16/real/2026-09-30/r6/*`

## 10. Forbidden
- V4-14 runtime
- ALGORITHM_STATE_REPLAY_PASS
- V4-14 Accepted Head
- Data Head advance
- Production / Shadow / Focus
- Radar / Cohort / Settlement
- DB migration
- business algorithm changes

## 11. Completion
```text
R17R1A_V4_13_ACTIVE_BINDING_REPAIR = PASS
V4_13_ACCEPTED_HEAD_AMENDED_R1 = CREATED
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_13_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
ACTIVE_CONTRACT_FAMILY_CLOSURE = PASS
NEXT = R17R1B_V4_14_CONTRACT_REFREEZE
```
