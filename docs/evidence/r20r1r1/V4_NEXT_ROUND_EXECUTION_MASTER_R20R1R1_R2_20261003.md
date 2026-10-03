# V4 Next Round Execution Master R20R1R1 R2｜2026-10-03

## 0. Baseline

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Current baseline:

`555409d79c58517761472531404f0ee5cccd81af`

---

# 1. External Audit Result

```text
R20R1_EXTERNAL_AUDIT =
BLOCKED_FORWARD_MATURITY_DEBT_PATH_UNREACHABLE
```

Keep:

```text
R20R1_SCOPE_DECOMPOSITION = PASS_KEEP
R20R1_REAL_MATURITY_FEASIBILITY = PASS_KEEP
R20R1_CURRENT_FAIL_CLOSED_SCOPE = PASS_KEEP
R20R1_TESTED_SOURCE_GOVERNANCE = PASS_KEEP
R20R1_PROTECTED_STATE = PASS_KEEP
```

Repair only:

```text
P0 =
FORWARD_MATURITY_DEBT_POSITIVE_PATH

P1 =
HORIZON_SCOPED_DEBT_STATE
```

Disk cleanup has already been completed by the user and is explicitly removed from this round:

```text
PRECLEAN_EXTERNAL_VERIFICATION = OUT_OF_SCOPE
PRECLEAN_RECOVERY_TASK = REMOVED
```

---

# 2. Read These Files

1. `V4_R20R1_INDEPENDENT_EXTERNAL_AUDIT_R2_20261003.md`
2. `V4_15_R20R1R1_FORWARD_MATURITY_DEBT_REPAIR_TASK_R2_20261003.md`
3. `V4_NEXT_ROUND_EXECUTION_MASTER_R20R1R1_R2_20261003.md`

This master is the highest scheduler for the round.

There is no disk-cleanup task in this execution batch.

---

# 3. Execution Topology

```text
A. R20R1R1 forward maturity reachability repair
        ↓
B. horizon-scoped debt semantics
        ↓
C. positive + negative independent tests
        ↓
D. clean regression
        ↓
E. exact tested source + candidate seal
        ↓
unified push
        ↓
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

---

# 4. Core Principle

The maturity-debt mechanism must satisfy both:

```text
SAFE WHEN NO REAL MATURITY EXISTS
```

and:

```text
ACTUALLY CLOSABLE WHEN REAL ACCEPTED FUTURE DATA MATURES
```

Current R20R1 satisfies only the first.

R20R1R1 must prove both.

---

# 5. Required Semantic Separation

Do not conflate:

```text
real accepted-source settlement runtime maturity
```

with:

```text
real-time accepted cohort maturity
```

The accepted Sept-30 R20 trajectory is:

```text
REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED
RECONSTRUCTED_ASOF
```

It may later prove settlement-runtime maturity after exact future accepted endpoints arrive.

It may never automatically prove historical PIT or real-time cohort availability.

---

# 6. Horizon Rule

Never use:

```text
any proof -> global matured real claims unblocked
```

Required:

```text
OPEN
PARTIAL_MATURITY_EVIDENCE
FULL_REQUIRED_HORIZONS_PROVEN
```

with exact per-horizon coverage.

---

# 7. Frozen Business Scope

Do not modify accepted business algorithms or historical evidence for:

```text
V4-08
V4-09
V4-10
V4-11
V4-12
V4-13
V4-14
R20 runtime
```

Only the validation-debt mechanism and its versioned capability contracts may change.

---

# 8. Protected State

Until next external audit:

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

# 9. Final Required State

```text
R20R1R1_FORWARD_MATURITY_REACHABILITY =
PASS_LOCAL

CURRENT_REAL_MATURITY_EVIDENCE =
NONE

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

PROVED_HORIZONS = []
UNPROVED_HORIZONS = [1,3,5,10,20]

FUTURE_POSITIVE_PATH_ENGINEERING_REACHABILITY =
PASS

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED

V4_15_ACCEPTED_HEAD =
NOT_CREATED

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

No V4-15 promotion and no V4-16 in this round.
