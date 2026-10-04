# V4 Runtime Execution Master｜DM01-R4R2 R25 Bridge Integration｜2026-10-05

## 0. Baseline

Repository: `NanOns/a-share-market-structure-research`
Branch: `codex/v4-system-reform`

Execution baseline:

`54a214167cfd4414901d2002b0a3cf5da45f4e36`

External authority:

`V4_DM01_R4R1_PIT_LINEAGE_REPAIR_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md`

## 1. Current State

```text
R4R1 lineage composition = PASS_EXTERNAL
R4R1 real_forward_evidence = PASS_EXTERNAL
R4R1 first availability = PASS_EXTERNAL
R4R1 promoted-head lineage = PASS_EXTERNAL

R25 bridge validator = PASS_CORE

BLOCKED:
formal daily-input bridge schema
formal bridge producer
R25 independent preflight parity
```

## 2. Execute Only

`DM01_R4R2_R25_TARGET_SESSION_BRIDGE_INTEGRATION_REPAIR_TASK_20261005.md`

Do not reopen R4/R4R1 PASS_KEEP areas.

## 3. Repair Topology

```text
versioned daily-input contract
        ↓
exact target-session bridge producer
        ↓
daily_input.target_session_pit_binding
        ↓
independent R25 bridge preflight
        ↓
runtime GoForwardInputAuthority parity
        ↓
future WAIT unchanged
        ↓
clean regression
        ↓
STOP_WAIT_DM01_R4R2_INDEPENDENT_EXTERNAL_AUDIT
```

## 4. Hard Prohibition

```text
no fake 2026-10-08 package
no Data Head movement
no Stage Head movement
no R25 grant
no Shadow execution
no real counters
no Production/Focus/Default UI permission
```

## 5. Required Exit

```text
DM01_R4R2_LOCAL_REPAIR =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

REAL_TARGET_SESSION_PACKAGE =
NOT_CREATED

R25 =
WAIT_ACCEPTED_DAILY_INPUT

REAL_SHADOW_EXECUTION =
NOT_STARTED

NEXT =
STOP_WAIT_DM01_R4R2_INDEPENDENT_EXTERNAL_AUDIT
```
