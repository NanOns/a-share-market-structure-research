# V4 Phase 0 Final Targeted Repair R3 — Execution Ledger

- Governing repair card: `DA-MSR-V4-PHASE0-EXTERNAL-AUDIT-R3.1`.
- Repair card: `D:/Users/lps/Desktop/V4_PHASE0_R2_EXTERNAL_AUDIT_AND_FINAL_REPAIR_R3_1_20260925.md`.
- Governing technical contract: `DA-MSR-V4.2.2-CODEX-REV2`, SHA-256 `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`.
- Starting HEAD: `310696d57165a52354a33a7b8d65a8a769063e50`.
- Execution boundary: additive migration 008, Phase 0 scope gate, explicit 00G non-numeric-value limitation, tests, and R3 acceptance receipts only. No database reset, TDX writes/downloads, 00D rerun, V4-01, scanner, factor, Radar, Focus, or BaoStock work.

## Planned stage contracts and evidence

### P0-A — Freeze prior accepted publication state

- **Contract:** REV2 §4.7 as restated in R3 §§4–11 and §26. The prior must be the immediately previous market session's accepted publication head, bound to its state-head ID and logical digest. Same-day revisions inherit an identical prior tuple. A gap is valid only when the previous market session has no accepted head, or at the declared first calendar boundary.
- **Change:** forward-only `008_prior_session_state_freeze_integrity.sql`; no data reset. Give `publication_heads` an explicit state-head/logical-digest identity, replace the ambiguous prior computation digest with `prior_session_state_logical_digest`, and add trigger checks and session/head serialization.
- **Evidence:** PostgreSQL migration checksum, schema/FK inspection, transaction-rollback negative tests for accepted-head identity, state-head identity/digest, same-day freeze, and false gaps.
- **Acceptance:** migrations 008 and 009 applied by the hash-checked runner. Final schema has 15 V4 tables, 25 validated foreign keys, zero unvalidated foreign keys, and zero runtime rows. PostgreSQL negative-vector suite covers the required accepted-head/state/digest, frozen same-day tuple, gap, and head-mutation cases.
- **Next:** P0-B gate owner binding and hard BLOCKED-stage semantics.

### P0-B — Owner-bound required scopes and derived RAW permission

- **Contract:** R3 §§12–17 and §26. `A_STOCK_TDX_SOURCE` belongs to 00D, `LIFECYCLE_SCHEMA` to 00B, and `PUBLICATION_IDENTITY` to 00C. RAW permission is derived from accepted required Phase 0 evidence plus the RAW capability declaration at 00E. Any BLOCKED stage blocks Phase 0; non-entry capability blocks use DEGRADED_PASS.
- **Change:** `phase0_gate.py`, final gate contract, and negative tests.
- **Evidence:** wrong-owner claims, caller-declared RAW, BLOCKED stage with a false block flag, and FULL_PASS with blocked non-entry capability.
- **Acceptance:** wrong-owner claims, unowned RAW self-declaration, BLOCKED stage with `blocks_v4_01=false`, and FULL_PASS with a non-entry blocked scope are covered by passing tests. The final machine gate derives RAW from 00E plus every accepted Phase 0 stage and the owner-bound required scopes.
- **Next:** P1-A parameter policy boundary and final aggregate gate.

### P1-A — Explicit non-numeric parameter boundary

- **Contract:** R3 §§19–20 and §26. Keep parameter values finite-number-or-null. The two unassigned matrix/enum-by-capability policies remain fail-closed and must move to a separate versioned policy contract before values are assigned; 00G is DEGRADED_PASS while this limitation remains.
- **Change:** declare and validate this boundary in the framework, retain all affected candidate values as null, and add a nonblocking limitation to the final gate.
- **Evidence:** framework/registry consistency tests and a negative non-numeric assignment vector.
- **Acceptance:** all 63 Phase 0 tests pass. Framework and registry explicitly restrict values to finite number or null; quality enum/matrix values remain null and fail-closed until a separate versioned policy contract exists. 00G is recorded `DEGRADED_PASS`.
- **Next:** external Phase 0 audit; do not start V4-01 before the audit authorizes entry.

### P0-7 — Physical backup audit fact

- **Contract:** R3.1 correction and §§22/26. The PostgreSQL physical backup was explicitly requested by the user before the old database was deleted. Preserve it as a verified deletion safety measure, not a V4 migration input or Phase 0 entry dependency.
- **Change:** no backup data or prior database is restored or modified.
- **Evidence:** existing R2 backup receipt and audit record.
- **Acceptance:** final machine receipt records `USER_EXPLICITLY_REQUESTED_PRE_DELETE_SAFETY_MEASURE`, verified status, informational role, and `is_v4_migration_input=false`.
- **Next:** include the corrected fact in final receipt.
