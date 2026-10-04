# V4 R31R1｜V4-22 Audit Contract Repair Independent External Audit R1｜2026-10-05

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`

Drive authority synchronized before repository inspection:

- `V4_R31_V4_22_INDEPENDENT_AUDIT_CONTRACT_DESIGN_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md`
- `V4_22_R31R1_FINAL_VERDICT_OPEN_ITEM_AND_SESSION_LINKAGE_REPAIR_TASK_20261005.md`
- `V4_NEXT_ROUND_EXECUTION_MASTER_R31R1_20261005.md`

Execution baseline:

`2ec72a9fa5bd72a4049c55009466668ea1d219a9`

Audited remote HEAD:

`abe8311d55db3fecc086a77c3ce8a16f4309df54`

Exact tested source:

`1260284f27790f748fbfc684ed0fb83f716fe6ec`

Tested tag:

`codex/r31r1-v4-22-audit-contract-repair-tested-source-20261005`

---

# 1. Unique External Decision

```text
R31R1_EXTERNAL_AUDIT =
PARTIAL_PASS_R31R2_REQUIRED

R31R1_SCOPE_AND_HARD_BOUNDARY = PASS
R31R1_TESTED_SOURCE_GOVERNANCE = PASS
R31R1_PROTECTED_STATE = PASS
R31R1_CLEAN_REGRESSION = PASS_KEEP_SCOPED

R31_FINAL_VERDICT_OPEN_ITEM_CONSUMPTION = PASS_CORE
R31_ITEM_LEVEL_AUTHORITY_VALIDATION = PASS
R31_EXACT_SESSION_PARENT_LINKAGE = PASS_CORE

R31_CHILD_LEDGER_SCHEMA_FAIL_CLOSED = FAIL_P0
R31_OPEN_ITEM_CLOSURE_EVIDENCE_VERIFICATION = FAIL_P0
R31_REPAIR_REPRODUCIBILITY_AND_STAGE_IDENTITY = FAIL_P1

V4_22_CONTRACT_DESIGN =
BLOCKED_PENDING_R31R2

V4_22_FINAL_AUDIT_ENTRY =
BLOCKED_WAIT_REAL_GATES

V4_22_FINAL_PASS =
NOT_GRANTED

V4_22_ACCEPTED_HEAD =
NOT_CREATED

NEXT =
R31R2_FAIL_CLOSED_CLOSURE_EVIDENCE_AND_REPRODUCIBILITY_REPAIR
```

R31R1 is not rejected as a whole. The original R31 defects were materially reduced and most of the requested narrow repair is correct. The remaining blockers are narrower than R31R1 itself.

---

# 2. Drive Authority / Scope｜PASS

The latest Drive task chain was synchronized first.

No R32 task existed before this audit.

R31R1 remained the unique current authority and required:

```text
CONTRACT_DESIGN_ONLY
```

The repository changed only within the allowed narrow repair area:

```text
config/v4_22_independent_audit_contract_v1.json
reports/r31/audit_oracle.py
reports/r31r1/*
docs/evidence/r31r1/*
tests/test_v4_22_independent_audit_contract.py
tests/test_v4_22_r31r1_repair.py
```

No business writer, Focus route, default UI route, production permission, accepted head, real Forward evidence or settlement ownership was changed.

---

# 3. Tested Source Governance｜PASS

Tested source:

`1260284f27790f748fbfc684ed0fb83f716fe6ec`

Current HEAD:

`abe8311d55db3fecc086a77c3ce8a16f4309df54`

The tested tag resolves to the exact tested source.

Current HEAD is exactly one evidence-only closure commit ahead.

The post-test delta contains only the explicit closure allowlist:

```text
docs/evidence/r31r1/R31R1_REPAIR_ACCEPTANCE.md
reports/r31r1/CLEAN_CHECKOUT_PROOF.json
reports/r31r1/CLEAN_REGRESSION.json
reports/r31r1/LOCAL_TEST_SUMMARY.json
reports/r31r1/R31R1_CANDIDATE_SEAL.json
reports/r31r1/TESTED_SOURCE_GOVERNANCE.json
reports/r31r1/clean-output.txt
reports/r31r1/clean-summary.json
reports/r31r1/clean-tests.xml
```

No post-test implementation drift was found.

---

# 4. Clean Regression｜PASS_KEEP_SCOPED

Declared clean regression:

```text
tests = 427
passed = 424
failures = 3
errors = 0
skipped = 0
deselected = 0
```

The three failures are exactly the inherited R26-A01 debt:

```text
tests.upgrade_v3.test_v3_unified_entry::test_v3_is_the_single_unified_workbench_entry
tests.upgrade_v3.test_p01_01_lock_scope::test_hot_rank_route_skips_request_scope
tests.upgrade_v3.test_p01_01_lock_scope::test_send_marks_disconnected_client_closed
```

No new R31R1 regression was introduced in the declared scope.

---

# 5. Protected State｜PASS

Independent repository comparison confirms the protected heads are byte-identical to the R31R1 baseline:

```text
V4_STAGE_ACCEPTED_HEAD.json = unchanged
V4_DATA_ACCEPTED_HEAD.json  = unchanged
V4_15_ACCEPTED_HEAD.json    = unchanged
```

Current frozen state remains:

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

Accepted heads remain absent for V4-16 through V4-22.

---

# 6. Original P0-A｜Open Items Are Now Consumed by Final Formula｜PASS_CORE

The original R31 defect was:

```text
final_verdict() ignored contract["open_items"]
```

R31R1 repaired this.

The current formula now explicitly requires closure/disposition for:

```text
OPEN-01
OPEN-02
OPEN-03
OPEN-04
OPEN-05
OPEN-06
OPEN-07
OPEN-08
OPEN-10
```

while preserving:

```text
OPEN-09 = OPEN_NONBLOCKING_DEBT
```

The current real contract still has:

```text
open_item_closure_bindings = {}
```

which is correct because no real open item has been externally closed.

Therefore the current state cannot accidentally reach final PASS.

This part of the original P0 is repaired.

---

# 7. P0 Remaining｜Closure `exact_evidence` Is Not Actually Verified

## 7.1 Required Rule

R31R1 explicitly required:

```text
No self-asserted closure.
Every closure receipt must contain exact evidence and independent authority.
```

## 7.2 Actual Logic

`closure_allowed()` only verifies that these fields are truthy:

```text
explicit_disposition
exact_evidence
authority
date_source
independent_recheck
```

`final_verdict()` then verifies the canonical digest of the whole receipt against a preloaded binding.

It does NOT independently read or validate:

```text
exact_evidence[].path
exact_evidence[].sha256
exact_evidence[].contract_id
closure authority path/digest/contract identity
```

## 7.3 Direct Counterexample Already Present in R31R1 Test

`tests/test_v4_22_r31r1_repair.py -> closed_future()` creates:

```text
exact_evidence = [
  {
    "path": "SIM_ONLY",
    "sha256": "SIM_ONLY"
  }
]

date_source = "SIM_20261005_INDEPENDENT_AUTHORITY"
```

and uses the existing open-item authority.

`R31R1-FINAL-05` then expects:

```text
formula_result == V4_22_FINAL_PASS
```

This proves the formula treats a canonical digest binding as sufficient even when the claimed `exact_evidence` is not independently readable or verifiable.

The simulation does not grant production authority, but the frozen future final-formula semantics remain too weak.

## 7.4 Additional Authority Problem

The closure receipt is forced to use:

```text
receipt.authority == item.authority
```

but the current `item.authority` is primarily the predecessor R30R1 external audit that established the item as OPEN.

A future closure should be bound to the exact independent closure authority, not automatically to the document that originally recorded the open state.

## 7.5 Classification

```text
R31_OPEN_ITEM_CLOSURE_EVIDENCE_VERIFICATION =
FAIL_P0
```

Required repair:

- closure binding must contain an exact closure-authority binding;
- `exact_evidence` must be an array of exact immutable bindings;
- every evidence binding must be independently read with path + SHA256 + contract_id where applicable;
- nonexistent path, wrong SHA, wrong ID, placeholder `SIM_ONLY`, opener-only authority, or self-asserted receipt must fail closed;
- canonical receipt digest remains necessary but is not sufficient.

---

# 8. Original P0-B｜Exact Session Parent Linkage｜PASS_CORE

R31R1 correctly expanded the parent linkage from the old five-field partition to:

```text
capability
evidence_lane
model_contract_id
parameter_digest
state_lineage_id
source_publication
source_digest
```

and independently reads the exact V4-21 contract through:

```text
ledger_schema_binding
```

The session row must now contain the complete required V4-21 session schema and valid exact native owner/status.

It also independently requires non-empty:

```text
trade_date
market_session_id
publication_id
publication_revision
session_receipt_id
slot_receipt_digest
```

Event rows additionally enforce:

```text
T0 == parent.trade_date
calendar_identity == parent.calendar_identity
```

Outcome rows correctly do NOT assume:

```text
due_date == processing trade_date
```

`projection_evaluable=false` remains a valid referential parent but does not increment the design count.

The original same-partition / wrong-publication false-parent defect is therefore materially repaired.

---

# 9. P0 Remaining｜Child Ledger Required-Field Validation Is Fail-Open

## 9.1 R31R1 Requirement

R31R1 required exact V4-21 required schemas for all three ledgers:

```text
session_ledger
event_cohort_ledger
due_outcome_ledger
```

and explicitly required fail-closed behavior on missing required fields.

## 9.2 Actual Child Loop

For `events` and `outcomes`, the current oracle executes:

```text
if row.get("evidence_lane") not in REAL_LANES:
    continue
```

before validating:

```text
all(k in row for k in required)
```

Therefore a malformed child row with missing `evidence_lane` is silently skipped.

Example:

```text
events[0] is otherwise intended as an observation row
but evidence_lane field is missing
```

Current behavior:

```text
row.get("evidence_lane") == None
None not in REAL_LANES
→ continue
→ no finding
```

If no other finding exists, the oracle can return:

```text
PASS_DESIGN_ONLY
```

instead of failing closed.

The same logic also silently ignores an unknown/typo lane value rather than distinguishing it from one of the contract-defined diagnostic lanes.

## 9.3 Why This Matters

V4-21 explicitly defines known evidence lanes:

```text
SHADOW_REAL
PRODUCTION_REAL
HISTORICAL_REPLAY
RECONSTRUCTED_ASOF
ACTIVATION_SIMULATION
```

Missing or unknown lane is not equivalent to a recognized non-real diagnostic lane.

## 9.4 Classification

```text
R31_CHILD_LEDGER_SCHEMA_FAIL_CLOSED =
FAIL_P0
```

Required repair order for every ledger row:

```text
1. validate complete required schema
2. validate evidence_lane belongs to exact V4-21 evidence_lanes registry
3. if recognized diagnostic lane -> exclude from real referential counting
4. if recognized real lane -> run exact parent linkage
5. missing/unknown lane -> BLOCKED_AFFECTED_SCOPE
```

---

# 10. Original P1｜Item-Level Authority Validation｜PASS

R31R1 now independently validates every:

```text
audit_item.authority
audit_item.evidence_refs
open_item.authority
open_item.evidence_refs
```

through exact immutable readback.

It enforces:

```text
repo-contained path
exact SHA256
exact contract_id where present
domain authority compatibility
explicit cross-domain authorization
```

The new negative vectors cover:

```text
wrong authority SHA
path traversal / wrong path
wrong open evidence SHA
domain/item authority divergence
wrong contract_id
wrong open-item authority SHA
```

This original R31 P1 is repaired.

---

# 11. P1 Remaining｜Repair Is Not Fully Reproducible From Its Builder

The current canonical contract is now:

```text
version = 1.0.1
```

and contains new R31R1 fields:

```text
ledger_schema_binding
item_cross_domain_authorizations
open_item_closure_bindings
referential_integrity.parent_identity
```

However:

`reports/r31/build_contract.py`

still builds the old R31 contract:

```text
version = 1.0.0
```

and does not generate the R31R1 additions.

A rerun of that builder can therefore overwrite the repaired canonical contract with the pre-repair semantics.

The current contract also still contains the stale:

```text
next_stage = STOP_WAIT_R31_INDEPENDENT_EXTERNAL_AUDIT
```

while R31R1 evidence correctly states:

```text
STOP_WAIT_R31R1_INDEPENDENT_EXTERNAL_AUDIT
```

This is not a current production-safety breach, but it breaks deterministic repair provenance and leaves two competing stage identities.

Classification:

```text
R31_REPAIR_REPRODUCIBILITY_AND_STAGE_IDENTITY =
FAIL_P1
```

Required repair:

Either:

```text
A. update the active builder to deterministically reproduce the latest repaired contract
```

or:

```text
B. freeze the old R31 builder as historical-only with an explicit refusal guard,
   and add a new deterministic R31R2 repair builder that reproduces the canonical contract.
```

Add an idempotency/rebuild vector and align the canonical `next_stage`.

Historical R31 evidence itself must remain immutable/recoverable through the old commit/tag.

---

# 12. PASS_KEEP Areas

R31R2 must not reopen:

```text
11 audit domains
92-item audit matrix topology
10-item open registry existence
status vocabulary
cross-stage remediation carry
Amount A separation
FEP separate acceptance
R30R1 native session repair
current open-item consumption topology
OPEN-09 nonblocking-debt behavior
exact publication/source_digest parent identity
event T0/session-date check
outcome due_date independence
projection_evaluable=false referential semantics
item-level authority validation
tested-source governance pattern
protected current state
R26-A01 inherited regression debt
```

---

# 13. Required R31R2 Scope

Only repair:

```text
P0-A closure exact-evidence + closure-authority readback
P0-B child ledger required-field / evidence-lane fail-closed
P1   deterministic repair generation + stage identity alignment
```

No real evidence may be created.

No current open item may be closed.

No production permission or accepted head may be created.

---

# 14. Required Exit After R31R2

Local implementation may only claim:

```text
R31R2_LOCAL_REPAIR =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

R31_OPEN_ITEM_CLOSURE_EVIDENCE_VERIFICATION =
PASS_LOCAL_REPAIRED

R31_CHILD_LEDGER_SCHEMA_FAIL_CLOSED =
PASS_LOCAL_REPAIRED

R31_REPAIR_REPRODUCIBILITY_AND_STAGE_IDENTITY =
PASS_LOCAL_REPAIRED

V4_22_CONTRACT_DESIGN =
LOCAL_READY_FOR_EXTERNAL_AUDIT_AFTER_R31R2

V4_22_FINAL_AUDIT_ENTRY =
BLOCKED_WAIT_REAL_GATES

V4_22_FINAL_PASS =
NOT_GRANTED

V4_22_ACCEPTED_HEAD =
NOT_CREATED

NEXT =
STOP_WAIT_R31R2_INDEPENDENT_EXTERNAL_AUDIT
```

Commit/push is not external acceptance.
