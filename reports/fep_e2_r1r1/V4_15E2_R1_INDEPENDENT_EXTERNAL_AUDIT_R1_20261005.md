# V4-15E2 R1｜Conditional Statistics Baseline Independent External Audit R1｜2026-10-05

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`
Branch: `codex/v4-system-reform`

E2 execution baseline:

`06549c102da2a203a19004fbeb17a0a0cf717b6a`

Audited remote HEAD:

`87e5b36b32aafd73101f21225703228353d12140`

Commit:

`feat(fep): implement E2 conditional baseline with fail-closed support policy evidence`

Authority:

`V4_15E2_CONDITIONAL_STATISTICS_BASELINE_IMPLEMENTATION_TASK_R1_20261005.md`

---

# 1. Unique Decision

```text
V4_15E2_R1_EXTERNAL_AUDIT =
PARTIAL_PASS_E2R1_REPAIR_REQUIRED

E2_CONDITIONAL_ALGORITHM_MECHANICS =
PASS_KEEP

E2_FIXED_BACKOFF =
PASS_KEEP

E2_BUCKET_DATE_WEIGHTING =
PASS_KEEP

E2_WEIGHTED_QUANTILE =
PASS_KEEP

E2_DENOMINATOR_MISSINGNESS =
PASS_KEEP

E2_FOLD_REVISION_ISOLATION =
PASS_KEEP

E2_ARTIFACT_DETERMINISM_REGISTRY =
PASS_KEEP

E2_SCOPED_REGRESSION =
PASS_NO_INTRODUCED_ACTIVE_FAILURES

E2_HISTORICAL_ENGINEERING_POPULATION =
FAIL_P0_INPUT_TOO_NARROW

E2_SUPPORT_POLICY_FREEZE =
FAIL_P0_UNSET

E2_SUPPORT_POLICY_SCOPE_BINDING =
FAIL_P0

E2_REPRESENTATIVENESS_DIMENSION_SEMANTICS =
REPAIR_P1

V4_15E2_LOCAL_IMPLEMENTATION =
BLOCKED

E3_ENTRY =
NOT_AUTHORIZED

NEXT =
V4_15E2_R1R1_HISTORICAL_DATASET_AND_POLICY_REPAIR
```

This is not a request to redo E2 from scratch.

---

# 2. What R1 Did Correctly

Codex correctly refused to invent support thresholds.

Current exact input is:

```text
expected observations = 1
eligible mature labels = 0
dates = 0
blocks = 0
entities = 0
episodes = 0
```

Current local exit:

```text
V4_15E2_LOCAL_IMPLEMENTATION = BLOCKED
FEP_CONDITIONAL_BASELINE = DIAGNOSTIC_ONLY
FEP_SUPPORT_POLICY = UNSET_DIAGNOSTIC_ONLY
```

This fail-closed behavior is correct.

The implementation did not turn test parameters into an admission policy and did not lower thresholds to obtain PASS.

---

# 3. Conditional Mechanics｜PASS_KEEP

Implementation:

```text
src/workbench_analysis/fep_e2/conditional.py
src/workbench_analysis/fep_e2/support.py
src/workbench_analysis/fep_e2/input.py
src/workbench_analysis/fep_e2/registry.py
```

The following mechanics are materially correct and should be preserved:

```text
fixed L4 → L1 backoff order
first-supported-level selection
no outcome-sign selection of backoff
bucket-internal equal-date weighting
exact inverse empirical CDF weighted quantile
continuous descriptive statistics
categorical observed frequencies
ANY-event overlap semantics
complete denominator preservation
fold/revision binding
deterministic logical digest
append-only artifact publication
```

The test vectors cover the required negative mechanics.

Do not rewrite these modules unless a specific defect below requires a narrow change.

---

# 4. Regression｜PASS_KEEP

Current full E2 scoped regression:

```text
2509 passed
4 skipped
52 existing failures
0 introduced active failures
```

Existing debt remains:

```text
43 prior registered failures
9 independently reproduced pre-FEP baseline failures
```

The same two governed superseded nodes remain the only deselections.

Therefore:

```text
E2_REGRESSION =
PASS_NO_INTRODUCED_ACTIVE_FAILURES
```

---

# 5. P0-1｜The E2 Admission Dataset Is Too Narrow

Current `E1_FROZEN_DATASET.json` contains:

```text
1 expected observation
1 target = ABS_RETURN_N:T1
0 eligible rows
1 MISSING_LABEL
```

This is a valid smoke/diagnostic input.

It is **not** sufficient to freeze:

```text
minimum rows
minimum dates
minimum non-overlap blocks
minimum entities
minimum episodes
class support
missingness
representativeness
```

The current support discovery correctly reports:

```text
INSUFFICIENT_THRESHOLD_EVIDENCE
```

The error is not that E2 lacks future real samples.

The error is that R1 treated the single E1 acceptance snapshot as if it were the only allowed engineering population.

FEP R2 allows historical/reconstructed engineering evidence while keeping real FIRST_OBSERVED/OOS capability ungranted.

Therefore E2 must construct a larger historical engineering ENTRY population.

---

# 6. Do Not Use Existing Synthetic V4-15 History As Admission Evidence

V4-15 runtime contains many useful settlement vectors and outcome artifacts.

However historical publication counts explicitly classify much of the multi-date replay as:

```text
ENGINEERING_SYNTHETIC
```

Those vectors are valid for algorithm testing.

They must not be used to freeze the formal E2 support policy.

Likewise the current real 2026-09-30 cohort contains 117 events but only one market date and no matured accepted real horizons.

It also cannot justify a multi-date support policy.

Required distinction:

```text
synthetic vectors
→ mechanics only

single-date current real population
→ runtime capability evidence only

historical reconstructed real-source replay
→ E2 engineering support-policy evidence
```

---

# 7. P0-2｜Historical Engineering Dataset Required

Create a new isolated historical dataset builder for:

```text
FEP_STOCK_ENTRY_CORE
```

The dataset must be generated from real historical accepted/raw-authority source data with accepted algorithms, but its lineage must remain:

```text
RECONSTRUCTED_ASOF
or
RECONSTRUCTED_CORRECTED

execution_mode = REPLAY / HISTORICAL_SIMULATION

AS_RECORDED = false
FIRST_OBSERVED = false
REAL_OOS = false
production = false
shadow = false
```

Do not claim historical PIT effectiveness.

## 7.1 Historical observation population

Generate the full eligible ENTRY population for a fixed historical window.

Population must be independent of:

```text
UI Top-K
Focus
manual pin
future outcome
E2 statistics
model score
Priority result
```

ENTRY semantics must use the accepted owner/replay chain.

Do not fabricate synthetic ENTRY events merely to increase sample count.

## 7.2 Window freeze

Before any outcome statistics are computed:

```text
discover source coverage
discover warm-up requirements
discover owner/replay capability
discover calendar range
freeze historical start/end
```

Window selection may depend on:

```text
data coverage
algorithm warm-up
target horizon reachability
owner availability
calendar
```

It may not depend on:

```text
returns
positive rate
quantiles
best backoff performance
```

Use the maximal defensible contiguous window rather than hand-picking good periods.

## 7.3 Historical features

Feature snapshots must use accepted feature algorithms and historical data only through the observation cutoff.

No future row may enter a T0 feature.

Because historical first-availability is not proven, the resulting snapshot remains reconstructed engineering evidence.

## 7.4 Historical labels

FEP E2 must not implement label formulas.

Labels must be produced through the accepted V4-15 settlement/Forward owner interface.

The historical adapter may invoke the accepted V4-15 settlement runtime on frozen historical observations and accepted price-path sources.

Resulting labels must be explicitly:

```text
ENGINEERING_HISTORICAL_REPLAY
RECONSTRUCTED
NOT_REAL_OOS
```

Current V4-15 real maturity gates remain unchanged.

---

# 8. P0-3｜Support Policy Is Not Scoped Correctly

Current formal policy:

```text
config/fep_e2_support_policy_v1.json
```

contains one global `values` block and:

```text
required_classes = [POS, NEG]
```

But FEP R2 base identity includes:

```text
target
horizon
observation_scope
feature_variant
evidence_origin
contract versions
```

and categorical FIRST_EXIT support is not the same as continuous POS/NEG support.

Current `baseline()` does not verify that a support policy is authorized for the current query/target/horizon.

Therefore a global unscoped policy is unsafe.

## Required repair

Do not silently mutate the R1 policy semantics.

Create a versioned successor, for example:

```text
FEP_E2_SUPPORT_POLICY_REGISTRY_V1
or
FEP_E2_SUPPORT_POLICY_V1_1
```

Each admitted policy must include an exact applicability key, at least:

```text
entity_type
observation_scope
target_kind
target / target_family
horizon or horizon family
feature_variant
evidence_origin
label_quality_policy
contract versions
```

`baseline()` must fail closed when:

```text
policy applicability != query/base partition
```

Continuous and categorical/event support policies must not share incompatible `required_classes`.

Initial formal admission may be capability scoped, e.g.:

```text
ABS_RETURN_N:T1 continuous baseline = admitted
categorical targets = mechanics-only / UNSET
other horizons = UNSET
```

if historical evidence only supports that scope.

Do not force all targets to PASS.

---

# 9. P1｜Representativeness Dimension Availability

Current diagnostics encode missing dimensions using:

```text
UNAVAILABLE
```

but total variation can become `0` when both expected and observed populations contain only `UNAVAILABLE`.

That must not be reported as if the dimension was actually assessed.

Repair semantics should distinguish:

```text
ASSESSED
UNAVAILABLE_NOT_GATED
INSUFFICIENT_SUPPORT
```

For a dimension unavailable by contract:

```text
do not fail the baseline merely because it is unavailable
do not claim representativeness PASS for that dimension
```

The artifact must expose the dimension status.

---

# 10. Support Threshold Discovery Rules

Once the historical engineering population exists, threshold discovery must remain outcome-performance-free.

Allowed inputs:

```text
rows
dates
interval overlap
non-overlap blocks
entities
episodes
label availability
class-count feasibility
missingness
feature/category population coverage
```

Forbidden:

```text
mean return
positive-rate performance comparison across thresholds
quantile attractiveness
best backoff outcome
Priority performance
future model metric
```

Class counts are allowed only for support feasibility.

The threshold derivation report must explain why each threshold is chosen.

If a specific parameter still lacks defensible evidence:

```text
leave that policy scope UNSET
```

Do not lower it to 1 merely to unblock E2.

---

# 11. Historical Dataset Integrity

Required machine evidence must include:

```text
observation count
unique market dates
non-overlap blocks
entities
episodes
target/horizon counts
status counts
quality counts
missingness by date
reconstructed lineage
source coverage start/end
feature owner bindings
V4-15 settlement bindings
dataset logical digest
```

The denominator must include all expected observations/targets, including:

```text
PENDING
RIGHT_CENSORED
MATURED_DATA_MISSING
SUSPENDED
DELISTED
IDENTITY_UNKNOWN
ADJUSTMENT_UNKNOWN
```

No complete-case population deletion before denominator construction.

---

# 12. Do Not Rewrite E1

E1 final external acceptance remains PASS.

Do not modify:

```text
028–031 FEP migrations
E1 47-field owner contract
E1 three-time authority
E1 V4-18 successor
E1 accepted audit evidence
```

New historical replay artifacts are E2 engineering inputs.

They do not create a new E1 acceptance head.

---

# 13. Do Not Rewrite V4-15 Outcome Math

E2 may create an adapter around the accepted V4-15 settlement runtime.

It may not duplicate:

```text
R_N
MFE
MAE
benchmark
path MDD
event outcome
adjustment
```

formulas.

A deliberately perturbed V4-15 output must be rejected by the E2 input adapter.

---

# 14. Required Repair Tests

At minimum add:

```text
E2R1R1-01 multi-date historical population is non-synthetic
E2R1R1-02 window frozen before labels/statistics
E2R1R1-03 future T0 feature leakage blocked
E2R1R1-04 V4-15 label digest mismatch blocked
E2R1R1-05 reconstructed history never FIRST_OBSERVED
E2R1R1-06 synthetic V4-15 vector rejected for policy admission
E2R1R1-07 single-date 117-row population cannot satisfy date policy
E2R1R1-08 continuous T1 policy cannot be used for FIRST_EXIT
E2R1R1-09 T1 policy cannot silently apply to T20
E2R1R1-10 target-family policy mismatch blocked
E2R1R1-11 unavailable representativeness dimension marked NOT_GATED
E2R1R1-12 support policy frozen before statistics
E2R1R1-13 support threshold discovery does not read outcome performance
E2R1R1-14 historical dataset rebuild deterministic
E2R1R1-15 current real maturity permissions remain unchanged
```

Retain all existing E2-R1 mechanics tests.

---

# 15. Regression

Required:

```text
E2 repair targeted tests
E2 R1 tests
E1/FEP tests
V4-15 settlement tests
R25 WAIT
V4-18 successor
full current FEP scoped regression
```

Final requirement:

```text
introduced_active_failures = 0
```

Existing 52 debt nodes remain visible.

---

# 16. Protected State

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

# 17. External Audit Summary

Current correct disposition is:

```text
E2 algorithm mechanics =
implemented and reusable

E2 formal conditional baseline =
not yet admitted

root blocker =
historical engineering population / support-policy authority

real future sample wait =
NOT REQUIRED for this repair
```

Do not start E3 yet.
