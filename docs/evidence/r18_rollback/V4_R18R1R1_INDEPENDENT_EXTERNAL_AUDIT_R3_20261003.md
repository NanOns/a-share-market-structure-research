# V4 R18R1R1 Independent External Audit R3｜2026-10-03

## 1. Audit Target

- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- Audited remote HEAD: `f7b3402e4fbd5c98f4e76e3a56042a84960e120a`
- R18R1R1 clean-tested source: `c1e8b1eba279335b1f9dc3e41aab6847bda8e4c2`
- Current formal Stage Head: `V4_00_TO_V4_13_ACCEPTED`
- Current Data Head trade date: `2026-09-30`

## 2. Unique Decision

```text
R18R1R1_EXTERNAL_AUDIT =
PARTIAL_PASS_ROLLBACK_RECEIPT_REQUIRED

R18R1R1_PRECALL_CONSUMPTION = PASS_KEEP
R18R1R1_EDGE_CONSUMPTION_TRUTH = PASS_KEEP
R18R1R1_CROSS_PROCESS_R5 = PASS_KEEP
R18R1R1_CANONICAL_R5_GATE = PASS_KEEP
R18R1R1_INDEPENDENT_CONSUMPTION_ORACLE = PASS_KEEP
R18R1R1_NEGATIVE_MUTATION_SUITE = PASS_KEEP
R18R1R1_CLEAN_REGRESSION = PASS_KEEP

REAL_ACCEPTED_SOURCE_REPLAY = PASS_KEEP_CAPABILITY_SCOPED
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED_KEEP

V4_14_ROLLBACK_RECEIPT = MISSING_P0

V4_14_RUNTIME_CANDIDATE =
TECHNICALLY_READY_EXCEPT_ROLLBACK_RECEIPT

V4_14_ACCEPTED_HEAD = NOT_CREATED
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_13_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
ALGORITHM_STATE_REPLAY_PASS = NOT_GRANTED
```

## 3. Accepted / KEEP

R18R1R1 materially repairs the prior execution-truth defect.

The runtime now performs:

```text
build invocation input
→ bind exact incoming edges
→ persist immutable PRECALL_FROZEN envelope
→ exact readback / deserialize
→ pass deserialized invocation_input into owner callback
→ reject callback mutation
→ compute output
→ derive receipt from pre-call binding + output digest
```

Exact field-consumption paths are now proven, including:

```text
F0.base_seed_primitives -> A.seed_facts
F0.stock_core -> C.stock_core
A.base_seed_state -> C.base_seed_raw
F0.core_facts -> D1.core_facts
D0.confirmation_status -> D2.values.CONFIRMED
C.raw_qualification -> D2.values.PREWATCH
D2(T-1).rows[0] -> D2.prior_state
D0.rows[0] -> EVENT_DIFF.confirmation_facts
D2 -> EVENT_DIFF.d2_publication
D2(T-1) -> EVENT_DIFF.prior_d2_publication
D3_CONTEXT -> D3.context
D2 -> GATE_B.state
D3 -> GATE_B.profile
```

D1 now actually consumes frozen `core_facts` in `ledger.observe()`. EVENT_DIFF binds D0 confirmation facts before invocation and validates them against actual D2 provenance before executing the accepted event owner.

Where accepted upstream capability/history is unavailable, the replay now uses explicit pre-call UNKNOWN capability gates instead of false `EXECUTED` claims.

`full_dag_r5` preserves exact T-1 readback, different OS processes, producer exit before consumer start, r1/r2 same predecessor, and deterministic fresh-process replay.

Independent consumption oracle validates all 30 frozen edges and exact producer/consumer field mappings without importing the replay runtime for expected results.

Negative validation contains 11 new consumption attacks, 10 retained edge attacks, and 16 inherited attacks.

Clean detached regression:

```text
1142 passed
0 failed
0 errors
0 skipped
0 deselected
```

## 4. Historical PIT Is Not the Blocker

The V4.2.2 master contract explicitly states that historical-effect replay can only increase its evidence grade when price/universe/membership/source identity are provably PIT; otherwise it remains diagnostic.

Therefore:

```text
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED
```

does not by itself block an engineering/capability-scoped Replay Gate B acceptance.

This matches existing V4-05 governance, where Replay Gate A was formally accepted as `DATA_FACTOR_REPLAY_DEGRADED_PASS` while historical AS_RECORDED adjusted-price capability remained blocked.

A future V4-14 Accepted Head must preserve this limitation rather than upgrade it.

## 5. P0｜Active V4-14 Contract Explicitly Requires rollback_receipt

`config/v4_14_replay_gate_b_contract_v1_1.json` defines:

```text
runtime_completion_requirements = [
  all_dimension_independent_oracles,
  full_temporal_DAG_and_non_edges,
  actual_cross_process_persisted_readback,
  exact_same_previous_session_for_r1_r2,
  append_only_idempotent_revisions,
  capability_scoped_real_source_readback,
  temporal_leakage_matrix,
  deterministic_digests,
  rollback_receipt,
  independent_external_audit
]
```

The current R18/R18R1/R18R1R1 evidence covers the runtime requirements except:

```text
rollback_receipt
```

No V4-14-specific rollback receipt exists in the repository.

## 6. Existing Rollback Evidence Does Not Substitute

Existing files have different scopes:

- `docs/V4_00H_CAPABILITY_PERFORMANCE_ROLLBACK_20260925.md` freezes rollback policy but does not execute a V4-14 candidate rollback.
- `reports/audits/A09_SCHEMA_LEGACY_READBACK_AND_ROLLBACK_R1.json` proves V4-09 schema/legacy rollback.
- `reports/v4_07/V4_07_MIGRATION_ROLLBACK_TEST.json` proves migration 015 rollback in disposable PostgreSQL.

None binds the V4-14 r5 candidate, V4-14 contract package, or current Stage Head predecessor. They cannot satisfy this contract requirement.

## 7. Correct V4-14 Rollback Meaning

V4-14 has no Accepted Head and no production permission yet. Therefore this is not a production cutover rollback.

The correct drill is:

```text
exact accepted predecessor
V4_00_TO_V4_13_ACCEPTED
        ↓
isolated candidate activation simulation
using frozen predecessor / CAS governance
        ↓
fault injection
        ↓
rollback to exact predecessor bytes/digest
        ↓
prove actual accepted heads never changed
```

The r5 replay artifacts are immutable evidence and must not be deleted.

Rollback means:

```text
candidate is non-active/current
prior accepted head remains authoritative
failed candidate is retained/quarantined as evidence
no partial acceptance
```

## 8. Required Rollback Scenarios

At minimum:

```text
A. failure before activation
   -> predecessor unchanged

B. failure immediately after isolated candidate activation
   -> exact predecessor restored

C. stale predecessor / CAS mismatch
   -> activation rejected

D. candidate bytes/hash changed
   -> activation rejected

E. predecessor bytes/hash changed
   -> rollback rejected fail-closed

F. repeated rollback
   -> idempotent

G. candidate evidence after rollback
   -> byte-identical / append-only

H. actual repository protected heads
   -> byte-identical before and after drill
```

Protected real files include at least:

```text
AGENTS.md
data/v4/V4_DATA_ACCEPTED_HEAD.json
data/v4/V4_12_ACCEPTED_HEAD.json
data/v4/V4_13_ACCEPTED_HEAD.json
data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json
data/v4/V4_STAGE_ACCEPTED_HEAD.json
```

## 9. Receipt Fields

Follow `CAPABILITY_CUTOVER_AND_ROLLBACK_V1`:

```text
stage_id
contract_id
capability_scope
affected_dates
affected_entities
affected_fields
status
reason_codes
evidence_digests
previous_accepted_head
rollback_action
recovery_owner
next_action
```

The V4-14 receipt must also bind:

- exact canonical r5 gate;
- exact R18R1R1 candidate seal;
- exact V4-14 v1.1 package;
- exact predecessor Stage Head;
- isolated activation record;
- rollback result;
- post-rollback protected-head readback.

## 10. Authorized Next Round

```text
R18R1R1R1A
V4-14 Candidate Rollback Drill / Receipt

→

R18R1R1R1B
Independent Rollback Oracle + Clean Seal

→ unified commit + push

→ STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

No V4-14 promotion is authorized in this repair round.

If the next external audit passes, the following round may create the V4-14 Accepted Head, advance Stage Head to `V4_00_TO_V4_14_ACCEPTED`, grant a capability-scoped/degraded `ALGORITHM_STATE_REPLAY_PASS`, and authorize V4-15 contract-first entry.
