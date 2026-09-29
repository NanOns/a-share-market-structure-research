# V4-07 R2 Stage Entry

- Stage contract: V4_06_R2_CONTRACT_REPAIR_AND_V4_07_BASE_SEED_STAGE_TASK_20260929 Workstream B; authority includes REV2 §§14.2–14.4, 73, 78, 87A and the independent external audit dated 2026-09-30.
- Starting HEAD: 131d437e5ad9124e3a60648c5a9ce4c9cf7d39e4.
- Stage scope: repair S01 parameter binding and S02 accepted-run context generalization in the V4-07 producer; retain the BASE_SEED_V1 frozen config and accepted V4-05 data. Add independent parameter perturbation and two-date context evidence.
- External audit gate: V4_07_EXTERNAL_ACCEPTANCE_BLOCKED_R1_PRODUCER_GENERALIZATION_AND_PARAMETER_BINDING_REPAIR_REQUIRED. R1 is not accepted and cannot be promoted.
- S01 requirements: the production evaluator, machine-vector executor, and independent verifier receive one explicit parameter-set instance. Runtime thresholds must resolve through the frozen parameter IDs. Perturbed fixture values are 3 → 2.5, 3 → 4, and 10 → 11; the checked-in formal parameter package must remain byte-identical.
- S02 requirements: producer inputs bind target date, formal publication, Core row namespace, Core digest, expected identity count, and board counts through an accepted run context. The runner may load the current accepted V4-05 context. Producer code must not hard-code one date, publication identity, digest, or row count.
- Accepted current-source capability limitation: rps5_delta3 is UNKNOWN throughout the accepted V4-05 scope because of BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY; accepted T-1 close/MA20 fields are absent. Do not relax thresholds, rebuild raw history, or substitute unaccepted values. Track prior-RPS input repair as a separate open audit item.
- V4-06 disposition: prepare a separate Accepted Head promotion task under the scoped degraded external acceptance. Do not edit either Accepted Head or advance the global accepted range during V4-07 R2.
- Guardrails: TDX sources remain read-only; write evidence atomically under this repository; no V4-07 promotion and no V4-08 entry.
- Acceptance result at entry: PENDING_IMPLEMENTATION_AND_EVIDENCE.
- Required evidence: R2 parameter binding, multi-date producer, exact accepted-source replay, independent recompute, determinism, V4-06 isolation, and applicable persistence/regression checks. These gates are evidence for review and do not themselves establish external acceptance.
- Next stage after candidate closure: independent external V4-07 R2 review. V4-06 Accepted Head promotion remains a separate task.
