# V4-15E2｜FEP Conditional Statistics Baseline Implementation Task R1｜2026-10-05

> Project: A-share Market Structure Research V4
> Branch: `codex/v4-system-reform`
> Stage: V4-15E2
> Execution baseline: `06549c102da2a203a19004fbeb17a0a0cf717b6a`
> Upstream authority: `V4_15E1_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md`

## 0. Mission

Implement the frozen FEP R2 E2 layer:

```text
E1 as-of dataset
→ fixed conditional backoff
→ exact weighted descriptive statistics
→ support / thin-sample gates
→ missingness / representativeness diagnostics
→ baseline artifact registry
→ descriptive Shadow engineering
```

Highest allowed local exit:

```text
V4_15E2_LOCAL_IMPLEMENTATION =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

FEP_CONDITIONAL_BASELINE =
BASELINE_ENGINEERING_PASS_LOCAL
```

This is not a model stage.

Do not start E3.

## 1. Frozen Contract

Implement `CONDITIONAL_EXPECTANCY_V1`.

Base partition identity is immutable across:

```text
entity_type
observation_scope
signal_type
target
horizon
feature_variant
evidence_origin
label_quality_policy
contract versions
```

Never back off across this base partition.

FIRST_EXIT / categorical structural targets remain separate from continuous-return targets.

## 2. Fixed Backoff

Required order:

```text
L4 = base + regime + trend + position + risk
L3 = base + regime + trend + risk
L2 = base + regime
L1 = base
```

Selection rule:

```text
choose the first level from L4 → L1
that satisfies the frozen support gate
```

Forbidden:

```text
choose a level because return is higher
choose a level because positive-rate is better
search arbitrary condition combinations
cross base partition
fallback to global best rate
```

If none satisfies support:

```text
support_state = THIN_SAMPLE / INSUFFICIENT
diagnostic only
```

## 3. E2 Support Policy Freeze

E2 owns:

```text
minimum rows
minimum unique dates
minimum non-overlap date blocks
minimum entities
minimum episodes
positive/negative support
per-class support
missingness gate
representativeness gate
```

These thresholds may not be chosen after inspecting outcome performance.

Required order:

```text
1. inventory E1 dataset size and observable-label coverage
2. inventory date/entity/episode dependence
3. simulate time-block support
4. inspect class-count feasibility
5. inspect missingness/coverage
6. freeze thresholds
7. only then compute outcome statistics
```

Threshold discovery inputs must exclude:

```text
mean return
positive rate
quantiles
best backoff result
future model metric
Priority result
```

Do not use arbitrary defaults such as 100 rows / 60 days / 0.60 probability without evidence.

If a defensible threshold cannot be frozen:

```text
parameter = UNSET
E2 = diagnostic only
```

## 4. First Formal Scope

First E2 scope:

```text
FEP_STOCK_ENTRY_CORE
```

Use E1 engineering dataset mechanics.

Current real state remains:

```text
FEP_REAL_FIRST_OBSERVED_ENTRY =
NOT_GRANTED_WAIT_REAL_SESSION

CURRENT_REAL_MATURITY_EVIDENCE =
NONE

PROVED_HORIZONS =
[]
```

Therefore E2 may use accepted historical / reconstructed-as-of engineering datasets for algorithm validation.

It must not call them:

```text
REAL_OOS
FIRST_OBSERVED
PRODUCTION
```

Other scopes remain NOT_ENABLED unless separately admitted.

## 5. Dataset Identity

Every E2 statistics artifact must exact-bind:

```text
dataset_id
dataset_digest
feature_contract_id
target_contract_id
scope_id
fold/partition identity
label revision selections
complete denominator digest
support policy id
conditional statistics contract id
```

No `latest` dataset resolution.

No rebuilding old E1 rows from current heads.

## 6. Bucket Reweighting

Within selected bucket B:

```text
D_B = distinct market dates in B
n_dB = eligible rows in B on date d
w_iB = 1 / (D_B * n_dB)
sum_B(w_iB) = 1
```

Do not reuse full-scope weights after conditioning.

Mandatory counterexample:

```text
full scope:
same day 2 rows → each 0.5

bucket:
only one row, y=0.1

correct:
weight = 1
mean = 0.1
positive_rate = 1
```

Forbidden wrong result:

```text
mean = 0.05
positive_rate = 0.5
```

## 7. Continuous Statistics

For eligible continuous targets compute at minimum:

```text
weighted mean
weighted positive empirical rate
weighted p25
weighted median/p50
weighted p75
minimum
maximum
matched row count
unique dates
blocks
entities
episodes
support state
weight digest
```

Weighted empirical quantile must be implemented explicitly:

```text
sort y
accumulate normalized weights
return the smallest ordered y
whose cumulative weight >= q
```

Do not rely on an implicit library quantile default.

p25/p75 are result dispersion, not confidence intervals.

## 8. Categorical / Event Statistics

For categorical targets such as FIRST_EXIT:

```text
weighted class frequencies
including NONE where eligible
```

must sum to 1.

For independent ANY event targets:

```text
ANY_CONFIRM
ANY_INVALIDATE
ANY_EXPIRE
```

do not force rates to sum to 1.

Before later model/calibration stages, report:

```text
observed weighted frequency
```

not calibrated probability.

## 9. Support State

Support must use all applicable dimensions:

```text
rows
unique dates
non-overlap date blocks
entities
episodes
positive/negative counts
per-class counts
missingness
representativeness
```

Forbidden shortcuts:

```text
row count only
Kish n_eff only
same-day thousands of stocks treated as independent dates
one stock overlapping events treated as independent episodes
```

Mandatory negatives:

```text
100 stocks × 1 date
must fail multi-date support

1 entity × many overlapping events
must fail episode support when policy requires independent episodes
```

## 10. Missingness / Representativeness

For each base partition / target / horizon record:

```text
expected denominator
eligible labeled
pending
right-censored
matured-data-missing
suspended
delisted
identity unknown
adjustment unknown
other explicit reason
```

Continuous targets remain complete-case descriptive estimands unless a future contract changes that.

Compare observable subset against the full expected population using pre-outcome features/categories.

At minimum inspect:

```text
date
industry/sector when legally available
market state/regime
risk state
feature-support buckets
```

If representativeness fails:

```text
diagnostic only
no full-population claim
```

Do not invent sensitivity bounds for unidentified missing groups.

## 11. Thin Sample States

Machine-readable states must include equivalent semantics to:

```text
SUPPORTED
THIN_ROWS
THIN_DATES
THIN_BLOCKS
THIN_ENTITIES
THIN_EPISODES
THIN_CLASS
REPRESENTATIVENESS_FAIL
MISSINGNESS_FAIL
NOT_EVALUABLE
```

Backoff is driven only by frozen support policy.

## 12. Baseline Artifact Registry

Create immutable versioned baseline artifacts.

Suggested files:

```text
config/fep_conditional_statistics_contract_v1.json
config/fep_e2_support_policy_v1.json
src/workbench_analysis/fep_e2/conditional.py
src/workbench_analysis/fep_e2/support.py
src/workbench_analysis/fep_e2/registry.py
```

Each artifact must include:

```text
artifact_id
contract_id
scope
target
horizon
feature_variant
evidence_origin
dataset digest
support-policy digest
selected backoff level
condition tuple
support state
statistics payload
weight digest
denominator/missingness summary
created_at
logical digest
```

`created_at` must not affect logical digest.

## 13. Baseline Is Not a Model

E2 must not create:

```text
trained linear model
logistic model
quantile model
tree model
calibrator
OOD detector
champion
MODEL_DISPLAY grant
PRIORITY_USE grant
```

If a registry row needs artifact type:

```text
CONDITIONAL_STATISTICS_BASELINE
```

not model.

## 14. Descriptive Shadow Boundary

Allowed:

```text
historical conditional mean
historical weighted frequency
historical conditional distribution
support state
sample dates/blocks/entities/episodes
missingness state
```

Forbidden wording:

```text
this stock has X% probability of rising
predicted return
expected executable profit
buy probability
model confidence
```

No production UI integration is required in E2.

## 15. Backoff Counterfactuals

Mandatory:

```text
L4 supported, mean negative
L3 mean higher
→ must still select L4

L4 unsupported
L3 supported
→ select L3

L4..L1 all unsupported
→ thin/diagnostic only
```

Outcome sign/performance must not drive level selection.

## 16. Scope Isolation

Block aggregation across:

```text
ENTRY vs DAILY
Core vs Supplemental
different evidence_origin
different target
different horizon
different contract version
FIRST_EXIT vs continuous return
Sector context vs Core variant
```

Any cross-base partition aggregation must fail closed.

## 17. PIT / Revision Preservation

E2 consumes only E1-selected rows.

It must not:

```text
select newer label revision
change fold cutoff
promote pending label to eligible
rebuild snapshot from current head
read future State/Event as feature
```

Mandatory vector:

```text
early fold uses r1
late fold uses r2
current latest becomes r3

early E2 artifact remains bound to r1
```

## 18. Parameter Governance

Freeze only E2-owned parameters.

Required metadata:

```text
parameter_id
value or UNSET
unit
allowed range
owner_stage = E2
reason
evidence
introduced_at
supersedes
status
freeze_before_statistics_at
freeze_input_digest
```

Prove support thresholds were frozen before statistics generation.

## 19. Determinism

Repeated exact input:

```text
dataset
support policy
condition contract
```

must yield identical logical digest.

Exclude from logical digest:

```text
created_at
run_id
temporary path
```

Semantic changes must change digest:

```text
dataset revision
support threshold
backoff level
target/horizon
condition tuple
weight method
quantile method
```

## 20. Mandatory Negative Matrix

At minimum:

```text
E2-01 bucket reweight vs inherited scope weight
E2-02 weighted quantile exact definition
E2-03 supported L4 negative mean does not fallback
E2-04 unsupported L4 falls to L3
E2-05 no supported level → thin
E2-06 one date many stocks fails date support
E2-07 one entity overlapping episodes fails episode support
E2-08 cross scope aggregation blocked
E2-09 cross target/horizon blocked
E2-10 cross evidence-origin blocked
E2-11 categorical frequencies normalize
E2-12 ANY events may overlap
E2-13 pending/missing remain denominator
E2-14 representativeness fail blocks full-population claim
E2-15 later label revision cannot alter early artifact
E2-16 created_at does not change logical digest
E2-17 support-policy change changes digest
E2-18 no MODEL_DISPLAY/PRIORITY_USE created
E2-19 PRIORITY_V1 unchanged
E2-20 E2 failure does not affect Core/E1
```

## 21. Real-Sample Boundary

E2 engineering acceptance does not wait for future real samples.

But it also does not grant:

```text
real statistical effectiveness
real OOS support
production descriptive display
```

Historical/reconstructed baseline is sufficient for engineering validation.

## 22. Existing Debt

Current known existing debt remains:

```text
43 prior registered failures
9 independently reproduced pre-FEP failures
```

E2 required regression condition:

```text
introduced_active_failures = 0
```

Do not hide new failures as baseline debt.

## 23. Protected State

Must remain:

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_15_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_16_ACCEPTED_HEAD = NOT_CREATED

Production = false
Shadow = false
Focus = false

FEP_MODEL_DISPLAY = UNGRANTED
FEP_PRIORITY_USE = UNGRANTED
FEP_PRODUCTION = UNGRANTED

PRIORITY_V1 = UNCHANGED
```

Do not alter Core eligibility, Radar, Validation Cohort, Forward settlement or DM01/R25.

## 24. Tests

Run:

```text
E2 targeted
E1/FEP regression
V4-15 label adapter
R25 WAIT
V4-18 successor
main FEP scoped regression
```

Only already-governed superseded assertions may remain deselected.

## 25. Evidence

Create:

```text
reports/fep_e2_r1/
  ENTRY_BASELINE.json
  E1_INPUT_BINDING.json
  SUPPORT_POLICY_DISCOVERY.json
  SUPPORT_POLICY_FREEZE.json
  CONDITIONAL_CONTRACT_GATE.json
  BACKOFF_GATE.json
  WEIGHTING_GATE.json
  WEIGHTED_QUANTILE_GATE.json
  CONTINUOUS_BASELINE_GATE.json
  CATEGORICAL_BASELINE_GATE.json
  MISSINGNESS_GATE.json
  REPRESENTATIVENESS_GATE.json
  SCOPE_ISOLATION_GATE.json
  REVISION_PIT_GATE.json
  ARTIFACT_REGISTRY_GATE.json
  DETERMINISM_GATE.json
  NEGATIVE_MATRIX.json
  PROTECTED_STATE_READBACK.json
  TARGETED_SUMMARY.json
  SCOPED_REGRESSION_SUMMARY.json
  LOCAL_ACCEPTANCE_MATRIX.json
  FEP_E2_R1_CANDIDATE_SEAL.json
  COMPLETION_REPORT.md
```

## 26. Acceptance Matrix

At minimum:

```text
E2-A01 E1 exact input binding
E2-A02 support discovery excludes outcome performance
E2-A03 policy frozen before statistics
E2-A04 fixed L4→L1 backoff
E2-A05 bucket date weighting
E2-A06 exact weighted quantile
E2-A07 continuous statistics
E2-A08 categorical statistics
E2-A09 rows/dates/blocks/entities/episodes support
E2-A10 missingness denominator
E2-A11 representativeness
E2-A12 scope isolation
E2-A13 fold/revision PIT preservation
E2-A14 thin-sample fail closed
E2-A15 deterministic logical digest
E2-A16 baseline artifact registry
E2-A17 no model/calibration/OOD
E2-A18 no MODEL_DISPLAY/PRIORITY_USE
E2-A19 PRIORITY_V1 unchanged
E2-A20 scoped regression no new failures
```

A02–A06, A09–A14, A17–A20 are blocking CORE gates.

## 27. Required Exit

Only if all engineering gates pass:

```text
V4_15E2_LOCAL_IMPLEMENTATION =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

FEP_CONDITIONAL_BASELINE =
BASELINE_ENGINEERING_PASS_LOCAL

FEP_SUPPORT_POLICY =
FROZEN_ENGINEERING

FEP_DESCRIPTIVE_SHADOW =
ENGINEERING_READY_NOT_PRODUCTION

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

NEXT =
STOP_WAIT_V4_15E2_INDEPENDENT_EXTERNAL_AUDIT
```

If support thresholds cannot be defensibly frozen:

```text
V4_15E2_LOCAL_IMPLEMENTATION = BLOCKED
FEP_CONDITIONAL_BASELINE = DIAGNOSTIC_ONLY
NEXT = STOP_WAIT_EXTERNAL_REPAIR_DISPOSITION
```

Do not lower support gates to obtain PASS.
