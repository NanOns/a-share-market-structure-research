# V4 R23｜Realtime Shadow Runtime Engineering Independent External Audit R1｜2026-10-04

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`

Execution baseline: `942997f8a5bce06e34a6e37d013e4d27e7175438`  
Audited remote HEAD: `9724b0b2091b0d1e0ca55af17e1fc8c3948fdf42`  
Exact tested source: `23a4e62bd81ba3dc6687d603adf62cd0f7e50251`  
Immutable tag: `refs/tags/codex/r23-runtime-tested-source-20261004-r2`

# 1. Unique External Decision

```text
R23_EXTERNAL_AUDIT =
PARTIAL_PASS_OBSERVATION_SLOT_RUNTIME_COMPLETENESS_REPAIR_REQUIRED

R23_RUNTIME_COMPONENTS = PASS_KEEP
R23_DISABLED_ACTIVATION_BOUNDARY = PASS_KEEP
R23_STORAGE_SCHEMA = PASS_KEEP_ENGINEERING_ONLY
R23_SOURCE_RECEIPTS = PASS_KEEP
R23_CLOCK_RUNTIME = PASS_KEEP
R23_SHADOW_PRIOR = PASS_KEEP_ENGINEERING_BOUNDARY
R23_TRANSACTION_ATOMICITY = PASS_KEEP
R23_COHORT_ENROLLMENT = PASS_KEEP
R23_MEMBERSHIP_CAPTURE = PASS_KEEP_NON_PIT
R23_SETTLEMENT_ORCHESTRATION = PASS_KEEP
R23_HEALTH_RECEIPTS = PASS_KEEP
R23_ROLLBACK = PASS_KEEP
R23_LEGACY_ISOLATION = PASS_KEEP
R23_NEGATIVE_E2E = PASS_KEEP_24
R23_INDEPENDENT_RUNTIME_ORACLE = PASS_KEEP
R23_TESTED_SOURCE_GOVERNANCE = PASS_KEEP

R23_SLOT_RUNTIME_CONTRACT_COMPLETENESS = FAIL_P0
R23_OBSERVATION_REVISION_LINEAGE = P1_REPAIR_RECOMMENDED_SAME_ROUND

V4_16_RUNTIME_ENGINEERING = BLOCKED_PENDING_R23R1
V4_16_RUNTIME_ACTIVATION = NOT_AUTHORIZED

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

Production = false
Shadow = false
Focus = false
V4_16 = false
```

This audit does not reject the R23 runtime architecture. It blocks external acceptance until the persisted observation-slot record fully satisfies the already accepted Observation Slot V2 contract.

# 2. Scope / Tested Source｜PASS

The exact tested source is `23a4e62bd81ba3dc6687d603adf62cd0f7e50251`.  
Tag `codex/r23-runtime-tested-source-20261004-r2` resolves exactly to it.

Final branch HEAD is one evidence-only commit ahead. Post-tested-source changes contain only clean-regression / seal evidence. No runtime or contract implementation changed after the tested source.

# 3. R1 Failure Handling｜PASS

The initial failed attempt is retained:

```text
ATTEMPT_R1_DISPOSITION =
FAILED_HISTORICAL_SRC_NAMESPACE_GUARD

294 passed
12 failed
```

R2 moved the new runtime module into the correct `scripts` namespace, preserved accepted business-source bytes, reran the complete suites and sealed a new immutable source. This is correct failure governance.

# 4. Clean Regression｜PASS

```text
306 passed
0 failed
0 errors
0 skipped
0 deselected
```

Suites include PRE16 governance, R21 promotion, R22 contracts, R22R1 clock contracts and R23 runtime.

# 5. Runtime Activation Boundary｜PASS_KEEP

`config/v4_16_runtime_activation_authority_v1.json` keeps:

```text
runtime_authorized = false
real_shadow_authorized = false
production = false
shadow = false
focus = false
V4_16 = false

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
```

`REAL_SHADOW` mode fails before database creation/source consumption. Environment flags cannot grant permission.

The current engineering storage/runtime is intentionally `ENGINEERING_FIXTURE`-only. A later real-Shadow launch round must create a versioned real activation/storage adapter or successor migration; it must not merely flip a boolean. This is not an R23 defect because R23's required state is `ENGINEERING_CANDIDATE_DISABLED`.

# 6. Transaction / Persistence Architecture｜PASS_KEEP

R23 implements isolated SQLite persistence with append-only constraints, SHADOW_V4 namespace, publication-head CAS, unique observation/publication revisions, one original logical event, due-item idempotency, source-receipt identity and append-only runtime operations.

The positive E2E demonstrates manifest/publication/state/cohort/due/health/head inside one transaction. Negative N10 proves injected failure rolls visible runtime state back atomically.

# 7. Independent Runtime Oracle｜PASS_KEEP

`scripts/validate_r23_runtime.py` is independent of the runtime writer. It reads persisted SQLite state read-only and independently checks namespace/origin, row digests, publication revisions, cohort identity, slot identity, clock values, prior-state identity, source-manifest digest, source-receipt binding, due horizons, settlement numeric outputs, frozen controls/benchmark, health constraints, accepted-head CAS and stop-shadow preservation.

# 8. Negative E2E Matrix｜PASS_KEEP

All required N01–N24 families are present and passing, including real-runtime permission, clock/source failures, Legacy prior, missing previous session, correction/new-original, transaction rollback, duplicate event, raw fallback, future read, unaccepted future Data Head, non-PIT membership, A04/A08 blocks, optional BaoStock continuation, identity changes, UI feedback, control redraw, real-counter leakage and rollback delete.

# 9. P0 Finding｜R23-SLOT-01

The externally accepted `V4_16_OBSERVATION_SLOT_CONTRACT_V2` requires every slot to persist at minimum:

```text
trade_date
model_contract_id
parameter_set_id
state_lineage_id
execution_mode
namespace
scheduled_cutoff_at
observation_deadline
source_provider_available_at
system_available_at
computation_started_at
computation_finished_at
accepted_at
slot_status
publication_id
core_revision
source_manifest_digest
capability_scope
```

Current `ObservationSlotPlanner.plan()` persists only the slot key, cutoff/deadline, status and evidence origin; the acceptance path later adds accepted_at/publication/revision/sample_class.

Missing from the accepted slot record include at least:

```text
parameter_set_id
execution_mode
namespace
source_provider_available_at
system_available_at
computation_started_at
computation_finished_at
core_revision
source_manifest_digest
capability_scope
```

The facts exist elsewhere, but the contract explicitly requires the observation slot itself to be an auditable frozen record.

Therefore:

```text
R23_SLOT_RUNTIME_CONTRACT_COMPLETENESS = FAIL_P0
```

# 10. Why P0

The slot is the anti-selection / anti-backfill audit boundary. A future PIT_OBSERVED claim must allow an independent auditor to read one durable slot and answer which model/parameter/namespace ran, when mandatory sources became visible, when computation started/finished, when acceptance occurred, which manifest was frozen and what capability scope was evaluated.

Reconstructing these values later from separate tables weakens the accepted V4-16 contract.

# 11. Required Slot Semantics

R23R1 must persist the exact V2 required field set.

Recommended semantics:

```text
parameter_set_id =
exact accepted request parameter identity

execution_mode =
SHADOW

namespace =
SHADOW_V4

source_provider_available_at =
max(first_observed_at) across exact mandatory consumed receipts

system_available_at =
max(system_available_at) across exact mandatory consumed receipts

computation_started_at / computation_finished_at / accepted_at =
exact validated request timestamps

core_revision =
explicit deterministic publication/core revision identity

source_manifest_digest =
exact frozen mandatory-source manifest digest

capability_scope =
explicit canonical evaluated capability scope
```

# 12. Independent Oracle Upgrade

The current independent oracle validates slot identity/clock but does not compare persisted slot keys to:

`config/v4_16_observation_slot_contract_v2.json["fields"]`.

R23R1 must independently load that exact contract and require every accepted slot revision to contain all required fields, then recompute source visibility aggregates and manifest binding from persisted receipts/manifest.

# 13. P1 Finding｜Observation Revision Lineage

The positive E2E second observation is:

```text
observation_state = CORRECTED
source_correction = true
supersedes_observation = null
```

The V4-15 field registry defines `supersedes_observation` as append-only publication-revision lineage.

For a correction of the same logical event with a prior observation, R23R1 should bind:

```text
supersedes_observation = previous observation_id
```

and independently validate same logical_event_id / same slot lineage / no cycles.

# 14. PASS_KEEP Areas

Do not reopen clock contract, PRE16 governance, R22 freeze, activation-disabled authority, atomicity architecture, settlement, cohort T0 freeze, due planner, rollback, Legacy isolation, N01–N24 or the R1 historical disposition.

# 15. Final Boundary

Until R23R1 passes:

```text
V4_16_RUNTIME_ENGINEERING_EXTERNAL_ACCEPTANCE = BLOCKED
REAL_SHADOW_ACTIVATION = BLOCKED
V4_17 = BLOCKED
```

REV4 sequence remains:

```text
V4-16 Realtime Shadow Dual-Run
→ V4-17 Shadow UI
```

# 16. Next

```text
R23R1
OBSERVATION_SLOT_RUNTIME_COMPLETENESS
+
OBSERVATION_REVISION_LINEAGE

→ independent external audit
→ PASS
→ controlled V4-16 real Shadow activation preparation
```
