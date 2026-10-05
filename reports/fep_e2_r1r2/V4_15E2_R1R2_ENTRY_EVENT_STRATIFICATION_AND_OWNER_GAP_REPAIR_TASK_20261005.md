# V4-15E2 R1R2｜ENTRY Event Stratification & Owner-Gap Repair Task｜2026-10-05

Repository: `NanOns/a-share-market-structure-research`
Branch: `codex/v4-system-reform`
Execution baseline: `f8708c34063238547127cab4baefb17c2e5825ac`
Authority: `V4_15E2_R1R1_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md`

## Mission

Perform a narrow final E2 population repair.

Do not start E3.

## PASS_KEEP

Preserve:

```text
historical real-source scan
historical window 2024-07-15 → 2026-09-24
historical feature replay
RPS replay
V4-15 SettlementRuntime historical label adapter
reconstructed lineage controls
future-feature rejection
conditional weighting/quantile/backoff mechanics
support-policy exact applicability engine
representativeness dimension statuses
artifact registry/determinism
regression accounting
```

Do not rebuild E1.

## Root Defect

Accepted input provenance currently says:

```text
frozen_invalidation
implemented = false
required = true
producer = V4_12_EPISODE_INVALIDATION_NOT_IMPLEMENTED
```

Current replay suppresses normal `SEED/PREWATCH/CONFIRMED` evaluation whenever a prior episode exists.

The current `5024 observations / 5023 entities / 5023 episodes` must not be treated as the complete ENTRY population.

## Do Not Fabricate Missing Owner Input

Forbidden:

```text
derive frozen_invalidation from raw bars
invent FEP-local invalidation rules
treat UNKNOWN as FALSE
reuse current latest state
create a fake accepted V4_12 owner
modify old accepted V4_10/V4_12 contracts in place
```

If no accepted historical owner exists:

```text
REENTRY / affected NEW_CONFIRMED =
UNSET / NOT_ENABLED
```

## Formal ENTRY Event Strata

Keep:

```text
observation_scope = FEP_STOCK_ENTRY_CORE
```

but formal E2 base partitions must use event-specific signal identities:

```text
FIRST_PREWATCH
REENTRY
NEW_CONFIRMED
```

or exact versioned one-to-one equivalents.

Generic `ENTRY` may remain umbrella metadata only.

## FIRST_PREWATCH Population

Build the complete `FIRST_PREWATCH` population over the already frozen historical window.

Required:

```text
all entities scanned
all dates scanned
event-unique observation_id
episode_id bound
no prior-episode authority required
no outcome/result filtering
no UI/Focus/Top-K filtering
```

Do not fabricate `frozen_invalidation`.

If accepted reducer semantics do not allow first-episode reconstruction without that field, fail closed.

## NEW_CONFIRMED

Separate `NEW_CONFIRMED` from `FIRST_PREWATCH`.

Admit only events with exact reconstructible accepted upstream facts.

If required prior-episode input is unavailable:

```text
reason = OWNER_REQUIRED_INPUT_UNAVAILABLE
status = UNSET / NOT_ENABLED
```

Do not pool unavailable and admitted NEW_CONFIRMED cases.

## REENTRY

REENTRY requires accepted episode closure/invalidation identity.

Unless an accepted owner for the required prior-episode facts is independently found:

```text
REENTRY =
NOT_ENABLED_OWNER_INPUT_UNAVAILABLE
```

Retain blocked candidates in diagnostic denominator/state-scan evidence.

## Event Observation Identity

Every admitted event must bind:

```text
entity_id
observation_scope
signal_type
logical_event_id
episode_id
trade_date
source state/event publication
feature snapshot
target/horizon
reconstruction lineage
```

Same entity may have multiple events.

Different episode => different observation.

FIRST_PREWATCH and NEW_CONFIRMED in the same episode must not collapse into one event.

Do not count two events in one episode as two independent episodes.

## Supersede Pooled R1R1 Baseline

Retain the existing R1R1 baseline/policy for audit history.

Create an explicit disposition:

```text
POOLED_ENTRY_T1_BASELINE =
SUPERSEDED_DIAGNOSTIC_ONLY
```

Reason:

```text
pooled event estimand
+
incomplete prior-episode owner capability
```

Do not delete or overwrite historical artifacts.

## Event-Scoped Policy Successor

Create a versioned successor, recommended:

```text
config/fep_e2_support_policy_registry_v1_1.json
```

Bind predecessor exact bytes/digest.

At minimum attempt formal policy for:

```text
FEP_STOCK_ENTRY_CORE
FIRST_PREWATCH
ABS_RETURN_N:T1
CONTINUOUS
CORE
RECONSTRUCTED_CORRECTED
```

REENTRY and unavailable NEW_CONFIRMED remain `UNSET_DIAGNOSTIC_ONLY`.

## Re-Discover Support

Do not reuse pooled thresholds.

For every admitted event stratum, rerun outcome-performance-free discovery:

```text
rows
dates
non-overlap blocks
entities
episodes
POS/NEG class feasibility
missingness
representativeness
```

Freeze policy before statistics.

The existing sqrt-budget rule may remain only as `ENGINEERING_SUPPORT_HEURISTIC`.

## Conditional Baseline

Generate formal statistics only for admitted event strata.

Do not merge FIRST_PREWATCH, NEW_CONFIRMED, and REENTRY to obtain support.

The current pooled baseline must not feed E3.

## Denominator Ledger

Create a complete ledger for:

```text
FIRST_PREWATCH admitted
NEW_CONFIRMED admitted
NEW_CONFIRMED owner-input unavailable
REENTRY owner-input unavailable
PENDING label
RIGHT_CENSORED
other explicit exclusion reasons
```

Blocked transition candidates must not disappear before denominator accounting.

## Required Negative Tests

At minimum:

```text
01 pooled ENTRY policy rejected
02 FIRST_PREWATCH policy exact signal binding
03 FIRST_PREWATCH policy cannot serve REENTRY
04 same entity two episodes produce separate observations
05 same episode FIRST_PREWATCH and NEW_CONFIRMED remain separate events
06 missing frozen_invalidation cannot become FALSE
07 REENTRY without accepted owner input = NOT_ENABLED
08 owner-gap rows retained in denominator
09 pooled R1R1 baseline marked superseded
10 event-specific policy frozen before statistics
11 support discovery reads no outcome performance
12 V4-15 label adapter unchanged
13 historical feature replay unchanged
14 real FIRST_OBSERVED remains ungranted
15 PRIORITY_V1 unchanged
```

Retain all prior E2 tests.

## Evidence

Create:

```text
reports/fep_e2_r1r2/
  ENTRY_BASELINE.json
  R1R1_PASS_KEEP_READBACK.json
  ENTRY_EVENT_STRATA_CONTRACT.json
  FIRST_PREWATCH_POPULATION_GATE.json
  NEW_CONFIRMED_POPULATION_GATE.json
  REENTRY_OWNER_INPUT_GATE.json
  EVENT_DENOMINATOR_LEDGER.json
  POOLED_BASELINE_SUPERSESSION.json
  SUPPORT_POLICY_DISCOVERY_FIRST_PREWATCH_T1.json
  SUPPORT_POLICY_REGISTRY_FREEZE.json
  SUPPORT_POLICY_SCOPE_GATE.json
  CONDITIONAL_BASELINE_FIRST_PREWATCH_T1.json
  NEGATIVE_MATRIX.json
  PROTECTED_STATE_READBACK.json
  TARGETED_SUMMARY.json
  SCOPED_REGRESSION_SUMMARY.json
  LOCAL_ACCEPTANCE_MATRIX.json
  FEP_E2_R1R2_CANDIDATE_SEAL.json
  COMPLETION_REPORT.md
```

## Protected State

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

## Regression

Run:

```text
E2 R1R2 targeted
all E2 R1/R1R1 tests
FEP E1 tests
V4-15 settlement regression
R25 WAIT
V4-18 successor
full current FEP scoped regression
```

Required:

```text
introduced_active_failures = 0
```

Existing 52 debt nodes remain visible.

## Local Exit

If FIRST_PREWATCH:T1 is complete and supported:

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

FEP_DESCRIPTIVE_SHADOW =
ENGINEERING_READY_NOT_PRODUCTION

FEP_MODEL_ENGINEERING = NOT_STARTED
FEP_MODEL_DISPLAY = UNGRANTED
FEP_PRIORITY_USE = UNGRANTED
FEP_PRODUCTION = UNGRANTED

introduced_active_failures = 0

E3 =
NOT_AUTHORIZED_UNTIL_EXTERNAL_AUDIT

NEXT =
STOP_WAIT_V4_15E2_R1R2_INDEPENDENT_EXTERNAL_AUDIT
```

If FIRST_PREWATCH itself is incomplete:

```text
V4_15E2_R1R2_REPAIR = BLOCKED
NEXT = STOP_WAIT_EXTERNAL_REPAIR_DISPOSITION
```
