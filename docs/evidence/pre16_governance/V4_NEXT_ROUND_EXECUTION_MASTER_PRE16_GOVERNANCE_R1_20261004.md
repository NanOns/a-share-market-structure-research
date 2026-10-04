# V4 Next Round Execution Master｜PRE16 Governance R1｜2026-10-04

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
PRE16_STAGE10_TO_STAGE15_INDEPENDENT_REAUDIT =
PASS_WITH_PRE16_GOVERNANCE_RECONCILIATION_REQUIRED

V4_10 = PASS_KEEP
V4_11 = PASS_KEEP
V4_12 = PASS_KEEP
V4_13 = PASS_KEEP
V4_14 = PASS_KEEP
V4_15 = PASS_KEEP

V4_00_TO_V4_15_ACCEPTED_CHAIN =
PASS_CONTIGUOUS

PRE16_CURRENT_CROSS_STAGE_AUDIT_AUTHORITY =
RECONCILIATION_REQUIRED

V4_16_ENTRY =
HOLD
```

---

# 2. Execute Only One Work Package

Execute:

`V4_PRE16_CROSS_STAGE_GOVERNANCE_RECONCILIATION_TASK_R1_20261004.md`

Do not execute the previously prepared V4-16 R22 card yet.

---

# 3. Purpose

This round does not repair algorithms.

It only establishes a unique current machine-readable audit/capability-status authority because:

```text
historical R1 remediation registry
```

is still referenced by the global Stage object while later accepted/scoped evidence has advanced.

The repair must preserve historical R1 exactly and create a new current-status authority.

---

# 4. Execution Topology

```text
A. inventory all historical/current audit registries
        ↓
B. inventory exact accepted/scoped authority heads
        ↓
C. classify historical snapshots vs current authority
        ↓
D. derive current status per audit/capability from exact evidence
        ↓
E. create current cross-stage audit head
        ↓
F. scan runtime/business consumers of stale registry
        ↓
G. independent status oracle
        ↓
H. protected-byte verification
        ↓
I. clean governance regression
        ↓
J. candidate seal
        ↓
commit + push
        ↓
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

---

# 5. Hard Boundaries

Must not:

```text
modify V4-10～V4-15 business algorithms
rewrite any V4-10～V4-15 Accepted Head
change Stage Head
change Data Head
grant Production
grant Shadow
grant Focus
start V4-16
start V4-16 R22
turn implementation-only evidence into external acceptance
turn reconstructed evidence into AS_RECORDED/PIT
```

---

# 6. Current Stage Remains Frozen

Required after execution:

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_15_ACCEPTED

CURRENT_STAGE_AUTHORITY =
V4_15

V4_DATA_ACCEPTED_HEAD =
2026-09-30
```

The R21 V4-15 promotion remains PASS_KEEP.

---

# 7. Exit State

Required:

```text
PRE16_CROSS_STAGE_GOVERNANCE_RECONCILIATION =
PASS_LOCAL

CURRENT_CROSS_STAGE_AUDIT_AUTHORITY =
READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

V4_10_TO_V4_15 =
PASS_KEEP_NO_REOPEN

Production = false
Shadow = false
Focus = false
V4_16 = false

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

Only after independent external audit of this governance reconciliation passes may execution return to:

`V4_16_R22_REALTIME_SHADOW_CONTRACT_FREEZE_ENTRY_TASK_20261004.md`.
