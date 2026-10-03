# R18R1R1R1B｜Independent Rollback Oracle + Clean Seal｜2026-10-03

## 0. Entry

Execute only after:

```text
R18R1R1R1A_V4_14_ROLLBACK_DRILL = PASS_LOCAL
```

## 1. Goal

Independently prove the V4-14 rollback receipt is real and complete, then reseal the existing R18R1R1 runtime candidate for one final external audit.

No V4-14 promotion is authorized in this task.

## 2. Oracle Independence

The rollback oracle must not call the rollback implementation to derive expected results.

It must independently derive:

- exact current Stage Head bytes/digest;
- exact V4-13 predecessor authority;
- exact r5 candidate seal/gate;
- protected-head set;
- expected rollback target;
- allowed candidate-evidence retention;
- forbidden permissions.

## 3. Independent Checks

### RO01 Exact predecessor

The rollback target is the exact pre-drill:

```text
data/v4/V4_STAGE_ACCEPTED_HEAD.json
accepted_stage_range = V4_00_TO_V4_13_ACCEPTED
```

### RO02 No real V4-14 head

Reject if:

```text
data/v4/V4_14_ACCEPTED_HEAD.json
```

was created.

### RO03 Real heads unchanged

Recompute byte/hash equality for all protected heads.

### RO04 Sandbox isolation

All candidate activation/rollback writes are confined to the declared isolated sandbox.

### RO05 Activation CAS

Activation is accepted only when the sandbox predecessor exactly matches the frozen predecessor binding.

### RO06 Rollback exactness

After injected post-activation failure:

```text
post_rollback_bytes == predecessor_bytes
post_rollback_digest == predecessor_digest
```

### RO07 Candidate preservation

The r5 candidate seal, canonical gate, replay publications and pre-call invocation artifacts remain byte-identical.

### RO08 Idempotency

Second rollback does not change the restored predecessor.

### RO09 Failure receipt completeness

Validate all fields required by `CAPABILITY_CUTOVER_AND_ROLLBACK_V1`.

### RO10 Permission boundary

Receipt must not grant:

```text
production
shadow
focus
V4_15
Stage advance
Data advance
```

## 4. Mandatory Adversarial Mutations

Independently mutate copies and prove rejection for:

```text
wrong_predecessor_sha
wrong_predecessor_bytes
wrong_candidate_sha
candidate_missing
activation_with_stale_parent
rollback_to_wrong_parent
rollback_receipt_drops_reason_codes
rollback_receipt_drops_previous_head
rollback_receipt_claims_v4_14_accepted
rollback_receipt_claims_algorithm_replay_pass
rollback_deletes_candidate_evidence
rollback_mutates_real_stage_head
second_rollback_changes_bytes
sandbox_path_escape
```

## 5. Existing R18R1R1 KEEP Validation

Do not rerun expensive replay generation unless required.

The clean regression must include:

- relevant V4-08..V4-13 accepted owner tests;
- R17/R17R1 governance;
- V4-14 contract tests;
- R18/R18R1/R18R1R1 replay/oracle tests;
- new rollback tests.

No broad deselection.

## 6. Protected Files

Must remain byte-identical:

```text
AGENTS.md
data/v4/V4_DATA_ACCEPTED_HEAD.json
data/v4/V4_12_ACCEPTED_HEAD.json
data/v4/V4_13_ACCEPTED_HEAD.json
data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json
data/v4/V4_STAGE_ACCEPTED_HEAD.json
```

## 7. Final Seal

Create a new external-audit candidate seal, recommended:

```text
reports/r18r1r1r1b/V4_14_RUNTIME_CANDIDATE_ROLLBACK_COMPLETE_SEAL.json
```

It must bind:

- R18R1R1 runtime candidate seal;
- canonical r5 gate;
- independent consumption oracle;
- canonical rollback receipt;
- independent rollback oracle;
- negative mutation gate;
- clean detached regression;
- protected-head digests;
- real capability boundary.

## 8. Allowed Final State

```text
R18R1R1R1B_INDEPENDENT_ROLLBACK_ORACLE = PASS_LOCAL

V4_14_ROLLBACK_RECEIPT = PASS
EDGE_CONSUMPTION_TRUTH = PASS
R18_REAL_ACCEPTED_SOURCE_REPLAY = PASS_CAPABILITY_SCOPED
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED

V4_14_RUNTIME_CANDIDATE =
READY_FOR_FINAL_EXTERNAL_AUDIT_WITH_ROLLBACK

V4_14_ACCEPTED_HEAD = NOT_CREATED
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_13_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30

ALGORITHM_STATE_REPLAY_PASS =
NOT_GRANTED_PENDING_EXTERNAL_AUDIT

Production = false
Shadow = false
Focus = false
V4_15 = false

NEXT = STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

Unified commit + push, then STOP.
