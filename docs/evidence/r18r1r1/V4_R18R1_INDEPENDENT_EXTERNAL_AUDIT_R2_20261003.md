# V4 R18R1 Independent External Audit R2｜2026-10-03

## 1. Audit Target
- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- Audited remote HEAD: `e07da98989fc9fa30ef2015d6ac4cd3d6e47b798`
- R18R1 baseline: `70fc9b050497e798d077480d0ae4adf97e9824c6`
- Clean tested implementation source: `55c4356e24102862c5c0edd08c785c28a3efc4ec`

## 2. Unique Decision

```text
R18R1_EXTERNAL_AUDIT =
PARTIAL_PASS_RUNTIME_EDGE_CONSUMPTION_REPAIR_REQUIRED

R18R1A_EDGE_SET_CLOSURE = PASS_KEEP
R18R1B_CROSS_PROCESS_R4 = PASS_KEEP
R18R1B_CANONICAL_GATE = PASS_KEEP
R18R1C_EXPECTED_EDGE_ORACLE = PASS_KEEP

R18R1_RUNTIME_EDGE_CONSUMPTION = FAIL_P0
R18R1_EDGE_RECEIPT_EXECUTION_TRUTH = FAIL_P0

REAL_ACCEPTED_SOURCE_REPLAY = PASS_KEEP_CAPABILITY_SCOPED
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED_KEEP

V4_14_RUNTIME_CANDIDATE = REPAIR_REQUIRED_BEFORE_PROMOTION

V4_14_ACCEPTED_HEAD = NOT_CREATED
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_13_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
ALGORITHM_STATE_REPLAY_PASS = NOT_GRANTED
```

## 3. PASS / KEEP

The previous P0 “missing frozen edges” defect is materially repaired:

- 24 frozen owner edges and 6 replay-required edges are independently derived from the accepted DAG;
- `full_dag_r4` is the unique current candidate;
- old `full_dag`, `full_dag_r2`, `full_dag_r3` remain immutable historical attempts;
- missing/unexpected edge sets are empty;
- cross-process T-1→T mechanics remain valid;
- same-day r1/r2 predecessor isolation remains valid;
- deterministic fresh-process replay remains valid;
- independent oracle does not derive the expected edge set from runtime output;
- 1095 clean detached tests pass with 0 fail/error/skip/deselect;
- real accepted-source evidence remains capability-scoped and does not overclaim historical PIT.

These items are KEEP.

## 4. P0 G01｜Receipts Are Added After Consumer Execution

In `src/workbench_analysis/v4_14_owner_edge_runtime.py`, owner nodes are first computed by `prepare()` / legacy replay.

Only after all consumer outputs exist does the code iterate through the frozen edges and execute:

```text
consumer.setdefault('edge_inputs', {})[edge_id] = producer_source
```

The edge receipt then points to this post-hoc `edge_inputs` echo.

Therefore the current invariant proves:

```text
producer source
==
post-hoc consumer evidence ledger copy
```

but does not generally prove:

```text
producer source
was actually consumed by the owner invocation
that generated consumer.output
```

A receipt may therefore be byte-consistent while not representing runtime dataflow.

## 5. P0 G02｜Concrete False EXECUTED Edge: F0 -> D1 core_facts

The frozen DAG requires:

```text
F0 -> D1
field = core_facts
time_role = T
```

R18R1 marks it:

```text
status = EXECUTED
execution_mode = EXACT_FROZEN_FIXTURE_PRODUCER
```

But D1 is still computed in `v4_14_full_dag.py` from the V4-12 frozen structure-vector inputs:

```text
structural_inputs =
machine_vector.defaults + selected_vector.inputs
ledger.observe(...)
```

The D1 invocation does not consume `nodes['F0']['output']` or an exact `core_facts` projection from it.

After D1 has already been calculated, the generic receipt loop copies the F0 output into:

```text
D1.edge_inputs[edge_id]
```

This is evidence bookkeeping, not execution lineage.

Therefore `F0 -> D1 = EXECUTED` is currently false.

## 6. P0 G03｜Concrete False EXECUTED Edge: D0 -> EVENT_DIFF confirmation_facts

The replay-required DAG declares:

```text
D0 -> EVENT_DIFF
field = confirmation_facts
time_role = T
```

R18R1 marks the edge `EXECUTED`.

But current event execution is effectively:

```text
state_events(d2, frozen_prior_state)
```

The D0 confirmation output is not supplied as a direct event-diff invocation input.

Again, the receipt is populated after computation through the generic `edge_inputs` ledger.

So this edge is also not proven as an actual consumed runtime dependency.

## 7. P0 G04｜Receipt Payloads Are Often Whole-node Echoes, Not Exact Field Payloads

Examples include:

```text
F0 -> A :: base_seed_primitives
F0 -> C :: stock_core
A  -> C :: base_seed_raw
D0 -> D2 :: confirmation
C  -> D2 :: stock_raw
```

The receipt `input_ref` commonly points to the full producer node output, while the actual owner invocation consumes only a nested field/scalar/projection.

Independent checks partially validate several mappings, but the formal receipt still does not identify the exact payload consumed by the call.

For a Replay Gate intended to prove owner-edge execution, the binding must be field-precise.

## 8. P0 G05｜Current Oracle Can Validate the Post-hoc Ledger

The new oracle correctly rejects missing/extra/wrong edges and checks several actual owner inputs.

However its generic edge proof resolves:

```text
receipt.input_ref
receipt.consumer_input_ref
```

and confirms they are equal.

Because `consumer_input_ref` points to the post-hoc `edge_inputs` copy, the oracle can accept a receipt whose producer payload never participated in the owner invocation.

The next oracle must validate a pre-execution invocation envelope, not a receipt-populated evidence mirror.

## 9. Repair Boundary

KEEP:
- frozen 30-edge expected set;
- edge identity / authority;
- full_dag_r4 history;
- cross-process launcher;
- r1/r2 rules;
- deterministic replay;
- vector runtime;
- business algorithms;
- real scoped evidence boundary.

Do not rewrite r4.

Create a new r5 candidate after fixing true consumption.

## 10. Authorized Next Round

```text
R18R1R1A
Pre-execution Edge Binding / Exact Field Consumption Repair

R18R1R1B
Cross-process Full-DAG R5 Replay + Canonical Gate

R18R1R1C
Independent Consumption Oracle + Clean Seal

STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

No V4-14 promotion is authorized in this repair round.
