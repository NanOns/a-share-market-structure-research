# V4 R18R1R1R1 Final Independent External Audit R1｜2026-10-03

## 1. Audit Target

- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- Audited remote HEAD: `f4ad7d632e53734798c064f011e2b53ecd99bc27`
- Execution baseline: `f7b3402e4fbd5c98f4e76e3a56042a84960e120a`
- Clean-tested implementation source: `04b310c2b011dbeb99dd1c2430165201917dd328`
- Final seal commit: `f4ad7d632e53734798c064f011e2b53ecd99bc27`

## 2. Unique Decision

```text
R18R1R1R1_EXTERNAL_AUDIT =
PASS_FINAL_V4_14_RUNTIME_CAPABILITY_SCOPED

R18R1R1_PRECALL_CONSUMPTION = PASS_KEEP
R18R1R1_EDGE_CONSUMPTION_TRUTH = PASS_KEEP
R18R1R1_CROSS_PROCESS_R5 = PASS_KEEP
R18R1R1_CANONICAL_R5_GATE = PASS_KEEP
R18R1R1_INDEPENDENT_CONSUMPTION_ORACLE = PASS_KEEP

R18R1R1R1_V4_14_ROLLBACK_DRILL = PASS
R18R1R1R1_INDEPENDENT_ROLLBACK_ORACLE = PASS
V4_14_ROLLBACK_RECEIPT = PASS

REAL_ACCEPTED_SOURCE_REPLAY = PASS_CAPABILITY_SCOPED
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED

V4_14_RUNTIME_CANDIDATE =
EXTERNALLY_ACCEPTED_READY_FOR_PROMOTION

V4_14_ACCEPTED_HEAD_PROMOTION = AUTHORIZED
V4_15_CONTRACT_FIRST_ENTRY = AUTHORIZED_AFTER_PROMOTION_GATE_PASS
```

## 3. Rollback Drill

Canonical receipt:

`reports/r18r1r1r1a/V4_14_ROLLBACK_RECEIPT.json`

SHA-256:

`7035c130027ecaef2f5443cea05c64f328081b01abf839ec98ed34828a43bc5c`

The drill covers eight required scenarios.

### RB01
Failure before activation. No candidate activation occurred; first and second rollback are idempotent.

### RB02
Candidate activated only inside the sandbox, then failure injected; first rollback restored the exact predecessor and second rollback was idempotent.

### RB03
Stale predecessor CAS rejected activation.

### RB04
Mutated candidate digest rejected activation.

### RB05
Candidate activated, then mutated parent/archive evidence was rejected; subsequent rollback with the exact parent restored the predecessor.

### RB06
Second post-activation fault path restored the exact predecessor and proved repeated rollback idempotency.

### RB07
All frozen `full_dag_r5`, invocation, canonical gate, prior runtime seal, consumption oracle and related candidate artifacts remain append-only and byte-identical.

### RB08
The real protected heads are identical before and after the entire drill.

## 4. Rollback Implementation Boundary

`src/workbench_analysis/v4_14_candidate_rollback_drill.py` is sandbox-only.

The sandbox path is restricted to:

`reports/r18r1r1r1a/sandbox/`

It rejects path escape, uses an exclusive CAS lock, verifies candidate evidence before activation/rollback, requires the exact predecessor bytes, rejects unrelated current-head state, and restores only the exact parent archive.

No real accepted head is modified by the drill.

## 5. Independent Rollback Oracle

Oracle source:

`scripts/v4_14_rollback_oracle.py`

The oracle derives expected protected heads, candidate artifacts and predecessor bytes directly from audited Git baseline:

`f7b3402e4fbd5c98f4e76e3a56042a84960e120a`

It does not import or call the rollback implementation to generate expected results.

It independently verifies:

- exact predecessor authority;
- no real `V4_14_ACCEPTED_HEAD`;
- protected heads unchanged;
- sandbox isolation;
- activation CAS;
- exact rollback bytes;
- candidate evidence preservation;
- rollback idempotency;
- failure-receipt completeness;
- permission boundary.

The negative suite covers 14 mandatory mutations plus 6 permission mutations.

## 6. Regression

Clean detached regression was executed against:

`04b310c2b011dbeb99dd1c2430165201917dd328`

Result:

```text
1168 passed
0 failed
0 errors
0 skipped
0 deselected
```

The final seal commit only adds clean-regression evidence and the final candidate seal. It does not alter implementation source.

## 7. Protected State

Current formal state remains:

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_13_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_14_ACCEPTED_HEAD = NOT_CREATED
ALGORITHM_STATE_REPLAY_PASS = NOT_GRANTED_PENDING_EXTERNAL_AUDIT
Production = false
Shadow = false
Focus = false
```

The following protected files remain byte-identical to the audited baseline:

- `AGENTS.md`
- `data/v4/V4_DATA_ACCEPTED_HEAD.json`
- `data/v4/V4_12_ACCEPTED_HEAD.json`
- `data/v4/V4_13_ACCEPTED_HEAD.json`
- `data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json`
- `data/v4/V4_STAGE_ACCEPTED_HEAD.json`

## 8. Evidence Scope

The historical effectiveness limitation is retained:

```text
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED
```

This does not block engineering Replay Gate B acceptance. It must remain explicit in the future Accepted Head.

Therefore the authorized promotion semantics are capability-scoped/degraded:

```text
ALGORITHM_STATE_REPLAY_PASS = DEGRADED_PASS_CAPABILITY_SCOPED
```

This must not be rewritten as an unqualified historical-effectiveness PASS.

## 9. Promotion Authorization

The next round may create:

`data/v4/V4_14_ACCEPTED_HEAD.json`

and advance:

```text
V4_STAGE_ACCEPTED_HEAD:
V4_00_TO_V4_13_ACCEPTED
→ V4_00_TO_V4_14_ACCEPTED
```

The Data Head remains `2026-09-30`.

The promotion must bind the exact externally audited rollback-complete seal and preserve all upstream accepted heads.

No production/shadow/focus permission is granted by V4-14 promotion.

## 10. V4-15 Entry Authorization

After the V4-14 promotion gate passes locally, V4-15 may enter **contract-first design/freeze only**.

No V4-15 runtime, database migration, Radar publication, Cohort enrollment or Settlement execution is authorized until the complete V4-15 contract package is independently sealed and externally audited.

Authorized next sequence:

```text
R19A V4-14 Accepted Head Promotion
→
R19B V4-15 Radar / Cohort Contract Freeze
  and
R19C V4-15 Settlement / Benchmark / Controls Contract Freeze
→
R19D V4-15 Contract Integration + Independent Completeness Oracle
→
unified commit + push
→
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```
