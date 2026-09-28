# V4-01 R8.1 Identity Event Discovery — External Review Package

Date: 2026-09-28  
Internal result: **PASS; ready for external review**  
External acceptance: **pending**

## Scope and contract

The R8.1 gate implements versioned historical-backscan and daily-incremental identity-event discovery over the V4-01 Required Scope. Candidate discovery unions official code-change events, dated aliases, adjacent dated roster changes, lifecycle boundaries, persistent retrospective bar aliases, and source-symbol reassignment/code-reuse candidates. Weak name continuity creates candidates only. Discovery does not merge or rewrite canonical identities. Unresolved Required Scope candidates fail the gate.

The prior external finding was that R8 candidate discovery depended too heavily on persistent identical overlapping bars and existing aliases. This package records the generic R8.1 repair and its independent re-audit evidence.

## Evidence and acceptance

- Test receipt: `reports/v4_joint/V4_R8_1_DM01_TEST_RECEIPT_R1_20260928.json` (SHA-256 `8607b0564675d96f2edd1af265ff2b1220ae43dc905082584e8ddcf42c2416ed`), status `PASS`, counts `{"error": 0, "failed": 0, "passed": 241, "skipped": 2, "xfailed": 0, "xpassed": 0}`.
- Candidate receipt: `reports/v4_01/V4_01_IDENTITY_EVENT_DISCOVERY_R8_1.json` (SHA-256 `e5c96e5a711fc6fb60233b3e57dce68ddd98d77d7649612bbf0293b617853b7a`), candidates `38`, unresolved Required Scope `0`.
- Independent postcheck: `reports/v4_01/V4_01_R8_1_INDEPENDENT_POSTCHECK_R1_20260928.json` (SHA-256 `e0dc6113cc2e9942e78d31b6cbbb76467988bdeeb84c69c39827b4c1e6a00eab`), status `PASS`.
- Joint reseal: `reports/v4_joint/V4_00_01_02_JOINT_FINAL_RECEIPT_R2_20260928.json` (SHA-256 `030cd6ad2f3b67f101b68dc98c8d55d157c51597b5de8b8dc8a70ac59f2e9df7`).
- R7 canonical identity map and Required Scope universe hashes match the previously accepted R8 evidence; no recanonicalization was required.

Internal acceptance is limited to the R8.1 identity-discovery gate and joint 00/01/02 reseal. No new external acceptance is claimed. The accepted V4-02 R6 artifacts and Phase 0 baseline remain bound as parents. V4-03 remains blocked until external review accepts this package.

## Next stage

Independent external review of candidate completeness, evidence quality, the zero-unresolved Required Scope result, and joint reseal integrity.
