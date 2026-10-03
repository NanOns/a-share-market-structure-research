# R18R1R1A｜Pre-execution Edge Binding / Exact Field Consumption Repair｜2026-10-03

## 0. Baseline
Use remote HEAD:
`e07da98989fc9fa30ef2015d6ac4cd3d6e47b798`

## 1. KEEP
Do not reopen:
- 24 owner + 6 replay-required frozen edge identities;
- R18A 60-vector / 17-dimension runtime;
- R18/R18R1 cross-process launcher;
- V4-14 v1.1 contracts;
- accepted V4-08..V4-13 business algorithms;
- real evidence-class boundary;
- current formal heads.

## 2. Goal
An edge may be `EXECUTED` only if its exact field payload is bound before the owner call and participates in the invocation or frozen owner validation that produces the consumer output.

Post-hoc copying into `edge_inputs` is not execution proof.

## 3. Pre-execution Invocation Envelope
Before every owner invocation, build and freeze:

```text
node_id
owner authority
invocation_input
edge_bindings[]
invocation_input_digest
```

Each edge binding must include:

```text
edge_id
producer
consumer
field
time_role
producer_payload_ref
producer_payload_digest
consumer_argument_path
consumer_argument_digest
binding_mode
```

Required:

```text
producer payload == exact consumer argument payload
```

for `EXECUTED`.

The invocation envelope must exist before the owner function is called.

## 4. Receipt Generation Rule
Generate receipt only from the frozen pre-call invocation envelope plus post-call output digest.

Do not mutate consumer invocation inputs after owner execution.

Remove the pattern:

```text
consumer.edge_inputs[edge_id] = source
```

as proof of execution.

An optional diagnostics mirror may exist, but it cannot be the authority for `EXECUTED`.

## 5. Exact Field Projection
Receipts must bind the field actually consumed, not the entire producer node.

Examples:

```text
F0 -> A  base_seed_primitives
F0 -> C  stock_core
A -> C   base_seed_raw
D0 -> D2 confirmation
C -> D2  stock_raw
```

No whole-node digest may substitute for a field-level dependency unless the owner contract explicitly defines the whole node as the field payload.

## 6. F0 -> D1 Mandatory Repair
Current R18R1 incorrectly marks this edge EXECUTED.

Repair so that D1 is actually invoked from an exact frozen `core_facts` producer payload that is bound as F0 engineering fixture output before accepted owner structure execution.

Allowed:
- project exact frozen V4-12 vector inputs into an explicit F0 `core_facts` fixture payload;
- bind that exact payload into D1 invocation;
- cite the frozen fixture source.

Forbidden:
- calculate D1 independently, then copy F0 into the ledger afterward.

If the accepted owner interface cannot consume the frozen field without changing business semantics, do not label it EXECUTED. Use the exact contract-authorized degraded status and prove why.

## 7. D0 -> EVENT_DIFF Mandatory Repair
The frozen replay edge must be truthful.

Either:
1. bind exact D0 confirmation facts into a pre-execution event-diff envelope and have the accepted event owner validate/consume that binding before output generation; or
2. if the accepted event owner contract truly has no direct current D0 dependency, resolve the contract inconsistency explicitly rather than emitting a false EXECUTED receipt.

Do not redesign event business rules.

## 8. All EXECUTED Edges Audit
Mechanically audit every edge currently marked EXECUTED.

For each, prove:

```text
pre-call producer field payload
==
consumer invocation argument
```

or accepted read-only validation payload.

Any edge without this proof must not remain `EXECUTED`.

## 9. Degraded Edge Rule
For `DEGRADED_ACCEPTED_CAPABILITY`:
- bind exact upstream evidence/capability reason;
- do not fabricate a consumer argument;
- consumer must receive UNKNOWN/degraded input through the actual invocation path where the owner contract requires it;
- the receipt must not point to a post-hoc echo as if consumed.

## 10. Completion
```text
R18R1R1A_PREEXEC_EDGE_BINDING = PASS_LOCAL
EXECUTED_EDGE_CONSUMPTION_TRUTH = PASS_LOCAL
POST_HOC_EDGE_LEDGER_NOT_AUTHORITY = PASS
NEXT = R18R1R1B_FULL_DAG_R5
```

Continue directly to R18R1R1B.
