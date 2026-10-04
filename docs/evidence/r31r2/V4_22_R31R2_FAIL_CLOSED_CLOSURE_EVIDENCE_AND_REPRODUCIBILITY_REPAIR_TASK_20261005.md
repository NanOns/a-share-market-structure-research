# V4-22 R31R2｜Fail-Closed Closure Evidence + Child Ledger + Reproducibility Repair Task｜2026-10-05

## 0. Mission

Perform one narrow follow-up repair after R31R1 external audit.

Execution baseline:

`abe8311d55db3fecc086a77c3ce8a16f4309df54`

External authority:

`V4_R31R1_V4_22_AUDIT_CONTRACT_REPAIR_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md`

This remains:

```text
CONTRACT_DESIGN_ONLY
```

Repair only:

```text
P0-A closure exact_evidence / closure authority is not independently read back
P0-B event/outcome missing or unknown evidence_lane can be silently skipped
P1   repaired canonical contract is not deterministically reproducible from active builder
```

---

# 1. PASS_KEEP Boundary

Do not reopen:

```text
R31/R31R1 domain topology
92 audit items
10 open items
status vocabulary
cross-stage carry
OPEN-09 nonblocking debt
OPEN-01..08 + OPEN-10 final-formula consumption
publication/source_digest parent linkage
event T0 == parent trade_date
outcome due_date independence
projection_evaluable=false referential-parent rule
item-level authority validation
tested-source governance model
current protected heads/state
R26-A01 inherited regression debt
```

---

# 2. P0-A｜Closure Evidence Must Be Independently Readable

## 2.1 Problem

Current final formula accepts a closure after canonical digest binding even when:

```text
exact_evidence = [{"path":"SIM_ONLY","sha256":"SIM_ONLY"}]
```

because `exact_evidence` is only checked for truthiness.

This does not satisfy:

```text
NO_SELF_ASSERTED_CLOSURE
EXACT_EVIDENCE
INDEPENDENT_RECHECK
```

---

## 2.2 Required Closure Binding Schema

Add an explicit closure binding schema.

Recommended:

```text
open_item_closure_bindings[item_id] = {
  "item_id": "...",
  "capability_scope": [...],
  "canonical_sha256": "...",
  "closure_authority": {
    "path": "...",
    "sha256": "...",
    "contract_id": "..."   // when applicable
  },
  "exact_evidence": [
    {
      "path": "...",
      "sha256": "...",
      "contract_id": "..." // when applicable
    }
  ]
}
```

The receipt itself must contain the same exact immutable identities.

Do NOT use only:

```text
receipt.authority == item.authority
```

as closure proof.

The authority that originally recorded an item as OPEN is not automatically authority that it later closed.

---

## 2.3 Required Verification

Before a closure can satisfy final formula:

```text
read closure_authority by exact path + SHA256 + contract_id
read every exact_evidence binding by exact path + SHA256 + contract_id
verify receipt canonical SHA
verify item_id
verify capability_scope
verify explicit_disposition
verify date_source
verify independent_recheck == true
verify closure authority is explicitly authorized for this closure
```

Any unavailable or malformed binding fails closed.

No latest/mtime/glob fallback.

---

# 3. P0-B｜All Ledger Rows Must Validate Required Schema Before Lane Filtering

## 3.1 Problem

Current child loop performs:

```python
if row.get("evidence_lane") not in REAL_LANES:
    continue
```

before required-field validation.

Missing/unknown lane can therefore disappear from the audit.

---

## 3.2 Required Order

Read exact V4-21:

```text
evidence_lanes
session_ledger.required
event_cohort_ledger.required
due_outcome_ledger.required
```

For every supplied row in all three ledgers:

```text
1. validate every required field exists
2. validate evidence_lane is one of the exact V4-21 lane ids
3. validate lane-required namespace/origin/publication semantics where applicable
4. recognized non-real diagnostic lane:
      excluded from real parent/count logic
      but remains schema-valid
5. recognized real lane:
      continue exact parent linkage
6. missing or unknown lane:
      BLOCKED_AFFECTED_SCOPE
```

Do not interpret missing/unknown as non-real.

---

# 4. P1｜Repair Reproducibility / Builder Governance

## 4.1 Problem

Current canonical contract is `1.0.1`, but `reports/r31/build_contract.py` still regenerates R31 `1.0.0`.

The canonical contract also still advertises:

```text
STOP_WAIT_R31_INDEPENDENT_EXTERNAL_AUDIT
```

instead of the current R31R1/R31R2 stage identity.

---

## 4.2 Required Solution

Choose exactly one governed model:

### Option A｜Latest Builder

Update the active builder so a clean rebuild deterministically reproduces the latest canonical contract.

or

### Option B｜Historical Builder Freeze + Repair Builder

Keep the old R31 builder only as historical reconstruction, but:

```text
- add explicit historical-only guard
- prevent accidental overwrite of newer canonical contract
- add new deterministic R31R2 repair builder
- new builder must reproduce exact latest contract bytes from the declared baseline
```

Preferred if preserving historical generation semantics matters.

Align:

```text
version
repair provenance
next_stage
tested source metadata
```

without rewriting old R31 evidence.

---

# 5. Mandatory Negative / Counterfactual Vectors

Add at minimum:

```text
R31R2-CLOSURE-01
closure exact_evidence path does not exist
→ FINAL_AUDIT_BLOCKED

R31R2-CLOSURE-02
closure exact_evidence SHA mismatch
→ FINAL_AUDIT_BLOCKED

R31R2-CLOSURE-03
closure evidence contract_id mismatch
→ FINAL_AUDIT_BLOCKED

R31R2-CLOSURE-04
exact_evidence = SIM_ONLY placeholder
→ FINAL_AUDIT_BLOCKED

R31R2-CLOSURE-05
closure authority is only the predecessor OPEN authority
with no explicit closure authority
→ FINAL_AUDIT_BLOCKED

R31R2-CLOSURE-06
closure authority path/SHA mismatch
→ FINAL_AUDIT_BLOCKED

R31R2-CLOSURE-07
valid exact closure authority + all exact evidence + canonical receipt
→ formula may proceed
→ still no acceptance_granted / production_grant in design oracle
```

```text
R31R2-LEDGER-01
real event missing evidence_lane
→ BLOCKED_AFFECTED_SCOPE

R31R2-LEDGER-02
real outcome missing evidence_lane
→ BLOCKED_AFFECTED_SCOPE

R31R2-LEDGER-03
session evidence_lane unknown
→ BLOCKED_AFFECTED_SCOPE

R31R2-LEDGER-04
event evidence_lane typo/unknown
→ BLOCKED_AFFECTED_SCOPE

R31R2-LEDGER-05
outcome evidence_lane typo/unknown
→ BLOCKED_AFFECTED_SCOPE

R31R2-LEDGER-06
recognized HISTORICAL_REPLAY with complete schema
→ excluded from real gate
→ no false blocker

R31R2-LEDGER-07
recognized RECONSTRUCTED_ASOF with complete schema
→ excluded from real gate
→ no false blocker

R31R2-LEDGER-08
SHADOW_REAL complete exact row
→ normal exact parent logic
```

```text
R31R2-BUILD-01
clean rebuild from declared baseline
→ exact canonical contract SHA

R31R2-BUILD-02
re-run repair builder
→ idempotent same SHA

R31R2-BUILD-03
historical builder attempts overwrite newer contract
→ explicitly blocked if Option B

R31R2-BUILD-04
canonical next_stage
→ STOP_WAIT_R31R2_INDEPENDENT_EXTERNAL_AUDIT
```

---

# 6. Required Source Changes

Prefer narrow changes.

Allowed:

```text
config/v4_22_independent_audit_contract_v1.json
reports/r31/audit_oracle.py
reports/r31/build_contract.py               // only if Option A / guard
reports/r31r2/*
tests/test_v4_22_r31r2_repair.py
tests/test_v4_22_independent_audit_contract.py // only direct dependency
docs/evidence/r31r2/*
```

Do not modify V4-21 business semantics.

Do not rewrite historical R31/R31R1 audit evidence to hide failures.

---

# 7. Current State Must Remain Frozen

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

No real evidence may be manufactured.

No current open item may be closed.

---

# 8. Regression / Tested Source Governance

Create a new exact R31R2 tested source.

Recommended tag:

```text
codex/r31r2-v4-22-audit-contract-failclosed-tested-source-20261005
```

Required:

```text
exact branch
exact tested source
annotated immutable tag
clean checkout
explicit evidence-only closure allowlist
0 new failures
0 errors
0 skipped
0 deselected
```

Inherited R26-A01 failures remain separately visible.

---

# 9. Required Local Exit

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
