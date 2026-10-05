# V4-15E3｜FEP Interpretable Model Final Independent External Audit R1｜2026-10-05

## 0. Audit Target
Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`  
Execution baseline: `7a10c0a3b1563532b7f1eda5af9b90f204fd03d6`  
Audited HEAD: `77c7c2c85a5ff0bbd27bb664900673de7a3bff5a`

## 1. Unique Decision
```text
V4_15E3_FINAL_EXTERNAL_AUDIT =
PASS_FINAL_ENGINEERING_CAPABILITY_SCOPED

FEP_MODEL_ENGINEERING =
PASS_EXTERNAL_FIRST_PREWATCH_T1

MODEL_EFFECTIVENESS =
NO_INCREMENT

POINT_MODEL =
ENGINEERING_ONLY

QUANTILE_MODELS =
ENGINEERING_DIAGNOSTIC_ONLY

OOD_REFERENCE =
MARGINAL_ONLY_JOINT_UNSET

OUTER_PREDICTABLE_COVERAGE =
46 / 205 = 22.4390%

REAL_OOS =
NOT_GRANTED

FIRST_OBSERVED =
NOT_GRANTED

MODEL_DISPLAY =
UNGRANTED

PRIORITY_USE =
UNGRANTED

FEP_PRODUCTION =
UNGRANTED

E4_ENTRY =
AUTHORIZED_OPTIONAL_CHALLENGER

E5_ENTRY =
NOT_BLOCKED_BY_E4

NEXT =
V4_15E4_TREE_CHALLENGER_ENGINEERING
```

## 2. Exact E2 Input｜PASS
E3 consumes the exact accepted E2 FIRST_PREWATCH × ABS_RETURN_N:T1 artifacts and does not rebuild membership from current heads or reselect newer label revisions. Pooled ENTRY, REENTRY and NEW_CONFIRMED are rejected.

## 3. Protocol Freeze｜PASS
The active lineage is `FEP_E3_R1_FIRST_PREWATCH_T1_SERIALIZATION_V1_1`. Primary metric is `DATE_BALANCED_MAE`. Split rule, purge rule, feature manifest, hyperparameter budgets, calibration role, OOD rule, runtime versions and coherence rule are frozen before active-lineage fitting and outer scoring.

An earlier split-feasibility attempt stopped before protocol freeze with:
```text
model_trials = 0
outer_opened = false
outcome_performance_consumed = false
```
This is valid fail-closed discovery.

## 4. v1 → v1.1 Pre-Outer Repair｜PASS
A serialization-ordering defect was found before any Outer Test opening. The old lineage is retained as `SUPERSEDED_PRE_OUTER_SERIALIZATION_LINEAGE`.

Evidence:
```text
prior outer openings = 0
current outer openings = 1
```

The successor v1.1 freezes a new 12-trial lineage and only then opens the Outer Test.

## 5. Chronological Split｜PASS
The split is:
```text
TRAIN
→ INTERNAL_TUNE
→ CALIBRATION
→ OUTER_TEST
```
Dates are grouped and strictly chronological. No random CV is used. Split discovery uses date/sample/block feasibility and not outcome performance.

## 6. Purge / Leakage Controls｜PASS_ENGINEERING_RECONSTRUCTED
The purge ledger contains 4553 rows with 254 exclusions. Reasons include required feature quality unavailable, label-event-end boundary crossing and pending label.

Checks cover:
```text
label_event_end
feature source trade date
source_fact_available_at
label_revision_available_at
label_training_mature_at
shared episode overlap
```

The temporal model remains dual-clock reconstructed engineering and does not prove historical first availability or PIT:
```text
REAL_OOS = false
FIRST_OBSERVED = false
```

## 7. Feature / Preprocessing｜PASS
20 registered Core fields are frozen before fitting. No result-driven feature selection is used.

Preprocessing:
```text
fit partition = TRAIN
fit rows = 3893
imputer = NOT_USED_COMPLETE_CASE
TRAIN-only scaler/category vocabulary
```

## 8. Training / Tuning｜PASS
Active lineage keeps 12 bounded trials:
```text
6 Huber point trials
6 linear quantile trials
```

Selection uses `INTERNAL_TUNE` only.

Selected point model:
```text
HuberRegressor
alpha = 1.0
epsilon = 1.75
```

Selected quantile models:
```text
q25 alpha = 0.01
q50 alpha = 0.01
q75 alpha = 0.01
```

All trial artifacts remain retained.

## 9. Calibration / Quantile Diagnostics｜PASS_ENGINEERING_WITH_WEAK_RESULT
Probability calibration is correctly `NOT_APPLICABLE_REGRESSION`.

Calibration empirical coverage is weak:
```text
q25 ≈ 10.00%
q50 ≈ 18.61%
q75 ≈ 49.60%
middle interval ≈ 39.60%
```

Outer:
```text
q25 ≈ 22.86%
q50 ≈ 51.43%
q75 ≈ 59.29%
middle interval ≈ 36.43%
```

This does not block engineering acceptance, but it blocks any calibrated predictive-interval claim.

## 10. OOD｜PASS_ENGINEERING_WITH_MAJOR_LIMITATION
OOD reference is TRAIN-only and covers schema, missingness, non-finite values, unknown categories, quality state and marginal numeric support envelopes.

Not implemented:
```text
JOINT_OOD = UNSET
global_OOD_OK = false
```

## 11. Outer Population｜PASS_WITH_LOW_COVERAGE
Frozen Outer ledger:
```text
205 observations
```

Predictable under the TRAIN-only preprocessing/OOD gate:
```text
46 observations
35 dates
24 blocks
46 entities
46 episodes
```

Coverage:
```text
22.4390%
```

The other 159 rows remain in the population ledger as NOT_EVALUABLE. OOD admission is determined without reading Outer outcomes, so this is not outcome cherry-picking.

The low coverage remains a major non-production limitation.

## 12. Baseline Comparison｜PASS_SAME_POPULATION
The comparison baseline is built before Outer scoring from accepted E2 baseline mechanics restricted to TRAIN.

Exact same 46 observations and date-balanced weights are used.

```text
Model DATE_BALANCED_MAE
= 0.0264982642

Baseline DATE_BALANCED_MAE
= 0.0253833272

absolute improvement delta
= -0.0011149370

relative improvement delta
≈ -4.3924%
```

Therefore:
```text
MODEL_EFFECTIVENESS = NO_INCREMENT
```

The negative result is correctly retained.

## 13. One-Shot Outer｜PASS
The active lineage opens the Outer Test exactly once. Any subsequent semantic model change requires a new lineage and must record that the historical test has already been seen.

## 14. Regression｜PASS
```text
Targeted:
225 passed
1 skipped
0 failed

Scoped:
2584 passed
4 skipped
52 existing debt failures
0 introduced active failures
```

## 15. Protected State｜PASS
```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_15_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_16_ACCEPTED_HEAD = NOT_CREATED

R25 = WAIT_ACCEPTED_DAILY_INPUT
real FEP DB rows = 0
TDX = UNTOUCHED

FIRST_OBSERVED = NOT_GRANTED
REAL_OOS = NOT_GRANTED

MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED

Production = false
Shadow = false
Focus = false

PRIORITY_V1 = UNCHANGED
```

## 16. Acceptance Boundary
E3 is accepted as model engineering, not as model effectiveness.

Current factual interpretation:
```text
engineering pipeline works
chronological experiment works
leakage controls work
registry works

BUT

point model did not beat baseline
quantile calibration is weak
OOD coverage is only 22.44%
JOINT_OOD is not implemented
real forward evidence is absent
```

No model promotion is permitted.

## 17. E4 Disposition
E4 is an optional tree challenger and is not an E5 prerequisite.

Because E3's historical Outer Test is already seen, E4 may reference the same population only as:
```text
SEEN_OUTER_DIAGNOSTIC_ONLY
```

It may not claim a new independent/OOS test on those rows.

## 18. Final State
```text
V4_15E3_FINAL_EXTERNAL_AUDIT =
PASS_FINAL_ENGINEERING_CAPABILITY_SCOPED

FEP_MODEL_ENGINEERING =
PASS_EXTERNAL_FIRST_PREWATCH_T1

MODEL_EFFECTIVENESS =
NO_INCREMENT

E4_ENTRY =
AUTHORIZED_OPTIONAL_CHALLENGER

E5 =
NOT_BLOCKED_BY_E4

NEXT =
V4_15E4_TREE_CHALLENGER_ENGINEERING
```
