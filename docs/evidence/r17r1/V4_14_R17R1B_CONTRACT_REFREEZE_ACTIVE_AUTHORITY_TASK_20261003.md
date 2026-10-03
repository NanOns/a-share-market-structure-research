# R17R1B｜V4-14 Replay Gate B Contract Re-freeze Against Active Authority｜2026-10-03

## 0. Entry
Execute only after:
```text
R17R1A_V4_13_ACTIVE_BINDING_REPAIR = PASS
ACTIVE_CONTRACT_FAMILY_CLOSURE = PASS
```

Do not overwrite R17C V4-14 v1.0 files.

## 1. Goal
Create a corrected V4-14 v1.1 contract-freeze package bound to the amended active V4-13 authority.

This round remains contract-only. Do not implement V4-14 replay runtime.

## 2. Versioned V4-14 Contracts
Create same-family successors, recommended:
- `config/v4_14_replay_gate_b_contract_v1_1.json`
- `config/v4_14_replay_case_registry_v1_1.json`
- `config/v4_14_temporal_non_edge_registry_v1_1.json`
- `config/v4_14_quality_degradation_v1_1.json`
- `config/v4_14_machine_vectors_v1_1.json`

Each must keep the same contract_id, monotonic version, and exact supersedes.

## 3. Required Active Authority
The new package must bind:
- `data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json`
- active projection v1.2
- active DAG v1.2
- active Rotation/Structure Enrichment v1.2

No active runtime/replay edge may bind `config/v4_13_projection_v1.json`.

Old members are allowed only in explicit lineage roles such as `supersedes`, `derived_from`, or historical lineage.

## 4. Rebuild Replay DAG From Active Package
Do not blindly copy V4-13 DAG v1.1.

Resolve through the amended active package:
- `D1 -> PROFILE / structure_projection` must bind projection v1.2;
- Rotation/Structure enrichment must bind enrichment v1.2.

## 5. ACTIVE_CONTRACT_FAMILY_CLOSURE Gate
Upgrade the independent V4-14 validator to prove:
1. V4-14 refs point to current accepted/amended heads.
2. Every current owner edge resolves to active contract versions.
3. Superseded same-family members cannot be current consumer/runtime bindings.
4. Historical lineage refs remain allowed only in explicit lineage fields.
5. V4-14 v1.1 files have correct supersedes lineage.

Negative tests must substitute exact old refs and still be rejected.

## 6. Preserve R17C Semantics
KEEP all 17 Replay Gate B dimensions and temporal rules.

Do not change expected behaviors unrelated to authority repair.

## 7. Required Gate
```text
R17R1B_V4_14_CONTRACT_REFREEZE = PASS_LOCAL
ACTIVE_CONTRACT_FAMILY_CLOSURE = PASS
V4_14_CONTRACT_COMPLETENESS = PASS_READY_FOR_EXTERNAL_AUDIT
V4_14_RUNTIME = NOT_IMPLEMENTED
ALGORITHM_STATE_REPLAY_PASS = NOT_GRANTED
```

## 8. Regression
Run:
- R17A governance tests;
- R17B promotion/current-head tests updated for amended head;
- R16/R16R1 V4-13 runtime regressions;
- V4-13 active-family closure tests;
- R17C replay-contract tests against v1.1 package;
- stale-ref negative substitutions.

No broad deselection.

## 9. Protected
Keep byte-identical:
- `AGENTS.md`
- `data/v4/V4_DATA_ACCEPTED_HEAD.json`
- `data/v4/V4_12_ACCEPTED_HEAD.json`
- `data/v4/V4_13_ACCEPTED_HEAD.json`

During R17R1B, also keep the new amended V4-13 head and Stage Head byte-identical.

## 10. Forbidden
- V4-14 runtime
- V4_14_ACCEPTED_HEAD
- ALGORITHM_STATE_REPLAY_PASS
- Production / Shadow / Focus
- V4-15
- Data Head advance
- DB migration
- algorithm threshold changes

## 11. Final
```text
R17R1A_V4_13_ACTIVE_BINDING_REPAIR = PASS
R17R1B_V4_14_CONTRACT_REFREEZE = PASS_LOCAL
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_13_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_14_CONTRACT_COMPLETENESS = PASS_READY_FOR_EXTERNAL_AUDIT
V4_14_RUNTIME = NOT_IMPLEMENTED
ALGORITHM_STATE_REPLAY_PASS = NOT_GRANTED
NEXT = STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

After clean detached validation, unified commit + push, STOP.
