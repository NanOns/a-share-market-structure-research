# V4 Next Round Execution Master R22｜2026-10-04

## 0. Baseline

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Execution baseline:

`a1bb12f19e758784e55a1a93acaad1954861a0fc`

---

# 1. External Audit Authority

```text
R21_EXTERNAL_AUDIT =
PASS_FINAL_V4_15_PROMOTION_CAPABILITY_SCOPED

V4_15 =
CLOSED_ACCEPTED_CAPABILITY_SCOPED

V4_16_CONTRACT_FREEZE_ENTRY =
AUTHORIZED
```

There is no additional V4-15 repair round.

---

# 2. Highest Scheduler

Execute:

`V4_16_R22_REALTIME_SHADOW_CONTRACT_FREEZE_ENTRY_TASK_20261004.md`

under this master.

R22 is contract-first only.

---

# 3. Execution Topology

```text
A. bind exact V4-15 accepted/current authority
        ↓
B. locate/freeze accepted scheduled cutoff + observation deadline authority
        ↓
C. freeze PIT_OBSERVED / SHADOW evidence semantics
        ↓
D. freeze daily_observation_slot
        ↓
E. freeze SHADOW_V4 namespace + prior-state rules
        ↓
F. freeze realtime cohort enrollment/revision semantics
        ↓
G. freeze daily settlement-worker/outbox/idempotency rules
        ↓
H. freeze capability-scoped Shadow health receipts
        ↓
I. freeze daily PIT sector-membership observation
        ↓
J. freeze independent machine vectors
        ↓
K. independent contract-completeness oracle
        ↓
L. clean contract/governance regression
        ↓
M. exact tested source + candidate seal
        ↓
unified push
        ↓
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

---

# 4. Critical Boundaries

R22 must not:

```text
start real Shadow execution
create V4_16_ACCEPTED_HEAD
advance Stage Head
change Data Head
change production Focus source
change default UI
grant Production
grant Shadow
declare SHADOW_STABLE
declare PROVISIONAL_FORWARD_EVIDENCE
use historical replay to create PIT_OBSERVED
```

---

# 5. Real Observation Semantics To Freeze

Required future real observation identity:

```text
evidence_origin = PIT_OBSERVED
execution_mode = SHADOW
namespace = SHADOW_V4
```

The observation slot is:

```text
(model_contract_id, state_lineage_id, trade_date)
```

Only the first compliant accepted publication before the frozen observation deadline may create the original real enrollment.

---

# 6. Legacy Isolation

Throughout V4-16:

```text
PRODUCTION_LEGACY
```

remains production.

Shadow V4:

```text
must use SHADOW_V4 prior state
must not use Legacy prior state
must not write Legacy namespace
must not change Focus source
```

---

# 7. Settlement

V4-15 settlement runtime is PASS_KEEP.

R22 only freezes its realtime execution contract:

```text
accepted Shadow publication
→ due planner
→ due queue/outbox
→ accepted future source
→ result revision
```

No due horizon may be fabricated.

---

# 8. Stability / Forward Gates Are Future Counters

R22 must make later §52A gates measurable but must not claim them.

In particular:

```text
20 consecutive real accepted Shadow sessions
```

cannot be replaced by:

```text
historical replay
engineering fixture
backfill
reconstructed observation
```

Real evidence accumulation is non-blocking for continued engineering development.

---

# 9. Protected State

Must remain byte-identical:

```text
V4_15_ACCEPTED_HEAD
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
v4_current_stage_authority_v2
```

Current stage remains:

```text
V4_00_TO_V4_15_ACCEPTED
```

---

# 10. Exit State

Required:

```text
R22_V4_16_CONTRACT_FREEZE_ENTRY =
PASS_LOCAL

V4_16_CONTRACT_COMPLETENESS =
PASS_READY_FOR_EXTERNAL_AUDIT

V4_16_RUNTIME =
NOT_AUTHORIZED

REAL_SHADOW_OBSERVATIONS =
0

V4_15 =
CURRENT_ACCEPTED_STAGE

Production = false
Shadow = false
Focus = false

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```
