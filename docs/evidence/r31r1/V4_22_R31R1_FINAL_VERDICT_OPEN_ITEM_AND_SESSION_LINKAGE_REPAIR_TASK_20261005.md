# V4-22 R31R1｜Final Verdict Open-Item + Session Linkage Repair Task｜2026-10-05

## 0. Mission

Perform a narrow repair of the R31 V4-22 independent-audit contract candidate.

This round repairs only the externally identified R31 defects:

```text
P0-A final verdict does not enforce explicit closure of blocking open items
P0-B OPEN-10 event/outcome parent can bind to an under-identified session
P1   item-level authority/evidence refs are not independently validated
```

Execution baseline:

`2ec72a9fa5bd72a4049c55009466668ea1d219a9`

External authority:

`V4_R31_V4_22_INDEPENDENT_AUDIT_CONTRACT_DESIGN_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md`

This is still:

```text
CONTRACT_DESIGN_ONLY
```

It is NOT the final V4-22 independent audit.

---

## 1. PASS_KEEP Boundary

Do not reopen or redesign:

```text
11 audit domains
7-value status vocabulary
92-item audit matrix topology
10-item open registry existence
18-entry cross-stage remediation carry
Amount A separation
FEP separate acceptance
R30R1 native session repair
current no-production authority behavior
protected heads/state
current real gate state
R26-A01 inherited regression debt
```

Do not close any current real-evidence item.

Do not create any V4 accepted head.

---

# 2. P0-A｜Final Verdict Must Enforce Open-Item Closure

## 2.1 Problem

Current `final_verdict()` ignores `contract["open_items"]`.

Therefore a synthetic future state can return:

```text
V4_22_FINAL_PASS
```

after audit items and runtime gates are satisfied even though OPEN-01..OPEN-08 never completed the required explicit disposition protocol.

This violates:

```text
NO_AUTO_CLOSE
```

---

## 2.2 Required Contract Addition

Freeze explicit open-item closure receipt bindings.

Recommended:

```text
open_item_closure_bindings = {}
```

Future closure binding identity:

```text
item_id
capability_scope
canonical_sha256
authority_id / authority
```

Every closure receipt must contain at least:

```text
item_id
capability_scope
explicit_disposition
exact_evidence
authority
date_source
independent_recheck
```

No self-asserted closure.

No inferred closure from a later gate alone.

---

## 2.3 Final Formula Rule

For each open item:

### Blocking item

If:

```text
blocking_scope != []
```

then final pass requires an exact independently bound closure receipt.

Current blocking open items:

```text
OPEN-01
OPEN-02
OPEN-03
OPEN-04
OPEN-05
OPEN-06
OPEN-07
OPEN-08
```

### OPEN-09

Remain:

```text
OPEN_NONBLOCKING_DEBT
```

and do not by themselves block V4-22 final formula.

### OPEN-10

Although its registry-level blocking scope is empty, it has the explicit rule:

```text
OPEN-10_DISPOSITION_REQUIRED_BEFORE_FINAL_PROJECT_ACCEPTANCE
```

V4-22 final formula must not report final PASS while OPEN-10 lacks the exact independent disposition required by the external audit.

The dedicated:

```text
A22-GOVERNANCE-OPEN10
```

item may be used as part of this proof, but the open-item closure/disposition itself must remain explicit and machine-bound.

---

# 3. P0-B｜Exact Session Parent Linkage

## 3.1 Problem

Current referential oracle parents event/outcome rows using only:

```text
capability
evidence_lane
model_contract_id
parameter_digest
state_lineage_id
```

This is too coarse.

A session from a different trade date/publication can satisfy a child row in the same partition.

A malformed session missing the V4-21 required session identity can also satisfy the parent relationship.

---

## 3.2 Use V4-21 Required Schema as Authority

Read exact:

`config/v4_21_continued_forward_observation_contract_v1.json`

and bind the required fields for:

```text
session_ledger
event_cohort_ledger
due_outcome_ledger
```

Do not silently duplicate a reduced schema.

The independent oracle may cache the accepted immutable required-field lists after exact readback, but it must fail closed on missing required fields.

---

## 3.3 Required Session Parent Identity

The child-to-session relationship must include exact observation provenance.

At minimum use the common identity:

```text
capability
evidence_lane
model_contract_id
parameter_digest
state_lineage_id
source_publication
source_digest
```

and independently validate the session’s exact:

```text
trade_date
market_session_id
publication_id
publication_revision
session_receipt_id
slot_receipt_digest
native_session_authority_id
native_session_authority_sha256
native_session_status
```

For events:

```text
T0
```

must be consistent with the exact accepted session/publication relation defined by V4-21.

For outcomes:

do not assume:

```text
due_date == processing session trade_date
```

Instead bind the outcome revision to the exact observation publication/session that processed it via source publication/digest and the accepted session identity.

---

## 3.4 Evaluability Rule

Preserve R30R1 semantics:

```text
native_session_status = ACCEPTED_ON_TIME
projection_evaluable = false
```

is:

```text
not a missed slot
not countable for accepted-session streak
but may remain a referential parent
```

only when the session row is otherwise a complete exact V4-21 accepted session for the same publication/session provenance.

---

# 4. P1｜Item-Level Authority Validation

Extend independent contract validation beyond domain-level bindings.

Validate exact path/digest/contract identity for every:

```text
audit_item.authority
audit_item.evidence_refs
open_item.authority
open_item.evidence_refs
```

Required:

```text
path inside repo root
exact sha256
exact contract_id where present
domain/item authority compatibility
no silent fallback
no latest/mtime lookup
```

If an item references an authority outside its domain registry, the contract must explicitly authorize that cross-domain reference; otherwise fail closed.

---

# 5. Mandatory Negative / Counterfactual Tests

Add at minimum:

```text
R31R1-FINAL-01
all blocking audit items PASS
all runtime gates PASS
OPEN-01 unresolved
→ FINAL_AUDIT_NOT_READY / BLOCKED
→ never V4_22_FINAL_PASS

R31R1-FINAL-02
OPEN-01 closure receipt missing exact evidence
→ BLOCKED

R31R1-FINAL-03
OPEN-01 closure scope mismatch
→ BLOCKED

R31R1-FINAL-04
OPEN-01 closure receipt digest mismatch
→ BLOCKED

R31R1-FINAL-05
OPEN-09 remains OPEN_NONBLOCKING_DEBT
all blocking obligations validly closed
→ OPEN-09 alone does not block

R31R1-FINAL-06
OPEN-10 lacks explicit independent disposition
→ never V4_22_FINAL_PASS

R31R1-REFINT-01
same five-part partition
different source_publication
→ BLOCKED_AFFECTED_SCOPE

R31R1-REFINT-02
same five-part partition
different source_digest
→ BLOCKED_AFFECTED_SCOPE

R31R1-REFINT-03
session missing market_session_id
→ BLOCKED_AFFECTED_SCOPE

R31R1-REFINT-04
session missing trade_date/publication/session receipt identity
→ BLOCKED_AFFECTED_SCOPE

R31R1-REFINT-05
event T0 belongs to another accepted session/publication
→ BLOCKED_AFFECTED_SCOPE

R31R1-REFINT-06
outcome belongs to another observation publication
→ BLOCKED_AFFECTED_SCOPE

R31R1-REFINT-07
complete exact ACCEPTED_ON_TIME + projection_evaluable=false
→ referential parent allowed
→ accepted-session count remains zero

R31R1-REFINT-08
Production real without accepted production session authority
→ BLOCKED_AFFECTED_SCOPE

R31R1-AUTH-01
audit item authority sha mutated
→ validate_contract FAIL

R31R1-AUTH-02
audit item authority path mutated
→ validate_contract FAIL

R31R1-AUTH-03
open item evidence ref digest mutated
→ validate_contract FAIL

R31R1-AUTH-04
domain/item authority divergence
→ validate_contract FAIL
```

---

# 6. Required Source Changes

Prefer narrow changes.

Allowed:

```text
config/v4_22_independent_audit_contract_v1.json

reports/r31/audit_oracle.py
reports/r31/build_contract.py
reports/r31/validate_and_seal.py

tests/test_v4_22_independent_audit_contract.py
or an additional dedicated R31R1 test file

reports/r31r1/*
docs/evidence/r31r1/*
```

Historical R31 acceptance/seal/evidence artifacts must not be rewritten to conceal the external audit result.

If existing R31 source files are modified, the historical R31 candidate remains recoverable from Git commit/tag.

Do not modify V4-21 business semantics merely to make the audit pass.

---

# 7. Current State Must Remain Frozen

After repair:

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

V4_22_FINAL_PASS = NOT_GRANTED
V4_22_ACCEPTED_HEAD = NOT_CREATED
```

No real evidence may be manufactured by design fixtures.

---

# 8. Tested Source Governance

Create a new R31R1 exact tested source.

Required:

```text
exact branch = codex/v4-system-reform
exact tested source commit
immutable annotated tag
clean checkout proof
post-test delta
```

Recommended tag:

```text
codex/r31r1-v4-22-audit-contract-repair-tested-source-20261005
```

Post-test semantic drift is forbidden.

Prefer an explicit allowlist of closure artifacts rather than treating arbitrary `reports/r31r1/*.json` or `docs/evidence/r31r1/*.md` as automatically evidence-only.

---

# 9. Regression

Run the full previously declared R31 regression scope plus all R31R1 tests.

Expected inherited debt only:

```text
test_v3_is_the_single_unified_workbench_entry
test_hot_rank_route_skips_request_scope
test_send_marks_disconnected_client_closed
```

Required:

```text
0 new failures
0 errors
0 skipped
0 deselected
```

Do not hide inherited failures.

---

# 10. Required Evidence

Recommended:

```text
reports/r31r1/
  FINAL_VERDICT_OPEN_ITEM_GATE.json
  OPEN_ITEM_CLOSURE_BINDING_GATE.json
  SESSION_PARENT_LINKAGE_GATE.json
  SESSION_PARENT_NEGATIVE_MATRIX.json
  ITEM_AUTHORITY_VALIDATION_GATE.json
  ITEM_AUTHORITY_NEGATIVE_MATRIX.json
  OPEN10_REFERENTIAL_INTEGRITY_RECHECK.json
  PROTECTED_BYTES.json
  LOCAL_TEST_SUMMARY.json
  CLEAN_REGRESSION.json
  TESTED_SOURCE_GOVERNANCE.json
  R31R1_CANDIDATE_SEAL.json

docs/evidence/r31r1/
  R31R1_REPAIR_ACCEPTANCE.md
  task/master/external-audit copies
```

---

# 11. Exit

Required local exit:

```text
R31R1_LOCAL_REPAIR =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

R31_FINAL_VERDICT_OPEN_ITEM_ENFORCEMENT =
PASS_LOCAL_REPAIRED

R31_OPEN10_SESSION_REFERENTIAL_INTEGRITY =
PASS_LOCAL_REPAIRED

R31_ITEM_LEVEL_AUTHORITY_VALIDATION =
PASS_LOCAL_REPAIRED

V4_22_CONTRACT_DESIGN =
LOCAL_READY_FOR_EXTERNAL_AUDIT_AFTER_R31R1

V4_22_FINAL_AUDIT_ENTRY =
BLOCKED_WAIT_REAL_GATES

V4_22_FINAL_PASS =
NOT_GRANTED

V4_22_ACCEPTED_HEAD =
NOT_CREATED

NEXT =
STOP_WAIT_R31R1_INDEPENDENT_EXTERNAL_AUDIT
```

Commit/push is not external acceptance.
