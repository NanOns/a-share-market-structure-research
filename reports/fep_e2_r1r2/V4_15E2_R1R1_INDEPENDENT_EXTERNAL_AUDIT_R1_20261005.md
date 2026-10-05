# V4-15E2 R1R1｜Independent External Audit R1｜2026-10-05

Repository: `NanOns/a-share-market-structure-research`
Branch: `codex/v4-system-reform`
Execution baseline: `87e5b36b32aafd73101f21225703228353d12140`
Audited HEAD: `f8708c34063238547127cab4baefb17c2e5825ac`

## Unique Decision

```text
V4_15E2_R1R1_EXTERNAL_AUDIT =
PARTIAL_PASS_E2R1R2_REQUIRED

E2_HISTORICAL_REAL_SOURCE_REPLAY = PASS_KEEP_RECONSTRUCTED_ENGINEERING
E2_HISTORICAL_FEATURE_REPLAY = PASS_KEEP
E2_V4_15_LABEL_ADAPTER = PASS_KEEP
E2_WINDOW_FREEZE = PASS_KEEP
E2_POLICY_SCOPE_BINDING_MECHANICS = PASS_KEEP
E2_REPRESENTATIVENESS_UNAVAILABLE_SEMANTICS = PASS_KEEP
E2_CONDITIONAL_MECHANICS = PASS_KEEP
E2_SCOPED_REGRESSION = PASS_NO_INTRODUCED_ACTIVE_FAILURES

E2_ENTRY_EVENT_POPULATION_COMPLETENESS = FAIL_P0
E2_ENTRY_EVENT_STRATIFICATION = FAIL_P0
E2_CURRENT_POOLED_T1_BASELINE = NOT_ACCEPTED_SUPERSEDE_REQUIRED

E2_FIRST_PREWATCH_T1 = REPAIRABLE_CAPABILITY_SCOPE
E2_REENTRY = NOT_ADMISSIBLE_UNTIL_OWNER_INPUT_EXISTS
E2_NEW_CONFIRMED = NOT_ADMISSIBLE_WHERE_PRIOR_EPISODE_INPUT_IS_REQUIRED

E3_ENTRY = NOT_AUTHORIZED_YET

NEXT =
V4_15E2_R1R2_ENTRY_EVENT_STRATIFICATION_AND_OWNER_GAP_REPAIR
```

## PASS_KEEP

R1R1 correctly replaced the prior one-observation/zero-label input with a real historical reconstructed engineering replay.

Historical window:

```text
2024-07-15 → 2026-09-24
```

Current scan:

```text
5337 entities
2,860,632 date/entity states
5024 ENTRY observations
5023 eligible T1 labels
```

Lineage remains correctly limited to:

```text
RECONSTRUCTED_CORRECTED
HISTORICAL_SIMULATION
AS_RECORDED = false
FIRST_OBSERVED = false
REAL_OOS = false
production = false
shadow = false
```

The feature side uses accepted owner algorithms and historical source data. RPS is rebuilt through the accepted `rps_midrank` owner rather than current membership. The V4-15 historical label adapter delegates forward outcome generation to `SettlementRuntime`, so FEP does not reimplement `R_N` or settlement arithmetic.

The historical window was frozen before label/statistics work. Support-policy applicability is now exact by scope/target/horizon/feature/evidence/contract identity. Representativeness correctly distinguishes `ASSESSED`, `UNAVAILABLE_NOT_GATED`, and `INSUFFICIENT_SUPPORT`.

Regression:

```text
targeted: 141 passed / 1 skipped / 0 failed
scoped:   2532 passed / 4 skipped
existing debt: 52
introduced active failures: 0
```

## P0-1｜ENTRY Population Is Not Complete

Frozen FEP R2 defines `FEP_STOCK_ENTRY_CORE` as every compliant entry logical event, with `FIRST_PREWATCH`, `REENTRY`, and `NEW_CONFIRMED` stratified.

Current code contains:

```python
blocked = bool(
    prior
    and prior['episode_id']
    and not candidate_policy()['fields']['frozen_invalidation']['implemented']
)
```

When this branch is active, normal `SEED/PREWATCH/CONFIRMED` evaluation is suppressed and several fields are forced to `UNKNOWN`.

The accepted provenance contract says:

```text
frozen_invalidation:
  implemented = false
  required = true
  producer_contract_id = V4_12_EPISODE_INVALIDATION_NOT_IMPLEMENTED
```

Therefore later episode transitions are not fully reconstructible.

Independent symptom:

```text
eligible rows = 5023
entities = 5023
episodes = 5023
total ENTRY observations = 5024
```

Across a replay window longer than two years, the near one-to-one entity/episode relationship is consistent with the missing prior-episode owner suppressing subsequent episode entry logic.

The open item `FEP_E2_HISTORICAL_D2_FACT_AVAILABILITY` therefore changes the formal ENTRY estimand and cannot remain merely diagnostic if the output is used as the complete ENTRY baseline.

## P0-2｜ENTRY Event Types Are Pooled

Current admitted policy uses:

```text
observation_scope = FEP_STOCK_ENTRY_CORE
signal_type = ENTRY
```

and evidence states the baseline pools owner-enrolled `FIRST_PREWATCH/NEW_CONFIRMED` events while retaining event type only as row metadata.

That violates the frozen design requirement that:

```text
FIRST_PREWATCH
REENTRY
NEW_CONFIRMED
```

be stratified.

The existing pooled result:

```text
weighted_mean = 0.0042856332
positive_empirical_frequency = 0.4829343395
selected_level = L1
```

is therefore not an accepted E2 baseline and must be retained only as superseded diagnostic evidence.

## Correct Repair Boundary

Do not fabricate `frozen_invalidation` or `episode_invalidation_contract_id` from raw bars or FEP-local heuristics.

Split ENTRY capability by exact event stratum.

For `FIRST_PREWATCH`, prior-episode invalidation is not needed before the first episode. This stratum may be independently reconstructed and admitted if its full denominator is proven.

For `REENTRY`, if accepted prior-episode invalidation input remains unavailable:

```text
REENTRY = NOT_ENABLED / UNSET
```

For `NEW_CONFIRMED`, admit only cases whose required upstream owner facts are independently reconstructible; otherwise keep that stratum UNSET.

Keep `observation_scope = FEP_STOCK_ENTRY_CORE`, but formal statistical base partitions must use event-specific `signal_type` values, e.g.:

```text
FIRST_PREWATCH
REENTRY
NEW_CONFIRMED
```

A generic `ENTRY` may remain only as umbrella metadata.

## Current Support Policy

The current pooled support policy must be preserved as history but marked:

```text
SUPERSEDED_POOLED_ENTRY_ESTIMAND
```

After event stratification, support discovery and freeze must be rerun for each admitted stratum.

The current `INDEPENDENT_REPETITION_SQRT_BUDGET_V1` is acceptable only as an engineering support heuristic. It is not proof of statistical significance, predictive stability, confidence, or production readiness.

## Required Exit

If `FIRST_PREWATCH:T1` can be independently closed:

```text
V4_15E2_R1R2_REPAIR =
PASS_LOCAL_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

FEP_CONDITIONAL_BASELINE =
BASELINE_ENGINEERING_PASS_LOCAL_CAPABILITY_SCOPED

ADMITTED_ENTRY_EVENT_SCOPE =
FIRST_PREWATCH:T1

REENTRY =
UNSET_OWNER_INPUT_NOT_AVAILABLE

NEW_CONFIRMED =
UNSET_UNLESS_EXACT_OWNER_INPUT_PROVEN

POOLED_ENTRY_BASELINE =
SUPERSEDED_DIAGNOSTIC_ONLY

FEP_MODEL_ENGINEERING = NOT_STARTED
FEP_MODEL_DISPLAY = UNGRANTED
FEP_PRIORITY_USE = UNGRANTED
FEP_PRODUCTION = UNGRANTED

introduced_active_failures = 0

E3 = NOT_AUTHORIZED_UNTIL_EXTERNAL_AUDIT

NEXT =
STOP_WAIT_V4_15E2_R1R2_INDEPENDENT_EXTERNAL_AUDIT
```

If `FIRST_PREWATCH` itself cannot be proven complete, remain BLOCKED.
