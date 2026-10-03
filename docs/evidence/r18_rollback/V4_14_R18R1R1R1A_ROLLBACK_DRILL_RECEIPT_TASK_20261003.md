# R18R1R1R1A｜V4-14 Candidate Rollback Drill / Receipt｜2026-10-03

## 0. Baseline

Execute from remote HEAD:

```text
f7b3402e4fbd5c98f4e76e3a56042a84960e120a
```

Read:
- `V4_R18R1R1_INDEPENDENT_EXTERNAL_AUDIT_R3_20261003.md`
- this task card
- `V4_NEXT_ROUND_EXECUTION_MASTER_R18R1R1R1_20261003.md`

## 1. KEEP / Frozen Work

Do not reopen:
- R18A 60 vectors / 17 dimensions;
- frozen V4-14 v1.1 package;
- `full_dag_r5`;
- 30-edge expected set;
- pre-call consumption mapping;
- R18R1R1 cross-process process boundary;
- same-day r1/r2 predecessor behavior;
- deterministic replay;
- consumption oracle;
- real accepted-source capability-scoped replay;
- V4-08..V4-13 business algorithms.

## 2. Goal

Satisfy the explicit V4-14 runtime completion requirement:

```text
rollback_receipt
```

without promoting V4-14.

The drill must prove that a failed V4-14 candidate activation can be isolated and reverted to the exact currently accepted V4-13 predecessor.

## 3. No Real Head Mutation

The drill must never mutate the actual repository files:

```text
data/v4/V4_STAGE_ACCEPTED_HEAD.json
data/v4/V4_DATA_ACCEPTED_HEAD.json
data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json
```

Perform activation/rollback only in:
- a temporary detached root; or
- a dedicated rollback-drill sandbox under `reports/`.

The sandbox must start from exact copied bytes of the current accepted Stage Head.

## 4. Reuse Existing Governance Semantics

Do not invent a second promotion model.

Reuse the same governance semantics already used by accepted promotion flows such as R17B:

```text
frozen predecessor
exact-byte bindings
append-only candidate evidence
atomic head write / compare-and-swap semantics
fail-closed digest checks
parent Stage archive
```

A test-only sandbox adapter is allowed only to isolate writes; it must preserve the same predecessor/hash/CAS invariants.

## 5. Rollback State Model

Initial authoritative state:

```text
accepted_stage_range = V4_00_TO_V4_13_ACCEPTED
V4_14_ACCEPTED_HEAD = absent
ALGORITHM_STATE_REPLAY_PASS = NOT_GRANTED
```

Candidate evidence:

```text
reports/r18r1r1c/V4_14_RUNTIME_CANDIDATE_R18R1R1_SEAL.json
reports/r18r1r1b/final_full_dag_gate.json
reports/v4_14_replay_r18/full_dag_r5/
```

The sandbox may create a simulated candidate activation pointer/head only inside the drill sandbox.

It must not create:

```text
data/v4/V4_14_ACCEPTED_HEAD.json
```

in the real repository.

## 6. Mandatory Scenarios

### RB01 Failure Before Activation
Inject failure after candidate validation but before sandbox activation.

Required:
```text
sandbox head == exact predecessor
no partial candidate authority
```

### RB02 Failure After Sandbox Activation
Activate candidate in sandbox using exact predecessor CAS, inject failure before simulated acceptance completion, then rollback.

Required:
```text
post-rollback sandbox head bytes == pre-drill predecessor bytes
```

### RB03 Stale Predecessor CAS
Supply wrong predecessor digest/revision.

Required:
```text
activation rejected
head unchanged
```

### RB04 Candidate Mutation
Change candidate path/hash/bytes in the test copy.

Required:
```text
candidate validation rejected
activation forbidden
```

### RB05 Predecessor Mutation
Change copied predecessor bytes after snapshot but before rollback.

Required:
```text
rollback fails closed
wrong predecessor is never accepted
```

### RB06 Repeated Rollback
Run rollback twice.

Required:
```text
second rollback idempotent
authoritative predecessor unchanged
```

### RB07 Append-only Candidate Evidence
After rollback, verify r5 candidate artifacts, invocation evidence, canonical gate and candidate seal remain exact-byte unchanged.

Rollback must not delete evidence.

### RB08 Real Protected Heads
Before and after all sandbox scenarios, hash/read back the real protected heads.

Required:
```text
all byte-identical
```

## 7. Canonical Receipt

Create one canonical receipt, recommended:

```text
reports/r18r1r1r1a/V4_14_ROLLBACK_RECEIPT.json
```

It must contain at least:

```text
contract_id
stage_id
capability_scope

execution_baseline
candidate_seal
canonical_r5_gate
v4_14_contract_package

previous_accepted_head
previous_accepted_head_archive

scenarios[]
rollback_authority
rollback_action
rollback_result

affected_dates
affected_entities
affected_fields
reason_codes
evidence_digests

protected_heads_before
protected_heads_after

candidate_artifacts_preserved
idempotent
production = false
shadow = false
focus = false

next_action
```

Also include all required failure-receipt fields from:

```text
CAPABILITY_CUTOVER_AND_ROLLBACK_V1
```

## 8. Rollback Meaning

Successful rollback means:

```text
prior accepted Stage Head remains authoritative
candidate is non-active
candidate evidence remains immutable
no partial V4-14 acceptance exists
```

It does not mean deleting r5.

## 9. Negative Tests

At minimum reject:

```text
wrong predecessor digest
wrong candidate digest
sandbox activation without exact predecessor
rollback to non-parent bytes
rollback after candidate evidence mutation
rollback receipt missing previous_accepted_head
rollback receipt missing reason_codes
rollback claiming production permission
rollback that deletes candidate artifacts
real Stage Head mutation during drill
```

## 10. Completion Gate

Required local state:

```text
R18R1R1R1A_V4_14_ROLLBACK_DRILL = PASS_LOCAL
V4_14_ROLLBACK_RECEIPT = CREATED
ROLLBACK_TO_EXACT_V4_13_PREDECESSOR = PASS
REAL_PROTECTED_HEADS_UNCHANGED = PASS
CANDIDATE_EVIDENCE_APPEND_ONLY = PASS

V4_14_ACCEPTED_HEAD = NOT_CREATED
ALGORITHM_STATE_REPLAY_PASS = NOT_GRANTED_PENDING_EXTERNAL_AUDIT

NEXT = R18R1R1R1B_INDEPENDENT_ROLLBACK_ORACLE
```

Continue directly to R18R1R1R1B.
