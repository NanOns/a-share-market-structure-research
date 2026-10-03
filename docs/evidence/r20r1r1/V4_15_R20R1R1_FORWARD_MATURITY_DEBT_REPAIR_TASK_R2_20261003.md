# V4-15 R20R1R1｜Forward Maturity Debt Reachability Repair R2｜2026-10-03

## 0. Priority

```text
P0 =
MAKE_GO_FORWARD_REAL_MATURITY_VALIDATION_ACTUALLY_REACHABLE

P1 =
MAKE_MATURITY_STATUS_HORIZON_SCOPED
```

Disk cleanup is explicitly outside this task and is not a prerequisite.

Do not change accepted business algorithms.

---

# 1. Baseline

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Execution baseline:

`555409d79c58517761472531404f0ee5cccd81af`

Read first:

- `V4_R20R1_INDEPENDENT_EXTERNAL_AUDIT_R2_20261003.md`
- this task
- `V4_NEXT_ROUND_EXECUTION_MASTER_R20R1R1_R2_20261003.md`

---

# 2. Keep Existing R20R1 Successes

Do not undo:

```text
V4_15_RUNTIME_ENGINEERING = PASS

REAL_ACCEPTED_SOURCE_T0_INTEGRATION =
PASS_CAPABILITY_SCOPED

REAL_ACCEPTED_SOURCE_PENDING_DUE_READBACK =
PASS_CAPABILITY_SCOPED

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED
```

Do not rewrite R20 evidence.

Do not advance Stage/Data.

---

# 3. P0 Root Cause

Current maturity packet validator requires both:

```text
owner publication belongs to frozen V4-14 runtime seal
```

and:

```text
cohort_namespace = REALTIME_ACCEPTED
```

But the only sealed real V4-14 publication is Sept-30 and its accepted R20 enrollment is:

```text
RECONSTRUCTED_ASOF
```

Therefore the advertised future maturity proof path has no positive reachable input.

---

# 4. Required Capability Separation

## 4.1 Settlement-runtime maturity

Introduce an explicit capability:

```text
REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME
```

This capability may use:

```text
REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED
+
RECONSTRUCTED_ASOF T0
```

provided:

- T0 publication/enrollment/freeze are exact accepted lineage;
- freeze exists before future endpoint opening;
- future endpoint source is exact accepted Data Head authority;
- outcome is independently recomputed;
- no raw/provider fallback;
- no historical-availability claim.

It must persist:

```text
T0_OBSERVATION_SCOPE =
RECONSTRUCTED_ASOF

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED
```

## 4.2 Real-time cohort maturity

Track separately, for example:

```text
REALTIME_ACCEPTED_COHORT_MATURITY =
NOT_GRANTED
```

Do not require `REALTIME_ACCEPTED` merely to prove settlement-runtime maturity.

---

# 5. Horizon-Scoped State

Required persisted fields:

```text
required_horizons = [1,3,5,10,20]
proved_horizons
unproved_horizons

capability_by_horizon = {
  "1": ...,
  "3": ...,
  "5": ...,
  "10": ...,
  "20": ...
}
```

Required aggregate states:

```text
OPEN
PARTIAL_MATURITY_EVIDENCE
FULL_REQUIRED_HORIZONS_PROVEN
```

Rules:

```text
0 proved
→ OPEN

some but not all
→ PARTIAL_MATURITY_EVIDENCE

all required horizons
→ FULL_REQUIRED_HORIZONS_PROVEN
```

Do not globally unblock unqualified matured-real claims while any required horizon remains unproved.

---

# 6. Current Real Evidence Must Remain Unchanged

Current actual state remains:

```text
proved_horizons = []
unproved_horizons = [1,3,5,10,20]

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED
```

The repair must not fabricate a mature result now.

---

# 7. Required Positive Reachability Test

Add at least one positive test using an isolated temporary exact-authority fixture representing:

```text
accepted Sept-30 real publication
accepted RECONSTRUCTED_ASOF enrollment
immutable Sept-30 T0 freeze
future accepted Data Head with T+1
accepted T+1 exact endpoint
OBSERVED T+1 outcome
independent recomputation
```

Expected:

```text
validate_packet = PASS
for settlement-runtime maturity

proved_horizons = [1]
unproved_horizons = [3,5,10,20]

aggregate_state =
PARTIAL_MATURITY_EVIDENCE

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED

stage_promotion_authorized =
false
```

This fixture proves implementation reachability only.

It must not alter the current real capability state.

---

# 8. Required Negative Tests

At minimum reject:

- synthetic owner;
- unsealed owner;
- owner/enrollment lineage mismatch;
- raw-provider fallback;
- historical-price-only packet;
- future endpoint not bound by accepted Data Head;
- endpoint opened before T0 freeze;
- mixed evaluation basis;
- wrong horizon/due date;
- corrupted outcome;
- caller boolean pretending independent proof;
- RECONSTRUCTED_ASOF attempting historical PIT upgrade;
- one proved horizon producing aggregate FULL;
- one proved horizon globally unblocking all matured-real claims;
- duplicated packet changing existing receipt;
- corrected source overwriting prior observation.

---

# 9. Independent Oracle

The independent R20R1R1 oracle must not import:

```text
maturity debt writer
settlement evaluator
Radar/Cohort evaluator
```

to derive expected outcomes.

It must independently verify:

- current no-proof state;
- positive fixture reachability;
- horizon coverage transitions;
- partial/full aggregate state;
- exact accepted-source binding;
- PIT remains denied;
- Stage/Data/prod state remains protected.

---

# 10. Clean Regression

Run:

```text
all R20 current tests
all R20R1 tests
all new R20R1R1 tests
```

No broad deselection.

Historical 1168 + R19 62 may remain prior accepted immutable contexts unless changed dependencies require rerun.

If implementation source changes, create a new remote-reachable immutable tested-source tag.

---

# 11. Protected State

Must remain:

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

# 12. Required End State

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

Do not enter V4-15 promotion or V4-16 in this task.
