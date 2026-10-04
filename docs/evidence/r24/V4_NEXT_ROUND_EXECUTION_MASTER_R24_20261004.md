# V4 Next Round Execution Master R24｜2026-10-04

## 0. Baseline

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`

Execution baseline:

`b6b3105e713187462f49054e62fa70df8b9bd292`

---

# 1. External Authority

```text
R23R1_EXTERNAL_AUDIT =
PASS_FINAL_OBSERVATION_SLOT_RUNTIME_COMPLETENESS

R23_RUNTIME_ENGINEERING =
EXTERNALLY_ACCEPTED_DISABLED_CANDIDATE

V4_16_REAL_SHADOW_ACTIVATION_ENGINEERING_ENTRY =
AUTHORIZED

V4_16_REAL_SHADOW_ACTIVATION =
NOT_AUTHORIZED
```

---

# 2. Execute One Work Package

Execute:

`V4_16_R24_REAL_SHADOW_ACTIVATION_READINESS_TASK_20261004.md`

This round makes the real Shadow path activation-capable but keeps the committed authority disabled.

---

# 3. Execution Topology

```text
A. formalize R23/R23R1 external engineering acceptance
        ↓
B. create runtime dependencies V2
        ↓
C. bind R23R1 slot policy centrally
        ↓
D. create real-storage successor contract/migration
        ↓
E. create activation authority V2 = disabled
        ↓
F. refactor REAL_SHADOW from unconditional reject
   to accepted-authority gate
        ↓
G. implement real source-readiness adapter
        ↓
H. freeze real initialization boundary
        ↓
I. implement one-session launch controller
        ↓
J. isolated activation-simulation E2E
        ↓
K. A01–A20 negative activation matrix
        ↓
L. independent activation oracle
        ↓
M. Legacy/rollback/protected-state checks
        ↓
N. clean detached regression
        ↓
O. immutable tested source + candidate seal
        ↓
commit + push
        ↓
STOP_WAIT_R24_INDEPENDENT_EXTERNAL_AUDIT
```

---

# 4. Hard Boundaries

Do not:

```text
start a real market-session Shadow run
create real PIT_OBSERVED rows
increment real Shadow counters
create V4_16_ACCEPTED_HEAD
advance Stage Head
advance Data Head
grant Production
grant Focus
start V4-17 acceptance
```

---

# 5. Engineering Continuity

Real-evidence accumulation must not globally block unrelated engineering.

After R24 external acceptance, actual launch and V4-17 UI engineering may be scheduled separately/partly in parallel, while V4-17G evidence gates continue accumulating over real sessions.

---

# 6. Required Exit

```text
R24_REAL_SHADOW_ACTIVATION_READINESS =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

REAL_SHADOW_RUNTIME =
ACTIVATION_CAPABLE_DISABLED_CANDIDATE

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

Stage = V4_00_TO_V4_15_ACCEPTED
Data = 2026-09-30

Production = false
Shadow = false
Focus = false
V4_16 = false

NEXT =
STOP_WAIT_R24_INDEPENDENT_EXTERNAL_AUDIT
```
