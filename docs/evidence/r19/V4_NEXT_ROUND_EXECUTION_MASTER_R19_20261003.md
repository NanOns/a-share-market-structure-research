# V4 Next Round Execution Master R19｜2026-10-03

## 0. Baseline

Repository:
`NanOns/a-share-market-structure-research`

Branch:
`codex/v4-system-reform`

Execution baseline:
`f4ad7d632e53734798c064f011e2b53ecd99bc27`

## 1. External Audit Decision

```text
R18R1R1R1_EXTERNAL_AUDIT =
PASS_FINAL_V4_14_RUNTIME_CAPABILITY_SCOPED

V4_14_RUNTIME_CANDIDATE =
EXTERNALLY_ACCEPTED_READY_FOR_PROMOTION

V4_14_ACCEPTED_HEAD_PROMOTION = AUTHORIZED

V4_15_CONTRACT_FIRST_ENTRY =
AUTHORIZED_AFTER_R19A_PROMOTION_GATE_PASS
```

Historical limitation remains:

```text
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED
```

and must not be upgraded.

## 2. Read These Files

- `V4_R18R1R1R1_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md`
- `V4_14_R19A_ACCEPTED_HEAD_PROMOTION_TASK_20261003.md`
- `V4_15_R19B_RADAR_COHORT_CONTRACT_FREEZE_TASK_20261003.md`
- `V4_15_R19C_SETTLEMENT_BENCHMARK_CONTROLS_CONTRACT_FREEZE_TASK_20261003.md`
- `V4_15_R19D_CONTRACT_INTEGRATION_INDEPENDENT_ORACLE_TASK_20261003.md`
- `V4_NEXT_ROUND_EXECUTION_MASTER_R19_20261003.md`

This master is the highest scheduler.

## 3. Strict Sequence

```text
R19A
V4-14 Accepted Head Promotion
↓
R19A promotion gate PASS
↓
R19B Radar/Cohort Contract Freeze
       ∥
R19C Settlement/Benchmark/Controls Contract Freeze
↓
R19D Contract Integration + Independent Completeness Oracle
↓
clean detached regression
↓
unified commit + push
↓
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

R19B and R19C may run in parallel only after R19A promotion gate passes.

## 4. R19A Required State

Create formal:
`data/v4/V4_14_ACCEPTED_HEAD.json`

Advance Stage Head only to:

`V4_00_TO_V4_14_ACCEPTED`

Data Head remains:
`2026-09-30`

Promotion semantics:

```text
status = ALGORITHM_STATE_REPLAY_DEGRADED_PASS
ALGORITHM_STATE_REPLAY_PASS =
DEGRADED_PASS_CAPABILITY_SCOPED
```

Must preserve:

```text
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED
REAL_ACCEPTED_SOURCE_REPLAY = PASS_CAPABILITY_SCOPED
```

No production/shadow/focus permission.

## 5. R19B Scope

Freeze only the V4-15 contract family for:
- Radar events;
- Why Now;
- Conflict/Hypothesis;
- daily ledger;
- logical event identity;
- event observations/revisions;
- enrollment identity;
- complete Validation Cohort.

No runtime.

## 6. R19C Scope

Freeze only the V4-15 contract family for:
- due planner;
- forward price path;
- outcome states/revisions;
- competing outcomes;
- market benchmark;
- sector benchmark;
- rotation basket;
- Control A/B/C;
- matched controls;
- settlement readback.

No runtime.

Do not invent benchmark coverage/quote-age thresholds that remain unset in accepted policy.

## 7. R19D Scope

Integrate R19B + R19C into:
- unified field registry;
- unified DAG and non-edges;
- source capability matrix;
- quality degradation contract;
- storage schema design;
- integrated machine vectors;
- independent completeness oracle;
- V4-15 stage-entry gate.

No runtime implementation.

## 8. Global Frozen Inputs

Do not rewrite:
- V4-08 through V4-14 business algorithms;
- V4-14 `full_dag_r5`;
- pre-call invocation runtime;
- consumption mapping/oracle;
- rollback receipt/oracle;
- accepted V4-13 heads;
- Data Head.

## 9. Global Forbidden

Until next external audit:

```text
V4_15 runtime
real Radar publications
real Cohort enrollment
real Settlement execution
V4_15 Accepted Head
Stage Head > V4_00_TO_V4_14_ACCEPTED
Data Head advance
Production
Shadow
Focus
V4-16
formal DB migration apply
FEP runtime
raw/provider fallback
business threshold redesign
```

## 10. Required End State

```text
R19A_V4_14_PROMOTION = PASS_LOCAL

V4_14_ACCEPTED_HEAD = CREATED
ALGORITHM_STATE_REPLAY_PASS =
DEGRADED_PASS_CAPABILITY_SCOPED

V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_14_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

R19B_V4_15_RADAR_COHORT_CONTRACT_FREEZE = PASS_LOCAL
R19C_V4_15_SETTLEMENT_CONTRACT_FREEZE = PASS_LOCAL
R19D_V4_15_CONTRACT_INTEGRATION = PASS_LOCAL

V4_15_CONTRACT_COMPLETENESS =
PASS_READY_FOR_EXTERNAL_AUDIT

V4_15_RUNTIME = NOT_IMPLEMENTED
V4_15_ACCEPTED_HEAD = NOT_CREATED

Production = false
Shadow = false
Focus = false

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

## 11. Next After External Audit

Only if R19 contract package passes independent external audit may the next round implement V4-15 runtime:

```text
Radar projection
→ complete cohort enrollment
→ due planner
→ benchmark/control freezing
→ settlement/outcome revision
→ readback
```

V4-16 remains blocked until V4-15 runtime is separately implemented and accepted.
