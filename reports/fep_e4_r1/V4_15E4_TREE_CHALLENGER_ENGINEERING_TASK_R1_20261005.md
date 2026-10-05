# V4-15E4｜FEP Tree Challenger Engineering Task R1｜2026-10-05

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`  
Stage: V4-15E4  
Execution baseline: `77c7c2c85a5ff0bbd27bb664900673de7a3bff5a`

## 0. Mission
Implement one bounded nonlinear challenger for the exact E3 capability:
```text
FEP_STOCK_ENTRY_CORE
FIRST_PREWATCH
ABS_RETURN_N:T1
CORE
RECONSTRUCTED_CORRECTED
```

E4 is engineering only.

The E3 historical Outer Test has already been seen:
```text
E4_SAME_OUTER_EVIDENCE =
SEEN_OUTER_DIAGNOSTIC_ONLY
```

No new independent-OOS claim is allowed.

## 1. Exact E3 Reuse
Bind exact:
```text
active E3 protocol v1.1
fold manifest
purge ledger
feature manifest
preprocessing
OOD reference
model rows
E3 models
E3 outer population ledger
E3 candidate seal
```

Do not rebuild E2/E3 membership or resolve newer labels.

## 2. Frozen Scope
Only:
```text
FIRST_PREWATCH × ABS_RETURN_N:T1
```

Reject pooled ENTRY, REENTRY, NEW_CONFIRMED, other targets, horizons and DAILY scope.

## 3. Challenger Family
Use only:
```text
HistGradientBoostingRegressor
```

Point:
```text
loss = absolute_error
```

Quantiles:
```text
loss = quantile
q25 / q50 / q75
```

Do not add XGBoost, LightGBM, CatBoost, Random Forest search or neural models in R1.

## 4. Feature Representation
Reuse exact E3:
```text
feature manifest
feature_terms
TRAIN-only preprocessing
category vocabulary
complete-case membership
```

No new features, imputation, feature selection or outcome-driven transforms.

## 5. Fold Reuse
Reuse exactly:
```text
TRAIN
INTERNAL_TUNE
CALIBRATION
OUTER_TEST
```

No new split and no invented new holdout.

## 6. Hyperparameter Budget
Freeze before fitting using resource/engineering considerations only.

Upper bounds:
```text
point trials <= 8
quantile trials <= 12
total challenger fits <= 20
```

Allowed bounded parameters:
```text
learning_rate
max_leaf_nodes
max_depth
min_samples_leaf
l2_regularization
```

All attempts remain append-only.

## 7. Selection
Use only `INTERNAL_TUNE`.

Point primary metric:
```text
DATE_BALANCED_MAE
```

Quantile:
```text
DATE_BALANCED_PINBALL_PER_Q
```

CALIBRATION and seen Outer may not select hyperparameters.

## 8. Calibration Diagnostics
Reuse exact E3 CALIBRATION population.

Report:
```text
pinball
q25/q50/q75 empirical coverage
middle interval coverage
crossing frequency
interval width
```

No probability calibration claim.

Only the already frozen E3 coherence rule may be used.

## 9. OOD / Population
Reuse exact E3 TRAIN-only OOD reference and eligibility semantics.

For direct comparison:
```text
E4 comparable population
=
E3 exact predictable population
```

Do not relax OOD because trees can extrapolate.

## 10. Seen Outer Rule
Same E3 historical Outer rows may only be:
```text
SEEN_OUTER_DIAGNOSTIC_ONLY
TEST_PREVIOUSLY_SEEN = true
REAL_OOS = false
PROMOTION_EVIDENCE = false
```

Forbidden:
```text
NEW_OUTER_TEST
UNSEEN_TEST
INDEPENDENT_OOS
```

## 11. Comparison
Use exact same E3 predictable Outer observation IDs.

Compare:
```text
E2 TRAIN-only baseline
E3 Huber point model
E4 tree point challenger
```

Point metrics:
```text
DATE_BALANCED_MAE
DATE_BALANCED_HUBER_LOSS
DATE_BALANCED_RMSE
weighted sign hit
coverage
dates
blocks
entities
episodes
```

Quantile diagnostics compare E3 vs E4 on pinball, coverage, width and coherence.

Primary challenger criterion remains DATE_BALANCED_MAE.

## 12. Allowed Dispositions
```text
CHALLENGER_ENGINEERING_PASS_INCREMENT_DIAGNOSTIC
CHALLENGER_ENGINEERING_PASS_NO_INCREMENT
CHALLENGER_ENGINEERING_PASS_MIXED
CHALLENGER_ENGINEERING_BLOCKED
```

Even if E4 is better on the seen historical Outer:
```text
CHAMPION = false
PROMOTION = UNGRANTED
```

## 13. Preserve E3
Do not rewrite:
```text
E3 MODEL_EFFECTIVENESS = NO_INCREMENT
```

E4 cannot retroactively turn E3 into a winner.

## 14. Interpretability
Save model-computation diagnostics only:
```text
permutation/feature importance on TRAIN or CALIBRATION
tree complexity
leaf support
```

No causal/资金意图 interpretation.

No Outer-based feature selection.

## 15. Registry
Persist immutable:
```text
challenger protocol
trial ledger
selected point challenger
selected quantile challengers
calibration diagnostics
seen-outer predictions
seen-outer diagnostic comparison
feature-importance diagnostic
candidate seal
```

## 16. Required Negative Matrix
At minimum:
```text
E4-01 new/random split rejected
E4-02 E3 fold mutation rejected
E4-03 pooled ENTRY rejected
E4-04 REENTRY/NEW_CONFIRMED rejected
E4-05 new feature rejected
E4-06 OOD relaxation rejected
E4-07 seen Outer tuning rejected
E4-08 seen Outer called UNSEEN rejected
E4-09 seen Outer called REAL_OOS rejected
E4-10 promotion claim rejected
E4-11 trial budget overflow rejected
E4-12 failed trial deletion rejected
E4-13 calibration selection rejected
E4-14 post-result coherence rule rejected
E4-15 E3 artifact mutation rejected
E4-16 PRIORITY_V1 mutation rejected
E4-17 MODEL_DISPLAY grant rejected
E4-18 PRIORITY_USE grant rejected
E4-19 production/shadow grant rejected
E4-20 E4 failure leaves E3/E2/Core unchanged
```

## 17. Protected State
Must remain:
```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_15_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_16_ACCEPTED_HEAD = NOT_CREATED

R25 = WAIT_ACCEPTED_DAILY_INPUT
PRIORITY_V1 = UNCHANGED

E3 MODEL_EFFECTIVENESS = NO_INCREMENT

FIRST_OBSERVED = NOT_GRANTED
REAL_OOS = NOT_GRANTED

MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED

Production = false
Shadow = false
Focus = false
```

## 18. Regression
Run:
```text
E4 targeted
all E3 tests
all E2 tests
all FEP E1 tests
V4-15 settlement regression
R25 WAIT
V4-18 successor
full FEP scoped regression
```

Required:
```text
introduced_active_failures = 0
```

## 19. Evidence
Create:
```text
reports/fep_e4_r1/
  ENTRY_BASELINE.json
  E3_INPUT_BINDING.json
  CHALLENGER_PROTOCOL_DISCOVERY.json
  CHALLENGER_PROTOCOL_FREEZE.json
  FOLD_REUSE_GATE.json
  FEATURE_REUSE_GATE.json
  OOD_REUSE_GATE.json
  TRAINING_TRIAL_LEDGER.json
  POINT_CHALLENGER_GATE.json
  QUANTILE_CHALLENGER_GATE.json
  CALIBRATION_DIAGNOSTIC_GATE.json
  FEATURE_IMPORTANCE_DIAGNOSTIC.json
  SEEN_OUTER_POPULATION_GATE.json
  SEEN_OUTER_DIAGNOSTIC_EVALUATION.json
  BASELINE_E3_E4_COMPARISON.json
  MODEL_REGISTRY_GATE.json
  NEGATIVE_MATRIX.json
  PROTECTED_STATE_READBACK.json
  TARGETED_SUMMARY.json
  SCOPED_REGRESSION_SUMMARY.json
  LOCAL_ACCEPTANCE_MATRIX.json
  FEP_E4_R1_CANDIDATE_SEAL.json
  COMPLETION_REPORT.md
```

## 20. Required Exit
If challenger engineering works:
```text
V4_15E4_LOCAL_IMPLEMENTATION =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

FEP_CHALLENGER_ENGINEERING =
PASS_LOCAL

CHALLENGER_EFFECTIVENESS =
INCREMENT_DIAGNOSTIC
or
NO_INCREMENT
or
MIXED

SEEN_OUTER_DIAGNOSTIC_ONLY =
true

NEW_INDEPENDENT_OOS_EVIDENCE =
false

CHAMPION =
false

MODEL_DISPLAY =
UNGRANTED

PRIORITY_USE =
UNGRANTED

FEP_PRODUCTION =
UNGRANTED

NEXT =
STOP_WAIT_V4_15E4_INDEPENDENT_EXTERNAL_AUDIT
```

If challenger is blocked:
```text
V4_15E4_LOCAL_IMPLEMENTATION =
NO_INCREMENT_OR_BLOCKED_NONBLOCKING

E5 =
STILL_AUTHORIZED_BY_E2_E3

NEXT =
STOP_WAIT_V4_15E4_INDEPENDENT_EXTERNAL_AUDIT
```
