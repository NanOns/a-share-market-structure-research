# V4 Next Round Execution Master R27｜2026-10-04

## 0. Baseline
Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`  
Execution baseline: `c1787b77e08a26e344d3cbb88148a60f93c3df3e`

## 1. External State
```text
R26_EXTERNAL_AUDIT = PASS_FINAL_V4_17_SHADOW_UI_ENGINEERING_SCOPED
V4_17_ENGINEERING = EXTERNALLY_ACCEPTED
V4_17_FINAL_ACCEPTANCE = NOT_GRANTED
R25_REAL_ACTIVATION_PACKET = WAIT_ACCEPTED_DAILY_INPUT
REAL_SHADOW_OBSERVATIONS = 0
```

## 2. Execute
Execute only:
`V4_18_R27_MIGRATION_REPLAY_CONTRACT_DESIGN_TASK_20261004.md`

This is CONTRACT_DESIGN_ONLY.

## 3. Topology
```text
migration namespace matrix
→ pre-state inheritance
→ open episode/enrollment preservation
→ pending settlement preservation
→ Focus/user-pin preservation
→ cutover-gap policy
→ rollback contract
→ M01-M20 vector registry
→ implementation-entry gate
→ protected-state check
→ clean regression
→ contract candidate seal
→ STOP_WAIT_R27_INDEPENDENT_EXTERNAL_AUDIT
```

## 4. Hard Boundary
Do not execute migration, start production migration writer, change production Focus, switch Shadow/Legacy source, claim `MIGRATION_REPLAY_PASS`, or create `V4_18_ACCEPTED_HEAD`.

## 5. Exit
```text
V4_18_CONTRACT_DESIGN = PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT
V4_18_IMPLEMENTATION_ENTRY = BLOCKED_WAIT_REAL_SHADOW_GATE
MIGRATION_REPLAY_PASS = NOT_GRANTED
R25_REAL_ACTIVATION_PACKET = WAIT_ACCEPTED_DAILY_INPUT
NEXT = STOP_WAIT_R27_INDEPENDENT_EXTERNAL_AUDIT
```
