# R18R1B｜Cross-process Full-DAG R4 + Canonical Evidence Authority｜2026-10-03

## 0. Entry
Execute only after:
`R18R1A_OWNER_EDGE_COMPLETE_HARNESS = PASS_LOCAL`

## 1. Goal
Run a new append-only replay namespace, recommended:
`reports/v4_14_replay_r18/full_dag_r4/`

Do not modify:
- `full_dag/`
- `full_dag_r2/`
- `full_dag_r3/`

They remain immutable historical attempts.

## 2. Cross-process Rules
Reuse the accepted process mechanics:
```text
T-1 child process
→ persist immutable publication
→ parent wait confirms exit
→ fresh T child process
→ exact persisted T-1 readback
```

For each adjacent replay pair require:
- different PID;
- `producer_exited=true`;
- `os_wait_completed=true`;
- consumer starts after producer exit;
- `in_memory_prior=false`;
- exact previous market session;
- exact previous manifest path/hash/bytes.

## 3. Same-day Revision
For target T:
```text
T r1 previous = exact T-1
T r2 previous = exact same T-1
```

Forbidden:
`T r2 previous = T r1`

Revision must not create duplicate state/event/episode identity.

## 4. Full Edge Execution
Every replay publication must contain:
```text
edge_receipts[]
edge_completeness
```

The final r4 gate must prove closure of the frozen owner-edge set.

A 10-node coarse trace is supplementary only and cannot prove Full-DAG completeness.

## 5. Required Behavioral Trajectory
Retain the valid R18 lifecycle proofs:
- hysteresis first evaluable downgrade held;
- second evaluable session permits downgrade;
- expiry threshold reached only on evaluable sessions;
- UNKNOWN pauses counters per owner contract;
- hard invalidation;
- reentry / parent episode;
- support TESTING / RECLAIMED / RETESTING / BROKEN / UNKNOWN;
- persistent confirmation suppression;
- same-day revision isolation;
- deterministic fresh-process rerun.

## 6. Canonical Evidence Authority
Create one canonical stage-level gate, recommended:
`reports/r18r1b/final_full_dag_gate.json`

Create explicit attempt disposition:
```text
full_dag    = SUPERSEDED_R18_ATTEMPT
full_dag_r2 = SUPERSEDED_R18_ATTEMPT
full_dag_r3 = SUPERSEDED_BY_R18R1_EDGE_COMPLETE_REPLAY
full_dag_r4 = CURRENT_R18R1_CANDIDATE
```

All old bytes remain immutable.

All downstream R18R1C oracle/seal artifacts must bind only the canonical r4 gate.

## 7. Independent Persisted Validator
Independently recompute:
- edge-set equality;
- exact owner authority;
- exact producer/consumer/field/time_role;
- exact T/T-1 source date;
- previous-session chain;
- process ordering;
- append-only revisions;
- no raw/provider fallback;
- state/event/episode identity.

## 8. Completion
```text
R18R1B_CROSS_PROCESS_FULL_DAG_R4 = PASS_LOCAL
CROSS_PROCESS_PREVIOUS_SESSION = PASS
SAME_DAY_REVISION_ISOLATION = PASS
OWNER_EDGE_COMPLETENESS = PASS
CANONICAL_FULL_DAG_GATE = CREATED
NEXT = R18R1C_INDEPENDENT_EDGE_ORACLE
```

Continue directly to R18R1C.
