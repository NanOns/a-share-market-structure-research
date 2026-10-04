# V4 Next Round Execution Master R24R1｜2026-10-04

## 0. Baseline

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Execution baseline:

`0c9f59fbe723fe0fb0e9d1a6750c339894bc7a5b`

---

# 1. External Audit Decision

```text
R24_EXTERNAL_AUDIT =
PARTIAL_PASS_FORWARD_AUTHORITY_AND_COHORT_IDENTITY_REPAIR_REQUIRED

R24_CORE_ACTIVATION_ARCHITECTURE =
PASS_KEEP

R24_FORWARD_DAILY_INPUT_AUTHORITY =
FAIL_P0

R24_COHORT_ENROLLMENT_IDENTITY =
FAIL_P0

R24_REALTIME_ADMISSION_WRAPPER_SEMANTICS =
P1_REPAIR_SAME_ROUND

V4_16_REAL_SHADOW_ACTIVATION =
HOLD
```

---

# 2. Execute One Work Package

Execute only:

`V4_16_R24R1_GO_FORWARD_INPUT_AUTHORITY_AND_COHORT_IDENTITY_REPAIR_TASK_20261004.md`

Do not start a real Shadow session.

---

# 3. Topology

```text
A. bind R24 external audit
        ↓
B. separate immutable stage authority from advancing daily input authority
        ↓
C. create V4-16 go-forward input authority
        ↓
D. create runtime dependencies V3
        ↓
E. prove isolated future market-session reachability (> 2026-09-30)
        ↓
F. repair COHORT_V1 enrollment identity
        ↓
G. formalize owner candidate vs realtime admission boundary
        ↓
H. add F01–F14
        ↓
I. add C01–C04
        ↓
J. rerun A01–A20
        ↓
K. independent R24R1 oracle
        ↓
L. protected-byte verification
        ↓
M. full clean regression
        ↓
N. immutable tested source + candidate seal
        ↓
commit + push
        ↓
STOP_WAIT_R24R1_INDEPENDENT_EXTERNAL_AUDIT
```

---

# 4. PASS_KEEP

Do not redesign:

```text
real storage successor
activation authority structure
authority-first gate
source readiness internal clock
initialization boundary concept
owner projection business semantics
transaction atomicity
rollback
Legacy isolation
```

---

# 5. Hard Boundaries

Do not:

```text
edit historical CurrentStageAuthority V2 in place
rewrite V4-15 Accepted Head
rewrite V4_DATA_ACCEPTED_HEAD to fabricate a future date
activate committed REAL_SHADOW
consume current live source as real evidence
create PIT_OBSERVED real rows
create V4_16_ACCEPTED_HEAD
advance Stage Head
grant Production
grant Focus
start V4-17 acceptance
```

---

# 6. Exit

```text
R24R1 =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

REAL_SHADOW_RUNTIME =
FUTURE_SESSION_ACTIVATION_CAPABLE_DISABLED_CANDIDATE

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

Stage =
V4_00_TO_V4_15_ACCEPTED

Data =
2026-09-30

Production = false
Shadow = false
Focus = false
V4_16 = false

NEXT =
STOP_WAIT_R24R1_INDEPENDENT_EXTERNAL_AUDIT
```
