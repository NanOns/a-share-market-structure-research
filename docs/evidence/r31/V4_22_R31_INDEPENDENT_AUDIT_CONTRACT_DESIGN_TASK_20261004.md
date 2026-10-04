# V4-22 R31｜Independent Audit Contract Design Task｜2026-10-04

## 0. Mission

Freeze the machine contract and audit matrix for V4-22 Independent Audit.

This round is:

```text
CONTRACT_DESIGN_ONLY
```

It is NOT the final V4-22 audit.

Execution baseline:

`791543c3bdbd4b80b2679b447d257cc27dd504ad`

External authority:

`V4_R30R1_V4_21_NATIVE_SESSION_REPAIR_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md`

---

## 1. Normative Stage Definition

REV4 V4-22:

```text
Independent Audit
=
data
algorithm
publication
migration
UI
Forward
rollback
independent acceptance

open items do not automatically close
```

V4-22 must audit accepted facts; it must not manufacture missing evidence.

---

## 2. Machine Contract

Create, recommended:

```text
config/v4_22_independent_audit_contract_v1.json
```

Freeze:

```text
audit domain registry
capability scope
evidence classes
authority bindings
status vocabulary
blocking rules
open-item carry rules
independent oracle requirements
tested-source governance
final verdict formula
```

---

## 3. Status Vocabulary

At minimum:

```text
PASS
FAIL
BLOCKED
NOT_VERIFIABLE
NOT_APPLICABLE
OPEN_NONBLOCKING_DEBT
WAIT_REAL_EVIDENCE
```

Do not collapse:

```text
BLOCKED
NOT_VERIFIABLE
OPEN_NONBLOCKING_DEBT
```

into generic FAIL/PASS.

Every item needs:

```text
item_id
domain
capability_scope
required_evidence
authority
current_status
blocking_scope
disposition_rule
evidence_refs
```

---

## 4. Audit Domains

At minimum freeze these domains:

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

Optional FEP branch must remain separately scoped and may not inherit Core acceptance.

---

## 5. Data Audit

Must verify:

```text
accepted Data Head
calendar/trade-date correctness
PIT source identity
Raw/Adjusted integrity
Universe / membership basis
capability-scoped degraded sources
no silent latest/mtime discovery
```

Historical accepted data through current Data Head may PASS independently.

Future real-session data remains separate.

---

## 6. Algorithm Audit

Must verify:

```text
accepted algorithm contracts
field registry / producer / time semantics
AST/parameter identity where required
deterministic replay
no same-day feedback
no duplicate episode
revision idempotency
capability dependency graph
```

Contract-design acceptance does not substitute for real runtime evidence.

---

## 7. Publication / Realtime Audit

Audit:

```text
clock authority
source readiness
Observation Slot V2
exact daily-input authority
Shadow publication identity
state lineage
accepted session status
native authority
same-day revision
CAS
```

Current real status must remain:

```text
WAIT_REAL_EVIDENCE
```

while R25 has no accepted target-session package.

---

## 8. Shadow Stable / Forward Audit

Do not recompute or grant gates ad hoc.

Read exact accepted authority receipts for:

```text
SHADOW_STABLE_PASS[capability]
FORWARD_GATE[capability]
```

Verify:

```text
real PIT sessions only
model/parameter partition
20 consecutive accepted-session semantics
complete Validation Cohort
controls / benchmarks
right censor
observed vs corrected revisions
no historical replay sample inflation
```

Current gates remain NOT_GRANTED.

---

## 9. UI Audit

Audit separately:

```text
V4-17 read-only Shadow UI
same context token
no fallback
NO_REAL_SHADOW_DATA behavior
mixed Legacy/V4/Shadow module identity
Focus write permission
default UI source resolution
deep-link immutability
cache/session invalidation
```

Current V4-17 engineering may PASS while:

```text
V4_17_FINAL_ACCEPTANCE
```

remains blocked by missing real publication.

---

## 10. Migration Audit

Verify future accepted V4-18 runtime evidence for:

```text
prestate inheritance
open episode preservation
pending settlement ownership
user pin/manual work preservation
namespace mapping
cutover gap
idempotent replay
rollback
```

R27 contract-design PASS is not `MIGRATION_REPLAY_PASS`.

Current status:

```text
WAIT_REAL_EVIDENCE / BLOCKED
```

---

## 11. Cutover Audit

Audit V4-19/V4-20 only from accepted runtime receipts.

Verify per capability:

```text
SHADOW_STABLE_PASS
FORWARD_GATE
MIGRATION_REPLAY_PASS
required dependency permissions
production_permission
Focus source route
default UI route
```

No GLOBAL V4 PASS.

Current:

```text
production_permission[*] = false
Focus source cutover = false
DEFAULT_UI_CUTOVER = false
```

---

## 12. Rollback Audit

Must independently verify:

```text
capability-scoped rollback
route CAS
accepted history preservation
pending settlement preservation
user pin/manual work preservation
Shadow/Production evidence retention
Legacy recovery path
cutover-gap reconciliation
```

A rollback design vector is not a runtime rollback drill.

---

## 13. Forward Observation Audit

Audit V4-21:

```text
evidence lanes
native session authority
accepted-session denominator
event/cohort ledger
due/outcome ledger
right censor
model/parameter partitions
Shadow vs Production continuity
gate readback ownership
```

No new settlement owner.

---

## 14. Mandatory Open-Item Carry

Create an explicit open-item registry.

At minimum current items include:

```text
OPEN-01:
R25 WAIT_ACCEPTED_DAILY_INPUT

OPEN-02:
REAL_SHADOW_OBSERVATIONS = 0

OPEN-03:
V4_17_FINAL_ACCEPTANCE = NOT_GRANTED

OPEN-04:
V4_17G = NOT_GRANTED

OPEN-05:
MIGRATION_REPLAY_PASS = NOT_GRANTED

OPEN-06:
production_permission[*] = false

OPEN-07:
DEFAULT_UI_CUTOVER = false

OPEN-08:
REAL_CONTINUED_FORWARD_OBSERVATION = NOT_STARTED

OPEN-09:
R26_A01 historical V3 regression debt (3 inherited failures)

OPEN-10:
R30R1_P2_LEDGER_REFERENTIAL_INTEGRITY_VECTOR
```

No item may disappear merely because a later stage exists.

Closure requires:

```text
explicit disposition
exact evidence
authority
date/source
independent recheck
```

---

## 15. R30R1 P2 Audit Vector

V4-22 contract design must explicitly register:

```text
A22-V421-REFINT-01
orphan real event without matching accepted-session partition
→ BLOCKED_AFFECTED_SCOPE

A22-V421-REFINT-02
orphan real outcome without matching accepted-session partition
→ BLOCKED_AFFECTED_SCOPE
```

This may be implemented as an independent audit/design oracle.

Do not silently modify V4-21 business semantics.

---

## 16. Independent Oracle Rules

V4-22 oracle must not import:

```text
business writer
migration writer
cutover writer
production route writer
```

It may import immutable schema/constants only when the audit independently recomputes identities/digests.

Prefer:

```text
raw DB/file readback
independent digest
independent relation checks
independent authority-path verification
```

---

## 17. Tested Source Governance

Final audit must bind:

```text
exact audited branch
exact tested source commit
immutable annotated tag
clean checkout proof
post-test delta
```

If final HEAD differs from tested source:

```text
only evidence-only delta allowed
```

Otherwise final audit is blocked.

---

## 18. Final Verdict Formula

Freeze a deterministic final verdict.

Recommended:

```text
V4_22_FINAL_PASS
only if
all required blocking audit items are PASS
AND required real gates are externally accepted
AND no unresolved P0/P1 blocker exists
AND all capability permissions match exact receipts
AND tested-source governance passes
```

Allowed non-final verdicts:

```text
FINAL_AUDIT_NOT_READY
FINAL_AUDIT_BLOCKED
CAPABILITY_SCOPED_ACCEPTANCE
```

Do not infer global PASS from partial capability acceptance.

---

## 19. Current R31 State

R31 must report truthfully:

```text
V4_22_CONTRACT_DESIGN =
LOCAL_READY_FOR_EXTERNAL_AUDIT (if contract passes)

V4_22_FINAL_AUDIT_ENTRY =
BLOCKED_WAIT_REAL_GATES

V4_22_FINAL_PASS =
NOT_GRANTED
```

Because current real state is still:

```text
R25 = WAIT_ACCEPTED_DAILY_INPUT
REAL_SHADOW_OBSERVATIONS = 0
V4_17G = NOT_GRANTED
MIGRATION_REPLAY_PASS = NOT_GRANTED
production_permission[*] = false
DEFAULT_UI_CUTOVER = false
REAL_CONTINUED_FORWARD_OBSERVATION = NOT_STARTED
```

---

## 20. Protected State

Do not modify:

```text
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_15_ACCEPTED_HEAD
V4_16 through V4_21 accepted-head absence
V4_16 activation authority
Focus source route
default UI route
real Shadow counters
production permissions
```

Do not create:

```text
V4_22_ACCEPTED_HEAD
```

---

## 21. Required Evidence

Recommended:

```text
reports/r31/
  INDEPENDENT_AUDIT_CONTRACT_GATE.json
  AUDIT_DOMAIN_REGISTRY.json
  OPEN_ITEM_REGISTRY.json
  DATA_AUDIT_MATRIX.json
  ALGORITHM_AUDIT_MATRIX.json
  PUBLICATION_SHADOW_AUDIT_MATRIX.json
  UI_AUDIT_MATRIX.json
  FORWARD_AUDIT_MATRIX.json
  MIGRATION_CUTOVER_AUDIT_MATRIX.json
  ROLLBACK_AUDIT_MATRIX.json
  REFERENTIAL_INTEGRITY_AUDIT.json
  FINAL_VERDICT_FORMULA.json
  CURRENT_AUDIT_STATE.json
  PROTECTED_BYTES.json
  LOCAL_TEST_SUMMARY.json
  CLEAN_REGRESSION.json
  R31_CONTRACT_CANDIDATE_SEAL.json
```

---

## 22. Exit

Required:

```text
V4_22_CONTRACT_DESIGN =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

V4_22_FINAL_AUDIT_ENTRY =
BLOCKED_WAIT_REAL_GATES

V4_22_FINAL_PASS =
NOT_GRANTED

V4_22_ACCEPTED_HEAD =
NOT_CREATED

NEXT =
STOP_WAIT_R31_INDEPENDENT_EXTERNAL_AUDIT
```
