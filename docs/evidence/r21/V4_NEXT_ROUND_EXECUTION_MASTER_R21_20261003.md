# V4 Next Round Execution Master R21｜2026-10-03

## 0. Baseline

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Execution baseline:

`14b183dedf8a55b12e9368229482ab4bdb3395b1`

---

# 1. External Audit Authority

```text
R20R1R2_EXTERNAL_AUDIT =
PASS_FINAL_V4_15_RUNTIME_CANDIDATE_CAPABILITY_SCOPED

V4_15_PROMOTION =
AUTHORIZED
```

R20/R20R1/R20R1R1/R20R1R2 runtime implementation is PASS_KEEP.

There is no R20R1R3.

---

# 2. Execute These Tasks

Primary task:

`V4_15_R21_ACCEPTED_HEAD_PROMOTION_TASK_20261003.md`

This master is the highest scheduling authority.

---

# 3. Execution Topology

```text
A. Freeze parent Stage Head + current authority bytes
        ↓
B. Create V4-15 accepted entry contract
        ↓
C. Create V4_15_ACCEPTED_HEAD
        ↓
D. Create current-stage authority v2
        ↓
E. Atomically advance V4_STAGE_ACCEPTED_HEAD to V4-15
        ↓
F. Update current reader for V4-15
        ↓
G. Preserve explicit V4-14 replay predecessor bridge
        ↓
H. Independent promotion validation
        ↓
I. rollback-restoration validation
        ↓
J. scoped clean regression
        ↓
K. tested source + promotion candidate seal
        ↓
unified push
        ↓
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

---

# 4. Critical Atomicity Rule

The following state is forbidden even temporarily as a completed candidate:

```text
Stage Head = V4-15
AND
CurrentStageAuthority = V4-14 only
```

Likewise forbidden:

```text
CurrentStageAuthority = V4-15
AND
V4_15_ACCEPTED_HEAD does not exist
```

Accepted Head, Stage Head and current-authority transition form one promotion transaction.

---

# 5. Capability Boundary

Promotion grants engineering/capability-scoped acceptance only.

It does not grant:

```text
REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME
HISTORICAL_PIT_EFFECTIVENESS
REALTIME_ACCEPTED_COHORT_MATURITY
Production
Shadow
Focus
```

Keep:

```text
CURRENT_REAL_MATURITY_EVIDENCE = NONE
PROVED_HORIZONS = []
UNPROVED_HORIZONS = [1,3,5,10,20]
```

These are non-blocking validation debts.

---

# 6. Non-Blocking Test Enhancement

Carry forward:

```text
V4_15_FWD_ADJ_VECTOR_01 =
SUPPORTED_CORPORATE_ACTION_NON_IDENTITY_PROJECTION_VECTOR
```

as an open non-blocking test enhancement.

Do not delay V4-15 Promotion for this item.

---

# 7. Protected State

Must not change:

- V4_DATA_ACCEPTED_HEAD date or bytes;
- V4_14_ACCEPTED_HEAD bytes;
- R20/R20R1/R20R1R1/R20R1R2 accepted evidence;
- accepted business algorithms V4-00 through V4-14.

Production / Shadow / Focus remain false.

---

# 8. Exit State

Required:

```text
R21_V4_15_PROMOTION =
PASS_LOCAL

V4_15_ACCEPTED_HEAD =
CREATED

V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_15_ACCEPTED

CURRENT_STAGE_AUTHORITY =
V4_15

V4_14_REPLAY_PREDECESSOR =
PASS

V4_DATA_ACCEPTED_HEAD =
2026-09-30

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED

V4_16 =
false

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

After R21 is pushed, do not start V4-16 until independent external promotion audit passes.
