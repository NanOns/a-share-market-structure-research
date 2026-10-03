# R20E｜V4-15 Full Persisted E2E / Independent Oracle / Clean Seal｜2026-10-03

## 0. Entry Gates
Execute only after all are PASS_LOCAL:

```text
R20A_CURRENT_STAGE_AUTHORITY
R20B_BYTE_IDENTITY_PORTABILITY
R20C_V4_15_RADAR_COHORT_RUNTIME
R20D_V4_15_SETTLEMENT_RUNTIME
```

## 1. Goal
Prove one complete persisted engineering path:

```text
Current V4-14 Accepted Authority
→ accepted V4-14 publication
→ Radar projection
→ daily ledger
→ logical event / observation
→ enrollment
→ benchmark / controls frozen at T0
→ due planner
→ future accepted-source readback
→ settlement / competing outcomes
→ outcome revision
→ readback
```

Then run an independent oracle and clean detached regression.

No V4-15 promotion in this round.

## 2. Current Authority
The E2E must use R20A current-stage authority.

Required:
```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_14_ACCEPTED
V4_14_ACCEPTED_HEAD = current authority
V4_DATA_ACCEPTED_HEAD = 2026-09-30
```

Reject any V4-13-as-current fallback.

## 3. Persisted Process Boundary
Use persisted artifacts rather than an in-memory-only chain.

At minimum:
```text
producer process:
V4-14 accepted publication -> Radar/Cohort persisted artifacts

exit / exact readback

settlement process:
read enrollment + frozen T0 authorities
-> due planner
-> accepted future source
-> persisted outcome revision
```

Record:
- process IDs;
- start/end;
- exact input/output refs;
- source digests;
- calendar;
- current authority;
- evidence class.

## 4. T0 Freeze Proof
Before any future session is read, freeze:
- logical event;
- enrollment;
- T0;
- benchmark constituents/weights;
- control assignments;
- comparison reference;
- calendar identity;
- adjustment identity;
- contract/parameter/source digests.

Independent oracle must prove these artifacts predate future-source settlement reads in the E2E evidence order.

## 5. Required E2E Trajectories
At minimum include:
1. FIRST_PREWATCH -> pending -> observed horizon settlement;
2. PREWATCH -> CONFIRMED while settlement continues;
3. PREWATCH -> INVALIDATED while settlement continues;
4. same-day r1/r2 correction with one logical event and stable T0;
5. source correction producing corrected observation but preserving first-observed enrollment;
6. one market-relative unavailable case while absolute settlement survives;
7. one sector-relative unavailable case while absolute survives;
8. Control A unavailable while B/C remain independent;
9. one later control crossing signal without redrawing ITT assignment;
10. one real accepted-source capability-scoped trajectory.

## 6. Revision / Append-only
Prove:
```text
same source rerun -> no new evaluation revision
corrected source -> append new revision
first observed -> immutable
T0 -> immutable
control assignment -> immutable
benchmark T0 identity -> immutable
```

Changed-byte overwrite of an existing publication or revision must fail closed.

## 7. No Feedback
Prove from actual runtime traces that these never become upstream inputs:

```text
Focus
UI Top-K
Forward outcome
Corrected outcome
FEP prediction
future price
```

to:
```text
T0 eligibility
owner state
Radar qualification
enrollment decision
```

## 8. Portability Integration
Use R20B representation-aware exact reader where current accepted artifacts require it.

Every non-literal representation acceptance must emit an explicit portability receipt.

No hidden normalization.

## 9. Independent E2E Oracle
The oracle must not import:
- Radar runtime evaluator;
- Cohort runtime evaluator;
- Settlement runtime evaluator;
- portability resolver implementation

to derive expected results.

It independently reconstructs:
- current Stage/V4-14 authority;
- event/enrollment identities;
- expected T0 freeze;
- due sessions;
- price formulas;
- control/benchmark identity;
- append-only revision semantics;
- capability degradation;
- portability admission.

## 10. Mandatory Adversarial Tests
At minimum:
```text
stage_pointer_reverted_to_v4_13
stale_v4_14_entry
v4_14_head_digest_mutated
future_source_before_T0_freeze
Focus_filters_enrollment
UI_filters_enrollment
same_day_revision_new_logical_event
source_correction_resets_T0
source_correction_redraws_controls
benchmark_reweights_missing_member
marked_threshold_invented
control_future_refill
control_assignment_changed_after_crossing
same_source_creates_duplicate_revision
corrected_source_overwrites_first_observed
mixed_adjustment_basis
unregistered_CRLF_normalization
binary_normalization
changed_byte_overwrite
FEP_feedback
raw_provider_fallback
```

All must fail.

## 11. Capability-scoped Real Evidence
Real accepted-source E2E may prove engineering readback only.

Preserve:
```text
REAL_ACCEPTED_SOURCE_V4_15 = PASS_CAPABILITY_SCOPED
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED
Production = false
Shadow = false
Focus = false
```

Do not convert historical reconstructed evidence into real performance claims.

## 12. Clean Detached Regression
Run:
- accepted upstream owner regressions;
- R17/R18 replay/rollback historical regressions in historical context;
- R20A current-stage authority tests in current context;
- R20B portability tests;
- R20C Radar/Cohort tests;
- R20D Settlement tests;
- R20E E2E/oracle tests.

No broad deselection.

## 13. Tested Source Governance
The exact clean-tested implementation source for R20 must be reachable through a remote-addressable immutable Git ref or branch ancestry.

Do not repeat the R19 bundle-only tested-source pattern.

The final seal commit may add evidence only relative to that reachable tested source.

## 14. Protected State
Must remain:
```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_14_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_14_ACCEPTED_HEAD = KEEP
V4_15_ACCEPTED_HEAD = NOT_CREATED
```

No Production/Shadow/Focus/V4-16 permission.

## 15. Final Candidate Seal
Create one candidate seal binding:
- current-stage authority gate;
- portability gate;
- Radar/Cohort runtime gate;
- Settlement runtime gate;
- persisted E2E;
- independent oracle;
- real capability-scoped evidence;
- clean regression;
- protected heads;
- exact reachable tested-source Git identity.

## 16. Allowed Final State
```text
R20E_V4_15_FULL_PERSISTED_E2E = PASS_LOCAL
R20E_INDEPENDENT_ORACLE = PASS_LOCAL

R19_AUDIT_01 = CLOSED_LOCAL
R19_AUDIT_02 = CLOSED_LOCAL

V4_15_RUNTIME_CANDIDATE =
READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

REAL_ACCEPTED_SOURCE_V4_15 =
PASS_CAPABILITY_SCOPED

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED

V4_15_ACCEPTED_HEAD = NOT_CREATED
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_14_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30

Production = false
Shadow = false
Focus = false
V4_16 = false

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

Unified commit + push, then STOP.
