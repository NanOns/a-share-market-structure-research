# R19B｜V4-15 Radar / Cohort Contract Freeze｜2026-10-03

## 0. Entry Gate

Execute only after:

```text
R19A_V4_14_PROMOTION = PASS_LOCAL
```

V4-15 remains contract-first only.

No runtime implementation, publication, enrollment write or database migration is authorized in this task.

## 1. Goal

Freeze the complete machine-readable contract family for:

- Radar events;
- Why Now;
- Conflict / evidence presentation;
- Hypothesis schema;
- Validation Cohort;
- daily ledger;
- logical event identity;
- observation revision;
- enrollment identity.

The contract must derive from the accepted V4-14 publication/state/event outputs and must not feed back into V4-07..V4-14.

## 2. Master Contract Sections

At minimum read and encode the semantics from:
- main chain / no-feedback architecture;
- Research Projection / Why Now;
- Conflict Panel;
- Hypothesis Contract;
- Focus boundary;
- Validation Cohort;
- §45A daily ledger / logical events / revisions;
- implementation-stage table and Definition of Done.

## 3. Required Contract Artifacts

Recommended minimum set:

```text
config/v4_15_radar_contract_v1.json
config/v4_15_radar_event_registry_v1.json
config/v4_15_why_now_schema_v1.json
config/v4_15_conflict_hypothesis_schema_v1.json
config/v4_15_cohort_contract_v1.json
config/v4_15_cohort_revision_policy_v1.json
config/v4_15_radar_cohort_field_registry_v1.json
config/v4_15_radar_cohort_machine_vectors_v1.json
```

Names may follow repository conventions, but every semantic family must have one explicit authority.

## 4. Radar Input Authority

The Radar contract may consume only accepted V4-14/V4-13 state/event/profile publications and frozen accepted dependencies.

It must not:
- recompute PREWATCH/CONFIRMED/Structure;
- read Focus selection;
- read UI Top-K;
- read future outcomes;
- read FEP predictions;
- change owner algorithms.

Radar is a read-only projection/event layer.

## 5. Daily Ledger Identity

Freeze exact unique identity:

```text
(model_contract_id,
 state_lineage_id,
 publication_id,
 entity_type,
 entity_id,
 signal_type)
```

Daily ledger is not a logical-event count.

It may contain persistent state rows without creating a new logical event.

## 6. Logical Event Identity

Freeze exact logical event key:

```text
(model_contract_id,
 state_lineage_id,
 entity_type,
 entity_id,
 episode_id,
 event_type,
 event_trade_date)
```

At minimum support:

```text
FIRST_PREWATCH
REENTRY_PREWATCH
UPGRADE_TO_WARM
NEW_CONFIRMED
REACCELERATION_EVENT
INVALIDATION
```

Rules:
- PERSISTENT does not create a new logical event;
- a same-day revision must not create a second logical event;
- a revision belongs to the same logical event unless the frozen owner defines a new episode;
- STOCK and SECTOR events remain distinct namespaces.

If stock WARM has no accepted owner detector, it must be `NOT_APPLICABLE`, never synthesized.

## 7. Event Observation / Revision

Freeze observation identity:

```text
(logical_event_id, publication_id)
```

Observation states:

```text
ASSERTED
RETRACTED
CORRECTED
```

Rules:
- append-only;
- source correction does not erase AS_RECORDED observation;
- correction does not redraw controls;
- correction does not reset T0;
- first real-time ASSERTED freezes the enrollment identity;
- reconstructed/corrected cohorts remain separate from first-observed cohorts.

## 8. Enrollment Identity

The first real-time ASSERTED event must freeze:

- enrollment_id;
- T0 market date;
- model/state lineage;
- entity and episode;
- signal/event type;
- source publication;
- source/parameter/contract digests;
- comparison reference;
- benchmark identities;
- control assignment identities;
- market calendar;
- adjustment identity;
- evidence class.

Enrollment must not depend on Focus/UI inclusion.

## 9. Validation Cohort

Freeze `COHORT_V1` semantics:

```text
all final eligible STOCK / SECTOR PREWATCH/WARM/CONFIRMED
```

subject to the accepted owner capabilities.

Rules:
- Focus, manual pin and display cap never limit enrollment;
- SEED is diagnostic only, not a primary validation event;
- Near-Miss is control/diagnostic material, not a primary eligible cohort;
- exited/invalidated events remain enrolled for future settlement;
- later conversion/invalidity does not stop external outcome collection.

## 10. Why Now

Freeze structured fields at minimum:

```text
previous_stage
current_stage
changed_facts[]
changed_domains[]
newly_satisfied_rules[]
new_risk_flags[]
```

`why_now` is derived explanation, not a qualification algorithm.

It must bind each item to exact accepted facts/events.

## 11. Conflict / Hypothesis

Conflict output must contain:

```text
supporting_evidence[]
opposing_evidence[]
unknown_evidence[]
```

Hypothesis object must contain:

```text
hypothesis_id
statement
evidence_for[]
evidence_against[]
next_discriminator[]
expiry_condition[]
quality
```

Hypothesis is not eligibility.

If a second evidence-backed competing explanation is unavailable:

```text
HYPOTHESIS_SET_INCOMPLETE
```

Do not fabricate a second story.

## 12. No Display Bias

The contract may freeze display-ready event priority but must preserve:
- complete eligible ledger;
- complete logical events;
- complete cohort population.

Homepage caps and de-duplication are later UI concerns and may not alter the underlying ledger/cohort.

Risk-change events must remain visible in the event stream even when final eligibility has become false.

## 13. Field Registry

Every output field must declare:

```text
field_id
producer
consumer
type
unit
time_role
source_binding
quality states
UNKNOWN/NOT_APPLICABLE behavior
revision behavior
identity participation
```

No field may have two current authorities.

## 14. Machine Vectors

At minimum include positive/negative vectors for:

- FIRST_PREWATCH;
- persistent PREWATCH;
- REENTRY;
- direct NEW_CONFIRMED;
- invalidation;
- stock WARM not implemented;
- same-day revision;
- retraction/correction;
- source correction preserves first-observed enrollment;
- Focus exclusion still enrolled;
- display exclusion still enrolled;
- persistent row does not create duplicate logical event;
- multi-sector context does not duplicate stock logical event;
- new episode after formal exit;
- UNKNOWN evidence remains UNKNOWN;
- hypothesis incomplete;
- risk event after eligibility false.

Expected outputs must be frozen statically, not generated by the future runtime evaluator.

## 15. Completion

Required:

```text
R19B_V4_15_RADAR_COHORT_CONTRACT_FREEZE = PASS_LOCAL
RADAR_COHORT_CONTRACT_COMPLETENESS = PASS_LOCAL
V4_15_RUNTIME = NOT_IMPLEMENTED
V4_15_ACCEPTED_HEAD = NOT_CREATED

NEXT = R19D_AFTER_R19B_AND_R19C
```
