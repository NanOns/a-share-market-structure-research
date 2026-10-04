# PRE16 Finalization + R22 Entry Task｜2026-10-04

## 0. Mission

Mechanically formalize the externally accepted PRE16 governance result, then—only if the formalization gate passes—continue into the already defined V4-16 R22 Contract Freeze / Entry work.

This task must not reopen V4-10～V4-15 and must not start real Shadow runtime.

Execution baseline:

`b2c3dd81c4bfed2364b6ea2693860114421f990c`

External authority:

`V4_PRE16_GOVERNANCE_R1_1_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md`

---

# 1. Phase 0｜Mechanical External-Acceptance Formalization

Bind the exact externally supplied audit file and digest.

Create a versioned external acceptance record, recommended:

```text
data/v4/V4_PRE16_GOVERNANCE_ACCEPTED_HEAD_R1.json
```

It must bind:

```text
audited remote HEAD =
b2c3dd81c4bfed2364b6ea2693860114421f990c

tested source =
dabb5eb2fcdd4b52cfa4d9d684f9d9a9786c42bf

tested tag =
codex/pre16-gov-r1-1-tested-source-20261004-r1

external decision =
PASS_FINAL_CANONICAL_BLOCK_SCOPE_REPAIR
```

---

# 2. Current Audit Head Formalization

Update only the current PRE16 governance head/config or create a versioned successor.

Required semantic changes:

```text
GOV_PRE16_01 =
EXTERNALLY_ACCEPTED_CLOSED

GOV_PRE16_02 =
EXTERNALLY_ACCEPTED_CLOSED

GLOBAL_V4_16_CONTRACT_ENTRY_BLOCKERS =
[]
```

Preserve:

```text
A04_H21_CONSUMER =
CAPABILITY_ONLY_BLOCK

A04_HISTORICAL_AMOUNT_A =
CAPABILITY_ONLY_BLOCK

A08_CURRENT_RUNTIME =
CAPABILITY_ONLY_BLOCK / OPEN_EXTERNAL_REAUDIT

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME =
NONBLOCKING_VALIDATION_DEBT

REALTIME_ACCEPTED_COHORT_MATURITY =
NONBLOCKING_VALIDATION_DEBT

PROVED_HORIZONS = []
UNPROVED_HORIZONS = [1,3,5,10,20]
```

Do not turn capability debts into PASS.

---

# 3. Formalization Must Be Mechanical

Allowed changes are limited to:

```text
PRE16 current governance head/config
new PRE16 external acceptance head/record
PRE16 formalization validator/tests/evidence
R22 contract-freeze files after Phase 0 gate
```

Forbidden before the formalization gate passes:

```text
V4-16 runtime implementation
Shadow publication
PIT_OBSERVED claims
Stage Head advance
Data Head advance
Production/Focus changes
```

---

# 4. Protected Bytes

Keep exact:

```text
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_10_ACCEPTED_HEAD
V4_11_ACCEPTED_HEAD
V4_12_ACCEPTED_HEAD
V4_13_ACCEPTED_HEAD_AMENDED_R1
V4_14_ACCEPTED_HEAD
V4_15_ACCEPTED_HEAD
config/v4_current_stage_authority_v2.json
V4-14/V4-15 business runtime
all historical audit registries
```

---

# 5. Phase 0 Independent Gate

Create a validator that proves:

```text
external audit exact bytes/digest match
audited HEAD matches
tested source/tag match
only GOV_PRE16_01/GOV_PRE16_02 acceptance disposition changed
global contract entry blocker list becomes []
capability-only blockers unchanged
all validation debts unchanged
all protected bytes unchanged
Production/Shadow/Focus/V4_16 remain false
```

Required result:

```text
PRE16_EXTERNAL_ACCEPTANCE_FORMALIZATION =
PASS_LOCAL

GLOBAL_V4_16_CONTRACT_ENTRY_BLOCKERS =
[]
```

If this gate fails:

```text
STOP
DO_NOT_START_R22
```

---

# 6. Phase 1｜R22 Contract Freeze / Entry

Only after Phase 0 PASS_LOCAL, execute the previously issued:

`V4_16_R22_REALTIME_SHADOW_CONTRACT_FREEZE_ENTRY_TASK_20261004.md`

with these additional inputs:

```text
PRE16 external acceptance head/record
current cross-stage audit head
blocking scope matrix
canonical issue map
```

R22 must explicitly bind the current audit authority and preserve capability-only blocks.

---

# 7. R22 Capability Behavior

R22 contract design must ensure:

```text
Amount-A H21 formal consumer
→ not active in Shadow until its own gate passes

Historical Amount-A formal consumer
→ unavailable / not active

V4-09 N01 current runtime PREWATCH capability
→ not active in Shadow until separately accepted
```

These restrictions must not prevent unrelated V4-16 contract engineering.

---

# 8. No Runtime Yet

Even if R22 contract freeze passes locally:

```text
Production = false
Shadow = false
Focus = false
V4_16 runtime = false
REAL_SHADOW_OBSERVATIONS = 0
```

R22 may only reach:

```text
V4_16_CONTRACT_COMPLETENESS =
PASS_READY_FOR_EXTERNAL_AUDIT
```

No actual realtime Shadow run in this task.

---

# 9. Required Evidence

Phase 0:

```text
reports/pre16_finalization/
  EXTERNAL_AUDIT_BINDING.json
  ACCEPTANCE_DISPOSITION.json
  BLOCKER_TRANSITION_ORACLE.json
  PROTECTED_BYTES.json
  LOCAL_TEST_SUMMARY.json
  FINALIZATION_GATE.json
```

Phase 1:

use the R22 evidence contract already defined in the R22 task.

---

# 10. Required End State

```text
PRE16_GOVERNANCE =
EXTERNALLY_ACCEPTED_FORMALIZED

GLOBAL_V4_16_CONTRACT_ENTRY_BLOCKERS =
[]

V4_10_TO_V4_15 =
PASS_KEEP_NO_REOPEN

V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_15_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

R22_V4_16_CONTRACT_FREEZE_ENTRY =
PASS_LOCAL

V4_16_CONTRACT_COMPLETENESS =
PASS_READY_FOR_EXTERNAL_AUDIT

V4_16_RUNTIME =
NOT_AUTHORIZED

REAL_SHADOW_OBSERVATIONS =
0

Production = false
Shadow = false
Focus = false

NEXT =
STOP_WAIT_R22_INDEPENDENT_EXTERNAL_AUDIT
```
