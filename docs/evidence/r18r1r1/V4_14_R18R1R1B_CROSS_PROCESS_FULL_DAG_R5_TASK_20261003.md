# R18R1R1B｜Cross-process Full-DAG R5 Replay + Canonical Gate｜2026-10-03

## 0. Entry
Require:
`R18R1R1A_PREEXEC_EDGE_BINDING = PASS_LOCAL`

## 1. New Namespace
Create:
`reports/v4_14_replay_r18/full_dag_r5/`

Do not modify r4 or older attempts.

Disposition:
```text
full_dag/r2/r3 = historical
full_dag_r4 = superseded by consumption-truth repair
full_dag_r5 = current R18R1R1 candidate
```

## 2. Re-run Complete Cross-process Trajectory
Reuse the accepted OS process launcher and 22-session trajectory.

Preserve:
- exact previous market session;
- producer exit before consumer start;
- distinct PID;
- no in-memory prior;
- r1/r2 exact same T-1;
- deterministic fresh-process repeat.

## 3. Invocation Evidence
Every r5 publication must contain immutable pre-execution node invocation envelopes.

For every `EXECUTED` edge:
```text
receipt producer_payload_digest
==
precall consumer_argument_digest
```

For every degraded edge:
- exact capability/degradation authority;
- actual UNKNOWN/degraded owner invocation path;
- no fabricated KNOWN payload.

## 4. Canonical Gate
Create:
`reports/r18r1r1b/final_full_dag_gate.json`

This gate must bind only r5.

Required:
```text
EXPECTED_EDGE_SET = 30 exact frozen edges
missing_edges = []
unexpected_edges = []
false_executed_edges = []
unbound_consumer_arguments = []
post_hoc_only_edges = []
```

## 5. Behavior KEEP
Re-prove:
- hysteresis;
- expiry;
- UNKNOWN pause;
- invalidation;
- reentry;
- structure lifecycle;
- event suppression;
- revision isolation;
- deterministic replay.

## 6. Completion
```text
R18R1R1B_CROSS_PROCESS_FULL_DAG_R5 = PASS_LOCAL
EDGE_CONSUMPTION_TRUTH = PASS
CANONICAL_FULL_DAG_GATE_R5 = CREATED
NEXT = R18R1R1C_CONSUMPTION_ORACLE
```

Continue directly to R18R1R1C.
