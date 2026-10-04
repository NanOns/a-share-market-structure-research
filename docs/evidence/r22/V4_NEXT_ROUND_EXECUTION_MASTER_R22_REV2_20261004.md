# V4 Next Round Execution Master R22 REV2｜2026-10-04

## 0. Baseline

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Execution baseline:

`b2c3dd81c4bfed2364b6ea2693860114421f990c`

---

# 1. External Authority

```text
PRE16_GOV_R1_1_EXTERNAL_AUDIT =
PASS_FINAL_CANONICAL_BLOCK_SCOPE_REPAIR

V4_10_TO_V4_15 =
PASS_KEEP_NO_REOPEN
```

---

# 2. Execute Sequentially In One Round

## Phase 0

Execute the formalization section in:

`V4_PRE16_EXTERNAL_ACCEPTANCE_FORMALIZATION_AND_R22_ENTRY_TASK_20261004.md`

Required gate:

```text
PRE16_EXTERNAL_ACCEPTANCE_FORMALIZATION =
PASS_LOCAL

GLOBAL_V4_16_CONTRACT_ENTRY_BLOCKERS =
[]
```

If Phase 0 fails:

```text
STOP
```

## Phase 1

If and only if Phase 0 passes, execute:

`V4_16_R22_REALTIME_SHADOW_CONTRACT_FREEZE_ENTRY_TASK_20261004.md`

plus the additional current-audit bindings defined in the formalization task.

---

# 3. Do Not Execute R22 Runtime

This round remains contract-first.

Forbidden:

```text
real Shadow execution
PIT_OBSERVED publication
V4_16_ACCEPTED_HEAD
Stage Head advance
Data Head advance
Production cutover
Focus cutover
default UI cutover
```

---

# 4. Capability Scope

The following remain capability-only blocked and must be preserved by R22 contracts:

```text
A04_H21_CONSUMER
A04_HISTORICAL_AMOUNT_A
A08_CURRENT_RUNTIME
```

They do not block unrelated V4-16 contract engineering.

---

# 5. Exit

```text
PRE16_GOVERNANCE =
EXTERNALLY_ACCEPTED_FORMALIZED

GLOBAL_V4_16_CONTRACT_ENTRY_BLOCKERS =
[]

R22_V4_16_CONTRACT_FREEZE_ENTRY =
PASS_LOCAL

V4_16_CONTRACT_COMPLETENESS =
PASS_READY_FOR_EXTERNAL_AUDIT

V4_16_RUNTIME =
NOT_AUTHORIZED

REAL_SHADOW_OBSERVATIONS =
0

Stage =
V4_00_TO_V4_15_ACCEPTED

Data =
2026-09-30

Production = false
Shadow = false
Focus = false

NEXT =
STOP_WAIT_R22_INDEPENDENT_EXTERNAL_AUDIT
```
