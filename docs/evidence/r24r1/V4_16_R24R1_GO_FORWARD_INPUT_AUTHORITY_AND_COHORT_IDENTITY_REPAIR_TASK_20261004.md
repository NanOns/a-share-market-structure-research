# V4-16 R24R1｜Go-Forward Input Authority + Cohort Identity Repair Task｜2026-10-04

## 0. Mission

Repair the two P0 blockers found by R24 independent external audit:

```text
R24_FORWARD_DAILY_INPUT_AUTHORITY
R24_COHORT_ENROLLMENT_IDENTITY
```

and formalize the V4-16 realtime admission layer.

Do not redesign the R24 activation/storage/source-readiness architecture.

Execution baseline:

`0c9f59fbe723fe0fb0e9d1a6750c339894bc7a5b`

External audit authority:

`V4_R24_REAL_SHADOW_ACTIVATION_READINESS_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md`

---

# 1. PASS_KEEP

Keep unchanged unless exact binding/version succession requires otherwise:

```text
V4_16_RUNTIME_ENGINEERING_ACCEPTED_HEAD_R1
V4_16_CLOCK_CONTRACT_V1
V4_16_OBSERVATION_SLOT_CONTRACT_V2
V4_16_R23R1_SLOT_RUNTIME_POLICY_V1

real storage isolation
R24 real migration
activation authority structure
source readiness internal timestamp policy
real initialization boundary concept
owner projection business semantics
transaction atomicity
rollback
Legacy isolation
A01–A20
```

Do not modify V4-10～V4-15 accepted business heads.

---

# 2. P0-A｜Create Go-Forward Daily Input Authority

The real V4-16 runtime must stop using frozen `CurrentStageAuthority` as the target-date input authority.

Create a V4-16-specific authority successor.

Recommended:

```text
config/v4_16_go_forward_input_authority_v1.json
```

plus a machine-readable per-session head/fixture contract.

The authority has two layers:

```text
A. immutable algorithm/stage authority
B. advancing accepted daily input authority
```

---

# 3. Immutable Algorithm Layer

Bind exact immutable accepted owners/contracts:

```text
V4-10
V4-11
V4-12
V4-13
V4-14
V4-15

model contract
parameter set
clock contract
slot contract
cohort contract
settlement contract
```

This layer must not advance daily.

Historical Stage Head remains:

```text
V4_00_TO_V4_15_ACCEPTED
```

---

# 4. Daily Input Layer

For every target market date, require an exact accepted daily-input object containing at least:

```text
daily_input_id
revision
target_trade_date
accepted_at

calendar binding
previous_market_session
target_market_session confirmation

identity/universe binding
membership binding or explicit NOT_REQUIRED_FOR_SCOPE
mandatory TDX/current source binding
adjusted/raw daily binding as required
source package/snapshot identity
source observed/system available timestamps

data quality/capability matrix
source manifest digest
```

The authority must prove:

```text
target_trade_date is an accepted market session
previous_market_session is exact
all mandatory Pure-Core source facts are target-date valid
max_source_trade_date <= target_trade_date
```

---

# 5. Daily Data Must Advance Without Reopening Stage

A future daily input authority may advance:

```text
target_trade_date
calendar/source snapshots
daily facts
```

without changing:

```text
V4_STAGE_ACCEPTED_HEAD
V4_15_ACCEPTED_HEAD
algorithm owners
model/parameter identity
```

Do not edit historical `CurrentStageAuthority` V2 to pretend its 2026-09-30 freeze is rolling.

---

# 6. Runtime Dependencies V3

Create a successor dependency manifest, recommended:

```text
config/v4_16_runtime_dependencies_v3.json
```

It must bind the go-forward input authority contract and all accepted immutable runtime dependencies.

The per-session activation grant must additionally bind:

```text
daily_input_authority
daily_input_digest
target_trade_date
```

No implicit latest discovery.

---

# 7. Runtime Authority Successor

Create a V4-16 runtime input-authority class that exposes the interfaces required by:

```text
clock
owner projection
settlement
calendar/prior-session logic
```

while reading target-date source identities from the exact daily input authority.

Do not silently instantiate old `CurrentStageAuthority` for future target-date acceptance.

It may reuse immutable methods/contracts but must not inherit the hard:

```text
accepted_trade_date == 2026-09-30
```

gate for live target-date validation.

---

# 8. Future-Date Reachability Fixture

Mandatory positive engineering fixture:

```text
target_trade_date > 2026-09-30
```

Do not use 2026-09-28/29/30 as the sole positive reachability proof.

The fixture must include an explicit accepted-like calendar containing:

```text
previous_market_session
target_trade_date
```

and exact target-date source facts.

Expected:

```text
OLD_CURRENT_STAGE_AUTHORITY = rejects future target
NEW_GO_FORWARD_AUTHORITY = accepts isolated future fixture

ACTIVATION_SIMULATION only
NOT_REAL_EVIDENCE
REAL_SHADOW_OBSERVATIONS = 0
```

No current live source may be consumed.

---

# 9. Negative Daily-Authority Matrix

Add at minimum:

```text
F01 target date not in bound calendar
F02 previous session mismatch
F03 daily-input digest mismatch
F04 source target date mismatch
F05 max_source_trade_date > target
F06 source accepted_at after allowed evidence boundary
F07 missing mandatory Pure-Core source
F08 stale previous-day package used for target day
F09 unaccepted identity/universe
F10 membership required by capability but missing
F11 membership missing for Pure-Core only -> Pure-Core continues
F12 attempt implicit latest daily-input discovery
F13 daily-input revision rollback
F14 daily-input authority model/parameter mismatch
```

---

# 10. P0-B｜Repair COHORT_V1 Enrollment Identity

Load exact:

`config/v4_15_cohort_contract_v1.json`

Require:

```text
enrollment_key =
[
  logical_event_id,
  cohort_namespace
]

primary_namespace =
FIRST_OBSERVED
```

For a first real Shadow enrollment:

```text
cohort_namespace =
FIRST_OBSERVED

enrollment_id =
digest([
  logical_event_id,
  cohort_namespace
])
```

Do not use:

```text
SHADOW_V4_FIRST_OBSERVED
```

inside the COHORT_V1 identity.

`SHADOW_V4` remains storage/runtime namespace only.

---

# 11. Independent Enrollment Identity Oracle

For every simulated admitted enrollment:

1. load accepted COHORT_V1 contract;
2. read `enrollment_key`;
3. read actual persisted key field values;
4. independently compute the expected enrollment ID;
5. require exact equality.

Add negative cases:

```text
C01 Shadow-specific literal used in cohort identity
C02 cohort_namespace mutated after ID creation
C03 logical_event_id mutated
C04 duplicate logical event with alternate enrollment ID
```

---

# 12. P1｜Formalize Realtime Admission Layer

Freeze this boundary:

```text
OWNER PROJECTION
→ produces accepted logical-event / eligibility candidate facts

V4-16 REALTIME ADMISSION
→ independently requires:
   accepted on-time V4-16 slot
   accepted mandatory-source receipts
   exact owner logical event
   COHORT_V1 key
→ creates FIRST_OBSERVED enrollment
```

Projected enrollment may be used only as a candidate/template, not cohort acceptance.

Label this explicitly as:

```text
CANDIDATE_ENROLLMENT_TEMPLATE
NOT_COHORT_ACCEPTANCE
```

or equivalent.

---

# 13. Admission Must Not Upgrade Reconstructed Evidence by Annotation

Independent oracle must prove the final admitted enrollment is supported by persisted V4-16 runtime facts:

```text
slot_status = ACCEPTED_ON_TIME
PIT source receipts complete
slot visibility valid
publication before deadline
owner logical event exists
COHORT_V1 identity valid
```

Only then may real mode classify final persisted V4-16 enrollment as PIT-observed real evidence.

Simulation remains NOT_REAL_EVIDENCE.

---

# 14. Activation Authority Remains Disabled

Committed authority remains:

```text
runtime_authorized = false
real_shadow_authorized = false
grant = null
external_acceptance = null
```

Positive future fixture uses isolated simulation authority only.

---

# 15. Protected State

Keep exact:

```text
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_10～V4_15 Accepted Heads
V4_16_RUNTIME_ENGINEERING_ACCEPTED_HEAD_R1
R22/R22R1/R23/R23R1 accepted contracts/evidence
R24 historical candidate evidence
```

Do not create:

```text
V4_16_ACCEPTED_HEAD
```

Do not alter formal real counters.

---

# 16. Existing R24 Negative Matrix

A01–A20 must remain passing.

Add F01–F14 and C01–C04.

---

# 17. Independent Oracle

The R24R1 independent oracle must not import the real runtime writer, go-forward writer, or owner projection writer.

It must independently inspect:

```text
daily input authority
calendar range / prior session
source target dates
max_source_trade_date
slot
manifest
owner logical event
enrollment key
publication
source receipts
authority binding
storage identity
```

---

# 18. Full Regression

Run all prior PRE16/R21/R22/R22R1/R23/R23R1/R24 suites plus R24R1 in clean detached checkout.

No broad deselection.

---

# 19. Required Evidence

Recommended:

```text
reports/r24r1/
  FORWARD_INPUT_AUTHORITY_GATE.json
  FUTURE_SESSION_REACHABILITY_GATE.json
  DAILY_INPUT_NEGATIVE_MATRIX.json
  COHORT_IDENTITY_GATE.json
  REALTIME_ADMISSION_GATE.json
  INDEPENDENT_R24R1_ORACLE.json
  A01_A20_REGRESSION.json
  PROTECTED_BYTES.json
  LOCAL_TEST_SUMMARY.json
  CLEAN_REGRESSION.json
  R24R1_CANDIDATE_SEAL.json
```

---

# 20. Required Exit

```text
R24R1_FORWARD_DAILY_INPUT_AUTHORITY =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

R24R1_COHORT_IDENTITY =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

R24R1_REALTIME_ADMISSION =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

REAL_SHADOW_RUNTIME =
FUTURE_SESSION_ACTIVATION_CAPABLE_DISABLED_CANDIDATE

runtime_authorized = false
real_shadow_authorized = false

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

V4_16_ACCEPTED_HEAD = NOT_CREATED

Production = false
Shadow = false
Focus = false
V4_16 = false

NEXT =
STOP_WAIT_R24R1_INDEPENDENT_EXTERNAL_AUDIT
```

Do not launch a real market-session Shadow run in R24R1.
