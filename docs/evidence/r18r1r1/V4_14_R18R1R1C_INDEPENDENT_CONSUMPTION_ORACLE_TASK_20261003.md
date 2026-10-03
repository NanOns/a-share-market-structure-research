# R18R1R1C｜Independent Consumption Oracle + Clean Seal｜2026-10-03

## 0. Entry
Execute after R18R1R1A/B local PASS.

## 1. Oracle Independence
Expected edges must still be derived directly from the frozen V4-14 DAG.

Expected consumed field mappings must be derived from:
- frozen owner contracts/interfaces;
- frozen fixture mapping contracts;
- accepted owner input schemas.

Do not derive expected consumption from runtime receipts.

## 2. Validate Pre-call Invocation
For each `EXECUTED` edge independently prove:
```text
exact producer field payload
==
exact pre-call consumer argument payload
```

and prove that the invocation envelope existed before the consumer output.

Do not use post-hoc `edge_inputs` as consumption evidence.

## 3. Required New Adversarial Tests
At minimum:

```text
F0_D1_receipt_present_but_D1_argument_unbound
D0_EVENT_receipt_present_but_event_argument_unbound
F0_A_whole_node_substituted_for_base_seed_primitives
F0_C_whole_node_substituted_for_stock_core
A_C_whole_node_substituted_for_base_seed_raw
D0_D2_wrong_confirmation_projection
C_D2_wrong_stock_raw_projection
consumer_argument_changed_after_receipt
receipt_changed_to_match_posthoc_echo
precall_envelope_created_after_output
degraded_edge_fabricates_known_value
```

All must fail.

Also retain all prior missing-edge / wrong-edge / temporal / process / revision / UNKNOWN / stale-authority perturbations.

## 4. Real Evidence Boundary
KEEP:
```text
REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED
AS_RECORDED = false
knowledge_lineage = RECONSTRUCTED_CORRECTED
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED
```

R5 synthetic consumption truth does not upgrade real historical effectiveness.

## 5. Clean Detached Regression
Run all relevant prior tests plus R18R1R1 tests.

No broad deselection.

Protected heads remain byte-identical.

## 6. Final State
```text
R18R1R1C_INDEPENDENT_CONSUMPTION_ORACLE = PASS_LOCAL
EDGE_CONSUMPTION_TRUTH = PASS

R18_REAL_ACCEPTED_SOURCE_REPLAY = PASS_CAPABILITY_SCOPED
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED

V4_14_RUNTIME_CANDIDATE =
READY_FOR_EXTERNAL_AUDIT_R18R1R1

V4_14_ACCEPTED_HEAD = NOT_CREATED
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_13_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
ALGORITHM_STATE_REPLAY_PASS = NOT_GRANTED_PENDING_EXTERNAL_AUDIT

NEXT = STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

Commit + push and STOP.
