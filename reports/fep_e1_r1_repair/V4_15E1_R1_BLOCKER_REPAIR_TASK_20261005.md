# V4-15E1 R1｜FEP Blocker Repair Task｜2026-10-05

## 0. Mission

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Execution baseline:

`e4ea913d8926e904e55cbf16993ec63c0e90b031`

External repair authority:

`V4_15E1_R1_INDEPENDENT_EXTERNAL_AUDIT_20261005.md`

Current state:

```text
FEP_DATABASE_ENGINEERING = PASS_KEEP
V4_15E1_FEP_LOCAL_IMPLEMENTATION = BLOCKED
E2 = NOT_AUTHORIZED
```

This task is a **narrow E1R1 repair**.

Do not redesign FEP.

Do not redo the PostgreSQL foundation that already passed.

---

# 1. PASS_KEEP / Frozen Implementation

Preserve unless an exact contradiction is independently proven:

```text
src/workbench_db/migrations/v4_postgres/028_fep_schema_v1.sql
src/workbench_db/migrations/v4_postgres/029_fep_append_only_v1.sql
src/workbench_db/migrations/v4_postgres/030_fep_validation_cas_v1.sql
src/workbench_db/migrations/v4_postgres/031_fep_roles_v1.sql
```

Also preserve:

```text
33-table schema identity
32 append-only guards
deployment_heads CAS semantics
role / SECURITY DEFINER model
dataset denominator structure
fold cutoff/selection structure
dataset composite FK
negative-vector semantics already passing
```

Do not change old accepted V4 heads.

---

# 2. WP-A｜Formalize Exact External Design Receipt

The formal external design receipt already exists.

Exact raw file:

```text
V4_2_2_FEP_R2_EXTERNAL_DESIGN_ACCEPTANCE_20260930.md

bytes = 14019

sha256 =
cd279e26fb9753eb1e333c7554f9f06393c9232ee44ff7be6d86e2f2f65d178e
```

Drive authority ID:

```text
1SdxQCravi5BpyHQ7yb7_IanQpcI0wBW2
```

Add **exact raw bytes** to:

```text
docs/evidence/fep_e1/
V4_2_2_FEP_R2_EXTERNAL_DESIGN_ACCEPTANCE_20260930.md
```

No semantic rewrite.

Update:

```text
DESIGN_AUTHORITY_READBACK.json
FEP_E1_CANDIDATE_SEAL.json
```

to exact-bind it.

Required:

```text
FEP_E1_EXTERNAL_DESIGN_RAW_RECEIPT = PASS
```

---

# 3. WP-B｜47-Field Accepted Owner Mapping

Current state:

```text
accepted_registry_fields = 47
implemented_current_ENTRY_mappings = 0
```

This must be repaired by exact owner discovery.

Do not assume all fields are in one V4-04 row.

For every FEP required field, inspect the current accepted chain and locate its actual authoritative value/quality source.

Allowed owner families include, only when exact accepted evidence proves them:

```text
V4-03 accepted factor artifact/publication
V4-04 profile derived_fields / states
V4-06 accepted supplemental enrichment
V4-09 PREWATCH accepted output
V4-11 State/Event accepted output
V4-12 Structure/Anchor/Support accepted output
V4-13 accepted advanced projection
market/sector accepted owner artifacts when explicitly required
```

## 3.1 Required Machine Mapping

Create a versioned exact mapping contract, e.g.:

```text
config/fep_feature_source_map_v1.json
```

Each field must contain at least:

```text
field_name
feature_contract_id
owner_stage
owner_accepted_head path + sha256
owner_artifact path + sha256
owner_publication / revision identity where applicable
entity key path
trade_date path
value_path
quality_path
availability_authority
source_digest path/rule
unit source
unit transform
window identity
allowed scope
mapping status
reason
```

No `latest` discovery.

No mtime availability.

No English alias guessing.

## 3.2 Availability Rule

For a feature value to be admitted into a PIT snapshot:

```text
actual accepted publication/receipt available_at
<= feature_cutoff
```

Trade date alone is not availability time.

A historical row reconstructed later must remain reconstructed.

## 3.3 Real Current ENTRY Admission

Create an exact current accepted ENTRY source readback against the latest available accepted 2026-09-30 owner chain.

This does **not** mean current labels are mature.

The goal is to prove:

```text
logical ENTRY observation identity
→ exact accepted owner rows
→ exact 47 feature mappings
→ exact values/quality/source digests
→ immutable dependency manifest
```

If a field truly has no accepted owner value/path:

```text
do not invent it
```

Instead produce:

```text
FEP_E1_FEATURE_MAPPING_CONTRACT_CONFLICT
```

and remain blocked.

Do not silently reduce the 47-field contract merely to obtain PASS.

## 3.4 Slot/Timing

Freeze an E1 ENTRY observation timing contract only from an existing accepted publication lifecycle.

Do not invent a wall-clock deadline.

If the current system only proves publication acceptance time, use that proof in the observation admission contract and keep prediction/model deadlines NOT_ENABLED.

Required close condition:

```text
FEP_E1_FEATURE_MAPPING_COMPLETE = PASS
FEP_E1_DATASET_COMPLETE_FEATURE_SIDE = true
```

---

# 4. WP-C｜Versioned V4-15 → FEP Three-Time Label Authority

Current V4-15 outcome rows do not provide an accepted authority for:

```text
source_fact_available_at
label_training_mature_at
label_revision_available_at
```

Create a versioned additive authority.

Suggested identity:

```text
V4_15_FEP_LABEL_TIME_AUTHORITY_V1
```

Suggested files:

```text
config/v4_15_fep_label_time_authority_v1.json
src/workbench_analysis/v4_15_fep_label_time.py
```

Paths may follow existing repository conventions.

## 4.1 Hard Boundary

Do not rewrite:

```text
existing V4-15 outcome rows
V4_15_ACCEPTED_HEAD
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
```

Do not recompute:

```text
R_N
MFE
MAE
benchmark
path
competing outcome
```

The adapter only establishes knowledge-time authority.

## 4.2 Exact Upstream Identity

Every timing sidecar/receipt must bind an exact upstream label identity, including as applicable:

```text
enrollment_id
horizon
outcome_contract_id
outcome_revision_id
evaluation_revision
evaluation_source_digest
source row digest
accepted owner head / publication
```

## 4.3 Three Times

The authority must define independently:

### source_fact_available_at

The earliest timestamp at which **all source facts actually consumed by this label revision** are proven available in the accepted system.

Must come from accepted source receipts/manifests/publication availability.

Forbidden substitutes:

```text
trade_date
due_date
report_cutoff
file mtime
current wall clock
```

unless the owner contract explicitly proves them as the actual source availability timestamp.

### label_training_mature_at

The timestamp at which the target's full required N-window and required quality/completeness conditions are proven satisfied for training.

For a pending or incomplete target:

```text
NOT_PROVEN
```

Do not auto-unlock just because the calendar reached T+N.

### label_revision_available_at

The timestamp at which this exact label revision/sidecar becomes accepted and readable in the system.

Must satisfy:

```text
label_revision_available_at >= source_fact_available_at
```

## 4.4 Current 2026-09-30 Real Rows

Current authority says:

```text
CURRENT_REAL_MATURITY_EVIDENCE = NONE
PROVED_HORIZONS = []
```

Therefore current pending rows must remain:

```text
NO_TRAINING_BINDING / PENDING
```

If any of the required three times cannot be proven:

```text
do not insert fep.label_source_bindings
```

Keep denominator rows pending.

This is a PASS condition for fail-closed behavior.

## 4.5 Engineering Fixture

Use isolated engineering fixtures to prove:

```text
T2 source known
T5 mature
T6 revision accepted

cutoff T3 → not trainable
cutoff T5 → still not trainable
cutoff T6 → eligible
```

but do not relabel fixture evidence as real.

Required close condition:

```text
V4_15_FEP_LABEL_TIME_AUTHORITY = PASS_ENGINEERING
FEP_V4_15_LABEL_ADAPTER = PASS_ENGINEERING_FAIL_CLOSED_REAL_PENDING
```

---

# 5. WP-D｜Versioned V4-18 Namespace Reconciliation

Do **not** edit:

```text
config/v4_18_migration_replay_contract_v1.json
```

in place.

Create a successor, e.g.:

```text
config/v4_18_migration_replay_contract_v1_1.json
```

with:

```text
contract_id = V4_18_MIGRATION_REPLAY_CONTRACT_V1_1
supersedes = exact path/sha256 of V1
```

## 5.1 Add FEP Declarations

Add all 33 FEP tables explicitly to the successor namespace matrix.

They must be identified as FEP-specific current engineering structures.

They must **not** receive migration/cutover authority merely because they are declared.

Use explicit semantics such as:

```text
read_source = FEP_E1_ENGINEERING
disposition = REFERENCE or NOT_MIGRATED
write_target = null
production_cutover = false
migration_replay_pass = NOT_GRANTED
```

Choose the exact enum values consistent with the successor contract and tests.

## 5.2 Test Versioning

Update:

```text
tests/test_v4_18_migration_contract.py
```

only as necessary to read the active successor contract.

Do not delete the V1 artifact.

Do not deselect:

```text
test_all_declared_tables_have_explicit_namespace_rules
```

It must pass against the successor inventory.

Required:

```text
introduced namespace failure = CLOSED
V4_18 migration execution = still NOT_GRANTED
V4_18 accepted head = still absent
```

---

# 6. E1 Integration Re-Test

After WP-A/B/C/D, rerun the full E1 gates.

## 6.1 Database PASS_KEEP Readback

Prove exact bytes or equivalent unchanged semantics for:

```text
028
029
030
031
```

and re-run:

```text
fresh PostgreSQL
upgrade PostgreSQL
33 table inventory
32 guard inventory
role/privilege
SECURITY DEFINER
CAS concurrency
rollback
dataset PIT vectors
```

If unchanged, do not rewrite them just to create new evidence.

## 6.2 Feature Admission

Required:

```text
47 / 47 exact owner mappings
0 guessed mappings
0 latest/mtime mappings
```

Any unavailable required field:

```text
E1 remains BLOCKED
```

## 6.3 Label Adapter

Required:

```text
exact timing authority contract exists
current pending rows do not manufacture timing
FEP adapter produces no real trainable label without proven authority
engineering time-chain fixture passes
```

## 6.4 Namespace

Required:

```text
tests.test_v4_18_migration_contract::
test_all_declared_tables_have_explicit_namespace_rules
= PASS
```

with no V4-18 production grant.

---

# 7. Regression Accounting

Current E1 R1 baseline classification is:

```text
43 prior registered failures
9 additional pre-existing failures reproduced on pre-FEP baseline
1 E1-introduced namespace failure
```

After repair, required:

```text
introduced active failures = 0
```

The 52 existing/baseline failures may remain visible unless independently repaired by their owner stage.

Do not hide them.

Do not relabel them as E1 PASS.

Do not add new deselections except the already governed superseded pre-seal R4 node.

---

# 8. Evidence Required

Create/update:

```text
reports/fep_e1_r1_repair/
  ENTRY_BASELINE.json
  EXTERNAL_DESIGN_RECEIPT_READBACK.json
  FEATURE_OWNER_MAPPING_GATE.json
  FEATURE_CURRENT_ENTRY_READBACK.json
  LABEL_TIME_AUTHORITY_GATE.json
  LABEL_ADAPTER_REAL_PENDING_READBACK.json
  LABEL_TIME_NEGATIVE_MATRIX.json
  V4_18_NAMESPACE_SUCCESSOR_GATE.json
  PASS_KEEP_DATABASE_READBACK.json
  TARGETED_SUMMARY.json
  SCOPED_REGRESSION_SUMMARY.json
  LOCAL_ACCEPTANCE_MATRIX.json
  FEP_E1_R1_REPAIR_CANDIDATE_SEAL.json
  COMPLETION_REPORT.md
```

Raw logs must be retained for PostgreSQL tests and regression.

---

# 9. Protected State

Must remain:

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_15_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

FEP_E1_ACCEPTED_HEAD =
NOT_CREATED

V4_16_ACCEPTED_HEAD =
NOT_CREATED

Production =
false

Shadow =
false

Focus =
false

FEP_MODEL_DISPLAY =
UNGRANTED

FEP_PRIORITY_USE =
UNGRANTED

FEP_PRODUCTION =
UNGRANTED
```

PRIORITY_V1 remains unchanged.

---

# 10. Local Exit

Only if all P0/P1 repair items pass:

```text
V4_15E1_R1_REPAIR =
PASS_LOCAL_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

V4_15E1_FEP_LOCAL_IMPLEMENTATION =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

FEP_DATABASE_ENGINEERING =
PASS_LOCAL

FEP_DATASET_ENGINEERING =
PASS_LOCAL

FEP_STOCK_ENTRY_CORE_DATA_PATH =
ENGINEERING_READY

FEP_REAL_MATURED_LABEL_EVIDENCE =
NOT_GRANTED_UNLESS_SEPARATELY_PROVEN

FEP_MODEL_ENGINEERING =
NOT_STARTED

FEP_MODEL_DISPLAY =
UNGRANTED

FEP_PRIORITY_USE =
UNGRANTED

FEP_PRODUCTION =
UNGRANTED

NEXT =
STOP_WAIT_V4_15E1_R1_INDEPENDENT_EXTERNAL_AUDIT
```

Do not create an E1 Accepted Head.

Do not start E2.

If any required field/time/namespace owner remains unproven:

```text
V4_15E1_R1_REPAIR = BLOCKED
NEXT = STOP_WAIT_EXTERNAL_REPAIR_DISPOSITION
```
