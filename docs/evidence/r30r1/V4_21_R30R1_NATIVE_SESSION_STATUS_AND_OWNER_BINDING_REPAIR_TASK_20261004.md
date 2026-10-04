# V4-21 R30R1｜Native Session Status + Owner Binding Repair Task｜2026-10-04

## 0. Mission

Repair the canonical session-status interface in V4-21 Continued Forward Observation contract design.

Execution baseline:

`3f0663804bf104dd3e61e65d9927cb7f2081fa3b`

External audit authority:

`V4_R30_V4_21_CONTINUED_FORWARD_OBSERVATION_CONTRACT_DESIGN_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md`

This is a narrow contract-design repair.

Do not implement real observation writing.

---

## 1. PASS_KEEP

Keep unchanged:

```text
evidence lane registry
event/cohort ledger
V4-15 due/outcome ownership
right-censor policy
stratification
Shadow/Production lane separation
gate readback
observation receipt design
idempotency/CAS
same-day feedback prohibition
```

---

## 2. Bind V4-16 Observation Slot Contract

Add exact owner binding to:

```text
config/v4_16_observation_slot_contract_v2.json
```

Freeze:

```text
contract_id
path
sha256
native slot_states
```

R30/R30R1 must not manually invent Shadow slot-state strings.

---

## 3. Shadow Native Status

For:

```text
evidence_lane = SHADOW_REAL
```

require:

```text
native_session_authority_id =
V4_16_OBSERVATION_SLOT_CONTRACT_V2
```

Allowed native status values must be read/frozen from that accepted contract:

```text
ACCEPTED_ON_TIME
MISSED_OBSERVATION_SLOT
```

Unknown or generic aliases fail closed.

---

## 4. Separate Native Status from Evaluability

Do not use:

```text
NON_EVALUABLE
```

as a native slot status.

Freeze distinct fields:

```text
native_session_status
projection_evaluable
projection_evaluable_reason
```

Equivalent names are allowed.

Examples:

### Accepted and evaluable
```text
native_session_status = ACCEPTED_ON_TIME
projection_evaluable = true
```

### Accepted but not evaluable for a capability/readback
```text
native_session_status = ACCEPTED_ON_TIME
projection_evaluable = false
projection_evaluable_reason = ...
```

### Missed slot
```text
native_session_status = MISSED_OBSERVATION_SLOT
projection_evaluable = false
```

These states must not be conflated.

---

## 5. Count / Streak Rule

For `SHADOW_REAL`:

```text
real_accepted_session =
PIT_OBSERVED
AND accepted real publication
AND execution_mode = SHADOW
AND native_session_status = ACCEPTED_ON_TIME
AND projection_evaluable = true
```

Session denominator:

```text
includes accepted calendar session rows
including missed and non-evaluable rows
```

Consecutive accepted streak:

```text
increments only for real_accepted_session = true
resets to 0 for missed or projection_evaluable=false
```

---

## 6. Production Lane Authority

Do not invent a generic native status for:

```text
PRODUCTION_REAL
```

Freeze:

```text
production_native_session_authority =
FUTURE_ACCEPTED_BINDING_REQUIRED
```

Until an accepted V4 production session/publication authority exists:

```text
PRODUCTION_REAL real_accepted_session_count =
NOT_COUNTABLE_FOR_REAL_GATE
```

Design fixtures may model a future authority only under explicit:

```text
CONTRACT_DESIGN_SIMULATION
```

and must not claim that authority currently exists.

---

## 7. Session Ledger Schema

Update session ledger to carry explicit:

```text
native_session_authority_id
native_session_status
projection_evaluable
projection_evaluable_reason
```

Do not leave a single ambiguous `slot_status` field as the only authority state.

If `slot_status` is retained for compatibility, define it as exact native status and not a projection alias.

---

## 8. Observation Receipt

Freeze how:

```text
accepted_session_status
```

is derived.

For Shadow:

```text
accepted_session_status =
exact native V4-16 slot status
```

or an explicit versioned projection field with separate native status included.

No receipt may collapse:

```text
ACCEPTED_ON_TIME
MISSED_OBSERVATION_SLOT
accepted-but-non-evaluable
```

into one ambiguous enum.

---

## 9. Repair Design Fixtures

Mandatory positive vectors:

```text
F21-01:
ACCEPTED_ON_TIME + evaluable=true
→ real accepted session = 1

F21-05:
MISSED_OBSERVATION_SLOT
→ denominator retained
→ real accepted = 0
→ streak breaks

F21-06:
ACCEPTED_ON_TIME + evaluable=false
→ denominator retained
→ real accepted = 0
→ streak breaks
→ not labeled missed
```

Keep the remaining F21 vector semantics.

---

## 10. Add Native-Status Negative Matrix

At minimum:

```text
S21-01 SHADOW_REAL native status "ACCEPTED" -> reject
S21-02 SHADOW_REAL native status "MISSED" -> reject
S21-03 native status "NON_EVALUABLE" -> reject
S21-04 unknown native slot status -> reject
S21-05 missing/wrong V4-16 slot authority binding -> reject
S21-06 PRODUCTION_REAL counted without accepted production session authority -> reject
S21-07 accepted-but-non-evaluable mistakenly counted -> reject
S21-08 MISSED_OBSERVATION_SLOT mistakenly treated evaluable -> reject
```

---

## 11. Independent Assertions

Tests must load:

```text
config/v4_16_observation_slot_contract_v2.json
```

and assert R30R1 Shadow allowed statuses equal the accepted source contract.

Do not duplicate the allowed status list only inside the design oracle.

---

## 12. Protected State

Keep:

```text
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_16 through V4_21 Accepted Head absence
R25 WAIT state
real Shadow counters = 0
production permission = false
Focus source cutover = false
default UI cutover = false
```

Do not create:

```text
V4_21_ACCEPTED_HEAD
```

---

## 13. Regression

Run:

```text
existing V3/Focus regression scope
V4-17
V4-18 contract
V4-19 contract
V4-20 contract
V4-21 contract
R30R1 repair tests
```

No broad deselection.

Historical R26-A01 debt remains separate.

---

## 14. Required Evidence

Recommended:

```text
reports/r30r1/
  NATIVE_SESSION_OWNER_BINDING.json
  SHADOW_SLOT_STATUS_GATE.json
  SESSION_EVALUABILITY_GATE.json
  PRODUCTION_SESSION_AUTHORITY_GATE.json
  OBSERVATION_RECEIPT_STATUS_GATE.json
  NATIVE_STATUS_NEGATIVE_MATRIX.json
  F21_REGRESSION.json
  PROTECTED_BYTES.json
  LOCAL_TEST_SUMMARY.json
  CLEAN_REGRESSION.json
  R30R1_CANDIDATE_SEAL.json
```

---

## 15. Exit

Required:

```text
R30R1_NATIVE_SESSION_STATUS_BINDING =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

V4_21_CONTRACT_DESIGN =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

V4_21_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_REAL_OBSERVATION

REAL_CONTINUED_FORWARD_OBSERVATION =
NOT_STARTED

V4_21_ACCEPTED_HEAD =
NOT_CREATED

NEXT =
STOP_WAIT_R30R1_INDEPENDENT_EXTERNAL_AUDIT
```
