# V4-15E2 R1R1｜Historical Engineering Dataset & Scoped Support Policy Repair Task｜2026-10-05

## 0. Mission

Repository:
`NanOns/a-share-market-structure-research`

Branch:
`codex/v4-system-reform`

Execution baseline:
`87e5b36b32aafd73101f21225703228353d12140`

Authority:
`V4_15E2_R1_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md`

This is a narrow E2 repair.

Do not start E3.

---

# 1. PASS_KEEP

Preserve the existing E2 mechanics unless this task explicitly requires a narrow change:

```text
CONDITIONAL_EXPECTANCY_V1 level order
bucket equal-date rational weighting
inverse empirical CDF quantile
continuous statistics
categorical/ANY-event mechanics
denominator preservation
fold/revision binding
artifact logical digest
append-only local registry
0 introduced regression failures
```

Do not rewrite the E1 PostgreSQL foundation.

---

# 2. Build Historical Engineering ENTRY Population

Create a deterministic builder for:

```text
FEP_STOCK_ENTRY_CORE
```

using real historical source data and accepted algorithms.

Suggested namespace:

```text
src/workbench_analysis/fep_e2/historical_dataset.py
config/fep_e2_historical_dataset_contract_v1.json
```

The exact path may follow repository conventions.

## 2.1 Population rule

The historical ENTRY population must be the complete replay population for the frozen window.

Do not select by:

```text
UI Top-K
Focus
manual pin
outcome
return
future label
E2 baseline value
Priority
```

Do not use `ENGINEERING_SYNTHETIC` historical events as admission population.

## 2.2 Historical replay lineage

All historical replay rows must state:

```text
evidence_origin = RECONSTRUCTED_ASOF or RECONSTRUCTED_CORRECTED
execution_mode = HISTORICAL_SIMULATION / REPLAY
AS_RECORDED = false
FIRST_OBSERVED = false
REAL_OOS = false
production = false
shadow = false
```

No historical PIT claim.

---

# 3. Freeze Historical Window Before Outcomes

Create:

```text
reports/fep_e2_r1r1/HISTORICAL_WINDOW_DISCOVERY.json
reports/fep_e2_r1r1/HISTORICAL_WINDOW_FREEZE.json
```

Window discovery may use only:

```text
accepted source coverage
historical canonical data coverage
calendar
algorithm warm-up requirements
owner/replay capability
maximum enabled target horizon
```

Forbidden:

```text
returns
positive rates
quantiles
best period
market regime performance
Priority result
```

Prefer the maximal contiguous reconstructible range.

Freeze exact start/end and digest before settlement/statistics.

---

# 4. Historical Feature Projection

For each historical ENTRY observation:

```text
use accepted feature algorithms/contracts
consume only data <= T0 feature cutoff
bind exact source/window/parameter identities
```

Do not read future rows into T0 features.

Do not substitute current membership/state for historical PIT truth unless the contract explicitly allows reconstructed evidence and marks the limitation.

Any unavailable mandatory input must remain UNKNOWN / explicit exclusion reason.

---

# 5. Historical Label Adapter Through V4-15

Create an E2 historical label adapter that invokes or exact-wraps the accepted V4-15 settlement/Forward owner.

It must NOT implement outcome formulas itself.

Required exact bindings include:

```text
V4_15_ACCEPTED_HEAD
V4_15 settlement contracts
Forward projection contract
source Data Head
calendar
identity
price-path source
adjustment source
outcome revision/digest
```

Historical labels are engineering replay labels only.

Required status:

```text
ENGINEERING_HISTORICAL_REPLAY
NOT_REAL_OOS
NOT_FIRST_OBSERVED
```

Do not alter current real V4-15 maturity state.

---

# 6. Build Multi-Date E2 Dataset

Create a versioned frozen historical E2 dataset with:

```text
full denominator
label selections
eligible rows
date ordinal
label end ordinal
entity/episode identity
regime/trend/position/risk conditions
feature-support state
target/horizon
label quality
reconstruction lineage
```

Required evidence:

```text
row count
date count
block count
entity count
episode count
label-status counts
target/horizon counts
class-count feasibility
missingness
```

The dataset must contain more than one date if it is used to freeze a multi-date policy.

A single-date cross-section must never be promoted as multi-date support evidence.

---

# 7. Versioned Scoped Support Policy

Current unscoped:

`config/fep_e2_support_policy_v1.json`

must remain historical R1 evidence.

Create a successor/registry.

Recommended:

```text
config/fep_e2_support_policy_registry_v1.json
```

or an explicitly versioned V1.1.

Every policy entry must have an applicability key including at least:

```text
entity_type
observation_scope
target_kind
target or target_family
horizon / horizon family
feature_variant
evidence_origin
label_quality_policy
contract versions
```

Policy parameters:

```text
minimum rows
minimum dates
minimum blocks
minimum entities
minimum episodes
class minimums
max missing fraction
max representativeness distance
```

must be frozen per admitted scope.

---

# 8. Runtime Policy Binding

Modify E2 baseline validation narrowly so that:

```text
query/base partition
must exactly match
support policy applicability
```

Mismatch must raise a fail-closed error.

Mandatory cases:

```text
continuous T1 policy → FIRST_EXIT = BLOCK
T1 policy → T20 = BLOCK unless policy explicitly covers T20
CORE policy → Supplemental = BLOCK
ENTRY policy → DAILY = BLOCK
```

Do not infer policy applicability from filename or latest registry row.

---

# 9. Threshold Discovery

For each candidate policy scope, generate:

```text
SUPPORT_POLICY_DISCOVERY
```

using no outcome performance.

Allowed:

```text
rows
dates
overlap intervals
non-overlap blocks
entities
episodes
label availability
class-count feasibility
missingness
pre-outcome category coverage
```

Forbidden:

```text
mean return
conditional return
positive-rate comparison across policies
quantile attractiveness
best backoff result
model score
Priority result
```

Class counts may be used for feasibility, not profitability.

Every chosen threshold must have:

```text
reason
source evidence
derivation rule
freeze_input_digest
freeze_before_statistics_at
```

If one scope lacks defensible evidence:

```text
leave only that scope UNSET
```

Do not globally block a separate scope that has sufficient evidence.

---

# 10. Initial Admission Scope

At minimum attempt formal admission for:

```text
FEP_STOCK_ENTRY_CORE
ABS_RETURN_N
T1
CONTINUOUS
RECONSTRUCTED engineering history
```

If this scope has enough historical support, freeze it.

Other horizons/targets may remain:

```text
UNSET_DIAGNOSTIC_ONLY
```

if evidence is insufficient.

Do not fake universal E2 acceptance.

A capability-scoped E2 baseline is acceptable.

---

# 11. Representativeness Dimension Status

Modify representativeness diagnostics to distinguish:

```text
ASSESSED
UNAVAILABLE_NOT_GATED
INSUFFICIENT_SUPPORT
```

If a dimension is unavailable by contract, do not encode its TV as a meaningful zero and call it assessed.

Policy gating should only apply to dimensions that are contractually assessable.

Artifacts must record both:

```text
dimension_status
distance/value if assessed
```

---

# 12. Statistics Only After Freeze

The actual conditional-statistics run must begin only after:

```text
historical dataset sealed
support discovery sealed
support policy sealed
```

Evidence timestamps/digests must prove ordering.

Do not compute baseline statistics and then retroactively choose thresholds.

---

# 13. Keep Existing R1 Diagnostic Artifact

Do not delete:

```text
reports/fep_e2_r1/DIAGNOSTIC_BASELINE.json
```

It is valid evidence that the single E1 observation was insufficient.

R1 remains historical traceability.

R1R1 creates new artifacts under:

```text
reports/fep_e2_r1r1/
```

---

# 14. Required Negative Tests

At minimum:

```text
01 synthetic V4-15 history rejected for policy admission
02 one-date 117-event population fails multi-date support
03 replay window changes after seeing returns → BLOCK
04 future T0 feature row → BLOCK
05 V4-15 outcome digest mismatch → BLOCK
06 reconstructed row marked FIRST_OBSERVED → BLOCK
07 T1 policy applied to T20 → BLOCK
08 continuous policy applied to FIRST_EXIT → BLOCK
09 ENTRY policy applied to DAILY → BLOCK
10 unavailable representation dimension → UNAVAILABLE_NOT_GATED
11 support threshold freeze after statistics start → BLOCK
12 policy derivation reads mean/quantile/backoff performance → BLOCK
13 rebuilt historical dataset deterministic
14 later current-head change does not mutate sealed dataset
15 E2 failure leaves E1/Core/PRIORITY_V1 untouched
```

Retain all E2-R1 tests.

---

# 15. Required Evidence

Create:

```text
reports/fep_e2_r1r1/
  ENTRY_BASELINE.json
  R1_PASS_KEEP_READBACK.json
  HISTORICAL_WINDOW_DISCOVERY.json
  HISTORICAL_WINDOW_FREEZE.json
  HISTORICAL_OBSERVATION_POPULATION.json
  HISTORICAL_FEATURE_GATE.json
  V4_15_HISTORICAL_LABEL_ADAPTER_GATE.json
  HISTORICAL_DATASET_SEAL.json
  SUPPORT_POLICY_DISCOVERY.json
  SUPPORT_POLICY_REGISTRY_FREEZE.json
  SUPPORT_POLICY_SCOPE_GATE.json
  REPRESENTATIVENESS_DIMENSION_GATE.json
  CONDITIONAL_BASELINE_GATE.json
  NEGATIVE_MATRIX.json
  PROTECTED_STATE_READBACK.json
  TARGETED_SUMMARY.json
  SCOPED_REGRESSION_SUMMARY.json
  LOCAL_ACCEPTANCE_MATRIX.json
  FEP_E2_R1R1_CANDIDATE_SEAL.json
  COMPLETION_REPORT.md
```

---

# 16. Local Acceptance

For at least one formally admitted capability scope, require:

```text
historical population = non-synthetic reconstructed real-source replay
multi-date support = proven
support policy = frozen before statistics
policy applicability = exact
conditional baseline = generated
artifact digest = deterministic
real FIRST_OBSERVED = still NOT_GRANTED
introduced_active_failures = 0
```

If ABS_RETURN_N:T1 passes but other scopes do not:

```text
E2 may exit capability-scoped PASS
```

with unready scopes explicitly UNSET.

---

# 17. Protected State

Must remain:

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_15_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_16_ACCEPTED_HEAD = NOT_CREATED

Production = false
Shadow = false
Focus = false

FEP_REAL_FIRST_OBSERVED_ENTRY = NOT_GRANTED
FEP_REAL_MATURED_LABEL_EVIDENCE = NOT_GRANTED

FEP_MODEL_ENGINEERING = NOT_STARTED
FEP_MODEL_DISPLAY = UNGRANTED
FEP_PRIORITY_USE = UNGRANTED
FEP_PRODUCTION = UNGRANTED

PRIORITY_V1 = UNCHANGED
```

---

# 18. Required Exit

If at least the initial continuous T1 scope is admitted:

```text
V4_15E2_R1R1_REPAIR =
PASS_LOCAL_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

FEP_CONDITIONAL_BASELINE =
BASELINE_ENGINEERING_PASS_LOCAL_CAPABILITY_SCOPED

FEP_SUPPORT_POLICY =
FROZEN_FOR_ADMITTED_SCOPES

FEP_DESCRIPTIVE_SHADOW =
ENGINEERING_READY_NOT_PRODUCTION

FEP_REAL_FIRST_OBSERVED_ENTRY =
NOT_GRANTED_WAIT_REAL_SESSION

FEP_MODEL_ENGINEERING =
NOT_STARTED

FEP_MODEL_DISPLAY =
UNGRANTED

FEP_PRIORITY_USE =
UNGRANTED

FEP_PRODUCTION =
UNGRANTED

introduced_active_failures =
0

E3 =
NOT_AUTHORIZED_UNTIL_E2_EXTERNAL_AUDIT

NEXT =
STOP_WAIT_V4_15E2_R1R1_INDEPENDENT_EXTERNAL_AUDIT
```

If no historical capability scope can be defensibly admitted:

```text
V4_15E2_R1R1_REPAIR = BLOCKED
NEXT = STOP_WAIT_EXTERNAL_REPAIR_DISPOSITION
```

Do not substitute synthetic history and do not lower the policy to obtain PASS.
