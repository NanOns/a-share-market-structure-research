# V4-15E1｜FEP Dataset Engineering Final Independent External Audit R1｜2026-10-05

## 0. Audit Target
Repository: `NanOns/a-share-market-structure-research`
Branch: `codex/v4-system-reform`
Execution baseline: `7474fb25c93286b0224635b77033451a81955ae1`
Audited HEAD: `06549c102da2a203a19004fbeb17a0a0cf717b6a`

## 1. Unique Final Decision
```text
V4_15E1_FINAL_EXTERNAL_AUDIT = PASS_FINAL_EXTERNAL

FEP_DATABASE_ENGINEERING = PASS_EXTERNAL
FEP_DATASET_ENGINEERING = PASS_EXTERNAL_ENGINEERING_SCOPE
FEP_FEATURE_MAPPING = PASS_47_OF_47_ENGINEERING
FEP_V4_15_THREE_TIME_AUTHORITY = PASS_ENGINEERING_REAL_PENDING
FEP_R25_GOVERNANCE_RECONCILIATION = PASS
FEP_V4_18_NAMESPACE_SUCCESSOR = PASS

FEP_REAL_FIRST_OBSERVED_ENTRY = NOT_GRANTED_WAIT_REAL_SESSION
FEP_REAL_MATURED_LABEL_EVIDENCE = NOT_GRANTED

FEP_MODEL_ENGINEERING = NOT_STARTED
FEP_MODEL_DISPLAY = UNGRANTED
FEP_PRIORITY_USE = UNGRANTED
FEP_PRODUCTION = UNGRANTED

E2_ENTRY = AUTHORIZED
NEXT = V4_15E2_CONDITIONAL_STATISTICS_BASELINE
```

No further E1 repair round is required.

## 2. PostgreSQL Foundation｜PASS
The accepted E1 PostgreSQL foundation remains unchanged:

```text
028_fep_schema_v1.sql
029_fep_append_only_v1.sql
030_fep_validation_cas_v1.sql
031_fep_roles_v1.sql
```

Verified semantics:

```text
33 FEP tables
32 immutable append-only fact/history tables
1 controlled mutable deployment_heads table
FK / unique / check constraints
role separation
SECURITY DEFINER
fixed search_path
CAS
idempotency
concurrency
transaction rollback
```

Fresh final targeted database result:

```text
94 passed
1 skipped
0 failed
```

Upgrade final targeted database result:

```text
95 passed
0 failed
```

Fresh/upgrade schema identities are equal.

## 3. 47-Field Feature Owner Adapter｜PASS
Versioned engineering owner contract:

```text
config/fep_feature_owner_contract_v1.json
contract_id = FEP_FEATURE_OWNER_V1
```

Implementation:

```text
src/workbench_analysis/fep_e1/feature_owner.py
```

It exact-binds accepted V4-03 head/receipt/artifact and maps all 47 accepted field envelopes, including the previously missing relative/RPS fields.

Accepted historical owner:

```text
5222 rows
47 exact field envelopes per row
```

The adapter does not recompute factors. It only validates and copies:

```text
value
quality
unknown_reason
output/source digest
input digest
window identity
producer contract
parameter set
type
unit
nullable
requiredness
```

Result:

```text
FEP_FEATURE_MAPPING_ENGINEERING = PASS
FEP_FEATURE_COUNT = 47
```

## 4. Historical / Engineering Boundary｜PASS
The engineering contract remains:

```text
evidence_origin = RECONSTRUCTED_ASOF
AS_RECORDED = false
FIRST_OBSERVED = false
production = false
shadow = false
historical_source_available_at = NOT_PROVEN
```

The engineering observation uses historical trade date 2026-09-24, but its actual engineering read / feature cutoff is 2026-10-05.

Therefore the implementation does not backdate current engineering readability to the historical trade date.

## 5. Deterministic Engineering Snapshot｜PASS
The engineering snapshot exact-binds:

```text
owner publication/projection
accepted V4-03 head
algorithm contract
parameter contract
calendar
universe
adjustment source
feature contract
actual consumed source-row digest
```

Readback:

```text
feature_count = 47
deterministic_same_capture = true
execution_mode = REPLAY
AS_RECORDED = false
FIRST_OBSERVED = false
```

No latest/mtime/guessed alias discovery is used.

## 6. Real FIRST_OBSERVED Gate｜PASS_FAIL_CLOSED
Current real admission remains:

```text
FEP_REAL_FIRST_OBSERVED_ENTRY = NOT_GRANTED_WAIT_REAL_SESSION
CURRENT_REAL_MATURITY_EVIDENCE = NONE
PROVED_HORIZONS = []
real_training_bindings = 0
```

No reconstructed evidence is upgraded to PIT_OBSERVED/FIRST_OBSERVED.

## 7. V4-15 Three-Time Authority｜PASS_KEEP
The additive V4-15 → FEP timing authority remains exact and separates:

```text
source_fact_available_at
label_training_mature_at
label_revision_available_at
```

The T3/T5/T6 engineering counterfactual remains valid.

Current real pending rows produce no training binding.

FEP does not recompute Forward returns, MFE, MAE, benchmark or structure outcome labels.

## 8. V4-18 Namespace Successor｜PASS
Historical V1 remains immutable.

Successor:

```text
config/v4_18_migration_replay_contract_v1_1.json
```

The historical test file was restored exactly to the E1 baseline:

```text
tests/test_v4_18_migration_contract.py
baseline == current content
```

New additive successor test:

```text
tests/fep/test_v4_18_namespace_successor.py
```

verifies the complete current namespace including all 33 FEP declarations while leaving V4-18 execution/cutover ungranted.

The obsolete V1 inventory node is registered:

```text
SUPERSEDED_PRE_FEP_NAMESPACE_ASSERTION
```

and is not counted as PASS.

## 9. R25 Historical Protection｜PASS
No R25 runtime/preflight dependency was patched.

Current readback:

```text
protected() = PASS
selection().status = WAIT_ACCEPTED_DAILY_INPUT
```

The formerly introduced R25/acceptance-seal failures are closed.

## 10. Final Scoped Regression｜PASS_WITH_EXISTING_DEBT
Full final scoped regression:

```text
2485 passed
4 skipped
52 existing failures
0 introduced active failures
```

Existing debt:

```text
43 prior registered failures
9 independently reproduced pre-FEP baseline failures
```

Governed deselections are exactly:

```text
tests/v4_dm01_r4/test_runtime.py::
test_current_real_v2_parent_and_future_wait
= SUPERSEDED_PRE_SEAL_ASSERTION

tests/test_v4_18_migration_contract.py::
test_all_declared_tables_have_explicit_namespace_rules
= SUPERSEDED_PRE_FEP_NAMESPACE_ASSERTION
```

No other deselection is used.

## 11. Protected State｜PASS
```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_15_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_16_ACCEPTED_HEAD = NOT_CREATED
FEP_E1_ACCEPTED_HEAD = NOT_CREATED

Production = false
Shadow = false
Focus = false
PRIORITY_V1 = UNCHANGED

FEP_MODEL_DISPLAY = UNGRANTED
FEP_PRIORITY_USE = UNGRANTED
FEP_PRODUCTION = UNGRANTED
```

## 12. Open Nonblocking Debt
Still open but outside E1 acceptance:

```text
FEP_E1_LEGACY_MIGRATION_REGISTRATION_GAP
historical 014..027 registration debt

FEP_E1_BASELINE_52_FAILURES
43 registered + 9 reproduced baseline failures
```

These do not block E2 engineering entry.

## 13. E1 Final Boundary
E1 is accepted for:

```text
database engineering
dataset engineering
47-field engineering owner mapping
historical/reconstructed feature snapshot mechanics
V4-15 label-time adapter
per-fold PIT dataset semantics
denominator integrity
role/CAS/append-only governance
```

E1 is NOT acceptance for:

```text
real FIRST_OBSERVED prediction
real matured training labels
conditional statistics effectiveness
model effectiveness
calibration
OOD
MODEL_DISPLAY
Priority V2
production
```

## 14. Final State
```text
V4_15E1_FINAL_EXTERNAL_AUDIT = PASS_FINAL_EXTERNAL
E1 = ENGINEERING_ACCEPTED
E2_ENTRY = AUTHORIZED
NEXT = V4_15E2_CONDITIONAL_STATISTICS_BASELINE
```
