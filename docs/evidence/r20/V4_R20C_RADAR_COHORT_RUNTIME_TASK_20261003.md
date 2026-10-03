# R20C｜V4-15 Radar / Cohort Runtime｜2026-10-03

## 0. Entry Gate
Execute only after:

```text
R20A_CURRENT_STAGE_AUTHORITY = PASS_LOCAL
```

R20B may still be running in parallel.

## 1. Authority
Use only the externally accepted V4-15 contract package from R19.

Bind exact:
- current V4-14 Accepted Head;
- R20A Current Stage Authority;
- R19B Radar/Cohort contracts;
- unified V4-15 field registry / DAG / source capability matrix;
- accepted owner publications.

No owner recomputation and no latest scanning.

## 2. Goal
Implement the engineering runtime for:

```text
Accepted V4-14 publication
→ Radar event projection
→ complete daily ledger
→ logical events / observations
→ first ASSERTED enrollment
→ complete Validation Cohort
```

This is runtime engineering only.

Do not create V4-15 Accepted Head.

## 3. Suggested Runtime Modules
Recommended:
```text
src/workbench_analysis/v4_15_radar_runtime.py
src/workbench_analysis/v4_15_cohort_runtime.py
src/workbench_analysis/v4_15_identity.py
src/workbench_analysis/v4_15_persistence.py
src/workbench_analysis/v4_15_readback.py
```

Names may follow repository conventions.

## 4. Radar Read-only Projection
Radar must consume accepted state/event/profile outputs.

It must not:
- recompute PREWATCH;
- recompute confirmation;
- recompute D1 structure;
- recompute D2 state;
- change accepted episode identity;
- read Focus/UI selections;
- read future outcomes/FEP predictions.

Every projected field must carry source authority/provenance.

## 5. Daily Ledger
Implement exact unique identity:

```text
(model_contract_id,
 state_lineage_id,
 publication_id,
 entity_type,
 entity_id,
 signal_type)
```

Persist the complete eligible ledger, independent of display caps.

Persistent eligible states may produce a daily ledger row but must not create duplicate logical events.

## 6. Logical Events
Implement exact key:

```text
(model_contract_id,
 state_lineage_id,
 entity_type,
 entity_id,
 episode_id,
 event_type,
 event_trade_date)
```

Supported event families exactly follow R19 contracts.

No synthetic stock WARM when the accepted owner is absent.

Same-day revision must preserve logical-event identity unless accepted owner semantics define a genuinely new episode.

## 7. Observations
Implement append-only:

```text
(logical_event_id, publication_id)
```

States:
```text
ASSERTED
RETRACTED
CORRECTED
```

A correction:
- appends observation;
- does not erase first observed;
- does not reset T0;
- does not redraw controls;
- does not silently change episode identity.

## 8. Enrollment
On first real-time ASSERTED eligible event, freeze one enrollment.

Enrollment must freeze the full R19 contract identity including:
- T0;
- model/state lineage;
- event / episode;
- source publication;
- contract/parameter/source digests;
- signal/comparison references;
- benchmark/control IDs or pending frozen assignment identities;
- calendar;
- adjustment identity;
- evidence class.

Focus/UI/manual pin/display cap may not alter enrollment eligibility.

## 9. Validation Cohort
Complete cohort must include all accepted eligible STOCK/SECTOR event families subject to owner availability.

Rules:
- invalidated/exited previously enrolled objects remain enrolled for future settlement;
- Near-Miss is not primary eligible cohort;
- SEED is diagnostic only;
- reconstructed/corrected cohort namespaces remain separate;
- no future data is used to decide T0 enrollment.

## 10. Persistence
Use append-only engineering persistence.

Allowed:
- immutable files/artifact store under a dedicated V4-15 runtime namespace;
- disposable DB fixtures for tests.

Forbidden this round:
- production DB migration apply;
- rewriting prior publications;
- deleting corrections/retractions.

Recommended engineering publication namespace:
```text
reports/v4_15_runtime_r20/radar_cohort/
```

## 11. Required E2E Scenarios
At minimum:
```text
FIRST_PREWATCH
PERSISTENT_PREWATCH
REENTRY_PREWATCH
DIRECT_NEW_CONFIRMED
INVALIDATION
same-day r1/r2 revision
RETRACTED observation
CORRECTED observation
source correction
Focus excluded
display excluded
multi-sector context
formal exit -> new episode reentry
UNKNOWN evidence
HYPOTHESIS_SET_INCOMPLETE
risk event after eligibility false
stock WARM owner absent
```

## 12. Identity / Dedup
Prove:
- one persistent episode does not duplicate enrollment;
- same-day correction does not reset T0;
- multi-sector context does not duplicate the stock logical event;
- formal exit followed by true reentry creates a new episode/enrollment only when owner semantics say so;
- revision IDs are not part of logical-event identity.

## 13. Why Now / Conflict / Hypothesis
Implement only the contracted read-only projection.

Every explanation item must bind accepted evidence.

Never allow:
```text
why_now -> eligibility
hypothesis -> eligibility
conflict panel -> owner state mutation
```

No fabricated second hypothesis.

## 14. Determinism
Same exact accepted inputs + same contracts must produce:
- same ledger identity;
- same logical events;
- same enrollments;
- same digests;
- no duplicate side effects.

## 15. Independent Runtime Oracle
Create an independent oracle that:
- derives expected identities from static R19 contracts;
- reads accepted owner inputs independently;
- does not import the runtime evaluator to generate expected outputs;
- verifies no Focus/UI/future dependency.

## 16. Negative Cases
At minimum reject:
- Focus filters cohort;
- UI Top-K filters cohort;
- persistent creates new event;
- same-day revision creates new logical event;
- correction resets T0;
- correction redraws controls;
- stock WARM synthesized;
- future source used at T0;
- FEP prediction used;
- duplicate stock event from multi-sector context;
- changed-byte overwrite of existing publication;
- current authority is V4-13 instead of V4-14.

## 17. Completion
Required:
```text
R20C_V4_15_RADAR_COHORT_RUNTIME = PASS_LOCAL
RADAR_RUNTIME = IMPLEMENTED_ENGINEERING
VALIDATION_COHORT_RUNTIME = IMPLEMENTED_ENGINEERING
RADAR_COHORT_PERSISTED_E2E = PASS_LOCAL

V4_15_ACCEPTED_HEAD = NOT_CREATED
Production = false
Shadow = false
Focus = false

NEXT = R20E_AFTER_R20D_AND_R20B
```
