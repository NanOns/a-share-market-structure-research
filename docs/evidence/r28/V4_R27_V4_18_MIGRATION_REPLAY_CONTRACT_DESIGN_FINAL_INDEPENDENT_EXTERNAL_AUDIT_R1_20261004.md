# V4 R27｜V4-18 Migration Replay Contract Design Independent External Audit R1｜2026-10-04

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`  
Execution baseline: `c1787b77e08a26e344d3cbb88148a60f93c3df3e`  
Audited remote HEAD: `94635fa369c60b3f8182cb4d813751a453682d88`  
Exact tested source: `f7c7277a9cafb972b9f0a00829a5d3dcff0a1f81`  
Immutable tested tag: `refs/tags/codex/r27-migration-contract-tested-source-20261004`

## 1. Unique External Decision

```text
R27_EXTERNAL_AUDIT =
PASS_FINAL_V4_18_MIGRATION_REPLAY_CONTRACT_DESIGN_SCOPED

V4_18_CONTRACT_DESIGN = PASS_EXTERNAL
V4_18_NAMESPACE_MATRIX = PASS_EXTERNAL
V4_18_PRESTATE_INHERITANCE = PASS_EXTERNAL
V4_18_OPEN_EPISODE_PRESERVATION = PASS_EXTERNAL
V4_18_PENDING_SETTLEMENT_PRESERVATION = PASS_EXTERNAL
V4_18_FOCUS_USER_STATE_PRESERVATION = PASS_EXTERNAL
V4_18_CUTOVER_GAP_POLICY = PASS_EXTERNAL
V4_18_ROLLBACK_CONTRACT = PASS_EXTERNAL
V4_18_IDEMPOTENCY_CONTRACT = PASS_EXTERNAL
V4_18_VECTOR_REGISTRY_M01_M20 = PASS_EXTERNAL_DESIGN_ONLY
V4_18_TESTED_SOURCE_GOVERNANCE = PASS_EXTERNAL

V4_18_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_REAL_SHADOW_GATE

MIGRATION_REPLAY_PASS =
NOT_GRANTED

V4_18_ACCEPTED_HEAD =
NOT_CREATED

R25_REAL_ACTIVATION_PACKET =
WAIT_ACCEPTED_DAILY_INPUT

V4_17_FINAL_ACCEPTANCE =
NOT_GRANTED

Production Focus cutover =
false
```

## 2. Change Scope

R27 changed only:

```text
config/v4_18_migration_replay_contract_v1.json
tests/test_v4_18_migration_contract.py
R27 evidence / seal / reports
```

No migration writer, production Focus source, V4-16 runtime, V4-17 real source, accepted business implementation or accepted head was changed.

`PROTECTED_BYTES.json` reports:

```text
changed = []
databases_opened = false
tdx_writes = false
```

## 3. Contract Is Not a Placeholder

The machine contract freezes:

```text
source/target namespace model
pre-state inheritance
open episode identity
pending settlement identity
Focus/user-work lanes
cutover-gap watermarks
idempotency
rollback ownership
historical context identity
future implementation interfaces
M01-M20 acceptance vectors
```

All future runtime interfaces are explicitly:

```text
implemented = false
```

and production writer execution remains forbidden.

## 4. Namespace Matrix

The contract inventories 186 declared source tables/semantic objects.

Disposition summary:

```text
REFERENCE      = 179
CARRY          = 6
NOT_MIGRATED   = 1
```

This is acceptable because physical target storage has not yet been independently accepted.

Historical tables are references and are not relabeled into production history.

The semantic CARRY objects explicitly include:

```text
SEMANTIC:prestate
SEMANTIC:open_episode
SEMANTIC:pending_settlement
SEMANTIC:user_pin
SEMANTIC:manual_notes_followup
SEMANTIC:legacy_gap_activity
```

`SEMANTIC:system_selected_focus` is explicitly:

```text
NOT_MIGRATED
```

so Legacy algorithm selection is not promoted to V4 algorithm evidence.

## 5. Pre-State Inheritance

The first future V4 production state must inherit:

```text
EXACT_LAST_ACCEPTED_SHADOW_PRESTATE
```

with explicit migration manifest and same model lineage.

`RECONSTRUCTED_ASOF` may initialize state only and may never become:

```text
PIT_OBSERVED enrollment
real sample
```

A model boundary creates a new cohort while preserving old episodes and pending outcomes.

## 6. Open Episode Preservation

The following are immutable across migration:

```text
logical_event_id
episode_id
T0
current_state
enrollment_id
control_assignment_ids
benchmark_ids
source_lineage
```

A replay may not create a second original enrollment for the same logical event.

Missing original identity blocks only the affected scope.

## 7. Pending Settlement Preservation

The contract preserves:

```text
enrollment_id
horizon
due_date
frozen_T0
controls
benchmarks
outcome_status
evaluation_revision
future_source_policy
```

Outcome revisions are append-only.

Unavailable future data keeps the due obligation pending with reason; it does not redraw T0, controls or benchmark identities.

## 8. Settlement Ownership

Rollback and cutover define:

```text
EXACTLY_ONE_AUTHORIZED_WORKER_PER_EXISTING_DUE_ID
```

Ownership transfer requires a receipt and must not create a new enrollment.

This closes the main double-settlement risk across Legacy/Shadow/V4 ownership.

## 9. Focus / User State

The contract separates:

```text
algorithm_eligibility
system_selected_focus
user_pin
manual_notes_followup
```

User pins/manual notes are explicitly excluded from algorithm evidence.

Native user-work export is not invented: if no accepted native mapping exists, the affected user-work scope blocks.

This is preferable to guessing a nonexistent user-pin table.

## 10. Cutover Gap

Gap interval:

```text
(ACCEPTED_SNAPSHOT_WATERMARK, FINAL_CUTOVER_WATERMARK]
```

per namespace.

The manifest requires ordered native ids/revisions, payload digests, counts, missing ranges and reconciliation digest.

Legacy writes, Shadow publications, outcome corrections, user pins and follow-up work must all be accounted exactly once or explicitly referenced.

Backup-only restore is forbidden.

## 11. Rollback

Rollback order is frozen to:

```text
1. fence new V4 production writes
2. capture final watermarks
3. reconcile gap activity
4. restore accepted Legacy routing with CAS
5. append rollback receipt
```

Rollback must preserve:

```text
accepted V4 history
Shadow history/context tokens
pending settlements/revisions
user pins/manual work
outbox/accepted receipts
```

Accepted V4 facts may never be deleted.

## 12. Idempotency

Frozen migration identity includes:

```text
migration_run_id
source_head_digest
expected_target_head
event_id
enrollment_id
due_id
user_pin_id
```

Identical replay returns the same receipt and cannot duplicate event/enrollment/due/pin state.

Changed payload under the same identity is a blocking conflict.

Target-head CAS failure permits no partial acceptance.

## 13. M01-M20

M01-M20 are correctly marked:

```text
DECLARATIVE_CONTRACT_VECTOR_NOT_RUNTIME_TEST
```

They cover prestate, open episode, due preservation, correction revisions, user pins, namespace mismatch, idempotency, source-head changes, CAS conflicts, cutover-gap activity, rollback retention, RECONSTRUCTED_ASOF non-promotion, historical context readback and latest/mtime prohibition.

They do not falsely claim runtime migration testing.

## 14. Implementation Entry

All five required future receipts remain null:

```text
externally accepted real V4-16 Shadow publication
accepted V4-17 real readback binding
accepted migration source snapshot
accepted target storage contract
accepted cutover/rollback authority
```

Current status:

```text
BLOCKED_WAIT_REAL_SHADOW_GATE
```

This is correct.

## 15. Regression

Clean source:

```text
245 tests
242 passed
3 inherited failures
0 errors
0 skipped
0 deselected
```

The three failures are exactly the same historical R26-A01 failures:

```text
test_v3_is_the_single_unified_workbench_entry
test_hot_rank_route_skips_request_scope
test_send_marks_disconnected_client_closed
```

No new R27 regression exists.

Classification remains:

```text
R26_A01 =
OPEN_NONBLOCKING_HISTORICAL_DEBT
```

## 16. Tested Source Governance

Annotated tag:

`codex/r27-migration-contract-tested-source-20261004`

resolves exactly to:

`f7c7277a9cafb972b9f0a00829a5d3dcff0a1f81`

Final remote HEAD is one evidence-only commit ahead.

No implementation drift occurred after clean testing.

## 17. Protected State

Still:

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_15_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30

V4_16_ACCEPTED_HEAD = NOT_CREATED
V4_17_ACCEPTED_HEAD = NOT_CREATED
V4_18_ACCEPTED_HEAD = NOT_CREATED

R25_REAL_ACTIVATION_PACKET =
WAIT_ACCEPTED_DAILY_INPUT

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

Production = false
Focus source cutover = false
```

## 18. Final

```text
R27_EXTERNAL_AUDIT =
PASS_FINAL_V4_18_MIGRATION_REPLAY_CONTRACT_DESIGN_SCOPED

V4_18_CONTRACT_DESIGN =
EXTERNALLY_ACCEPTED

V4_18_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_REAL_SHADOW_GATE

MIGRATION_REPLAY_PASS =
NOT_GRANTED
```

Next non-blocking work may continue as `V4-19 Focus Source Cutover CONTRACT_DESIGN_ONLY`; no production cutover is authorized.
