# V4-06 R2 Accepted Head Promotion Task

- Task ID: V4_06_R2_ACCEPTED_HEAD_PROMOTION_TASK_20260930
- Type: separate Accepted Head promotion preparation
- Authority: V4_06 R2 + V4_07 R1 Independent External Audit, dated 2026-09-30; project AGENTS.md; REV2; V4-06 R2 candidate evidence.
- External decision: V4_06_EXTERNAL_ACCEPTANCE_PASS_R2_SCOPED_DEGRADED.
- Preparation status: READY_FOR_SEPARATE_PROMOTION_EXECUTION
- No Accepted Head file or global accepted pointer is changed by this task preparation.

## Candidate input identity

- Candidate implementation commit: 4c6051586a617d01f2ebbe142ea4ded05660fec7.
- Candidate manifest: reports/v4_06/V4_06_R2_STAGE_CANDIDATE_MANIFEST.json.
- Candidate manifest SHA-256: 5d9297b324c57d66228f66b5e291b4cca2b8ca4325d92759676401b1f6352b14.
- Candidate closure: reports/v4_06/V4_06_R2_CLOSURE.md.
- Candidate status: V4_06_DEGRADED_PASS_CANDIDATE_R2.
- Accepted input remains V4-05 publication PUB-3c03e227-c60a-4d8c-86ae-2861507c257b, trade date 2026-09-28, Core logical digest d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74, 5,222 identities.

## Promotion scope

1. Revalidate the independent external decision and candidate manifest against the pushed candidate commit.
2. Create data/v4/V4_06_ACCEPTED_HEAD.json with external acceptance recorded as scoped degraded acceptance.
3. Update data/v4/V4_STAGE_ACCEPTED_HEAD.json from the V4-05 accepted boundary to V4-06 only, preserving all prior V4-00 through V4-05 bindings.
4. Record V4-06 status as DEGRADED_PASS and retain BAOSTOCK_LIVE_STRICT_BINDING = BLOCKED_DEGRADED.
5. Keep V4-06-BAOSTOCK-BINDING-TOLERANCE-01 OPEN with its existing scope and evidence.
6. Keep V4-07 without an Accepted Head or external acceptance claim. V4-07 R1 remains externally blocked pending its R2 repair and review.
7. Keep V4-08 blocked by PIT membership baseline and reconstruction requirements.

## Required promotion outputs

- data/v4/V4_06_ACCEPTED_HEAD.json
- data/v4/V4_STAGE_ACCEPTED_HEAD.json
- reports/v4_joint/V4_06_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json
- reports/v4_joint/V4_06_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json
- docs/evidence/V4_06_ACCEPTED_HEAD_PROMOTION_AND_V4_07_ENTRY_20260930.md

## Independent validation gates

- The external decision exactly matches the scoped degraded V4-06 R2 result.
- Candidate manifest SHA-256 and every listed path/hash/byte count match the promoted implementation.
- The V4-05 input publication and Core logical digest remain unchanged.
- V4-06 runtime, persistence, determinism, migration, clean-checkout, and contract-semantic receipts remain PASS.
- Live BaoStock strict binding remains blocked and its audit remains OPEN.
- The global accepted range advances through V4-06 only; all V4-00 through V4-05 bindings remain unchanged.
- V4-07 has no Accepted Head and V4-08 remains blocked.

## Terminal state

Successful promotion execution may report V4_06_ACCEPTED_HEAD_PROMOTION_PASS_R1. This task card alone does not promote V4-06. The separate promotion run must produce and validate the listed outputs before updating the global accepted pointer.
