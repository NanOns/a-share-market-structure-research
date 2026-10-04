# V4-18 R27｜Migration Replay Contract Design Task｜2026-10-04

## 0. Mission
Freeze the V4-18 Migration Replay contract while V4-16 real Shadow activation remains pending.

This is `CONTRACT_DESIGN_ONLY`, not implementation and not `MIGRATION_REPLAY_PASS`.

Execution baseline: `c1787b77e08a26e344d3cbb88148a60f93c3df3e`

External authority: `V4_R26_V4_17_SHADOW_UI_ENGINEERING_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md`

## 1. Hard Stage Boundary
REV4 requires V4-18 implementation after the real Shadow gate. Therefore R27 must not execute migration, switch namespaces, write production Focus, move pending real outcomes, create `V4_18_ACCEPTED_HEAD`, or claim `MIGRATION_REPLAY_PASS`.

## 2. Machine Contract
Create a versioned contract, recommended:
```text
config/v4_18_migration_replay_contract_v1.json
```
Freeze source/target namespaces, migration identities, predecessor rules, episode/enrollment identity, settlement identity, Focus/user-pin policy, UNKNOWN behavior, idempotency and rollback ownership.

## 3. Namespace Matrix
Explicitly cover:
```text
LEGACY_PRODUCTION
V3_FOCUS
SHADOW_V4
V4_PRODUCTION_FUTURE
```
For every state/table define read source, write target, copy/reference/carry/not-migrated behavior, immutable source identity, target identity rule and rollback behavior.

## 4. Pre-State Inheritance
Freeze the first production-V4 predecessor rule. Reconstructed initialization may initialize state but must never be relabeled as real PIT history. After cutover, prior accepted V4 state must be exact.

## 5. Open Episodes / Enrollments
Preserve logical_event_id, episode_id, T0, current state, original enrollment, controls, benchmarks and source lineage. Migration must never create a second original episode/enrollment.

## 6. Pending Settlement
Carry every accepted due obligation across migration, including enrollment_id, horizon, due_date, frozen T0, controls, benchmarks, outcome status/revision and future-source policy. Rollback cannot delete or redraw pending obligations.

## 7. Focus / User State
Separate algorithm eligibility, system-selected Focus, user-pinned Focus and manual notes/follow-up state. User pins/manual work must not be interpreted as algorithm evidence and must survive rollback.

## 8. Context Identity
Historical accepted Shadow context tokens/publication identities remain immutable/queryable. Cutover must not rewrite old Shadow contexts into production namespace.

## 9. Idempotency / Gap Policy
Freeze migration_run_id, source_head_digest, expected target head, logical_event/enrollment/due identities and user-pin identity. Replays with identical inputs must not duplicate logical state.

Define exact reconciliation if Legacy or Shadow receives accepted activity between snapshot and final cutover. No “restore one DB backup and ignore the gap”.

## 10. Rollback
Rollback must stop new V4 production writes, restore Legacy production read/write source, preserve accepted V4/Shadow history, preserve pending settlement, preserve user pins/manual state and emit a cutover-gap manifest. It must never delete accepted V4 facts.

## 11. UNKNOWN / Conflict
Identity collision, missing original enrollment, control/benchmark mismatch, due identity mismatch, user-pin ambiguity or namespace collision => `BLOCKED_AFFECTED_SCOPE`.

## 12. M01-M20 Contract Vectors
Define at minimum:
```text
M01 clean pre-state inheritance
M02 first production predecessor
M03 open episode preserved
M04 duplicate original rejected
M05 pending due preserved
M06 settlement revision preserved
M07 user pin preserved
M08 algorithm Focus vs user pin separated
M09 namespace mismatch blocked
M10 rerun idempotent
M11 source head changed after snapshot
M12 target-head CAS conflict
M13 Legacy cutover-gap activity
M14 Shadow cutover-gap activity
M15 rollback preserves V4 history
M16 rollback preserves pending settlement
M17 rollback preserves user pins
M18 reconstructed initialization not promoted to PIT
M19 historical context token remains queryable
M20 implicit latest/mtime migration source forbidden
```

## 13. Future Implementation Interfaces
Freeze interfaces for:
```text
MigrationSnapshotReader
MigrationPlanBuilder
MigrationReplayWriter
MigrationGapReconciler
MigrationRollbackController
MigrationIndependentOracle
```
R27 must not implement the production writer.

## 14. Future Implementation Entry Gate
Require before implementation:
```text
at least one externally accepted real V4-16 Shadow publication
accepted V4-17 real readback binding
accepted migration source snapshot
accepted target storage contract
accepted cutover/rollback authority
```
Otherwise:
```text
V4_18_IMPLEMENTATION_ENTRY = BLOCKED_WAIT_REAL_SHADOW_GATE
```

## 15. Carry Current State
```text
R25_REAL_ACTIVATION_PACKET = WAIT_ACCEPTED_DAILY_INPUT
V4_17_ENGINEERING = EXTERNALLY_ACCEPTED
V4_17_FINAL_ACCEPTANCE = NOT_GRANTED
```
Do not manufacture real Shadow data.

## 16. Protected State
Do not modify Stage/Data/V4-15 heads, V4-16 activation authority, V4-17 source authority, real Shadow counters or production Focus source. Do not create `V4_18_ACCEPTED_HEAD`.

## 17. Evidence
Recommended:
```text
reports/r27/MIGRATION_CONTRACT_GATE.json
reports/r27/NAMESPACE_MATRIX.json
reports/r27/PRESTATE_INHERITANCE_GATE.json
reports/r27/OPEN_EPISODE_GATE.json
reports/r27/PENDING_SETTLEMENT_GATE.json
reports/r27/FOCUS_USER_STATE_GATE.json
reports/r27/CUTOVER_GAP_POLICY.json
reports/r27/ROLLBACK_CONTRACT_GATE.json
reports/r27/MIGRATION_VECTOR_REGISTRY.json
reports/r27/IMPLEMENTATION_ENTRY_GATE.json
reports/r27/PROTECTED_BYTES.json
reports/r27/LOCAL_TEST_SUMMARY.json
reports/r27/CLEAN_REGRESSION.json
reports/r27/R27_CONTRACT_CANDIDATE_SEAL.json
```

## 18. Exit
```text
V4_18_CONTRACT_DESIGN = PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT
V4_18_IMPLEMENTATION_ENTRY = BLOCKED_WAIT_REAL_SHADOW_GATE
MIGRATION_REPLAY_PASS = NOT_GRANTED
R25_REAL_ACTIVATION_PACKET = WAIT_ACCEPTED_DAILY_INPUT
V4_17_FINAL_ACCEPTANCE = NOT_GRANTED
Production Focus cutover = false
NEXT = STOP_WAIT_R27_INDEPENDENT_EXTERNAL_AUDIT
```
