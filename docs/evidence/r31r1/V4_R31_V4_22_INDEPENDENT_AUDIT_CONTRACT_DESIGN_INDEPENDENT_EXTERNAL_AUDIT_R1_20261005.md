# V4 R31｜V4-22 Independent Audit Contract Design Independent External Audit R1｜2026-10-05

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`

Drive authority restored before repository audit:

- `V4_R30R1_V4_21_NATIVE_SESSION_REPAIR_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md`
- `V4_22_R31_INDEPENDENT_AUDIT_CONTRACT_DESIGN_TASK_20261004.md`
- `V4_NEXT_ROUND_EXECUTION_MASTER_R31_20261004.md`

Execution baseline:

`791543c3bdbd4b80b2679b447d257cc27dd504ad`

Audited remote HEAD:

`2ec72a9fa5bd72a4049c55009466668ea1d219a9`

Exact tested source:

`672f0cbf129c80e0b76e1a2574403a6b1a4a0414`

Immutable tested tag:

`refs/tags/codex/r31-independent-audit-contract-tested-source-20261004`

---

## 1. Unique External Decision

```text
R31_EXTERNAL_AUDIT =
PARTIAL_PASS_R31R1_REQUIRED

R31_SCOPE_AND_HARD_BOUNDARY = PASS
R31_DOMAIN_STATUS_AND_OPEN_REGISTRY = PASS_KEEP
R31_CROSS_STAGE_CARRY = PASS_KEEP
R31_TESTED_SOURCE_GOVERNANCE = PASS_KEEP
R31_PROTECTED_STATE = PASS_KEEP
R31_CLEAN_REGRESSION = PASS_KEEP_SCOPED

R31_FINAL_VERDICT_OPEN_ITEM_ENFORCEMENT =
FAIL_P0

R31_OPEN10_SESSION_REFERENTIAL_INTEGRITY =
FAIL_P0

R31_ITEM_LEVEL_AUTHORITY_VALIDATION =
FAIL_P1

V4_22_CONTRACT_DESIGN =
BLOCKED_PENDING_R31R1

V4_22_FINAL_AUDIT_ENTRY =
BLOCKED_WAIT_REAL_GATES

V4_22_FINAL_PASS =
NOT_GRANTED

V4_22_ACCEPTED_HEAD =
NOT_CREATED

NEXT =
R31R1_FINAL_VERDICT_OPEN_ITEM_AND_SESSION_LINKAGE_REPAIR
```

R31 is not rejected as an architecture. The 11-domain audit model, status vocabulary, open-item registry, cross-stage carry, protected-state discipline and tested-source governance are materially correct.

The blocking defects are concentrated in two machine-enforcement points:

1. the final verdict formula does not enforce explicit closure of blocking open items;
2. the OPEN-10 referential-integrity oracle accepts an insufficiently identified session parent.

A third P1 issue exists in item-level authority validation.

---

## 2. Drive Authority Synchronization｜PASS

The latest project task folder was synchronized before repository inspection.

The latest authoritative sequence is:

```text
R30R1 external audit
→ R31 V4-22 contract design task
→ R31 master execution card
```

No later R32 task exists in the current Drive task folder.

R31 is explicitly:

```text
CONTRACT_DESIGN_ONLY
```

and is not the final V4-22 independent audit.

---

## 3. Repository Head / Scope｜PASS

Current branch HEAD:

`2ec72a9fa5bd72a4049c55009466668ea1d219a9`

Commit message:

```text
docs(r31): seal exact clean regression and audit contract candidate
```

From baseline `791543c3...` to current HEAD:

```text
ahead_by = 2
behind_by = 0
```

The two-step source topology is:

```text
791543c3... baseline
        ↓
672f0cbf... tested source
        ↓
2ec72a9f... evidence-only closure
```

Changes are limited to:

```text
config/v4_22_independent_audit_contract_v1.json
reports/r31/*
docs/evidence/r31/*
tests/test_v4_22_independent_audit_contract.py
```

No V4 business writer, migration writer, production route, Focus route, default UI route, production database or accepted head was modified.

This matches the R31 stage boundary.

---

## 4. R30R1 Predecessor Binding｜PASS

R31 correctly consumes the externally accepted predecessor state:

```text
R30R1_EXTERNAL_AUDIT =
PASS_FINAL_NATIVE_SESSION_STATUS_AND_OWNER_BINDING_REPAIR

V4_21_CONTRACT_DESIGN =
EXTERNALLY_ACCEPTED_SCOPED

V4_21_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_REAL_OBSERVATION
```

The R30R1 P2 carry is preserved as OPEN-10.

---

## 5. Domain Registry / Status Vocabulary｜PASS_KEEP

R31 freezes all 11 required audit domains:

```text
A22-DATA
A22-ALGORITHM
A22-PUBLICATION
A22-SHADOW
A22-UI
A22-FORWARD
A22-MIGRATION
A22-CUTOVER
A22-ROLLBACK
A22-GOVERNANCE
A22-REGRESSION
```

Audit item count:

```text
92
```

Domain distribution:

```text
DATA         7
ALGORITHM    8
PUBLICATION  9
SHADOW       7
UI          10
FORWARD     14
MIGRATION    8
CUTOVER      8
ROLLBACK     8
GOVERNANCE   9
REGRESSION   4
```

Required status vocabulary is present:

```text
PASS
FAIL
BLOCKED
NOT_VERIFIABLE
NOT_APPLICABLE
OPEN_NONBLOCKING_DEBT
WAIT_REAL_EVIDENCE
```

All 92 audit items contain the required schema fields and all are currently conservatively classified as `NOT_VERIFIABLE` or `WAIT_REAL_EVIDENCE`.

No premature PASS is issued.

---

## 6. Open-Item Registry｜PASS_KEEP_FOR_CARRY

All ten required current open items are retained:

```text
OPEN-01 R25 WAIT_ACCEPTED_DAILY_INPUT
OPEN-02 REAL_SHADOW_OBSERVATIONS = 0
OPEN-03 V4_17_FINAL_ACCEPTANCE = NOT_GRANTED
OPEN-04 V4_17G = NOT_GRANTED
OPEN-05 MIGRATION_REPLAY_PASS = NOT_GRANTED
OPEN-06 production_permission[*] = false
OPEN-07 DEFAULT_UI_CUTOVER = false
OPEN-08 REAL_CONTINUED_FORWARD_OBSERVATION = NOT_STARTED
OPEN-09 R26_A01 historical V3 regression debt
OPEN-10 R30R1_P2_LEDGER_REFERENTIAL_INTEGRITY_VECTOR
```

OPEN-01 through OPEN-08 each retain non-empty blocking scope across all five capabilities.

OPEN-09 and OPEN-10 remain explicitly nonblocking carry records at the registry level.

R31 also preserves the complete 18-entry cross-stage remediation registry. Independent comparison against:

`reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R10.json`

shows the 18 `entries` are exactly equal to:

`reports/r31/OPEN_ITEM_REGISTRY.json -> cross_stage_entries`.

This includes `AUD-AMOUNT-A-06` and the other pre-existing cross-stage items.

---

# 7. P0 Finding｜Final Verdict Ignores Blocking Open-Item Closure

## 7.1 Task Requirement

R31 task section 14 states:

```text
No item may disappear merely because a later stage exists.

Closure requires:
explicit disposition
exact evidence
authority
date/source
independent recheck
```

OPEN-01 through OPEN-08 currently have blocking scope.

The contract also records:

```text
NO_AUTO_CLOSE
```

for these items.

## 7.2 Actual Oracle

`reports/r31/audit_oracle.py -> final_verdict()`

evaluates:

```text
required blocking audit_items
runtime gate receipts
source governance
unresolved_blockers argument
```

but does not evaluate:

```text
contract["open_items"]
```

and does not require explicit closure receipts for OPEN-01 through OPEN-08.

The function therefore has no machine path enforcing the task’s mandatory open-item closure protocol.

## 7.3 Direct Contradiction in Tests

`tests/test_v4_22_independent_audit_contract.py`

contains a future-simulation test that:

```text
marks all required audit items PASS
creates synthetic runtime gate receipts
does not explicitly close OPEN-01..OPEN-08
does not submit the required open-item closure evidence
```

and expects:

```text
formula_result == V4_22_FINAL_PASS
```

The function still sets:

```text
acceptance_granted = false
production_grant = false
```

which correctly prevents the current design oracle from issuing a live grant.

However, the frozen formula semantics are still wrong: the formula can report `V4_22_FINAL_PASS` while blocking open items have not completed their required explicit disposition protocol.

## 7.4 Consequence

This violates:

```text
NO_AUTO_CLOSE
```

and creates a future false-pass path.

Classification:

```text
R31_FINAL_VERDICT_OPEN_ITEM_ENFORCEMENT =
FAIL_P0
```

This is a contract-design blocker, not evidence that any current production permission was granted.

Current real state remains safely NOT_READY.

---

# 8. P0 Finding｜OPEN-10 Session Parent Is Under-Identified

## 8.1 Intended Rule

R30R1 carried OPEN-10 because V4-21 did not explicitly prove:

```text
orphan real event without session -> fail closed
orphan real outcome without session -> fail closed
```

R31 adds:

```text
A22-V421-REFINT-01
A22-V421-REFINT-02
```

This direction is correct.

## 8.2 Actual Parent Key

`reports/r31/audit_oracle.py` defines:

```text
PARTITION =
capability
evidence_lane
model_contract_id
parameter_digest
state_lineage_id
```

A session is added to the accepted-parent set when those five fields plus a small authority/status subset are valid.

The referential check does not require the V4-21 session identity:

```text
market_session_id
```

and does not bind the child to the same:

```text
source_publication
source_digest
trade_date / T0 relationship
```

## 8.3 Full V4-21 Session Schema Is Not Enforced

V4-21 session ledger requires, among other fields:

```text
source_publication
source_digest
accepted_at
source_quality
trade_date
market_session_id
market_session_ordinal
calendar_identity
publication_id
publication_revision
session_receipt_id
slot_receipt_digest
native_session_authority_id
native_session_authority_sha256
native_session_status
projection_evaluable
projection_evaluable_reason
```

The R31 positive fixture does not contain most of these fields.

Therefore a synthetic row that is not a valid V4-21 session-ledger row can still become a referential parent.

## 8.4 Counterexample 1｜Malformed Parent False Pass

A session row containing only:

```text
five-part partition
exact native authority id/digest
ACCEPTED_ON_TIME
PIT_OBSERVED
accepted_real_publication = true
execution_mode = SHADOW
```

but missing:

```text
market_session_id
trade_date
source_publication
source_digest
session_receipt_id
...
```

is accepted by the current oracle.

A real event in the same five-part partition then returns:

```text
PASS_DESIGN_ONLY
```

instead of failing closed.

## 8.5 Counterexample 2｜Cross-Day Parent False Pass

Example:

```text
accepted session:
trade_date = 2026-10-04

event:
T0 = 2026-10-05

same capability/lane/model/parameter/lineage
```

The current oracle treats the 2026-10-04 session as a valid parent of the 2026-10-05 event because date/publication identity is not part of the relationship.

The same issue applies to an outcome row when another session exists somewhere in the same large partition.

## 8.6 Required Repair Direction

The referential parent must be bound to exact observation provenance, not only the five-field evidence partition.

At minimum the independent oracle must validate the full required V4-21 ledger schemas and use a parent identity containing exact publication/session identity.

Recommended common parent linkage:

```text
capability
evidence_lane
model_contract_id
parameter_digest
state_lineage_id
source_publication
source_digest
```

plus validation of the native session’s exact:

```text
market_session_id
trade_date
publication_id
session_receipt_id
```

For event rows, the implementation should also enforce the accepted T0/session-date relation defined by V4-21.

For outcome rows, use the exact observation publication/session that processed the outcome revision; do not assume `due_date == processing session date`.

`projection_evaluable` remains a separate dimension. A native `ACCEPTED_ON_TIME` row with `projection_evaluable=false` may remain a referential parent if it is otherwise a complete exact accepted session, consistent with R30R1.

Classification:

```text
R31_OPEN10_SESSION_REFERENTIAL_INTEGRITY =
FAIL_P0
```

---

# 9. P1 Finding｜Item-Level Authority Is Not Independently Validated

`validate_contract()` independently verifies:

```text
audit_domains[].authority_bindings
```

but it does not independently read and verify every:

```text
audit_item.authority
audit_item.evidence_refs
open_item.authority
open_item.evidence_refs
```

against exact path/digest/contract_id.

The current generated contract appears internally consistent, but the validator does not fail closed if a future item-level authority or evidence reference is mutated while the domain-level registry remains valid.

The final verdict later compares an audit receipt to the contract’s item authority, so a self-consistent but incorrect item authority could become authoritative unless the independent item-level binding is validated first.

Classification:

```text
R31_ITEM_LEVEL_AUTHORITY_VALIDATION =
FAIL_P1
```

R31R1 should add mutation vectors for:

```text
wrong item authority path
wrong item authority sha256
wrong contract_id
wrong evidence_ref
domain/item authority mismatch
open-item authority mismatch
```

---

## 10. OPEN-10 Design Vector Coverage｜PARTIAL

Current negative vectors correctly catch the simplest case:

```text
sessions = []
event exists
→ BLOCKED_AFFECTED_SCOPE

sessions = []
outcome exists
→ BLOCKED_AFFECTED_SCOPE
```

They also test cross-partition mismatch and invalid native authority/status.

What is missing is the harder same-partition false-parent class:

```text
same five-part partition
but wrong session/publication/date
```

and:

```text
malformed session row
that is not valid under V4-21 required schema
```

Therefore OPEN-10 is not externally closed.

---

## 11. Tested Source Governance｜PASS_KEEP

Annotated tag:

`codex/r31-independent-audit-contract-tested-source-20261004`

resolves exactly to:

`672f0cbf129c80e0b76e1a2574403a6b1a4a0414`

Current HEAD is one closure commit ahead:

`2ec72a9fa5bd72a4049c55009466668ea1d219a9`

The post-test delta is limited to closure/evidence artifacts:

```text
docs/evidence/r31/R31_CONTRACT_ACCEPTANCE.md
reports/r31/CLEAN_CHECKOUT_PROOF.json
reports/r31/CLEAN_REGRESSION.json
reports/r31/INDEPENDENT_AUDIT_CONTRACT_GATE.json
reports/r31/LOCAL_TEST_SUMMARY.json
reports/r31/R31_CONTRACT_CANDIDATE_SEAL.json
reports/r31/STAGE_CONTRACT.json
reports/r31/TESTED_SOURCE_GOVERNANCE.json
reports/r31/clean-output.txt
reports/r31/clean-summary.json
reports/r31/clean-tests.xml
```

No post-test implementation drift exists in the actual current R31 candidate.

This area is PASS_KEEP.

R31R1 may tighten the whitelist to an explicit closure-artifact set, but this is not the reason R31 is blocked.

---

## 12. Regression｜PASS_KEEP_SCOPED

Exact clean tested source:

```text
406 tests
403 passed
3 inherited failures
0 errors
0 skipped
0 deselected
```

Inherited failures remain:

```text
tests.upgrade_v3.test_v3_unified_entry::test_v3_is_the_single_unified_workbench_entry
tests.upgrade_v3.test_p01_01_lock_scope::test_hot_rank_route_skips_request_scope
tests.upgrade_v3.test_p01_01_lock_scope::test_send_marks_disconnected_client_closed
```

No new R31 regression is shown in the declared scope.

This remains separate R26-A01 debt and is not the new R31 blocker.

---

## 13. Protected State｜PASS_KEEP

Current protected state remains:

```text
R25 = WAIT_ACCEPTED_DAILY_INPUT
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
V4_17G = NOT_GRANTED
MIGRATION_REPLAY_PASS = NOT_GRANTED
REAL_CONTINUED_FORWARD_OBSERVATION = NOT_STARTED

production_permission[*] = false
Focus_source_cutover = false
DEFAULT_UI_CUTOVER = false
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

No current production permission or final acceptance was falsely granted.

---

## 14. PASS_KEEP Areas

R31R1 must not reopen the following areas unless a direct dependency is discovered:

```text
11 audit domains
7-value status vocabulary
92-item audit matrix structure
current conservative NOT_VERIFIABLE / WAIT_REAL_EVIDENCE statuses
10-item open registry existence
18-entry cross-stage registry carry
Amount A separation
FEP separate-acceptance rule
R30R1 native session status repair
Production authority fail-closed rule
protected current state
no V4_22 accepted head
tested-source tag/clean-checkout pattern
current no-grant behavior
R26-A01 inherited debt classification
```

---

## 15. Required R31R1 Repair

R31R1 must be narrow and machine-verifiable.

Required:

### P0-A Final Verdict Open-Item Enforcement

Add exact closure receipt handling.

`V4_22_FINAL_PASS` must be impossible while any blocking open item lacks the required explicit closure disposition.

Required closure fields:

```text
item_id
capability_scope
explicit_disposition
exact_evidence
authority
date_source
independent_recheck
canonical_sha256 / exact receipt binding
```

OPEN-09 remains nonblocking debt.

OPEN-10 must retain its explicit independent disposition requirement before final project/V4-22 acceptance.

### P0-B Exact Session Parent Linkage

The independent referential-integrity oracle must validate full V4-21 required schemas and exact publication/session parent identity.

Do not allow:

```text
any session somewhere in same five-part partition
```

to satisfy the parent condition.

### P1 Item-Level Authority Validation

Every item-level authority/evidence reference must be independently validated against exact bytes and domain authority.

---

## 16. Mandatory Negative Vectors for R31R1

At minimum add:

```text
R31R1-FINAL-01
all audit items PASS + all runtime gates PASS
but OPEN-01 unresolved
→ NOT FINAL PASS

R31R1-FINAL-02
OPEN-01 claims closed without exact canonical closure receipt
→ BLOCKED

R31R1-FINAL-03
wrong capability_scope in closure receipt
→ BLOCKED

R31R1-FINAL-04
OPEN-09 remains open nonblocking debt
→ does not by itself block final formula

R31R1-FINAL-05
OPEN-10 lacks explicit independent disposition
→ NOT FINAL PASS

R31R1-REFINT-01
event and session share five-part partition
but source_publication/source_digest differ
→ BLOCKED_AFFECTED_SCOPE

R31R1-REFINT-02
event T0 belongs to another session/publication
→ BLOCKED_AFFECTED_SCOPE

R31R1-REFINT-03
session lacks market_session_id/trade_date/publication/session receipt fields
→ BLOCKED_AFFECTED_SCOPE

R31R1-REFINT-04
outcome shares five-part partition
but belongs to different observation publication
→ BLOCKED_AFFECTED_SCOPE

R31R1-REFINT-05
complete ACCEPTED_ON_TIME + projection_evaluable=false session
with exact publication/session identity
→ valid referential parent but not countable session/streak success

R31R1-AUTH-01
mutated audit-item authority sha/path/id
→ contract validation FAIL

R31R1-AUTH-02
mutated open-item evidence ref
→ contract validation FAIL

R31R1-AUTH-03
domain authority and item authority diverge
→ contract validation FAIL
```

---

## 17. Exit Requirement

R31R1 may only report:

```text
R31R1_LOCAL_REPAIR =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

V4_22_CONTRACT_DESIGN =
LOCAL_READY_FOR_EXTERNAL_AUDIT_AFTER_R31R1

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
STOP_WAIT_R31R1_INDEPENDENT_EXTERNAL_AUDIT
```

Push/commit is not external acceptance.

---

## 18. Final

```text
R31_EXTERNAL_AUDIT =
PARTIAL_PASS_R31R1_REQUIRED

NEXT =
R31R1_FINAL_VERDICT_OPEN_ITEM_AND_SESSION_LINKAGE_REPAIR
```
