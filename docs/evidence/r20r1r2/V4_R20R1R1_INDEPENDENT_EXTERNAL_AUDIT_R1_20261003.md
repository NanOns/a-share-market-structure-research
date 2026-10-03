# V4 R20R1R1 Independent External Audit R1｜2026-10-03

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`

Branch: `codex/v4-system-reform`

Current remote HEAD: `0a6b8b0553ac9503b1d6a78681659b35c2ba934e`

R20R1R1 exact tested source: `c1615c3452798d3565ebe653cb4ea5ce60e54a30`

Immutable tested tag: `codex/r20r1r1-tested-source-20261003-r2`

Execution baseline: `555409d79c58517761472531404f0ee5cccd81af`

---

# 1. Unique External Audit Decision

```text
R20R1R1_EXTERNAL_AUDIT =
BLOCKED_PRODUCTION_DATA_HEAD_SHAPE_MISMATCH

R20R1R1_HORIZON_SCOPED_DEBT = PASS_KEEP
R20R1R1_CURRENT_FAIL_CLOSED_STATE = PASS_KEEP
R20R1R1_ISOLATED_ENGINEERING_TRANSITIONS = PASS_KEEP
R20R1R1_TESTED_SOURCE_GOVERNANCE = PASS_KEEP
R20R1R1_PROTECTED_STATE = PASS_KEEP

R20R1R1_REAL_DM01_DATA_HEAD_REACHABILITY = FAIL_P0
R20R1R1_REAL_DM01_ROW_SCHEMA_ADMISSION = FAIL_P0

V4_15_ACCEPTED_HEAD_PROMOTION = BLOCKED
V4_16 = BLOCKED
```

The previous logical deadlock has been repaired in an isolated engineering model, but the positive fixture does not reproduce the actual accepted DM01 Data Head/component contract used by the project.

---

# 2. What Passed

## 2.1 Horizon-scoped debt semantics｜PASS KEEP

The new debt state correctly persists:

```text
required_horizons = [1,3,5,10,20]
proved_horizons
unproved_horizons
capability_by_horizon
```

and derives:

```text
OPEN
PARTIAL_MATURITY_EVIDENCE
FULL_REQUIRED_HORIZONS_PROVEN
```

A T+1-only proof remains PARTIAL and keeps unqualified maturity claims blocked.

This closes the prior P1 finding.

## 2.2 Current real state remains fail-closed｜PASS KEEP

The actual repository remains:

```text
CURRENT_REAL_MATURITY_EVIDENCE = NONE

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

PROVED_HORIZONS = []

UNPROVED_HORIZONS =
[1,3,5,10,20]

REALTIME_ACCEPTED_COHORT_MATURITY =
NOT_GRANTED

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED
```

The isolated fixtures do not upgrade current real capability.

## 2.3 Isolated positive transition logic｜PASS KEEP

Engineering fixtures demonstrate:

```text
[] -> OPEN
[1] -> PARTIAL_MATURITY_EVIDENCE
[1,3] -> PARTIAL_MATURITY_EVIDENCE
[1,3,5,10,20] -> FULL_REQUIRED_HORIZONS_PROVEN
```

The transition logic is internally consistent.

## 2.4 Correction / append-only semantics｜PASS KEEP

The new tests cover duplicate idempotence, next-revision correction, FIRST_OBSERVED preservation, LATEST_VALIDATED update, changed-source requirement, readback tamper rejection and no overwrite of prior proof.

## 2.5 Tested-source governance and regression｜PASS KEEP

The immutable tag `codex/r20r1r1-tested-source-20261003-r2` resolves to `c1615c3452798d3565ebe653cb4ea5ce60e54a30`.

Final HEAD is one evidence-only commit ahead.

Clean regression:

```text
R20 current = 107
R20R1 = 51
R20R1R1 = 35
TOTAL = 193 PASS
0 failed
0 errors
0 skipped
0 deselected
```

---

# 3. P0 Finding A｜Fixture Data Head Shape Does Not Match Real DM01 Data Head

## 3.1 Actual accepted Data Head

The actual `data/v4/V4_DATA_ACCEPTED_HEAD.json` uses:

```text
contract_id = V4_DATA_ACCEPTED_HEAD_V2
```

and `component_artifacts` contains named accepted production components such as:

```text
ADJUSTED_DAILY
RAW_DAILY
TRADING_STATUS
IDENTITY_UNIVERSE
ISST
PERIOD_ADJUSTED
PERIOD_RAW
PRICE_LIMIT
SPECIAL_PHASE
```

For the current accepted date, `ADJUSTED_DAILY` is one exact artifact descriptor for that accepted trade date.

The component receipt preserves:

```text
parent_component_bindings
parent_data_head_digest
trade_date
target_trade_date
```

which form the real daily lineage.

## 3.2 Engineering fixture shape

The R20R1R1 fixture instead constructs future Data Heads whose `component_artifacts` contains an invented collection:

```text
FORWARD_EVALUATION_INPUTS
```

and accumulates all T+1 ... T+N endpoint artifact descriptors directly into the final due-date Data Head.

That is not the current DM01 accepted Data Head production contract.

## 3.3 Validator admission logic

`scripts/r20r1r1_packet_validation.py` currently:

1. loads only the selected due-date Data Head;
2. recursively walks only that Data Head's `component_artifacts`;
3. requires every T+1 ... T+N endpoint descriptor to be directly present there.

This succeeds only because the engineering fixture places every historical endpoint into `FORWARD_EVALUATION_INPUTS`.

A real due-date Data Head does not directly contain all prior daily ADJUSTED_DAILY artifacts.

Therefore T+3/T+5/T+10/T+20 cannot be proven from the real production shape through the current validator.

---

# 4. P0 Finding B｜Fixture Row Schema Does Not Match Real ADJUSTED_DAILY Producer

## 4.1 Actual producer

The real producer is:

`src/workbench_analysis/dm01_incremental_component_builders_r3_3.py`

`build_raw_daily()` produces rows containing fields including:

```text
security_id
source_security_key
trade_date
open/high/low/close
volume
amount
source_authority
source_snapshot_id
source_digest
record_quality
identity_quality
membership_basis
identity_source_revision
```

`build_adjusted_daily()` extends those rows with fields including:

```text
raw_daily_digest
price_basis
adjustment_readiness
adjustment_source_revision
qfq_mul
qfq_add
```

and `_finish()` publishes:

```text
contract_id =
DM01_ADJUSTED_DAILY_ARTIFACT_R3_3
```

## 4.2 Fixture-only fields

The current positive fixture manufactures source rows containing:

```text
evaluation_basis_date
verified_identity
verified_adjustment
T0_basis_verified
transform_coefficients
T0_transform_coefficients
status = ACTUAL
```

Those are V4-15 settlement input semantics, not native fields produced by current DM01 ADJUSTED_DAILY.

The validator directly requires these fixture fields on accepted source rows.

Therefore the current positive path still depends on a source schema that production does not emit.

---

# 5. Required Architectural Correction

Do not change DM01 accepted source artifacts merely to satisfy V4-15.

The correct boundary is:

```text
REAL ACCEPTED DM01 DATA HEAD / COMPONENT LINEAGE
        ↓
exact accepted ADJUSTED_DAILY artifacts
        ↓
versioned V4-15 forward-evaluation projection
        ↓
settlement-runtime maturity validator
```

The forward-evaluation projection must be derived from existing accepted source fields and bind exact source artifact bytes.

It may create V4-15-specific fields such as:

```text
evaluation_basis_date
verified_identity
verified_adjustment
T0_basis_verified
transform_coefficients
T0_transform_coefficients
```

but those fields must be outputs of a separately versioned deterministic adapter/projection, not pretended to be native DM01 source fields.

---

# 6. Required Real Lineage Resolution

The validator must resolve each future session's accepted ADJUSTED_DAILY artifact from exact accepted production lineage.

It must not require all path artifacts to be direct children of the final Data Head.

Use authoritative structures already present, including where applicable:

- `V4_DATA_ACCEPTED_HEAD_V2`;
- exact `accepted_chain`;
- component receipts;
- `parent_component_bindings`;
- `parent_data_head_digest`;
- exact trade dates and digests.

Fail closed on:

- missing intermediate accepted session;
- ambiguous multiple accepted components for one date;
- digest mismatch;
- broken parent linkage;
- target-date mismatch;
- unaccepted component;
- raw/provider fallback.

---

# 7. Required Production-Shape Positive Fixture

The next repair must replace the current invented positive fixture with a production-shaped fixture.

For each simulated accepted date:

```text
V4_DATA_ACCEPTED_HEAD_V2
  component_artifacts:
    ADJUSTED_DAILY: <that date's artifact>
    ...
```

Each simulated accepted day must have its own exact ADJUSTED_DAILY artifact and production-style receipt/parent lineage.

The final T+N Data Head must not directly list all prior endpoint artifacts in a custom `FORWARD_EVALUATION_INPUTS` list.

The source rows must use the real DM01 producer schema.

Any V4-15 settlement fields must be produced by the separate forward-evaluation adapter.

---

# 8. Required End-to-End Positive Tests

At minimum prove with production-shaped fixtures:

```text
T+1
T+3
T+5
T+10
T+20
```

For each horizon:

1. resolve exact accepted sessions;
2. resolve exact daily accepted ADJUSTED_DAILY source artifact for each session;
3. create/read deterministic V4-15 forward projection;
4. independently verify projection math and source binding;
5. compute observed settlement result;
6. update horizon-scoped debt;
7. keep PIT and REALTIME cohort capability denied.

The independent oracle must derive endpoint lineage without importing the production resolver/writer.

---

# 9. Final External Audit State

```text
R20R1R1_EXTERNAL_AUDIT =
BLOCKED_PRODUCTION_DATA_HEAD_SHAPE_MISMATCH

R20R1R1_HORIZON_SCOPED_DEBT =
PASS_KEEP

R20R1R1_ISOLATED_ENGINEERING_TRANSITIONS =
PASS_KEEP

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED

V4_15_ACCEPTED_HEAD =
NOT_CREATED

V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_14_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

Production = false
Shadow = false
Focus = false
V4_16 = false

NEXT =
R20R1R2_REAL_DM01_INTEGRATION_REPAIR
```
