# V4-15 R21｜Accepted Head Promotion & Current Authority Transition｜2026-10-03

## 0. Mission

R20R1R2 has passed final external audit.

This task formally promotes the already-tested V4-15 runtime candidate into a capability-scoped V4-15 Accepted Head and advances the global Stage Head from V4-14 to V4-15.

This is a governance/promotion task, not a new algorithm-development round.

---

# 1. Execution Baseline

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Baseline:

`14b183dedf8a55b12e9368229482ab4bdb3395b1`

Read first:

1. `V4_R20R1R2_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md`
2. this task
3. `V4_NEXT_ROUND_EXECUTION_MASTER_R21_20261003.md`

---

# 2. External Authorization

Required input decision:

```text
R20R1R2_EXTERNAL_AUDIT =
PASS_FINAL_V4_15_RUNTIME_CANDIDATE_CAPABILITY_SCOPED

V4_15_PROMOTION =
AUTHORIZED
```

Promotion must fail closed if that exact external audit is not present and exact-byte bound.

---

# 3. Frozen V4-15 Capability Boundary

The new V4-15 Accepted Head may grant:

```text
V4_15_RUNTIME_ENGINEERING =
ENGINEERING_ACCEPTED

RADAR_COHORT_RUNTIME =
ENGINEERING_ACCEPTED

SETTLEMENT_RUNTIME =
ENGINEERING_ACCEPTED

PERSISTED_E2E =
ENGINEERING_ACCEPTED

INDEPENDENT_ORACLE =
ENGINEERING_ACCEPTED

REAL_ACCEPTED_SOURCE_T0_INTEGRATION =
PASS_CAPABILITY_SCOPED

REAL_ACCEPTED_SOURCE_PENDING_DUE_READBACK =
PASS_CAPABILITY_SCOPED

REAL_DM01_DATA_HEAD_REACHABILITY =
ENGINEERING_ACCEPTED

REAL_DM01_ROW_SCHEMA_ADMISSION =
ENGINEERING_ACCEPTED

FORWARD_EVALUATION_PROJECTION =
ENGINEERING_ACCEPTED

HORIZON_SCOPED_VALIDATION_DEBT =
ENGINEERING_ACCEPTED
```

It must preserve:

```text
CURRENT_REAL_MATURITY_EVIDENCE = NONE

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

REALTIME_ACCEPTED_COHORT_MATURITY =
NOT_GRANTED

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED
```

---

# 4. Create Versioned V4-15 Accepted Entry Contract

Create:

```text
config/v4_15_accepted_entry_contract_v1.json
```

It must bind at minimum:

- V4-14 Accepted Head predecessor;
- V4-15 contract package;
- R20 runtime candidate seal;
- R20R1 candidate/scope seal;
- R20R1R1 candidate seal;
- R20R1R2 candidate seal;
- R20R1R2 final external audit;
- exact tested source/tag;
- Data Head;
- calendar;
- identity/membership authority as applicable;
- maturity-debt current readback;
- forward projection contract;
- open validation debt.

Do not rewrite old contract-freeze files.

---

# 5. Create `data/v4/V4_15_ACCEPTED_HEAD.json`

Required high-level semantics:

```text
contract_id =
V4_15_ACCEPTED_HEAD_V1

stage =
V4-15

status =
RUNTIME_ENGINEERING_PASS_CAPABILITY_SCOPED

external_acceptance =
EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED

external_audit_decision =
PASS_FINAL_V4_15_RUNTIME_CANDIDATE_CAPABILITY_SCOPED

accepted_trade_date =
2026-09-30

tested_source =
81d989af438bdeda583a581f1ef7f311205e6139
```

Required permission state:

```text
production = false
shadow = false
focus = false
V4_16 = false
```

Required open debt:

```text
REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

REALTIME_ACCEPTED_COHORT_MATURITY =
NOT_GRANTED

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED

PROVED_HORIZONS = []

UNPROVED_HORIZONS =
[1,3,5,10,20]
```

Also record:

```text
V4_15_FWD_ADJ_VECTOR_01 =
OPEN_NONBLOCKING_TEST_ENHANCEMENT
```

Do not convert this test enhancement into a promotion blocker.

---

# 6. Stage Head Promotion

Before modifying Stage Head, persist exact bytes of the current:

```text
data/v4/V4_STAGE_ACCEPTED_HEAD.json
```

under R21 evidence as:

```text
PARENT_STAGE_HEAD.json
```

Then atomically advance:

```text
accepted_stage_range:
V4_00_TO_V4_15_ACCEPTED
```

Add exact:

```text
v4_15_binding
```

Add:

```text
v4_15_entry =
COMPLETED_EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED_RUNTIME

v4_15_external_acceptance =
PASS_FINAL_V4_15_RUNTIME_CANDIDATE_CAPABILITY_SCOPED
```

Add V4-15 capability summary.

Preserve all V4-00 ... V4-14 bindings/statuses.

Do not move Data Head.

---

# 7. Current Stage Authority Must Transition Atomically

This is a P0 promotion requirement.

Current governance still describes V4-14 as current:

```text
config/v4_current_stage_authority_v1.json
src/workbench_analysis/v4_current_stage_authority.py
```

Promotion is invalid if Stage Head becomes V4-15 while the current authority reader still requires:

```text
V4_00_TO_V4_14_ACCEPTED
data/v4/V4_14_ACCEPTED_HEAD.json
```

Therefore create a versioned V4-15 current authority contract, preferably:

```text
config/v4_current_stage_authority_v2.json
```

and update the current reader in a version-safe way.

Required current authority:

```text
accepted_stage_range =
V4_00_TO_V4_15_ACCEPTED

current_head =
data/v4/V4_15_ACCEPTED_HEAD.json

predecessor_v4_14 =
data/v4/V4_14_ACCEPTED_HEAD.json

data_head =
unchanged 2026-09-30 authority

V4_15_accepted = true
V4_16 = false

Production = false
Shadow = false
Focus = false
```

Do not mutate `v4_current_stage_authority_v1.json` if it is already historical evidence; supersede it with v2.

---

# 8. Preserve V4-14 Replay Compatibility

V4-14 remains an immutable accepted predecessor and replay authority for replay-specific contracts.

After promotion:

```text
CurrentStageAuthority.current_head
=
V4_15_ACCEPTED_HEAD
```

must not cause the V4-14 replay reader to interpret the V4-15 contract package as a V4-14 replay package.

Use an explicit split:

```text
current stage head = V4-15
replay predecessor head = V4-14
```

`ReplayAuthority` may use the V4-14 predecessor binding for replay-specific contract access while still consuming the V4-15 current-stage governance object.

No latest/glob discovery and no fallback to historical validators.

---

# 9. Historical R20A Reader Governance

R20A was an accepted pre-promotion current-stage test for V4-14.

Do not falsify its historical result.

After promotion, separate:

```text
historical R20A V4-14 current-reader evidence
```

from:

```text
R21 V4-15 current-reader evidence
```

If old tests are structurally tied to “V4-14 must be current”, register them individually as superseded current-stage tests rather than weakening their historical assertions.

The R21 current-reader suite must directly test V4-15.

---

# 10. Promotion Validation

Create independent R21 promotion validation that verifies:

1. V4-15 Accepted Head exists;
2. exact external audit binding;
3. exact R20/R20R1/R20R1R1/R20R1R2 candidate bindings;
4. tested-source tag resolves;
5. Stage Head range is exactly V4_00_TO_V4_15_ACCEPTED;
6. Stage Head V4-15 binding matches exact Accepted Head bytes;
7. Data Head remains 2026-09-30;
8. V4-14 Accepted Head bytes are unchanged;
9. V4-15 current authority reader resolves V4-15;
10. V4-14 replay bridge resolves V4-14 explicitly;
11. Production / Shadow / Focus remain false;
12. V4-16 remains false;
13. historical PIT remains NOT_GRANTED;
14. current real maturity remains NONE;
15. open validation debt is preserved.

---

# 11. Promotion Rollback Safety

Before mutation persist:

```text
PARENT_STAGE_HEAD.json
PARENT_CURRENT_STAGE_AUTHORITY.json
```

After mutation create a rollback validation recipe/receipt proving exact pre-promotion Stage Head and authority configuration can be restored from persisted immutable bytes.

Do not actually roll back a successful promotion unless validation fails.

---

# 12. Regression

Run at minimum:

- V4-15 runtime suites from R20/R20R1/R20R1R1/R20R1R2, excluding only tests individually registered as superseded because they assert V4-14 is the current stage;
- new R21 current-stage authority tests;
- V4-14 replay compatibility tests;
- promotion validation tests;
- rollback restoration tests.

Every excluded historical-current test must be individually named and justified.

No broad pattern deselection.

No unrelated test failure may be hidden.

---

# 13. Required R21 Outputs

Recommended:

```text
config/v4_15_accepted_entry_contract_v1.json
config/v4_current_stage_authority_v2.json

data/v4/V4_15_ACCEPTED_HEAD.json
data/v4/V4_STAGE_ACCEPTED_HEAD.json

reports/r21/
  PARENT_STAGE_HEAD.json
  PARENT_CURRENT_STAGE_AUTHORITY.json
  V4_15_PROMOTION_GATE.json
  CURRENT_V4_15_AUTHORITY_GATE.json
  V4_14_REPLAY_COMPATIBILITY_GATE.json
  ROLLBACK_VALIDATION.json
  LOCAL_TEST_SUMMARY.json
  V4_15_PROMOTION_CANDIDATE_SEAL.json

docs/audits/
  V4_R21_V4_15_PROMOTION_20261003.md
```

---

# 14. Required Final Local State

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

CURRENT_REAL_MATURITY_EVIDENCE =
NONE

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED

Production = false
Shadow = false
Focus = false
V4_16 = false

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

Do not start V4-16 implementation in this task.
