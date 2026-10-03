# V4-15 R20R1R2｜Real DM01 Data Head Integration Repair｜2026-10-03

## 0. Priority

```text
P0-A =
MAKE_MATURITY_VALIDATOR_CONSUME_REAL_V4_DATA_ACCEPTED_HEAD_SHAPE

P0-B =
MAKE_FORWARD_EVALUATION_USE_REAL_DM01_ADJUSTED_DAILY_ROW_SCHEMA
```

The horizon-scoped debt state machine is already PASS_KEEP and must not be redesigned.

---

# 1. Baseline

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Execution baseline:

`0a6b8b0553ac9503b1d6a78681659b35c2ba934e`

Read first:

- `V4_R20R1R1_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md`
- this task
- `V4_NEXT_ROUND_EXECUTION_MASTER_R20R1R2_20261003.md`

---

# 2. PASS_KEEP

Do not rewrite or weaken:

```text
OPEN
PARTIAL_MATURITY_EVIDENCE
FULL_REQUIRED_HORIZONS_PROVEN

proved_horizons
unproved_horizons
capability_by_horizon

FIRST_OBSERVED / LATEST_VALIDATED
append-only correction semantics
```

Also keep:

```text
CURRENT_REAL_MATURITY_EVIDENCE = NONE

REALTIME_ACCEPTED_COHORT_MATURITY =
NOT_GRANTED

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED
```

---

# 3. Root Cause A｜Invented Data Head Shape

Current positive fixture uses:

```text
component_artifacts.FORWARD_EVALUATION_INPUTS
```

containing all T+1...T+N source descriptors.

Real `V4_DATA_ACCEPTED_HEAD_V2` does not work this way.

The real head has named production components and only the current accepted component artifact in `component_artifacts`.

Therefore the current validator cannot resolve multi-day paths from production authority.

---

# 4. Required Real Accepted-Component Resolver

Implement a versioned resolver for exact accepted daily components.

Suggested responsibility:

```text
resolve_accepted_adjusted_daily_path(
    frozen_T0,
    due_date,
    current_data_head
)
```

It must:

1. verify current Data Head is exact accepted `V4_DATA_ACCEPTED_HEAD_V2`;
2. prove ancestry reaches the frozen T0 Data Head;
3. obtain the accepted session calendar;
4. derive exact T+1...T+N accepted session dates;
5. resolve exactly one accepted `ADJUSTED_DAILY` artifact for each required date;
6. validate each artifact:
   - exact digest/bytes;
   - `DM01_ADJUSTED_DAILY_ARTIFACT_R3_3`;
   - artifact trade_date equals required session;
   - accepted component receipt exists;
   - receipt artifact binding matches;
   - receipt parent lineage is valid;
7. reject gaps, ambiguity, wrong dates and unaccepted artifacts.

Use existing authoritative lineage where available:

```text
V4_DATA_ACCEPTED_HEAD_V2
accepted_chain
component receipts
parent_component_bindings
parent_data_head_digest
```

Do not introduce a second parallel truth if existing accepted lineage is sufficient.

Important:

A batch Data Head promotion may span multiple accepted sessions.

Do not assume `parent_archive` alone provides one Data Head object per trading session.

The resolver must follow actual accepted component/chain lineage.

---

# 5. Root Cause B｜Invented Endpoint Row Fields

Do not require real DM01 source rows to directly contain:

```text
evaluation_basis_date
verified_identity
verified_adjustment
T0_basis_verified
transform_coefficients
T0_transform_coefficients
```

Those are not native fields of current DM01 ADJUSTED_DAILY.

---

# 6. Versioned Forward-Evaluation Projection

Add a separate deterministic V4-15 projection layer.

Suggested contract:

```text
V4_15_ACCEPTED_FORWARD_EVALUATION_PROJECTION_V1
```

Each projected row must bind:

```text
source_data_head
source_adjusted_daily_artifact
source_component_receipt
security_id
trade_date
source row identity/digest
evaluation_basis_date
```

It may derive V4-15 settlement fields:

```text
verified_identity
verified_adjustment
T0_basis_verified
transform_coefficients
T0_transform_coefficients
```

from exact accepted DM01 evidence.

Do not modify the accepted DM01 source artifact.

---

# 7. Adjustment/Basis Requirements

The projection must use the project's accepted adjustment semantics.

Available DM01 accepted fields include:

```text
price_basis = TDX_NATIVE_AFFINE_QFQ
adjustment_readiness
adjustment_source_revision
qfq_mul
qfq_add
```

The projection must:

- fail closed when adjustment readiness is UNKNOWN;
- preserve exact TDX source identity;
- map every path row to one explicit endpoint evaluation basis;
- independently prove T0 reference mapping into that basis;
- never substitute BaoStock OHLC;
- never use an external adjustment service;
- never infer unsupported corporate-action transforms.

The formula and source-field mapping must be frozen in a versioned contract.

---

# 8. Production-Shaped Fixture Hard Rule

Replace the current reachability fixture design.

The new fixture must use the same structural shape as real DM01.

For each simulated future accepted date:

```text
V4_DATA_ACCEPTED_HEAD_V2
  component_artifacts:
    ADJUSTED_DAILY: <that date's artifact>
    other production-style components as needed
```

Each ADJUSTED_DAILY source artifact must use native producer fields.

Each component receipt must use production-style fields:

```text
component_id
artifact_path
artifact_sha256
artifact_bytes
trade_date
target_trade_date
parent_data_head_digest
parent_component_bindings
```

Do not place all historical path endpoints under:

```text
FORWARD_EVALUATION_INPUTS
```

or any equivalent fixture-only shortcut.

---

# 9. Required Tests

## 9.1 Production-shape positive tests

Must prove:

```text
T+1
T+3
T+5
T+10
T+20
```

using only production-shaped accepted Data Head/component lineage.

## 9.2 Schema negative tests

Reject:

- fixture-only `FORWARD_EVALUATION_INPUTS` as sufficient production authority;
- source row with invented settlement fields but no projection receipt;
- ADJUSTED_DAILY artifact without accepted receipt;
- receipt/artifact digest mismatch;
- trade-date mismatch;
- component lineage gap;
- parent-component mismatch;
- wrong accepted-chain membership;
- qfq/adjustment UNKNOWN;
- identity ambiguity;
- missing path session.

## 9.3 Projection tests

Prove:

- source row remains immutable;
- projection is deterministic;
- projection digest changes when any source descriptor changes;
- T0 transform is independently recomputed;
- common evaluation basis is identical across all path rows;
- no external price/adjustment fallback;
- PIT remains NOT_GRANTED.

---

# 10. Independent Oracle

The oracle must not import:

```text
production component resolver
forward projection writer
maturity debt writer
settlement evaluator
```

to derive its expectation.

It must independently traverse production-shaped accepted component lineage and independently recompute projection/settlement expectations.

---

# 11. Current Real State

Do not fabricate current maturity.

Current repository still has:

```text
Data Head = 2026-09-30
T0 = 2026-09-30
future accepted endpoint count = 0
```

Therefore after repair:

```text
CURRENT_REAL_MATURITY_EVIDENCE = NONE
PROVED_HORIZONS = []
UNPROVED_HORIZONS = [1,3,5,10,20]
```

must remain.

---

# 12. Regression

Run:

```text
all R20 current tests
all R20R1 tests
all R20R1R1 tests
all new R20R1R2 tests
```

No broad skip or deselection.

The previously accepted horizon-state behavior must remain unchanged.

If implementation source changes, publish a new exact immutable tested-source tag and prove final evidence commit is evidence-only.

---

# 13. Protected State

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

# 14. Required End State

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

Do not enter V4-15 promotion or V4-16 in this task.
