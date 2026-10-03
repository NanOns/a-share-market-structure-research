# R19A｜V4-14 Accepted Head Promotion｜2026-10-03

## 0. Baseline

Execute from remote HEAD:

`f4ad7d632e53734798c064f011e2b53ecd99bc27`

Read:
- `V4_R18R1R1R1_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md`
- this task card
- `V4_NEXT_ROUND_EXECUTION_MASTER_R19_20261003.md`

## 1. Goal

Promote the exact externally audited V4-14 rollback-complete runtime candidate.

Create:
`data/v4/V4_14_ACCEPTED_HEAD.json`

Advance only:
`data/v4/V4_STAGE_ACCEPTED_HEAD.json`

from:
`V4_00_TO_V4_13_ACCEPTED`

to:
`V4_00_TO_V4_14_ACCEPTED`

Do not advance Data Head.

## 2. Exact Promotion Authority

Bind exact:
- audited remote HEAD `f4ad7d632e53734798c064f011e2b53ecd99bc27`;
- tested implementation source `04b310c2b011dbeb99dd1c2430165201917dd328`;
- external audit document;
- `reports/r18r1r1r1b/V4_14_RUNTIME_CANDIDATE_ROLLBACK_COMPLETE_SEAL.json`;
- `reports/r18r1r1c/V4_14_RUNTIME_CANDIDATE_R18R1R1_SEAL.json`;
- `reports/r18r1r1b/final_full_dag_gate.json`;
- `reports/r18r1r1c/independent_consumption_oracle_gate.json`;
- `reports/r18r1r1r1a/V4_14_ROLLBACK_RECEIPT.json`;
- `reports/r18r1r1r1b/independent_rollback_oracle_gate.json`;
- V4-14 v1.1 contract package;
- `data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json`;
- current Data Head and calendar/membership authorities.

No “latest” scanning.

## 3. Formal Accepted Entry Contract

Create:
`config/v4_14_accepted_entry_contract_v1.json`

It must freeze:
- exact accepted-head namespace;
- exact rollback-complete candidate seal;
- exact V4-14 contract package;
- exact V4-13 amended predecessor;
- exact Data Head;
- exact evidence classes;
- capability degradation;
- historical PIT limitation;
- no production/shadow/focus permission.

## 4. Accepted Head Semantics

Required high-level status:

```text
stage = V4-14
status = ALGORITHM_STATE_REPLAY_DEGRADED_PASS
external_acceptance = EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED
ALGORITHM_STATE_REPLAY_PASS = DEGRADED_PASS_CAPABILITY_SCOPED
```

Capabilities must explicitly distinguish at least:

```text
ENGINEERING_SYNTHETIC_REPLAY = FULL_PASS
FULL_D0_D1_D2_REPLAY = ENGINEERING_ACCEPTED
EDGE_CONSUMPTION_TRUTH = PASS
CROSS_PROCESS_PREVIOUS_SESSION = PASS
SAME_DAY_REVISION_ISOLATION = PASS
DETERMINISTIC_REPLAY = PASS
ROLLBACK_RECEIPT = PASS
REAL_ACCEPTED_SOURCE_REPLAY = PASS_CAPABILITY_SCOPED
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED
REAL_SIGNAL_CAPABILITY = DEGRADED_BY_ACCEPTED_UPSTREAM_CAPABILITY
```

Do not use an unqualified historical/full-market effectiveness PASS.

## 5. Stage Head Update

Archive the exact current Stage Head before mutation.

Then update:
- `accepted_stage_range = V4_00_TO_V4_14_ACCEPTED`
- `v4_14_binding = exact V4_14 accepted head`
- `v4_14_status = ALGORITHM_STATE_REPLAY_DEGRADED_PASS`
- `v4_14_external_acceptance = exact external audit decision`
- `v4_14_capabilities = exact accepted capabilities`
- `v4_15_entry = CONTRACT_FREEZE_AUTHORIZED_RUNTIME_NOT_AUTHORIZED`

Preserve all unrelated pre-existing Stage Head fields byte/semantic-equivalently.

## 6. Protected Files

Must remain byte-identical:
- `AGENTS.md`
- `data/v4/V4_DATA_ACCEPTED_HEAD.json`
- all V4-01..V4-13 Accepted Heads;
- especially V4-12, original V4-13 and amended V4-13.

## 7. Promotion Gate

Independent promotion validator must not import the promotion writer.

It must verify:
- exact external audit;
- exact candidate seal;
- exact rollback receipt/oracle;
- exact parent Stage Head;
- exact amended V4-13 predecessor;
- exact Data Head unchanged;
- accepted range exactly V4_00_TO_V4_14_ACCEPTED;
- no historical PIT overclaim;
- no production/shadow/focus/V4-15 runtime permission.

## 8. Negative Cases

Reject:
- wrong audited HEAD;
- wrong tested-source SHA;
- stale Stage predecessor;
- old V4-13 original head used instead of amended head;
- missing rollback receipt;
- wrong rollback seal;
- old full_dag attempt instead of r5;
- historical PIT upgraded to PASS;
- Data Head moved;
- Production/Shadow/Focus enabled;
- V4-15 runtime authorized before contract package freeze.

## 9. Completion

Required:

```text
R19A_V4_14_PROMOTION = PASS_LOCAL
V4_14_ACCEPTED_HEAD = CREATED
ALGORITHM_STATE_REPLAY_PASS = DEGRADED_PASS_CAPABILITY_SCOPED
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_14_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30

Production = false
Shadow = false
Focus = false
V4_15_RUNTIME = NOT_AUTHORIZED

NEXT = R19B_R19C_V4_15_CONTRACT_FREEZE
```

Continue only if the promotion gate passes.
