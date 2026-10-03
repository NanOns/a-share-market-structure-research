# R18R1R1 pre-call consumption repair

Baseline: `e07da98989fc9fa30ef2015d6ac4cd3d6e47b798`. Authority: the five byte-exact documents under `docs/evidence/r18r1r1`; the master is the scheduler. A, B, C execute sequentially, followed by clean detached validation, unified commit/push and STOP.

## Separate P0 audit items

| Item | Scope and repair | Independent evidence |
|---|---|---|
| G01 | Eliminate post-hoc evidence mirrors as EXECUTED authority | Persisted pre-call envelopes; callable executes on deserialized exact input; mutation guard and actual callback tests |
| G02 | F0 to D1 exact core_facts consumption | Frozen V4-12 defaults/vector projected into F0; exact dictionary supplied to ledger.observe; independent literal-book check |
| G03 | D0 to Event interface resolution | D0 exact confirmation row in pre-call Event envelope; validated against actual D2 CONFIRMED/scenario provenance before accepted D2 verification and state_events |
| G04 | Exact field projections | Frozen mapping contract; base_seed_primitives, stock_core, scalar seed/prewatch/confirmation, exact prior state and anchor event |
| G05 | Independent consumption oracle | Direct frozen expected edges plus frozen field mapping and accepted schemas; persisted envelope equality; producer/argument precision; temporal/order/authority checks |

These are local acceptance items, with independent external acceptance still pending. The original 30-edge expected set is unchanged.

## Invocation authority

The runtime publishes each invocation envelope atomically before the callback. It reads those exact bytes back, passes a copy of the frozen invocation_input to the callback, and rejects any argument mutation. Receipts derive from that persisted pre-call envelope and the subsequent output digest. No edge_inputs ledger is used.

Each record has prepared, call-start and output sequence positions, pinned owner authority, execution context, exact field references and a persisted invocation reference. Callable tests observe the envelope on disk before producer/consumer output exists. Logical positions and content-addressed references remain deterministic across fresh processes; they are not wall-clock latency claims.

The accepted algorithms are unchanged. Structure consumes F0's exact fixture core_facts, including the separated-session counter read from the exact previous publication. The read-only prior anchor-event validation precedes ledger execution.

The Event owner accepts D2 and frozen prior state, rather than an additional D0 business predicate. This interface difference is explicitly resolved in the mapping contract: the wrapper validates the exact D0 row against D2 input provenance before calling unchanged accepted verify_d2_publication/state_events. Bootstrap has no prior event comparison and emits no event; the prior dependency remains UNKNOWN/degraded. No event threshold or predicate changes.

## Capability degradation

Edges without a direct accepted interface or sufficient engineering native/history coverage use a pre-call capability gate with value=null and quality=UNKNOWN, exact upstream reference/digest and frozen owner head. The gate is validated before owner execution. B0/B1/B2 and Context receive the retained UNKNOWN native/history inputs; no upstream-known value is fabricated to satisfy a missing capability. D1 to D2 retains the accepted V4-11 V4-12 structure-support unavailable reason. A degraded receipt is evidence of this gate, not a claim that its upstream field became a direct owner argument.

## Current and historical evidence

Only `reports/r18r1r1b/final_full_dag_gate.json` is current Full-DAG authority, and it binds only r5. All four previous Full-DAG namespaces retain their original bytes. The initial A local proof is a superseded local development attempt; A completion_gate_r2 is the stage entry authority used by B. Each r5 process uses the original launcher and 22-session trajectory. r1/r2 share exact T-1; fresh identical r1 readback is deterministic.

The real accepted-source gate is read back without changing its meaning: REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED, AS_RECORDED=false, RECONSTRUCTED_CORRECTED, HISTORICAL_PIT_EFFECTIVENESS=NOT_GRANTED. Synthetic consumption truth does not upgrade real historical effectiveness.

## Final boundary

The candidate seal binds tested source SHA, clean regression evidence, r5 canonical gate, all invocation publications, independent oracle, real readback and protected-head digests. No V4-14 Accepted Head, Stage/Data advance, formal Replay Pass, production/shadow/focus, V4-15 or raw/provider fallback is authorized. Unrelated workspace files are preserved.

NEXT: STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT after unified commit and push.
