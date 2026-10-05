# V4-15E3｜FEP Interpretable Model + Time-Split Engineering Task R1｜2026-10-05

> Project: A-share Market Structure Research V4  
> Branch: `codex/v4-system-reform`  
> Stage: V4-15E3  
> Execution baseline: `7a10c0a3b1563532b7f1eda5af9b90f204fd03d6`  
> Upstream authority: `V4_15E2_FINAL_CAPABILITY_SCOPED_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md`

## 0. Mission

Implement the first E3 engineering capability only for the accepted E2 scope:

```text
FEP_STOCK_ENTRY_CORE
FIRST_PREWATCH
ABS_RETURN_N:T1
CORE
RECONSTRUCTED_CORRECTED
```

Topology:

```text
accepted E2 FIRST_PREWATCH:T1 dataset/baseline
→ freeze experiment contract
→ chronological date-group splits
→ purge leakage
→ train-only preprocessing
→ interpretable robust point model
→ quantile models
→ isolated calibration/coverage diagnostics
→ OOD reference
→ coherence checks
→ one-shot outer test
→ baseline comparison
→ model registry / full experiment ledger
```

Highest allowed local exit:

```text
V4_15E3_LOCAL_IMPLEMENTATION =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

FEP_MODEL_ENGINEERING =
PASS_LOCAL_FIRST_PREWATCH_T1
```

No production/model-display/priority permission is granted.

---

## 1. Scope Is Frozen

E3 R1 may consume only the E2 admitted capability:

```text
observation_scope = FEP_STOCK_ENTRY_CORE
signal_type = FIRST_PREWATCH
target = ABS_RETURN_N:T1
horizon = 1
feature_variant = CORE
evidence_origin = RECONSTRUCTED_CORRECTED
```

Forbidden:

```text
pooled ENTRY
REENTRY
NEW_CONFIRMED
T3/T5/T10/T20
MARKET_EXCESS
SECTOR_EXCESS
DAILY_LANDMARK
```

Do not expand target/scope merely to increase sample count.

---

## 2. E2 Input Must Be Exact

Bind exact predecessor artifacts:

```text
reports/fep_e2_r1r2/FIRST_PREWATCH_E2_DATASET.json.gz
reports/fep_e2_r1r2/CONDITIONAL_BASELINE_FIRST_PREWATCH_T1.json
config/fep_e2_support_policy_registry_v1_1.json
reports/fep_e2_r1r2/FEP_E2_R1R2_CANDIDATE_SEAL.json
```

Verify exact bytes/digests.

Do not rebuild E2 membership from current heads.

Do not resolve newer labels.

---

## 3. Freeze Primary Experiment Before Outer Test

Create a versioned experiment contract before any outer-test metric is read.

Freeze at minimum:

```text
primary scope
primary target
primary horizon
primary point metric
secondary metrics
model families
feature contract
split rule
internal tuning budget
purge rule
calibration role
quantile levels
OOD reference rule
coherence rule
random seed
CPU/thread budget
outer-test window
```

For this continuous-return R1:

```text
primary target = ABS_RETURN_N:T1
primary horizon = 1
primary point metric = DATE_BALANCED_MAE
```

Secondary diagnostics may include:

```text
DATE_BALANCED_HUBER_LOSS
DATE_BALANCED_RMSE
weighted sign hit rate
Spearman rank correlation by date / aggregate
pinball loss for quantiles
quantile empirical coverage
```

Secondary metrics may not replace the frozen primary metric after seeing results.

---

## 4. Date-Grouped Chronological Split

No random CV.

All rows on the same market date must remain in the same split.

Required chronological stages:

```text
TRAIN
INTERNAL_TUNE
CALIBRATION
OUTER_TEST
```

The split rule must be derived/frozen using only:

```text
date counts
support counts
purge requirements
minimum feasible fold sizes
```

not model performance.

Do not mechanically use arbitrary percentages if they violate support.

If a defensible four-part split cannot be formed:

```text
E3 = BLOCKED
```

Do not merge outer test back into training.

---

## 5. Purge / Leakage Rule

Every boundary must consider actual:

```text
label_event_end
source_fact_available_at
label_revision_available_at
episode interval
```

Training/tune/calibration rows may not consume facts/labels that become available only inside the later partition.

At minimum:

```text
purge >= maximum target observation span
```

but implementation must produce an explicit row/date exclusion manifest, not only a numeric gap.

Same market date cannot appear on both sides.

Shared overlapping episode intervals at a boundary must be purged/grouped.

Do not require the same entity to be absent forever from future partitions.

---

## 6. Feature Manifest

Use only fields from accepted FEP/Core field registry and E2 snapshot.

Before model fitting, freeze an exact model feature manifest containing:

```text
field name
producer contract
type
unit
quality rule
missingness rule
encoding rule
transform rule
required/optional status
```

Forbidden:

```text
new ad-hoc factor formulas
future state/event
label-derived features
current-head reconstruction
silent sector/regime substitution
```

Unavailable features remain unavailable.

No result-driven feature selection.

---

## 7. Train-Only Preprocessing

Every learned preprocessing object must be fit only on the TRAIN segment or its internal training subfolds.

This includes:

```text
scaler
imputer
winsor
category encoder
feature selector
OOD reference
```

For missing values:

```text
no global imputation
no future statistics
no NOT_IMPLEMENTED → numeric low-value conversion
```

If an optional imputer is used, its strategy is frozen before outer test and must be trained only on the allowed training segment.

Unknown categorical levels outside the training vocabulary must be explicit OOD/UNKNOWN behavior.

---

## 8. Model Families

E3 R1 is interpretable only.

Required point-model family:

```text
regularized / robust Huber-style linear regression
```

Required distributional family:

```text
linear quantile regression
q = 0.25, 0.50, 0.75
```

Tree/boosting/random forest/neural models are forbidden in E3 R1.

Those belong to optional E4 challenger work.

Do not create a logistic “up probability” model from the continuous target in this R1 merely because positive-rate is available.

---

## 9. Hyperparameter Search

Internal tuning must be chronological and confined to TRAIN / INTERNAL_TUNE.

Freeze:

```text
candidate hyperparameter grid
maximum experiment count
selection metric
tie-break rule
```

before evaluation.

Forbidden:

```text
unbounded tuning
manual reruns until good result
using CALIBRATION or OUTER_TEST to choose alpha/lambda/features
deleting failed trials
```

Every attempted configuration must remain in the experiment ledger.

---

## 10. Calibration Semantics For Continuous Regression

Do not impose probability calibration on regression.

Set probability calibration as:

```text
NOT_APPLICABLE_REGRESSION
```

Use the independent CALIBRATION period for:

```text
quantile coverage diagnostics
interval-width diagnostics
residual distribution diagnostics
coherence diagnostics
```

If any quantile adjustment/rearrangement is applied, it must be pre-registered and learned only from allowed TRAIN/CALIBRATION information.

Do not use OUTER_TEST to repair intervals.

---

## 11. Quantile Coherence

Required raw quantiles:

```text
q25
q50
q75
```

Must test:

```text
q25 <= q50 <= q75
```

Do not silently sort/clip after seeing predictions.

If a rearrangement method is used:

```text
method must be frozen before outer test
raw predictions retained
coherent predictions retained separately
```

If coherence cannot be restored under the frozen rule:

```text
COHERENCE_FAILED
```

and no model display grant is possible.

---

## 12. OOD Engineering

Build an immutable TRAIN-only OOD reference.

At minimum cover:

```text
schema mismatch
unknown categorical value
required feature missing
non-finite numeric value
single-variable training support range
new unavailable/quality state
```

A simple engineering reference may use exact TRAIN-observed category sets and numeric support envelopes.

If joint-distribution OOD is not implemented:

```text
JOINT_OOD = UNSET
```

Do not call the prediction `OOD_OK` globally.

OOD is diagnostic engineering only in E3 R1.

---

## 13. Baseline Comparison

The primary comparison baseline is the accepted E2 FIRST_PREWATCH:T1 descriptive baseline.

For OUTER_TEST, construct a baseline predictor using only allowed pre-test information.

Do not evaluate the E2 full-history mean directly on its own training data as if it were an outer-test baseline.

Required comparison uses the same:

```text
outer dates
outer observations
date-balanced weighting
missing/OOD accounting
```

Report at minimum:

```text
model DATE_BALANCED_MAE
baseline DATE_BALANCED_MAE
absolute delta
relative delta
coverage
sample dates
blocks
entities
episodes
```

Do not require the model to beat baseline for engineering acceptance.

A non-improving model can still yield:

```text
MODEL_ENGINEERING_PASS
MODEL_EFFECTIVENESS = NO_INCREMENT
```

and must be retained.

---

## 14. One-Shot Outer Test

OUTER_TEST may be scored once for the frozen experiment lineage.

Record:

```text
outer_test_opened_at
experiment contract digest
model artifact digest
preprocessing digests
calibration artifact digest
OOD reference digest
prediction digest
evaluation digest
```

After outer-test scoring:

```text
do not change model/hyperparameters/features/splits
within the same experiment lineage
```

Any subsequent revised experiment is a new lineage and may not pretend the prior test was unseen.

---

## 15. Evidence Class

All E3 R1 results remain:

```text
HISTORICAL_SIMULATION
RECONSTRUCTED_CORRECTED
NOT_REAL_OOS
NOT_FIRST_OBSERVED
```

Even a clean chronological outer test inside reconstructed history is not real forward evidence.

Do not use words implying:

```text
production accuracy
real predictive probability
proven alpha
live edge
```

---

## 16. Registry / Experiment Ledger

Persist immutable engineering artifacts for:

```text
experiment contract
fold manifest
purge manifest
feature manifest
preprocessing
training trials
selected point model
selected quantile models
calibration diagnostics
OOD reference
raw predictions
coherent predictions
outer evaluation
baseline comparison
```

All failed trials remain append-only.

`created_at`/run id must not change logical model identity.

Changing any semantic training dependency must change the model digest.

---

## 17. Model State

E3 local model states must distinguish:

```text
ENGINEERING_ONLY
NO_INCREMENT
OUTER_TEST_FAILED
COHERENCE_FAILED
OOD_REFERENCE_INCOMPLETE
CALIBRATION_DIAGNOSTIC_ONLY
```

No model becomes CHAMPION for production by default.

Do not create:

```text
MODEL_DISPLAY ALLOW
PRIORITY_USE ALLOW
production activation
```

---

## 18. Required Negative Matrix

At minimum:

```text
E3-01 random date split rejected
E3-02 same date in train and test rejected
E3-03 label_event_end crossing boundary rejected
E3-04 late label revision leakage rejected
E3-05 future feature/source availability rejected
E3-06 scaler fit on full dataset rejected
E3-07 imputer fit on calibration/test rejected
E3-08 OOD reference fit on non-train data rejected
E3-09 outer test used for hyperparameter selection rejected
E3-10 outer test rerun after model change requires new lineage
E3-11 pooled ENTRY dataset rejected
E3-12 REENTRY/NEW_CONFIRMED input rejected
E3-13 unregistered feature rejected
E3-14 unknown category fail-closed
E3-15 quantile crossing detected
E3-16 silent post-test quantile sorting rejected
E3-17 failed trial cannot be deleted from ledger
E3-18 baseline/model compared on different outer population rejected
E3-19 probability calibration claim on continuous regression rejected
E3-20 MODEL_DISPLAY/PRIORITY_USE remain ungranted
```

---

## 19. Protected State

Must remain:

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_15_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

V4_16_ACCEPTED_HEAD =
NOT_CREATED

R25 =
WAIT_ACCEPTED_DAILY_INPUT

PRIORITY_V1 =
UNCHANGED

Production = false
Shadow = false
Focus = false

FEP_REAL_FIRST_OBSERVED_ENTRY =
NOT_GRANTED

FEP_MODEL_DISPLAY =
UNGRANTED

FEP_PRIORITY_USE =
UNGRANTED

FEP_PRODUCTION =
UNGRANTED
```

No Core / Radar / Validation Cohort / Forward accepted owner may be mutated.

---

## 20. Tests / Regression

Run:

```text
E3 targeted tests
all E2 tests
all FEP E1 tests
V4-15 SettlementRuntime regression
R25 WAIT regression
V4-18 successor regression
full FEP scoped regression
```

Required:

```text
introduced_active_failures = 0
```

Existing governed debt remains visible.

---

## 21. Required Evidence

Create:

```text
reports/fep_e3_r1/
  ENTRY_BASELINE.json
  E2_INPUT_BINDING.json
  EXPERIMENT_PROTOCOL_DISCOVERY.json
  EXPERIMENT_PROTOCOL_FREEZE.json
  DATE_SPLIT_GATE.json
  PURGE_GATE.json
  FEATURE_MANIFEST.json
  PREPROCESSING_GATE.json
  TRAINING_TRIAL_LEDGER.json
  POINT_MODEL_GATE.json
  QUANTILE_MODEL_GATE.json
  CALIBRATION_DIAGNOSTIC_GATE.json
  OOD_REFERENCE_GATE.json
  COHERENCE_GATE.json
  OUTER_TEST_SEAL.json
  OUTER_TEST_EVALUATION.json
  BASELINE_COMPARISON.json
  MODEL_REGISTRY_GATE.json
  NEGATIVE_MATRIX.json
  PROTECTED_STATE_READBACK.json
  TARGETED_SUMMARY.json
  SCOPED_REGRESSION_SUMMARY.json
  LOCAL_ACCEPTANCE_MATRIX.json
  FEP_E3_R1_CANDIDATE_SEAL.json
  COMPLETION_REPORT.md
```

---

## 22. Local Acceptance

Engineering PASS requires:

```text
exact E2 admitted scope
frozen chronological experiment protocol
no date leakage
explicit purge ledger
train-only preprocessing
bounded internal tuning
Huber-style point model
q25/q50/q75 quantile models
calibration diagnostics
OOD engineering reference
coherence state
one-shot outer test
same-population baseline comparison
immutable trial/model registry
0 introduced active failures
```

Engineering acceptance does NOT require statistically positive model improvement.

If the model does not improve:

```text
FEP_MODEL_ENGINEERING = PASS_LOCAL
MODEL_EFFECTIVENESS = NO_INCREMENT
```

This is preferable to tuning against the outer test.

---

## 23. Required Exit

If all engineering gates pass:

```text
V4_15E3_LOCAL_IMPLEMENTATION =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

FEP_MODEL_ENGINEERING =
PASS_LOCAL_FIRST_PREWATCH_T1

MODEL_EFFECTIVENESS =
INCREMENT_OR_NO_INCREMENT_AS_OBSERVED

REAL_OOS_EVIDENCE =
NOT_GRANTED

MODEL_DISPLAY =
UNGRANTED

PRIORITY_USE =
UNGRANTED

FEP_PRODUCTION =
UNGRANTED

E4 =
NOT_REQUIRED_FOR_E3_PASS

NEXT =
STOP_WAIT_V4_15E3_INDEPENDENT_EXTERNAL_AUDIT
```

If time split / purge / preprocessing / outer-test integrity cannot be proven:

```text
V4_15E3_LOCAL_IMPLEMENTATION = BLOCKED
NEXT = STOP_WAIT_EXTERNAL_REPAIR_DISPOSITION
```

Do not relax leakage controls to obtain PASS.
