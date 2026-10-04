# V4 R30R1｜V4-21 Native Session Status + Owner Binding Repair Independent External Audit R1｜2026-10-04

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`  
Execution baseline: `3f0663804bf104dd3e61e65d9927cb7f2081fa3b`  
Audited remote HEAD: `791543c3bdbd4b80b2679b447d257cc27dd504ad`  
Exact tested source: `0d85127a838a00d42652981d2935b18f21b62e68`  
Immutable tested tag: `refs/tags/codex/r30r1-native-session-repair-tested-source-20261004`

## 1. Unique External Decision

```text
R30R1_EXTERNAL_AUDIT =
PASS_FINAL_NATIVE_SESSION_STATUS_AND_OWNER_BINDING_REPAIR

R30_NATIVE_SESSION_STATUS_BINDING = CLOSED_EXTERNALLY_ACCEPTED
R30_SHADOW_SESSION_OWNER_BINDING = CLOSED_EXTERNALLY_ACCEPTED
R30_PRODUCTION_SESSION_AUTHORITY_FORMALIZATION = CLOSED_FOR_CONTRACT_DESIGN

V4_21_CONTRACT_DESIGN =
EXTERNALLY_ACCEPTED_SCOPED

V4_21_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_REAL_OBSERVATION

REAL_CONTINUED_FORWARD_OBSERVATION =
NOT_STARTED

V4_21_ACCEPTED_HEAD =
NOT_CREATED

R30R1_P2_LEDGER_REFERENTIAL_INTEGRITY_VECTOR =
OPEN_NONBLOCKING_CARRY_TO_V4_22
```

R30R1 closes the P0 interface defect identified in R30.

---

## 2. Exact V4-16 Observation Slot Binding｜PASS

The V4-21 contract now binds:

```text
contract_id = V4_16_OBSERVATION_SLOT_CONTRACT_V2
path = config/v4_16_observation_slot_contract_v2.json
sha256 = exact accepted bytes
```

The allowed Shadow native states are no longer duplicated manually.

They are exactly:

```text
ACCEPTED_ON_TIME
MISSED_OBSERVATION_SLOT
```

and tests load the accepted owner contract independently to verify exact equality.

Generic aliases are rejected.

---

## 3. Native Status vs Projection Evaluability｜PASS

The session contract now separates:

```text
native_session_authority_id
native_session_authority_sha256
native_session_status
projection_evaluable
projection_evaluable_reason
```

This correctly distinguishes:

### Accepted + evaluable
```text
ACCEPTED_ON_TIME
projection_evaluable = true
```

### Accepted but not evaluable
```text
ACCEPTED_ON_TIME
projection_evaluable = false
projection_evaluable_reason = ...
```

### Missed observation slot
```text
MISSED_OBSERVATION_SLOT
projection_evaluable = false
```

`NON_EVALUABLE` is no longer permitted as a native slot-status alias.

---

## 4. Shadow Real Session Count Rule｜PASS

A Shadow session is countable only if all of the following hold:

```text
evidence_lane = SHADOW_REAL
evidence_origin = PIT_OBSERVED
accepted_real_publication = true
execution_mode = SHADOW
native_session_authority = exact V4_16 slot contract
native_session_status = ACCEPTED_ON_TIME
projection_evaluable = true
```

This fixes the R30 bug where the design oracle expected the invented status:

```text
ACCEPTED
```

instead of the accepted V4-16 native status.

---

## 5. Missed / Non-Evaluable Streak Semantics｜PASS

### Missed slot
```text
native_session_status = MISSED_OBSERVATION_SLOT
```

Result:

```text
retained in session denominator
real accepted count = 0
consecutive accepted streak = 0
```

### Accepted but projection non-evaluable
```text
native_session_status = ACCEPTED_ON_TIME
projection_evaluable = false
```

Result:

```text
retained in denominator
real accepted count = 0
consecutive accepted streak = 0
not relabeled as missed
```

The reasons remain machine-distinguishable.

---

## 6. Observation Receipt Status｜PASS

The observation receipt now carries the exact native authority/status plus projection evaluability.

For Shadow:

```text
accepted_session_status =
exact native V4-16 slot status
```

while also preserving:

```text
native_session_authority_id
native_session_authority_sha256
native_session_status
projection_evaluable
projection_evaluable_reason
```

Therefore:

```text
ACCEPTED_ON_TIME + evaluable=false
```

cannot be confused with:

```text
MISSED_OBSERVATION_SLOT
```

---

## 7. Production Real Authority｜PASS_FOR_DESIGN

Current accepted production-session authority does not exist.

The V4-21 contract now explicitly freezes:

```text
production_native_session_authority =
FUTURE_ACCEPTED_BINDING_REQUIRED

production_accepted_binding =
null

production_current_real_gate_count =
NOT_COUNTABLE_FOR_REAL_GATE
```

The design fixture may model a future production authority only when:

```text
kind = CONTRACT_DESIGN_SIMULATION
authority_id starts with SIM_
status = CONTRACT_DESIGN_SIMULATION
```

Changing the same fixture to:

```text
REAL_OBSERVATION
```

without an accepted production authority fails:

```text
PRODUCTION_SESSION_AUTHORITY_REQUIRED_NOT_COUNTABLE
```

This is true fail-closed behavior, not merely prose.

---

## 8. Native Status Negative Matrix｜PASS

S21-01 through S21-08 all fail closed:

```text
S21-01 generic ACCEPTED rejected
S21-02 generic MISSED rejected
S21-03 NON_EVALUABLE as native status rejected
S21-04 unknown native status rejected
S21-05 wrong V4-16 authority digest rejected
S21-06 Production real without accepted authority rejected
S21-07 accepted-but-non-evaluable falsely claimed count rejected
S21-08 missed slot marked evaluable rejected
```

No real rows are written and no production grant is issued.

---

## 9. F21 Regression｜PASS

The repaired F21 vectors now use native V4-16 semantics.

Key cases:

```text
F21-01
ACCEPTED_ON_TIME + evaluable=true
→ count 1

F21-05
MISSED_OBSERVATION_SLOT
→ denominator retained
→ count 0
→ streak reset

F21-06
ACCEPTED_ON_TIME + evaluable=false
→ denominator retained
→ count 0
→ streak reset
→ not missed
```

The remaining R30 Forward-observation design semantics remain unchanged.

---

## 10. PASS_KEEP Sections｜PASS

The repair preserves byte-equivalent semantics for:

```text
continuity
current_state
daily_operation
due_outcome_ledger
event_cohort_ledger
evidence_lanes
gate_readback
implementation_entry
right_censor
stratification
recovery
prohibited rules
```

No settlement owner changed.

No real observation writer was introduced.

---

## 11. Regression｜PASS_SCOPED

Clean tested source:

```text
346 tests
343 passed
3 inherited failures
0 errors
0 skipped
0 deselected
```

The same historical R26-A01 failures remain:

```text
test_v3_is_the_single_unified_workbench_entry
test_hot_rank_route_skips_request_scope
test_send_marks_disconnected_client_closed
```

No new R30R1 regression exists.

---

## 12. Tested Source Governance｜PASS

Annotated tag:

`codex/r30r1-native-session-repair-tested-source-20261004`

resolves exactly to:

`0d85127a838a00d42652981d2935b18f21b62e68`

Final remote HEAD is one evidence-only commit ahead.

No implementation drift exists after the tested source.

---

## 13. Protected State｜PASS

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

production_permission[*] = false
Focus source cutover = false
DEFAULT_UI_CUTOVER = false
```

---

## 14. P2 Carry｜Ledger Referential Integrity Vector

The design readback assumes a real event/outcome partition already has a corresponding session group.

The contract’s daily operation orders:

```text
accepted session
→ events/cohort
→ due/outcome
```

but the design-vector suite does not yet explicitly prove:

```text
orphan real event without session -> fail closed
orphan real outcome without session -> fail closed
```

Current synthetic readback would rely on the existing group assumption rather than a dedicated referential-integrity error.

Classification:

```text
R30R1_P2_LEDGER_REFERENTIAL_INTEGRITY_VECTOR =
OPEN_NONBLOCKING_CARRY_TO_V4_22
```

This does not reopen the native-session P0 repair.

V4-22 Independent Audit must require explicit disposition before final project acceptance.

---

## 15. Final

```text
R30R1_EXTERNAL_AUDIT =
PASS_FINAL_NATIVE_SESSION_STATUS_AND_OWNER_BINDING_REPAIR

V4_21_CONTRACT_DESIGN =
EXTERNALLY_ACCEPTED_SCOPED

V4_21_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_REAL_OBSERVATION

NEXT =
V4_22_INDEPENDENT_AUDIT_CONTRACT_DESIGN
```
