# V4 R31R2｜V4-22 Fail-Closed Audit Contract Repair Final Independent External Audit R1｜2026-10-05

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`

Drive authority synchronized before repository inspection:

- `V4_R31R1_V4_22_AUDIT_CONTRACT_REPAIR_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md`
- `V4_22_R31R2_FAIL_CLOSED_CLOSURE_EVIDENCE_AND_REPRODUCIBILITY_REPAIR_TASK_20261005.md`
- `V4_NEXT_ROUND_EXECUTION_MASTER_R31R2_20261005.md`

Execution baseline:

`abe8311d55db3fecc086a77c3ce8a16f4309df54`

Audited remote HEAD:

`6f05278f50ee58bc904f5949c503de9223835463`

Exact tested source:

`3e69de81b6c97cf91da76f1066e487c88b0db11b`

Immutable tested tag:

`codex/r31r2-v4-22-audit-contract-failclosed-tested-source-20261005-v3`

---

# 1. Unique External Decision

```text
R31R2_EXTERNAL_AUDIT =
PASS_FINAL_R31R2_FAIL_CLOSED_REPAIR

R31R2_SCOPE_AND_HARD_BOUNDARY = PASS
R31R2_TESTED_SOURCE_GOVERNANCE = PASS
R31R2_PROTECTED_STATE = PASS
R31R2_CLEAN_REGRESSION = PASS_KEEP_SCOPED

R31_OPEN_ITEM_CLOSURE_EVIDENCE_VERIFICATION = PASS_EXTERNAL
R31_CHILD_LEDGER_SCHEMA_FAIL_CLOSED = PASS_EXTERNAL
R31_REPAIR_REPRODUCIBILITY_AND_STAGE_IDENTITY = PASS_EXTERNAL

R31_FINAL_VERDICT_OPEN_ITEM_CONSUMPTION = PASS_KEEP
R31_ITEM_LEVEL_AUTHORITY_VALIDATION = PASS_KEEP
R31_EXACT_SESSION_PARENT_LINKAGE = PASS_KEEP

V4_22_CONTRACT_DESIGN =
EXTERNALLY_ACCEPTED_SCOPED

V4_22_FINAL_AUDIT_ENTRY =
BLOCKED_WAIT_REAL_GATES

V4_22_FINAL_PASS =
NOT_GRANTED

V4_22_ACCEPTED_HEAD =
NOT_CREATED

REAL_SHADOW_OBSERVATIONS =
0

REAL_CONTINUED_FORWARD_OBSERVATION =
NOT_STARTED

NEXT =
RETURN_TO_R25_ACCEPTED_DAILY_INPUT_AND_FIRST_REAL_SHADOW_ACTIVATION
```

R31/R31R1/R31R2 contract-design repair chain is now closed for the required scope.

This acceptance is scoped to the V4-22 independent-audit contract design and machine fail-closed semantics. It is not final V4-22 project acceptance and grants no production permission.

---

# 2. Drive Authority / Scope｜PASS

The latest Drive sequence was synchronized before repository inspection.

R31R2 was the unique current execution authority.

The repository is four commits ahead of the R31R2 baseline and all changed files remain inside the allowed narrow repair scope:

```text
config/v4_22_independent_audit_contract_v1.json
reports/r31/audit_oracle.py
reports/r31/build_contract.py
reports/r31r2/*
docs/evidence/r31r2/*
tests/test_v4_22_independent_audit_contract.py
tests/test_v4_22_r31r1_repair.py
tests/test_v4_22_r31r2_repair.py
```

No business writer, V4-21 business semantics, Focus route, default UI route, production permission, real Forward writer, settlement owner, or accepted head was changed.

---

# 3. Tested Source Governance｜PASS

Exact tested source:

`3e69de81b6c97cf91da76f1066e487c88b0db11b`

Tested tag:

`codex/r31r2-v4-22-audit-contract-failclosed-tested-source-20261005-v3`

The tag resolves to the exact tested source.

Current HEAD is exactly one evidence-only closure commit ahead.

Post-test delta is restricted to the explicit R31R2 closure allowlist:

```text
docs/evidence/r31r2/R31R2_REPAIR_ACCEPTANCE.md
reports/r31r2/CLEAN_CHECKOUT_PROOF.json
reports/r31r2/CLEAN_REGRESSION.json
reports/r31r2/LOCAL_TEST_SUMMARY.json
reports/r31r2/R31R2_CANDIDATE_SEAL.json
reports/r31r2/TESTED_SOURCE_GOVERNANCE.json
reports/r31r2/clean-output.txt
reports/r31r2/clean-summary.json
reports/r31r2/clean-tests.xml
```

No post-test semantic drift was found.

---

# 4. Clean Regression｜PASS_KEEP_SCOPED

Final declared clean regression:

```text
tests = 457
passed = 454
failures = 3
errors = 0
skipped = 0
deselected = 0
```

The three failures remain exactly the inherited R26-A01 debt:

```text
tests.upgrade_v3.test_v3_unified_entry::test_v3_is_the_single_unified_workbench_entry
tests.upgrade_v3.test_p01_01_lock_scope::test_hot_rank_route_skips_request_scope
tests.upgrade_v3.test_p01_01_lock_scope::test_send_marks_disconnected_client_closed
```

Earlier R31R2 harness incidents were explicitly recorded and corrected. They are not hidden as passing evidence.

No new failure exists in the final clean scope.

---

# 5. Protected State｜PASS

Independent repository comparison confirms the protected heads remain byte-identical to the R31R2 baseline:

```text
V4_STAGE_ACCEPTED_HEAD.json = unchanged
V4_DATA_ACCEPTED_HEAD.json  = unchanged
V4_15_ACCEPTED_HEAD.json    = unchanged
```

Accepted heads remain absent:

```text
V4_16_ACCEPTED_HEAD
V4_17_ACCEPTED_HEAD
V4_18_ACCEPTED_HEAD
V4_19_ACCEPTED_HEAD
V4_20_ACCEPTED_HEAD
V4_21_ACCEPTED_HEAD
V4_22_ACCEPTED_HEAD
```

Current real state remains:

```text
R25 = WAIT_ACCEPTED_DAILY_INPUT
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
REAL_CONTINUED_FORWARD_OBSERVATION = NOT_STARTED

V4_17G = NOT_GRANTED
MIGRATION_REPLAY_PASS = NOT_GRANTED

production_permission[*] = false
Focus_source_cutover = false
DEFAULT_UI_CUTOVER = false
```

No real evidence was manufactured.

---

# 6. P0-A｜Closure Evidence / Authority Independent Readback｜PASS_EXTERNAL

The prior R31R1 defect is repaired.

`verify_closure()` now requires all of the following:

```text
exact canonical receipt digest
exact item_id
exact capability_scope
allowed explicit disposition
independent_recheck == true
explicit closure_authority
non-empty exact_evidence array
receipt/binding authority identity equality
closure authority explicitly authorized for this item
exact raw readback of closure authority
exact raw readback of every evidence binding
path contained within verification root
exact SHA256
exact contract_id where the referenced JSON declares contract_id
closure authorization explicitly present inside the independent authority
```

The opener document is no longer automatically accepted as the closer.

The current real contract correctly retains:

```text
closure_authority_authorizations = {}
open_item_closure_bindings = {}
```

because no current real open item is actually closed.

Mandatory negative vectors now cover missing evidence, SHA mismatch, contract-id mismatch, placeholder `SIM_ONLY`, opener-only authority, wrong authority digest, missing authorization, malformed recheck/disposition/path and valid exact closure.

No current false-pass path was found.

Classification:

```text
R31_OPEN_ITEM_CLOSURE_EVIDENCE_VERIFICATION =
PASS_EXTERNAL
```

---

# 7. P0-B｜Child Ledger Required Schema / Lane Fail-Closed｜PASS_EXTERNAL

The prior R31R1 fail-open ordering is repaired.

For sessions/events/outcomes the oracle now:

```text
1. validates the complete required schema first;
2. resolves evidence_lane against the exact V4-21 evidence_lanes registry;
3. validates namespace and lane semantics;
4. rejects missing/unknown lanes;
5. excludes recognized diagnostic lanes from real counting only after validation;
6. applies exact parent linkage only to real lanes.
```

Missing or typo lanes no longer disappear via an early `continue`.

Mandatory vectors cover:

```text
event missing evidence_lane
outcome missing evidence_lane
session unknown lane
event typo lane
outcome typo lane
HISTORICAL_REPLAY
RECONSTRUCTED_ASOF
ACTIVATION_SIMULATION
SHADOW_REAL
namespace mismatch
real publication mismatch
diagnostic row missing required identity
```

The accepted V4-21 diagnostic behavior remains consistent with the existing V4-21 design ledger: diagnostic lanes do not count as real evidence.

Classification:

```text
R31_CHILD_LEDGER_SCHEMA_FAIL_CLOSED =
PASS_EXTERNAL
```

---

# 8. P1｜Repair Reproducibility / Stage Identity｜PASS_EXTERNAL

R31R2 chose the governed Option B model:

```text
historical R31 builder
+
historical-only downgrade guard
+
deterministic R31R2 repair builder
```

The old:

`reports/r31/build_contract.py`

now refuses to overwrite a newer canonical contract:

```text
HISTORICAL_ONLY_REFUSE_NEWER_CANONICAL_CONTRACT
```

The new:

`reports/r31r2/build_contract.py`

reconstructs the exact baseline contract from Git object:

`abe8311d55db3fecc086a77c3ce8a16f4309df54`

checks its exact baseline SHA, applies only the declared R31R2 repair transformation, and deterministically produces the current canonical contract.

Current canonical contract:

```text
version = 1.0.2
baseline = abe8311d55db3fecc086a77c3ce8a16f4309df54
next_stage = STOP_WAIT_R31R2_INDEPENDENT_EXTERNAL_AUDIT
```

Rebuild/idempotency/historical-guard/stage-identity vectors pass.

Classification:

```text
R31_REPAIR_REPRODUCIBILITY_AND_STAGE_IDENTITY =
PASS_EXTERNAL
```

---

# 9. R31R1 PASS_KEEP Areas｜PRESERVED

Independent comparison confirms:

```text
audit_items unchanged
open_items unchanged
audit_domains unchanged
cross_stage_carry unchanged
item_cross_domain_authorizations unchanged
ledger_schema_binding unchanged
```

Therefore R31R2 did not silently redesign the accepted R31R1 topology.

Preserved:

```text
OPEN-01..08 + OPEN-10 final-formula consumption
OPEN-09 nonblocking debt
publication/source_digest parent identity
event T0/session-date check
outcome due-date independence
projection_evaluable=false referential-parent semantics
item-level authority validation
R30R1 native session semantics
Amount A separation
FEP separate-acceptance boundary
R26-A01 historical regression debt
```

---

# 10. Nonblocking Observations

Two hardening observations remain, neither creates a current false-PASS path.

## P2-A｜Legacy `governance()` helper is R31-path-oriented

The standalone helper in `reports/r31/audit_oracle.py` still carries the original R31 path-prefix assumptions.

R31R2 actual tested-source governance is independently sealed by the R31R2 contract metadata, explicit allowlist and `validate_and_seal.py`; therefore this does not invalidate the current R31R2 tested source.

Before a future unified V4-22 final-audit runner directly reuses that helper, prefer making it consume the contract-driven allowlist rather than hardcoded R31 prefixes.

Classification:

```text
OPEN_NONBLOCKING_P2_GOVERNANCE_HELPER_GENERALIZATION
```

## P2-B｜`evidence_root` remains a testability hook

Formal `final_verdict()` defaults to the repository root. R31R2 tests inject a temporary root to exercise exact closure evidence without writing simulated authority into the repository.

This is acceptable for the current contract-design test harness, but a future production/final-audit entrypoint should not expose arbitrary root override to untrusted callers.

Classification:

```text
OPEN_NONBLOCKING_P2_TEST_HOOK_HARDENING
```

Neither item warrants reopening R31R2.

---

# 11. V4-22 State After R31R2

The contract-design chain may now be closed as:

```text
V4_22_CONTRACT_DESIGN =
EXTERNALLY_ACCEPTED_SCOPED
```

But the following remain explicitly false/not granted:

```text
V4_22_FINAL_PASS
V4_22_ACCEPTED_HEAD
V4_17G
MIGRATION_REPLAY_PASS
production_permission
Focus_source_cutover
DEFAULT_UI_CUTOVER
```

Therefore:

```text
V4_22_FINAL_AUDIT_ENTRY =
BLOCKED_WAIT_REAL_GATES
```

This is now a real-evidence dependency, not another contract-design defect.

---

# 12. Return to the Real-Operation Mainline

Current R25 authority remains:

```text
R25_EXTERNAL_AUDIT =
PASS_VALID_WAIT_ACCEPTED_DAILY_INPUT

R25_REAL_ACTIVATION_PACKET =
WAIT_ACCEPTED_DAILY_INPUT
```

The reason is still valid:

```text
V4_DATA_ACCEPTED_HEAD accepted_trade_date = 2026-09-30
no exact accepted target-session daily input
no exact target-date OWNER_OUTPUT
no exact target-date T0_SNAPSHOT
```

The market is closed from 2026-10-01 through 2026-10-07. Earliest calendar opportunity is 2026-10-08, but the date alone does not grant authority.

Therefore the next mainline is not another design stage.

Next:

```text
WAIT_FOR_EXACT_ACCEPTED_TARGET_SESSION_INPUT
→ retry R25 activation packet
→ external audit of READY packet
→ separately authorize first Real Shadow execution
```

Do not rerun R25 merely because wall-clock time advanced.

---

# 13. Final

```text
R31R2_EXTERNAL_AUDIT =
PASS_FINAL_R31R2_FAIL_CLOSED_REPAIR

V4_22_CONTRACT_DESIGN =
EXTERNALLY_ACCEPTED_SCOPED

V4_22_FINAL_PASS =
NOT_GRANTED

NEXT =
RETURN_TO_R25_ACCEPTED_DAILY_INPUT_AND_FIRST_REAL_SHADOW_ACTIVATION
```
