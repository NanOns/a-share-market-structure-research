# V4 Next Round Execution Master R31R2｜V4-22 Fail-Closed Audit Contract Repair｜2026-10-05

## 0. Baseline

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`

Execution baseline:

`abe8311d55db3fecc086a77c3ce8a16f4309df54`

External audit authority:

`V4_R31R1_V4_22_AUDIT_CONTRACT_REPAIR_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md`

---

## 1. Current External State

```text
R31R1_EXTERNAL_AUDIT =
PARTIAL_PASS_R31R2_REQUIRED

R31R1_SCOPE_AND_HARD_BOUNDARY = PASS
R31R1_TESTED_SOURCE_GOVERNANCE = PASS
R31R1_PROTECTED_STATE = PASS
R31R1_CLEAN_REGRESSION = PASS_KEEP_SCOPED

R31_FINAL_VERDICT_OPEN_ITEM_CONSUMPTION = PASS_CORE
R31_ITEM_LEVEL_AUTHORITY_VALIDATION = PASS
R31_EXACT_SESSION_PARENT_LINKAGE = PASS_CORE

R31_CHILD_LEDGER_SCHEMA_FAIL_CLOSED = FAIL_P0
R31_OPEN_ITEM_CLOSURE_EVIDENCE_VERIFICATION = FAIL_P0
R31_REPAIR_REPRODUCIBILITY_AND_STAGE_IDENTITY = FAIL_P1

V4_22_CONTRACT_DESIGN =
BLOCKED_PENDING_R31R2

V4_22_FINAL_PASS =
NOT_GRANTED
```

---

## 2. Execute

Execute only:

`V4_22_R31R2_FAIL_CLOSED_CLOSURE_EVIDENCE_AND_REPRODUCIBILITY_REPAIR_TASK_20261005.md`

This remains:

```text
CONTRACT_DESIGN_ONLY
```

---

## 3. Repair Topology

```text
preserve all R31R1 PASS / PASS_CORE areas
        ↓
independently read exact closure authority
        ↓
independently read exact closure evidence bindings
        ↓
reject placeholders / opener-only authority / bad digest
        ↓
validate all ledger row schemas before lane filtering
        ↓
reject missing or unknown evidence_lane
        ↓
preserve recognized diagnostic-lane exclusion
        ↓
make latest repair contract deterministically reproducible
        ↓
align canonical stage identity / next_stage
        ↓
protected-state verification
        ↓
clean regression
        ↓
new tested-source tag
        ↓
R31R2 candidate seal
        ↓
STOP_WAIT_R31R2_INDEPENDENT_EXTERNAL_AUDIT
```

---

## 4. Hard Boundary

Do not:

```text
close any current real-evidence open item
grant V4_17G
grant MIGRATION_REPLAY_PASS
grant production_permission
switch Focus source
switch default UI
write real Forward evidence
create V4_22_ACCEPTED_HEAD
claim V4_22_FINAL_PASS
modify V4-21 business semantics
reopen R31R1 PASS areas without direct dependency
```

---

## 5. Required Exit

```text
R31R2_LOCAL_REPAIR =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

V4_22_CONTRACT_DESIGN =
LOCAL_READY_FOR_EXTERNAL_AUDIT_AFTER_R31R2

V4_22_FINAL_AUDIT_ENTRY =
BLOCKED_WAIT_REAL_GATES

V4_22_FINAL_PASS =
NOT_GRANTED

V4_22_ACCEPTED_HEAD =
NOT_CREATED

NEXT =
STOP_WAIT_R31R2_INDEPENDENT_EXTERNAL_AUDIT
```
