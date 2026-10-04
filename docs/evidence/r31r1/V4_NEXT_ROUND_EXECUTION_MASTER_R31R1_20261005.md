# V4 Next Round Execution Master R31R1｜V4-22 Audit Contract Repair｜2026-10-05

## 0. Baseline

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`

Execution baseline:

`2ec72a9fa5bd72a4049c55009466668ea1d219a9`

External audit authority:

`V4_R31_V4_22_INDEPENDENT_AUDIT_CONTRACT_DESIGN_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md`

---

## 1. Current External State

```text
R31_EXTERNAL_AUDIT =
PARTIAL_PASS_R31R1_REQUIRED

R31_SCOPE_AND_HARD_BOUNDARY = PASS
R31_DOMAIN_STATUS_AND_OPEN_REGISTRY = PASS_KEEP
R31_CROSS_STAGE_CARRY = PASS_KEEP
R31_TESTED_SOURCE_GOVERNANCE = PASS_KEEP
R31_PROTECTED_STATE = PASS_KEEP

R31_FINAL_VERDICT_OPEN_ITEM_ENFORCEMENT = FAIL_P0
R31_OPEN10_SESSION_REFERENTIAL_INTEGRITY = FAIL_P0
R31_ITEM_LEVEL_AUTHORITY_VALIDATION = FAIL_P1

V4_22_CONTRACT_DESIGN =
BLOCKED_PENDING_R31R1

V4_22_FINAL_PASS =
NOT_GRANTED
```

---

## 2. Execute

Execute only:

`V4_22_R31R1_FINAL_VERDICT_OPEN_ITEM_AND_SESSION_LINKAGE_REPAIR_TASK_20261005.md`

This remains:

```text
CONTRACT_DESIGN_ONLY
```

---

## 3. Repair Topology

```text
preserve R31 PASS_KEEP areas
        ↓
bind explicit open-item closure receipts
        ↓
make final_verdict consume blocking open-item dispositions
        ↓
preserve OPEN-09 as nonblocking debt
        ↓
require OPEN-10 explicit disposition before final PASS
        ↓
read exact V4-21 ledger required schemas
        ↓
replace five-field-only parent relation with exact publication/session relation
        ↓
add malformed/cross-day/cross-publication negative vectors
        ↓
validate item-level authority/evidence refs independently
        ↓
protected-state verification
        ↓
clean regression
        ↓
new tested-source tag
        ↓
R31R1 candidate seal
        ↓
STOP_WAIT_R31R1_INDEPENDENT_EXTERNAL_AUDIT
```

---

## 4. Hard Boundary

Do not:

```text
close current real-evidence open items
grant V4_17G
grant MIGRATION_REPLAY_PASS
grant production_permission
switch Focus source
switch default UI
write real Forward evidence
create V4_22_ACCEPTED_HEAD
claim V4_22_FINAL_PASS
modify V4-21 business semantics to satisfy the audit
reopen R31 PASS_KEEP areas without direct dependency
```

---

## 5. Required Exit

```text
R31R1_LOCAL_REPAIR =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

V4_22_CONTRACT_DESIGN =
LOCAL_READY_FOR_EXTERNAL_AUDIT_AFTER_R31R1

V4_22_FINAL_AUDIT_ENTRY =
BLOCKED_WAIT_REAL_GATES

V4_22_FINAL_PASS =
NOT_GRANTED

V4_22_ACCEPTED_HEAD =
NOT_CREATED

NEXT =
STOP_WAIT_R31R1_INDEPENDENT_EXTERNAL_AUDIT
```
