# V4 Next Round Execution Master R23R1｜2026-10-04

## 0. Baseline

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`

Execution baseline:

`9724b0b2091b0d1e0ca55af17e1fc8c3948fdf42`

# 1. External Audit Decision

```text
R23_EXTERNAL_AUDIT =
PARTIAL_PASS_OBSERVATION_SLOT_RUNTIME_COMPLETENESS_REPAIR_REQUIRED

R23_CORE_RUNTIME_ARCHITECTURE = PASS_KEEP
R23_SLOT_RUNTIME_CONTRACT_COMPLETENESS = FAIL_P0

V4_16_RUNTIME_ACTIVATION = HOLD
```

# 2. Execute One Work Package

Execute only:

`V4_16_R23R1_OBSERVATION_SLOT_RUNTIME_COMPLETENESS_REPAIR_TASK_20261004.md`

Do not start real Shadow.

# 3. Topology

```text
A. bind R23 external audit
        ↓
B. load accepted Observation Slot V2 fields[]
        ↓
C. persist complete slot records
        ↓
D. freeze source visibility aggregates
        ↓
E. freeze capability/core revision identities
        ↓
F. repair corrected-observation supersedes lineage
        ↓
G. independent slot oracle
        ↓
H. add N25–N32
        ↓
I. rerun persisted positive E2E
        ↓
J. protected-byte verification
        ↓
K. full clean regression
        ↓
L. immutable tested source + candidate seal
        ↓
commit + push
        ↓
STOP_WAIT_R23R1_INDEPENDENT_EXTERNAL_AUDIT
```

# 4. PASS_KEEP

Do not redesign:

```text
clock
source receipt identity
SHADOW_V4 namespace
transaction atomicity
cohort T0
settlement
health
rollback
Legacy isolation
N01–N24
```

# 5. Hard Boundaries

Do not:

```text
activate REAL_SHADOW
consume current market source as a real sample
create PIT_OBSERVED evidence
create V4_16_ACCEPTED_HEAD
advance Stage Head
advance Data Head
grant Shadow
grant Production
grant Focus
start V4-17
```

# 6. Exit

```text
R23R1_SLOT_RUNTIME_COMPLETENESS =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

Stage = V4_00_TO_V4_15_ACCEPTED
Data = 2026-09-30

Production = false
Shadow = false
Focus = false
V4_16 = false

NEXT =
STOP_WAIT_R23R1_INDEPENDENT_EXTERNAL_AUDIT
```
