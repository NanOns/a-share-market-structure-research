# R19D｜V4-15 Contract Integration / Independent Completeness Oracle｜2026-10-03

## 0. Entry Gate

Execute only after:

```text
R19A_V4_14_PROMOTION = PASS_LOCAL
R19B_V4_15_RADAR_COHORT_CONTRACT_FREEZE = PASS_LOCAL
R19C_V4_15_SETTLEMENT_CONTRACT_FREEZE = PASS_LOCAL
```

## 1. Goal

Integrate the two frozen V4-15 contract families into one complete, machine-readable stage-entry package and independently prove that the package is semantically closed before any runtime implementation begins.

No V4-15 runtime is implemented in this task.

## 2. Required Integration Artifacts

Recommended minimum set:

```text
config/v4_15_contract_package_v1.json
config/v4_15_field_registry_v1.json
config/v4_15_dag_registry_v1.json
config/v4_15_source_capability_matrix_v1.json
config/v4_15_quality_degradation_v1.json
config/v4_15_machine_vectors_v1.json
config/v4_15_storage_schema_design_v1.json
reports/r19d/V4_15_STAGE_ENTRY_GATE.json
```

Names may follow repository conventions.

## 3. Contract Package Authority

The package must bind exact:
- `data/v4/V4_14_ACCEPTED_HEAD.json`;
- current Data Head;
- accepted market calendar;
- accepted historical/security identity authorities;
- accepted PIT membership authority;
- all R19B contracts;
- all R19C contracts;
- upstream V4-07..V4-14 owner heads actually consumed;
- the V4.2.2 master contract sections used as design authority.

Do not scan for “latest”.

## 4. Unified Field Registry

Create one union registry from the two task families.

Independent checks:
- every current V4-15 field appears exactly once;
- no duplicated field authority;
- producer and time role are explicit;
- quality / UNKNOWN / NOT_APPLICABLE semantics are explicit;
- revision participation is explicit;
- identity participation is explicit;
- no field points to Focus/UI/FEP as an upstream Core/Radar source.

Any duplicate current authority is a P0 contract failure.

## 5. V4-15 DAG

Freeze the contract-level DAG:

```text
Accepted V4-14 publication
→ Radar event projection
→ complete daily ledger
→ logical event / observation
→ first ASSERTED enrollment
→ frozen benchmark + controls
→ due planner
→ future accepted source readback
→ settlement / outcome revision
→ readback / statistics consumers
```

Non-edges must explicitly include:

```text
Focus -> enrollment          FORBIDDEN
UI Top-K -> enrollment       FORBIDDEN
Forward outcome -> T0 state  FORBIDDEN
FEP prediction -> Core/Radar FORBIDDEN
Corrected outcome -> T0      FORBIDDEN
same-day future source       FORBIDDEN
```

## 6. Storage Schema Design

Contract-freeze round may define storage design but must not apply a formal migration.

The design must cover append-only identities for at least:
- radar daily ledger;
- logical events;
- event observations;
- enrollment;
- controls;
- benchmark snapshots;
- due items;
- settlement/outcome revisions;
- competing outcomes;
- readback indexes.

Include:
- keys;
- FKs;
- immutable columns;
- append-only revision rules;
- publication/date consistency;
- source digest bindings.

No migration file may be applied to the configured production database this round.

## 7. Capability Matrix

At minimum separate:

```text
RADAR_EVENT_PROJECTION
VALIDATION_COHORT
ABSOLUTE_FORWARD_SETTLEMENT
MARKET_RELATIVE_SETTLEMENT
SECTOR_RELATIVE_SETTLEMENT
CONTROL_A_LEGACY
CONTROL_B_DELTA3
CONTROL_C_MATCHED
COMPETING_OUTCOMES
OUTCOME_REVISION_READBACK
```

Capabilities must degrade independently.

Examples:
- missing sector benchmark must not block absolute stock return;
- Control A unavailable must not block Control B/C;
- unset MARKED_ESTIMATE thresholds must not block OBSERVED absolute settlement;
- absent stock WARM owner makes only that event family NOT_APPLICABLE;
- historical PIT limitations must remain explicit.

## 8. Independent Contract Oracle

The oracle must not import a future V4-15 runtime evaluator.

It must independently reconstruct:
- required contract file set;
- field authority set;
- DAG/non-edge set;
- event identities;
- horizon formulas;
- quality-state enumerations;
- machine-vector expected outputs;
- source capability matrix;
- storage identity rules.

Expected results must come from static contracts/master authority, not from the implementation under test.

## 9. Mandatory Cross-Family Tests

At minimum prove:

```text
Radar event -> cohort enrollment identity stable
persistent event -> no duplicate enrollment
same-day revision -> same logical event / append observation
invalidated event -> still future-settled
Focus excluded -> still enrolled/settled
display excluded -> still enrolled/settled
source correction -> first-observed preserved
outcome correction -> T0 unchanged
market benchmark missing -> absolute settlement survives
sector benchmark unavailable -> only sector-relative degrades
Control A unavailable -> B/C remain valid
marked-estimate gates unset -> no invented threshold
FEP cannot become upstream dependency
```

## 10. Stage Entry Gate

Create a formal V4-15 stage-entry gate that says exactly:

```text
V4_15_CONTRACT_COMPLETENESS = PASS_READY_FOR_EXTERNAL_AUDIT
V4_15_RUNTIME = NOT_IMPLEMENTED
V4_15_ACCEPTED_HEAD = NOT_CREATED
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_14_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

Do not change Stage Head accepted range in R19D.

## 11. Clean Detached Regression

Include:
- V4-14 promotion gate;
- all retained V4-14 replay/rollback tests;
- R19B contract tests;
- R19C contract tests;
- R19D integration/oracle tests;
- relevant accepted upstream owner tests.

No broad deselection.

## 12. Forbidden

Entire task:
- V4-15 runtime;
- Radar publication generation;
- real Cohort enrollment;
- real Settlement execution;
- V4-15 Accepted Head;
- Stage Head advance beyond V4-14;
- Data Head advance;
- production/shadow/focus;
- formal DB migration apply;
- FEP implementation;
- V4-16 entry.

## 13. Completion

Required:

```text
R19D_V4_15_CONTRACT_INTEGRATION = PASS_LOCAL
V4_15_CONTRACT_COMPLETENESS = PASS_READY_FOR_EXTERNAL_AUDIT
V4_15_RUNTIME = NOT_IMPLEMENTED
V4_15_ACCEPTED_HEAD = NOT_CREATED
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_14_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30

NEXT = STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```
