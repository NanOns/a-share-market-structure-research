# R18R1C｜Independent Edge Oracle + Real Scoped Recheck + Clean Seal｜2026-10-03

## 0. Entry
Execute only after R18R1A/B pass locally.

## 1. Goal
Repair the Full-DAG oracle completeness gap and seal a new V4-14 runtime candidate for external audit.

## 2. Independent Expected Edge Set
The oracle must read the frozen V4-14 DAG contract directly and independently construct:
```text
EXPECTED_OWNER_EDGE_SET
EXPECTED_REPLAY_REQUIRED_EDGE_SET
```

It must not use the runtime-emitted edge list as its expectation source.

## 3. Edge Equality
For every replay publication require:
```text
EXPECTED_APPLICABLE_EDGE_SET
==
EXECUTED
∪ DEGRADED_ACCEPTED_CAPABILITY
∪ NOT_APPLICABLE_BY_FROZEN_CONTRACT
```

Reject:
- missing B0;
- missing B2;
- missing Membership->Context;
- missing D1(T-1)->D1;
- missing Context producer;
- unexpected edge;
- wrong producer;
- wrong consumer;
- wrong field;
- wrong time_role;
- stale owner authority;
- hard-coded downstream substitute without frozen producer evidence.

## 4. Mandatory New Perturbations
In addition to the existing perturbations, add at minimum:
```text
delete_B0_edge
delete_B2_edge
delete_membership_context_edge
delete_D1_T_MINUS_1_edge
replace_B0_output_with_literal
replace_C_to_D0_lineage_with_unbound_fixture
wrong_edge_time_role
wrong_edge_owner_head
duplicate_edge_receipt
unexpected_feedback_edge
```

Every mutation must be rejected.

## 5. KEEP Existing Oracle
Keep:
- 60 vectors / 17 dimensions;
- state/hysteresis/expiry independent recomputation;
- event logical-key checks;
- episode continuity;
- deterministic replay;
- same-day predecessor;
- real OS process-boundary checks;
- historical-PIT rejection.

## 6. Real Accepted-source Recheck
The existing real accepted-source evidence class is KEEP in meaning.

Re-run/read back only as necessary to bind the new R18R1 seal.

Preserve:
```text
REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED
AS_RECORDED = false
knowledge_lineage = RECONSTRUCTED_CORRECTED
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED
```

Synthetic edge completeness must not upgrade real historical evidence.

## 7. Clean Detached Regression
Run from a clean detached implementation source:
- relevant V4-08..V4-13 owner tests;
- R17/R17R1 governance and active-family tests;
- all V4-14 v1.1 contract tests;
- R18A vector runtime tests;
- existing R18B process tests;
- new R18R1 edge-completeness tests;
- new edge-oracle perturbation tests.

No broad deselection.

## 8. Protected
Must remain byte-identical:
- `AGENTS.md`
- `data/v4/V4_DATA_ACCEPTED_HEAD.json`
- `data/v4/V4_12_ACCEPTED_HEAD.json`
- `data/v4/V4_13_ACCEPTED_HEAD.json`
- `data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json`
- `data/v4/V4_STAGE_ACCEPTED_HEAD.json`

No promotion in R18R1.

## 9. Final Candidate Seal
The new R18R1 seal must bind:
- tested implementation SHA;
- canonical r4 Full-DAG gate;
- edge-completeness summary;
- process receipts;
- same-day revision receipt;
- deterministic receipt;
- independent edge oracle;
- real scoped gate;
- evidence classes;
- regression totals;
- protected-head digests.

## 10. Allowed Final State
```text
R18R1C_INDEPENDENT_EDGE_ORACLE = PASS_LOCAL
OWNER_EDGE_COMPLETENESS = PASS

R18_REAL_ACCEPTED_SOURCE_REPLAY = PASS_CAPABILITY_SCOPED
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED

V4_14_RUNTIME_CANDIDATE = READY_FOR_EXTERNAL_AUDIT_R18R1

V4_14_ACCEPTED_HEAD = NOT_CREATED
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_13_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30

ALGORITHM_STATE_REPLAY_PASS = NOT_GRANTED_PENDING_EXTERNAL_AUDIT

NEXT = STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

Unified commit + push, then STOP.
