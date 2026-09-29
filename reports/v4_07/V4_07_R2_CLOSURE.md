# V4-07 R2 Candidate Closure

## Result

- Candidate state: V4_07_R2_CANDIDATE_PASS_PENDING_EXTERNAL_ACCEPTANCE_SIGNAL_CAPABILITY_DEGRADED.
- External acceptance: PENDING. This evidence closes the implementation stage and does not self-approve V4-07.
- Candidate artifact: reports/v4_07/staging/V4_07_BASE_SEED_CANDIDATE_R2.jsonl.gz.
- Accepted run: 2026-09-28; publication PUB-3c03e227-c60a-4d8c-86ae-2861507c257b; Core digest d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74; 5222 identities.
- Candidate SHA-256: bb9992c581092f91ba69ad8390daf522d3441951f5bc61437ff0e4653ed74e72.
- Candidate logical digest: 28c5f6f71f6568c29bb8b1580f8c6ff22475222c802b4d5317a3f0cbb3b16015.
- Output states: TRUE=0, FALSE=2443, UNKNOWN=2779.

## External audit repairs

- S01 PASS: production evaluator, machine-vector executor, and independent verifier consume an explicit parameter-set instance. Fixture perturbations 3→2.5, 3→4, and 10→11 moved the relevant predicates; formal config SHA stayed 241785e1a97dd2283eb8b361eb791f4e5c8f6ca67579a06f2a2d38c0c7586a1a.
- S02 PASS: accepted date, publication identities, source digests, identity count, and board counts flow through a validated accepted run context. Synthetic T/T+1 contexts returned row counts [2, 1], with date/publication/digest isolation and no future-row effect.
- Independent verifier recomputed 5222 rows with 0 mismatches and produced the same logical digest.
- Identical accepted-context replay passed. Machine vectors: 30 checked, 0 mismatches.
- Focused V4-07 runtime: 41 passed in 25.13s.
- Isolated full regression: 538 passed, 2 skipped in 30.98s on postgres (PostgreSQL) 18.6; disposable PostgreSQL cluster cleaned up. Migration 015 apply/rollback: PASS_ISOLATED_MIGRATION_AND_ROLLBACK.

## Scoped capability limitation

The accepted V4-05 input still reports rps5_delta3 UNKNOWN for all 5222 identities because of BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY. Accepted T-1 close/MA20 fields remain absent. No threshold relaxation, turnover substitution, raw-history reconstruction, or unaccepted RPS fallback was used. Real Base Seed signal capability remains degraded and is tracked separately in reports/audits/V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_AUDIT_20260930.md.

## Promotion and next stage

- No V4-07 Accepted Head was created. The global accepted range and V4-05 accepted inputs remain unchanged; V4-08 remains blocked by its PIT membership requirement.
- A separate V4-06 promotion task is prepared at docs/evidence/V4_06_R2_ACCEPTED_HEAD_PROMOTION_TASK_20260930.md. It preserves the open BaoStock live-binding audit and does not execute promotion here.
- Next V4-07 stage: independent external R2 acceptance review.

## Evidence index

- V4_07_R2_STAGE_RESULT.json
- V4_07_R2_STAGE_CANDIDATE_MANIFEST.json
- V4_07_R2_PARAMETER_BINDING_VERIFICATION.json
- V4_07_R2_MULTI_DATE_CONTEXT_VERIFICATION.json
- V4_07_R2_MACHINE_VECTOR_COVERAGE.json
- V4_07_R2_INDEPENDENT_POSTCHECK.json
- V4_07_R2_DETERMINISM_VERIFICATION.json
- V4_07_R2_RUNTIME_TEST_RECEIPT.json
- V4_07_R2_ISOLATED_FULL_REGRESSION.json
- V4_07_R2_MIGRATION_ROLLBACK_VERIFICATION.json
