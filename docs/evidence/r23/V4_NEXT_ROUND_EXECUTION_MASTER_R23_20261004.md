# V4 Next Round Execution Master R23｜2026-10-04

## 0. Baseline

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Execution baseline:

`942997f8a5bce06e34a6e37d013e4d27e7175438`

---

# 1. External Authority

```text
R22R1_EXTERNAL_AUDIT =
PASS_FINAL_CLOCK_AUTHORITY_AND_GOVERNANCE_NORMALIZATION

R22_CLOCK_AUTHORITY_REPAIR_01 =
CLOSED_EXTERNALLY_ACCEPTED

V4_16_RUNTIME_ENGINEERING_ENTRY =
AUTHORIZED
```

---

# 2. Execute One Work Package

Execute:

`V4_16_R23_REALTIME_SHADOW_RUNTIME_ENGINEERING_TASK_20261004.md`

This round implements the disabled V4-16 runtime candidate.

---

# 3. Execution Topology

```text
A. formalize R22R1 external acceptance
        ↓
B. runtime activation authority = FALSE
        ↓
C. implement Shadow storage/migrations
        ↓
D. implement clock + source readiness runtime
        ↓
E. implement observation slot planner
        ↓
F. implement source freeze + SHADOW_V4 prior
        ↓
G. wire accepted business producers
        ↓
H. implement atomic Shadow publication
        ↓
I. implement cohort/membership/due/health writes
        ↓
J. implement settlement orchestration
        ↓
K. implement stop-shadow/rollback
        ↓
L. positive isolated E2E
        ↓
M. negative E2E matrix
        ↓
N. independent runtime oracle
        ↓
O. protected-byte verification
        ↓
P. clean detached regression
        ↓
Q. immutable tested source + candidate seal
        ↓
commit + push
        ↓
STOP_WAIT_R23_INDEPENDENT_EXTERNAL_AUDIT
```

---

# 4. Critical Boundary

The runtime may be implemented but must remain disabled.

Required:

```text
runtime_authorized = false
real_shadow_authorized = false

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
```

Do not consume current market source availability as a real Shadow observation during tests.

---

# 5. Capability Isolation

Keep disabled in Shadow runtime:

```text
A04_H21_CONSUMER
A04_HISTORICAL_AMOUNT_A
A08_CURRENT_RUNTIME
```

Their limitations do not block unrelated infrastructure implementation.

---

# 6. No Stage Promotion

Do not:

```text
create V4_16_ACCEPTED_HEAD
advance V4_STAGE_ACCEPTED_HEAD
advance V4_DATA_ACCEPTED_HEAD
grant Shadow
grant Production
grant Focus
switch default UI
```

---

# 7. Required Exit

```text
V4_16_RUNTIME_ENGINEERING =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

V4_16_RUNTIME_IMPLEMENTED =
ENGINEERING_CANDIDATE_DISABLED

V4_16_RUNTIME_ACTIVATION =
NOT_AUTHORIZED

REAL_SHADOW_OBSERVATIONS =
0

PIT_OBSERVED_REAL_SAMPLES =
0

Stage =
V4_00_TO_V4_15_ACCEPTED

Data =
2026-09-30

Production = false
Shadow = false
Focus = false
V4_16 = false

NEXT =
STOP_WAIT_R23_INDEPENDENT_EXTERNAL_AUDIT
```
