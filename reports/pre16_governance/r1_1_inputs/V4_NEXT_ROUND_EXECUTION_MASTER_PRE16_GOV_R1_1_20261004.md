# V4 Next Round Execution Master｜PRE16 GOV R1.1｜2026-10-04

## 0. Baseline

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Execution baseline:

`0109d7f6c8b9f4cea6cde32b2342e4b6d4e0526b`

---

# 1. External Audit Decision

```text
PRE16_GOVERNANCE_EXTERNAL_AUDIT =
PARTIAL_PASS_CANONICAL_BLOCK_SCOPE_REPAIR_REQUIRED

PRE16_GOVERNANCE_CORE = PASS_KEEP
V4_10_TO_V4_15 = PASS_KEEP_NO_REOPEN

GOV_PRE16_02 = P0_REPAIR_REQUIRED

V4_16_CONTRACT_ENTRY = HOLD
```

---

# 2. Execute One Work Package

Execute only:

`V4_PRE16_GOVERNANCE_R1_1_CANONICAL_BLOCK_SCOPE_REPAIR_TASK_20261004.md`

Do not start R22 yet.

---

# 3. Purpose

The current audit head is substantially correct, but the same Amount-A H21 consumer issue is represented twice with inconsistent Shadow-blocking semantics.

Repair only:

```text
canonical logical-issue identity
+
global-stage vs capability-only blocker semantics
+
machine-readable alias integrity
```

---

# 4. Required Topology

```text
read external audit
→ freeze protected bytes
→ build canonical issue map
→ normalize blocker schema
→ alias duplicate audit-item identities
→ rebuild current audit head only
→ independent alias/block oracle
→ consumer rescan
→ targeted + clean regression
→ candidate seal
→ commit + push
→ STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

---

# 5. Hard Rules

Do not:

```text
reopen V4-10～V4-15
modify Stage Head
modify Data Head
modify V4-10～V4-15 Accepted Heads
modify V4-14/V4-15 business runtime
grant Shadow
grant Production
grant Focus
start V4-16
start R22
```

---

# 6. Required Exit

```text
GLOBAL_V4_16_CONTRACT_ENTRY_BLOCKERS =
[GOV_PRE16_01]

PRE16_GOV_R1_1 = PASS_LOCAL

V4_10_TO_V4_15 = PASS_KEEP_NO_REOPEN

Stage = V4_00_TO_V4_15_ACCEPTED
Data = 2026-09-30

Production = false
Shadow = false
Focus = false
V4_16 = false

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```
