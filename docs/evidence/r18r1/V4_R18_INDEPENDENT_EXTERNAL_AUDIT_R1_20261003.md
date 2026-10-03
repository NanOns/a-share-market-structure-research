# V4 R18 Independent External Audit R1｜2026-10-03

## Audit Target
- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- Audited remote HEAD: `70fc9b050497e798d077480d0ae4adf97e9824c6`
- Execution baseline: `47b7f72f374c059f35a66bf2fe298a3ec5fe7efc`
- Clean tested source: `8ac4187382765d3213341b5800b7749933e91266`

## Unique Decision

```text
R18_EXTERNAL_AUDIT = PARTIAL_PASS_FULL_DAG_OWNER_EDGE_REPAIR_REQUIRED

R18A_RUNTIME_HARNESS = PASS_KEEP

R18B_CROSS_PROCESS_MECHANICS = PASS_KEEP
R18B_SAME_DAY_REVISION_ISOLATION = PASS_KEEP
R18B_DETERMINISTIC_REPLAY = PASS_KEEP
R18B_FULL_DAG_OWNER_EDGE_COVERAGE = FAIL_P0

R18C_INDEPENDENT_VECTOR_ORACLE = PASS_KEEP
R18C_REAL_ACCEPTED_SOURCE_REPLAY = PASS_KEEP_CAPABILITY_SCOPED
R18C_FULL_DAG_ORACLE_COMPLETENESS = FAIL_P0

HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED_KEEP

V4_14_RUNTIME_CANDIDATE = REPAIR_REQUIRED_BEFORE_PROMOTION
V4_14_ACCEPTED_HEAD = NOT_CREATED
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_13_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
ALGORITHM_STATE_REPLAY_PASS = NOT_GRANTED
```

## PASS / KEEP

R18A is accepted: exact active authority, stale-ref rejection, append-only publication, 60 frozen vectors, all 17 dimensions, no production permissions.

R18B cross-process mechanics are accepted. The 2026-09-30 r1/r2 executions both read the exact 2026-09-29 predecessor, run in distinct child processes, and the producer process is waited/exited before the consumer begins. Determinism is also re-run in a separate process.

R18C frozen-vector oracle is accepted. It does not import the V4-14 replay evaluator for expected results and includes the required perturbation classes.

Real accepted-source replay remains accepted only as `REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED`; `AS_RECORDED=false`, `knowledge_lineage=RECONSTRUCTED_CORRECTED`, and `HISTORICAL_PIT_EFFECTIVENESS=NOT_GRANTED` are correctly preserved.

## P0 G01｜Claimed Full DAG Does Not Execute the Frozen Owner-edge DAG

The frozen V4-14 owner DAG explicitly contains edges including:

```text
F0 -> A
F0 -> B0
A  -> B0
B0 -> B1
B0 -> B2
F0 -> C
A  -> C
C  -> D0
F0 -> D1
D1(T-1) -> D1
D0 -> D2
D1 -> D2
C  -> D2
B0/B1/B2/MEMBERSHIP/CORE/NATIVE/BASE_SEED -> CONTEXT
D1/CONTEXT -> PROFILE/D3
```

plus replay-required D2/Event/Gate-B edges.

But `src/workbench_analysis/v4_14_full_dag.py` emits only the coarse trace:

```text
Accepted Source Binding
Seed
Sector/Rotation
PREWATCH
Confirmation
Structure
State Reducer
Event Diff
Profile/Context
Gate-B Observation
```

This is not equivalent to executing every frozen owner edge.

Concrete gaps:

1. B0 is not independently executed.
2. B2 is not independently executed.
3. B0->B1 is not proven from a B0 output; `rotation_acceptance()` evaluates a frozen rotation vector directly.
4. B0->B2 is not proven.
5. PREWATCH consumes fixed synthetic facts such as `mandatory_core_quality_ready=TRUE`, `delta3=3`, `compression_state=COMPRESSING`, `ma_structure_state=BEAR_ALIGNED`, `core_extension_risk=LOW` without edge-level producer receipts.
6. D0 uses a synthetic projection fixture instead of proving `C -> D0` lineage from the replayed C output.
7. Context does not prove the complete B0/B1/B2/Membership/Core/Native/BaseSeed dependency set.
8. No per-edge ledger proves that all accepted owner edges were executed or explicitly degraded.

Therefore current `FULL_DAG_PERSISTED_REPLAY = PASS_LOCAL` is an overclaim.

## P0 G02｜Oracle Checks Node Labels, Not Frozen Edge Coverage

`Oracle.manifest()` verifies the 10 coarse trace labels, but does not independently compare emitted replay edges against:

```text
config/v4_14_temporal_non_edge_registry_v1_1.json
  owner_edges
  replay_required_edges
```

A replay can omit B0/B2/Context producer edges and still pass.

Required invariant:

```text
EXPECTED_APPLICABLE_EDGE_SET
==
EXECUTED
∪ DEGRADED_ACCEPTED_CAPABILITY
∪ NOT_APPLICABLE_BY_FROZEN_CONTRACT
```

with exact producer/consumer/field/time_role/owner authority.

## P1 G03｜R18B Final Evidence Authority Is Ambiguous

`reports/r18b/full_dag_gate.json` still points to the older `full_dag/` attempt, while the final seal points to `full_dag_r3/`.

Old attempts may remain immutable, but the repaired round must create one canonical final gate and every downstream oracle/seal must bind that same gate.

## Repair Boundary

Do not reopen:
- R18A vector runtime;
- cross-process process machinery;
- r1/r2 predecessor logic;
- deterministic replay;
- accepted V4-08..V4-13 business algorithms;
- R17R1 authority closure;
- real evidence-class boundaries.

Do not rewrite old replay attempts.

## Authorized Next Round

```text
R18R1A
Owner-edge Complete Replay Harness

R18R1B
Cross-process Full-DAG R4 + Canonical Evidence Authority

R18R1C
Independent Edge Oracle + Real Scoped Recheck + Clean Seal

STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

Only after R18R1 external audit may V4-14 promotion be considered.
