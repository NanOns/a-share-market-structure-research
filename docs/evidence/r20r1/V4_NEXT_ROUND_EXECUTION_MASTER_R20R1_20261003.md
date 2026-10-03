# V4 Next Round Execution Master R20R1｜2026-10-03

## 0. Baseline

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Execution baseline:

`7f97f4487e2c8aaccb7e7701af4ccfddfa7ddec9`

## 1. External Audit Decision

```text
R20_EXTERNAL_AUDIT =
PARTIAL_PASS_REAL_MATURED_ACCEPTED_SOURCE_SCOPE_REPAIR_REQUIRED

R20A = PASS_KEEP
R20B_CURRENT_RUNTIME_SCOPE = PASS_KEEP
R20C = PASS_KEEP

R20D_ENGINEERING_RUNTIME = PASS_KEEP
R20E_ENGINEERING_E2E_ORACLE = PASS_KEEP

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT =
NOT_PROVEN_P0

V4_15_ACCEPTED_HEAD_PROMOTION =
BLOCKED_PENDING_R20R1_SCOPE_CLOSURE
```

## 2. Read These Files

- `V4_R20_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md`
- `V4_15_R20R1_REAL_MATURITY_SCOPE_CLOSURE_TASK_20261003.md`
- `V4_NEXT_ROUND_EXECUTION_MASTER_R20R1_20261003.md`

This master is the highest scheduler for the next round.

## 3. Execution Topology

```text
R20R1-A
Accepted-source maturity feasibility oracle
        ↓
R20R1-B
Capability decomposition
        ↓
R20R1-C
Versioned supersession gate
        ↓
R20R1-D
Fail-closed capability oracle/tests
        ↓
R20R1-E
Open go-forward maturity validation debt
        ↓
clean regression / exact source seal
        ↓
unified commit + push
        ↓
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

This is one focused P0 work package.

Do not split it into unrelated feature work.

## 4. Core Rule

Do not solve missing maturity evidence by inventing history.

The current accepted facts are:

```text
V4-14 accepted trade date = 2026-09-30
Data Head = 2026-09-30
real accepted-source future read count = 0
real 1/3/5/10/20 outcomes = PENDING
```

Therefore current evidence can support:

```text
engineering settlement runtime
current accepted T0 integration
pending due/readback
```

but cannot support:

```text
real matured accepted-source settlement
historical PIT effectiveness
```

unless a separate exact accepted matured lineage is independently found.

## 5. Non-Blocking Development Principle

The purpose of R20R1 is to repair the capability boundary, not to wait for 20 trading days.

If no earlier exact accepted matured lineage exists:

```text
REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE
```

and create an open go-forward validation debt.

After R20R1 is externally accepted, this maturity debt should not block unrelated continued system development. It only blocks claims/features that specifically require matured real settlement or historical PIT effectiveness.

## 6. Frozen Inputs

Do not rewrite:

- V4-08 through V4-14 accepted business algorithms;
- V4-14 Accepted Head;
- R20 runtime formulas and identity semantics;
- Data Head;
- historical R20 evidence as if it had said something else.

Use versioned R20R1 supersession metadata for promotion semantics.

## 7. Global Forbidden

Until next independent external audit:

```text
V4_15_ACCEPTED_HEAD
Stage Head advance to V4-15
Data Head advance
Production
Shadow
Focus
V4-16

fabricated historical accepted publication
synthetic -> real capability upgrade
engineering vector -> real maturity upgrade
raw/provider fallback
historical PIT upgrade
```

## 8. Required End State

```text
R20R1_SCOPE_CLOSURE = PASS_LOCAL

V4_15_RUNTIME_ENGINEERING = PASS

REAL_ACCEPTED_SOURCE_T0_INTEGRATION =
PASS_CAPABILITY_SCOPED

REAL_ACCEPTED_SOURCE_PENDING_DUE_READBACK =
PASS_CAPABILITY_SCOPED

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED

OPEN_VALIDATION_DEBT =
REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT

V4_15_ACCEPTED_HEAD = NOT_CREATED
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_14_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30

Production = false
Shadow = false
Focus = false
V4_16 = false

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

If a genuinely accepted matured lineage is found, bind it and prove it independently; do not silently change the above expected state without evidence.

## 9. Next After External Audit

If R20R1 passes independent external audit, the following round may:

1. create V4-15 Accepted Head with explicit capability-scoped semantics;
2. keep `REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT` and `HISTORICAL_PIT_EFFECTIVENESS` NOT_GRANTED unless separately proven;
3. advance Stage Head to V4-15;
4. authorize the next engineering phase without waiting for T+20 maturity, subject to the next stage contract.

V4-16 remains blocked until that promotion audit is complete.
