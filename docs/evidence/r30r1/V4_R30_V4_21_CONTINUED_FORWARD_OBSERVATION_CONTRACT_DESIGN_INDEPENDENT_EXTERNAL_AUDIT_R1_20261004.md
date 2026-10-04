# V4 R30｜V4-21 Continued Forward Observation Contract Design Independent External Audit R1｜2026-10-04

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`  
Execution baseline: `c38c25dd189b3996f53e85dc64bbc142db1c188e`  
Audited remote HEAD: `3f0663804bf104dd3e61e65d9927cb7f2081fa3b`  
Exact tested source: `9c6f582334fc0f27cf941bbf6d1515610bb52b15`  
Immutable tested tag: `refs/tags/codex/r30-forward-observation-contract-tested-source-20261004`

## 1. Unique External Decision

```text
R30_EXTERNAL_AUDIT =
PARTIAL_PASS_NATIVE_SESSION_STATUS_BINDING_REPAIR_REQUIRED

R30_EVIDENCE_LANE_REGISTRY = PASS_KEEP
R30_EVENT_COHORT_LEDGER = PASS_KEEP
R30_DUE_OUTCOME_LEDGER = PASS_KEEP
R30_RIGHT_CENSOR_POLICY = PASS_KEEP
R30_STRATIFICATION_POLICY = PASS_KEEP
R30_SHADOW_PRODUCTION_CONTINUITY = PASS_KEEP
R30_GATE_READBACK_POLICY = PASS_KEEP
R30_OBSERVATION_RECEIPT_SCHEMA = PASS_KEEP
R30_VECTOR_SCOPE = PASS_KEEP_DESIGN_ONLY
R30_TESTED_SOURCE_GOVERNANCE = PASS_KEEP

R30_NATIVE_SESSION_STATUS_BINDING =
FAIL_P0

R30_SHADOW_SESSION_OWNER_BINDING =
FAIL_P0

R30_PRODUCTION_SESSION_AUTHORITY =
P1_FORMALIZATION_REQUIRED

V4_21_CONTRACT_DESIGN =
BLOCKED_PENDING_R30R1

V4_21_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_REAL_OBSERVATION

REAL_CONTINUED_FORWARD_OBSERVATION =
NOT_STARTED

V4_21_ACCEPTED_HEAD =
NOT_CREATED
```

R30 is not rejected as an architecture. The defect is narrowly limited to the canonical accepted-session interface that feeds real-session counts and consecutive-session gates.

---

## 2. Change Scope｜PASS_KEEP

R30 changed only:

```text
config/v4_21_continued_forward_observation_contract_v1.json
tests/test_v4_21_forward_observation_contract.py
reports/r30/*
docs/evidence/r30/*
```

No settlement owner, real observation writer, Focus route, default UI route or accepted business runtime was modified.

Protected evidence confirms:

```text
actual_real_observations_written = 0
actual_ui_focus_route_changed = false
production_databases_opened = false
settlement_owner_changed = false
tdx_writes = false
```

---

## 3. Evidence Lanes｜PASS_KEEP

The machine contract correctly separates:

```text
SHADOW_REAL
PRODUCTION_REAL
HISTORICAL_REPLAY
RECONSTRUCTED_ASOF
ACTIVATION_SIMULATION
```

Only:

```text
PIT_OBSERVED
+
accepted real publication
+
matching execution mode
```

may count as real evidence.

Replay/reconstructed/simulation lanes are diagnostic only.

This is correct.

---

## 4. Model / Parameter / Lineage Partitions｜PASS_KEEP

Evidence partition key:

```text
capability
evidence_lane
model_contract_id
parameter_digest
state_lineage_id
```

is correct.

Model/parameter changes:

```text
do not rewrite old evidence
create a new observation partition
reset only affected consecutive windows
preserve prior partitions
```

This matches the project’s capability-scoped validation discipline.

---

## 5. Event / Cohort Ledger｜PASS_KEEP

The event ledger preserves:

```text
logical_event_id
enrollment_id
event_type
entity_id
T0
cohort_namespace
original_revision
eligible
displayed
control_assignment_ids
benchmark_ids
```

Rules correctly enforce:

```text
no second original
hidden/undisplayed eligible event remains in cohort
same-day outcome feedback forbidden
T0 controls/benchmark frozen
```

No display selection is allowed to rewrite Validation Cohort evidence.

---

## 6. Due / Outcome Ledger｜PASS_KEEP

The R30 due/outcome design correctly reuses accepted V4-15 ownership:

```text
DUE_PLANNER_V1
OUTCOME_STATUS_V1
OUTCOME_REVISION_V1
V4_16_SETTLEMENT_WORKER_CONTRACT_V1
```

No new settlement engine is introduced.

Important identity audit:

R30 uses the accepted V4-15 outcome revision key:

```text
enrollment_id
horizon
outcome_contract_id
evaluation_source_digest
```

while also preserving the native `due_id`.

This is valid because:

```text
evaluation_source_digest
```

identifies an append-only outcome evaluation revision, while aggregation deduplicates the due denominator by native `due_id`.

Therefore corrected source revisions do not create a second due denominator.

---

## 7. Right-Censor / Pending Policy｜PASS_KEEP

The contract preserves native V4-15 states:

```text
PENDING
RIGHT_CENSORED
OBSERVED
SUSPENDED_AT_HORIZON
MATURED_DATA_MISSING
DELISTED_BEFORE_HORIZON
IDENTITY_UNKNOWN
ADJUSTMENT_UNKNOWN
```

Projection states distinguish:

```text
PENDING_NOT_DUE
PENDING_SOURCE_UNAVAILABLE
RIGHT_CENSORED
OBSERVED
INVALIDATED_BY_CONTRACT
```

Correct prohibitions are frozen:

```text
pending != success/failure
censor != failure
MATURED_DATA_MISSING != censor
delisting return != synthetic 0 / -100%
missing metric != zero
```

This is correct.

---

## 8. Shadow / Production Continuity｜PASS_KEEP

The contract correctly preserves distinct lanes:

```text
SHADOW_REAL
PRODUCTION_REAL
```

Historical Shadow rows are never relabeled as Production.

Compatible reporting may combine:

```text
capability
model_contract_id
parameter_digest
state_lineage_id
```

only with explicit per-lane denominators.

Production cutover does not rewrite the original event/enrollment lane.

---

# 9. P0 Finding｜Native Session Status Mismatch

## 9.1 R30 Design Oracle Actual

`reports/r30/design_ledger.py` defines the real accepted-session condition as:

```text
real(session)
AND slot_status == "ACCEPTED"
AND evaluable == true
```

The positive fixture also uses:

```text
slot_status = "ACCEPTED"
```

Missed/non-evaluable fixtures use:

```text
"MISSED"
"NON_EVALUABLE"
```

## 9.2 Accepted V4-16 Native Contract

The externally accepted:

`config/v4_16_observation_slot_contract_v2.json`

defines native slot states as:

```text
ACCEPTED_ON_TIME
MISSED_OBSERVATION_SLOT
```

There is no native V4-16 Shadow slot state:

```text
ACCEPTED
MISSED
NON_EVALUABLE
```

`evaluable` may be a V4-21 projection/quality field, but it must not replace or rename the accepted native slot status.

## 9.3 Consequence

Under the current R30 design oracle, a future valid real Shadow row:

```text
slot_status = ACCEPTED_ON_TIME
```

would evaluate:

```text
real_accepted_sessions = 0
```

because the oracle requires:

```text
slot_status == ACCEPTED
```

This directly affects:

```text
20 consecutive accepted market sessions
SHADOW_STABLE_PASS readback
Forward session denominators
production permission prerequisites
```

Therefore this is P0.

---

# 10. P0 Root Cause｜Missing Shadow Slot Owner Binding

R30’s session ledger declares:

```text
owner =
V4_16_ACCEPTED_SLOT_AND_PUBLICATION_OWNER
```

but `owner_bindings[]` does not bind:

```text
V4_16_OBSERVATION_SLOT_CONTRACT_V2
```

This missing exact owner contract allowed the design oracle to invent generic slot status strings.

R30R1 must add exact path/digest binding to the accepted V4-16 slot contract.

---

# 11. Required Shadow Session Mapping

For `SHADOW_REAL`, freeze:

```text
native_session_authority =
V4_16_OBSERVATION_SLOT_CONTRACT_V2
```

Native mapping:

```text
ACCEPTED_ON_TIME
→ accepted real session candidate

MISSED_OBSERVATION_SLOT
→ denominator row retained
→ accepted count = 0
→ consecutive accepted streak breaks
```

Additional V4-21 quality/evaluability states must be separate fields.

For example:

```text
native_slot_status = ACCEPTED_ON_TIME
evaluable = false
evaluable_reason = ...
```

must remain distinguishable from:

```text
native_slot_status = MISSED_OBSERVATION_SLOT
```

Do not collapse the two concepts.

---

# 12. P1｜Production Session Authority

R30 also models:

```text
PRODUCTION_REAL
```

but no accepted V4 production-session authority exists yet.

Therefore the contract must not invent a generic production slot state.

R30R1 must freeze:

```text
PRODUCTION_REAL native session status =
BIND_FUTURE_ACCEPTED_PRODUCTION_SESSION_AUTHORITY
```

until V4-19/V4-20 production routing and production publication/session authority are externally accepted.

Production real evidence must remain:

```text
NOT_COUNTABLE
```

if that authority binding is absent.

This is a contract formalization issue, not a reason to remove the `PRODUCTION_REAL` lane.

---

# 13. Accepted Session Ledger Repair

The session ledger should explicitly separate:

```text
native_session_authority_id
native_session_status
projection_evaluable
projection_evaluable_reason
```

Recommended identity/read fields:

```text
capability
evidence_lane
model_contract_id
parameter_digest
state_lineage_id
market_session_id

native_session_authority_id
native_session_status
publication_id
publication_revision
projection_evaluable
projection_evaluable_reason
missed_reason
```

The exact field names may differ, but native vs projection state must be machine-distinguishable.

---

# 14. Design Vector Repair

R30R1 must replace invented fixture states with accepted/native semantics.

At minimum:

```text
F21-01:
SHADOW_REAL
slot_status = ACCEPTED_ON_TIME
evaluable = true
→ counts 1 real accepted session

F21-05:
slot_status = MISSED_OBSERVATION_SLOT
→ denominator retained
→ count 0
→ streak break

F21-06:
slot_status = ACCEPTED_ON_TIME
evaluable = false
→ denominator retained
→ count 0
→ streak break
→ distinguish from MISSED_OBSERVATION_SLOT
```

Add explicit negatives:

```text
S21-01 generic "ACCEPTED" rejected for SHADOW_REAL
S21-02 generic "MISSED" rejected
S21-03 "NON_EVALUABLE" used as native slot status rejected
S21-04 unknown native slot state rejected
S21-05 missing V4-16 slot authority digest rejected
S21-06 Production real counts without accepted production session authority rejected
```

---

# 15. PASS_KEEP Areas

Do not reopen:

```text
five evidence lanes
event/cohort ledger
V4-15 due/outcome ownership
right-censor policy
model/parameter partitions
Shadow/Production lane separation
gate readback read-only rule
observation receipt design
same-day feedback prohibition
F21-07 through F21-20 semantics except where session-status fixture needs normalization
```

This is a narrow interface repair.

---

# 16. Tested Source Governance｜PASS_KEEP

Annotated tag:

`codex/r30-forward-observation-contract-tested-source-20261004`

resolves exactly to:

`9c6f582334fc0f27cf941bbf6d1515610bb52b15`

Final remote HEAD is one evidence-only commit ahead.

No implementation drift exists after testing.

---

# 17. Regression｜PASS_KEEP_SCOPED

Clean source:

```text
333 tests
330 passed
3 inherited failures
0 errors
0 skipped
0 deselected
```

The same historical R26-A01 failures remain.

No new R30 general regression exists.

---

# 18. Protected State｜PASS

Still:

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_15_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30

V4_16_ACCEPTED_HEAD = NOT_CREATED
V4_17_ACCEPTED_HEAD = NOT_CREATED
V4_18_ACCEPTED_HEAD = NOT_CREATED
V4_19_ACCEPTED_HEAD = NOT_CREATED
V4_20_ACCEPTED_HEAD = NOT_CREATED
V4_21_ACCEPTED_HEAD = NOT_CREATED

R25 = WAIT_ACCEPTED_DAILY_INPUT
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
REAL_CONTINUED_FORWARD_OBSERVATION = NOT_STARTED
```

---

# 19. Final

```text
R30_EXTERNAL_AUDIT =
PARTIAL_PASS_NATIVE_SESSION_STATUS_BINDING_REPAIR_REQUIRED

NEXT =
R30R1_NATIVE_SESSION_STATUS_AND_OWNER_BINDING_REPAIR
```

Do not proceed to the next stage contract until R30R1 closes this interface.
