# DM01 R4R2 Acceptance Seal Governance Reconciliation R1

Execution baseline: `57ddef0dc21b48c27ccaab0b4d12b08616f85765`.
Authority: the three task/master/final audit documents copied into this report directory and bound in RECONCILIATION_ENTRY.json.

Historical R4 test restored exactly: 12735 bytes, SHA256 `22c96a78c97495b0a98c2cc10e639ab371b518c4c8546d63deedb24286884eec`.
Only `tests/v4_dm01_r4/test_runtime.py::test_current_real_v2_parent_and_future_wait` is deselected, registered as SUPERSEDED_PRE_SEAL_ASSERTION. The registry is evidence only; successor current-state coverage remains in tests/v4_dm01_r4r2/test_acceptance_seal.py.

R25 protected() PASS; selection() WAIT_ACCEPTED_DAILY_INPUT; target_trade_date null.
Accepted envelope EXTERNALLY_ACCEPTED_DM01_R4_RUNTIME; all extension bindings unchanged; production/shadow/focus false.
2026-10-08 WAIT_MARKET_CLOSE; source_requests 0; bridge_created false; r25_grant false.

Targeted: R4 24 PASS + 1 SUPERSEDED_PRE_SEAL_ASSERTION; R4R1 15 PASS; R4R2 bridge 18 PASS; Acceptance Seal 3 PASS.
Wider scoped regression: 43 existing registered debt failures, 0 new active failure nodes. These debts remain separately registered and open. The suite is not all green.
Initial targeted attempt lacked inherited PYTHONPATH for an entrypoint subprocess; raw evidence is retained under attempts. Corrected runs use the repository root and src in PYTHONPATH with no source edits.

Protected Stage V4_00_TO_V4_15_ACCEPTED; Data 2026-09-30; V4_16_ACCEPTED_HEAD absent; runtime_authorized/real_shadow_authorized false; observations and PIT samples 0. No real database, target package, Shadow start, TDX writes or source capture.

DM01_R4R2_ACCEPTANCE_SEAL_GOVERNANCE_RECONCILIATION = PASS_LOCAL_READY_FOR_FINAL_READBACK
DM01_R4_RUNTIME_ACCEPTANCE_HEAD = CREATED_EXTERNALLY_ACCEPTED
R25_PROTECTED_WAIT_SELECTION = PASS_WAIT_ACCEPTED_DAILY_INPUT
DM01_R4_GO_FORWARD_RUNTIME = EXTERNALLY_ACCEPTED_SCOPED_READY_FOR_NEXT_REAL_SESSION
REAL_TARGET_SESSION_PACKAGE = NOT_CREATED
REAL_SHADOW_EXECUTION = NOT_STARTED
REAL_SHADOW_OBSERVATIONS = 0
NEXT = STOP_WAIT_FINAL_INDEPENDENT_READBACK

This local result and Git delivery do not establish final external acceptance or permission to enter R25/Shadow.
Current regression outputs are reconciliation_targeted.* and reconciliation_wider.*; older output files remain historical evidence of the prior blocked seal.
