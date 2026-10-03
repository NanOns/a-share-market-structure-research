# V4 Next Round Execution Master R20R1R2｜2026-10-03

## 0. Baseline

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Execution baseline:

`0a6b8b0553ac9503b1d6a78681659b35c2ba934e`

---

# 1. External Audit Result

```text
R20R1R1_EXTERNAL_AUDIT =
BLOCKED_PRODUCTION_DATA_HEAD_SHAPE_MISMATCH
```

PASS_KEEP:

```text
R20R1R1_HORIZON_SCOPED_DEBT
R20R1R1_CURRENT_FAIL_CLOSED_STATE
R20R1R1_ISOLATED_ENGINEERING_TRANSITIONS
R20R1R1_TESTED_SOURCE_GOVERNANCE
R20R1R1_PROTECTED_STATE
```

Repair only:

```text
P0-A =
REAL_DM01_ACCEPTED_COMPONENT_LINEAGE

P0-B =
REAL_DM01_ROW_SCHEMA_TO_V4_15_FORWARD_PROJECTION
```

---

# 2. Read These Files

1. `V4_R20R1R1_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md`
2. `V4_15_R20R1R2_REAL_DM01_INTEGRATION_REPAIR_TASK_20261003.md`
3. `V4_NEXT_ROUND_EXECUTION_MASTER_R20R1R2_20261003.md`

This master is the highest scheduler for this round.

---

# 3. Execution Topology

```text
A. freeze actual DM01 Data Head/component contracts
        ↓
B. implement exact accepted ADJUSTED_DAILY lineage resolver
        ↓
C. implement versioned V4-15 forward-evaluation projection
        ↓
D. replace fixture-only Data Head shape with production-shaped fixture
        ↓
E. positive T+1/T+3/T+5/T+10/T+20 tests
        ↓
F. independent production-shape oracle
        ↓
G. full R20/R20R1/R20R1R1/R20R1R2 regression
        ↓
H. exact tested source + evidence-only seal
        ↓
unified push
        ↓
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

---

# 4. Critical Rule

Do not solve this by modifying DM01 accepted source artifacts to emit V4-15-specific fields.

The boundary must remain:

```text
accepted DM01 source
→ versioned deterministic V4-15 projection
→ settlement maturity
```

---

# 5. No Fixture Shortcut

The production positive test must not use:

```text
FORWARD_EVALUATION_INPUTS
```

or another invented list that places every historical endpoint directly in the final Data Head.

The fixture must mirror actual:

```text
V4_DATA_ACCEPTED_HEAD_V2
ADJUSTED_DAILY component
component receipt lineage
accepted chain / parent bindings
```

---

# 6. Frozen Prior Success

Do not redesign:

```text
OPEN
PARTIAL_MATURITY_EVIDENCE
FULL_REQUIRED_HORIZONS_PROVEN
```

Do not rewrite R20/R20R1/R20R1R1 historical evidence.

Do not alter accepted V4-08 through V4-14 business algorithms.

---

# 7. Protected State

Until next independent audit:

```text
V4_15_ACCEPTED_HEAD = NOT_CREATED

V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_14_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

Production = false
Shadow = false
Focus = false
V4_16 = false

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED
```

---

# 8. Final Required State

```text
R20R1R2_REAL_DM01_DATA_HEAD_REACHABILITY =
PASS_LOCAL

R20R1R2_REAL_DM01_ROW_SCHEMA_ADMISSION =
PASS_LOCAL

PRODUCTION_SHAPED_POSITIVE_PATH =
PASS

HORIZON_SCOPED_DEBT =
PASS_KEEP

CURRENT_REAL_MATURITY_EVIDENCE =
NONE

PROVED_HORIZONS = []

UNPROVED_HORIZONS =
[1,3,5,10,20]

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED

V4_15_ACCEPTED_HEAD =
NOT_CREATED

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

No V4-15 promotion and no V4-16 in this round.
