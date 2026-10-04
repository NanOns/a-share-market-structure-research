# PRE16-GOV-R1｜Current Cross-Stage Audit Authority Reconciliation Task｜2026-10-04

## 0. Mission

Before V4-16 contract/runtime work, close one cross-stage governance ambiguity:

```text
historical cross-stage audit registry
!=
current cross-stage audit status authority
```

The current Stage Head still carries the original R1 remediation registry, while later independently accepted scoped producers, capability dispositions and validation debts have advanced.

This task must create a single machine-readable **current audit-status authority** without rewriting historical evidence or any V4-10～V4-15 Accepted Head.

This is governance-only.

---

# 1. Execution Baseline

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Baseline:

`a1bb12f19e758784e55a1a93acaad1954861a0fc`

Read first:

1. `V4_PRE16_STAGE10_TO_STAGE15_INDEPENDENT_ACCEPTANCE_AUDIT_R1_20261004.md`
2. this task
3. latest V4.2.2 REV4 applicable architecture
4. all current accepted heads / scoped acceptance heads / current audit dispositions

---

# 2. Required Outcome

Create a new exact current authority, recommended:

```text
data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V1.json
config/v4_cross_stage_current_audit_authority_v1.json
```

The exact names may follow repository conventions.

The authority must answer:

```text
What is accepted now?
What is still open now?
What is accumulation-only?
What is permanently unavailable historically?
What is only a nonblocking validation debt?
What can current engineering consumers rely on?
```

It must not pretend that the original R1 registry is current.

---

# 3. Preserve Historical Registry

Keep byte-identical:

```text
reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R1.json
```

and all later historical consolidation registries.

The new authority must explicitly classify them as:

```text
HISTORICAL_GOVERNANCE_SNAPSHOT
```

or an equivalent unambiguous status.

Do not mutate historical statuses in place.

---

# 4. Source of Truth for Current Status

Current status may be derived only from exact accepted evidence.

At minimum inventory and reconcile:

```text
V4_DATA_ACCEPTED_HEAD
V4_STAGE_ACCEPTED_HEAD
V4_01 ... V4_15 Accepted Heads
V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1
V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1
A04 scoped accepted/go-forward heads
parallel scoped acceptance summary heads
latest cross-stage consolidation registries
current work-package status files
latest independent external acceptance records
current nonblocking audit-item registries
```

Do not infer closure because implementation/tests exist.

A status may be `ACCEPTED_SCOPED` only when an exact independent external acceptance or accepted authority explicitly grants that scope.

---

# 5. Required Status Taxonomy

Use machine-readable current-state categories at least equivalent to:

```text
ACCEPTED_SCOPED
ACCEPTED_FULL_REQUIRED_SCOPE
OPEN_ENGINEERING
OPEN_EXTERNAL_REAUDIT
ACCUMULATION_CONTINUES
PERMANENT_CAPABILITY_LIMITATION
BLOCKED_AFFECTED_SCOPE
NONBLOCKING_VALIDATION_DEBT
SUPERSEDED_HISTORICAL_STATUS
```

Every entry must include:

```text
audit/capability id
current_state
scope
blocks_engineering_stage
blocks_shadow_entry
blocks_production_cutover
requires_real_observation_accumulation
current_authority/evidence bindings
limitations
superseded historical statuses
```

Do not collapse capability-scoped acceptance into generic PASS.

---

# 6. Required Current Entries

At minimum reconcile the original cross-stage families:

```text
A01 DM01
A02 Prior RPS
A03 forward accumulation
A04 Amount A
A05
A06 BaoStock tolerance/binding scope
A07 pre-capture historical limitation
A08 V4-09 N01
A09 V4-09 N02
OWNER
READER
```

Also register current stage-level open validation debts relevant to V4-16:

```text
HISTORICAL_PIT_EFFECTIVENESS
REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME
REALTIME_ACCEPTED_COHORT_MATURITY
V4_15_FWD_ADJ_VECTOR_01
```

If other current authoritative open items exist, include them.

Do not silently omit an open P0/P1 because it is unrelated to V4-16.

---

# 7. A01 / Data Head Rule

The current authority must recognize the actual accepted Data Head:

```text
V4_DATA_ACCEPTED_HEAD_V2
accepted_trade_date = 2026-09-30
external_acceptance =
EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN
```

Do not leave A01 globally described as the original “all-nine blocked” state if later external acceptance superseded that affected scope.

At the same time, do not claim broader historical capability than the accepted Data Head actually grants.

---

# 8. A02 Rule

Bind:

```text
data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json
```

and preserve its limitations:

```text
AS_RECORDED = false
historical_first_availability_proven = false
knowledge_lineage = RECONSTRUCTED_CORRECTED
```

Thus:

```text
scoped producer accepted
!=
historical AS_RECORDED proven
```

---

# 9. A04 / Amount A Rule

Determine current exact A04 status from the latest accepted/external evidence.

Do not derive current status from the old R1 work-package file alone.

If go-forward producer scope is accepted but historical Amount A remains blocked/warmup/accumulation, represent these as separate capability dimensions.

No current consumer may receive broader Amount A permission than exact accepted evidence grants.

---

# 10. A08/A09 Rule

Engineering candidates or clean regressions do not close A08/A09.

If independent external re-audit has not granted them, current status remains:

```text
OPEN_EXTERNAL_REAUDIT
```

or equivalent.

If a later exact external acceptance exists, bind it and use its exact scope.

The task must discover this from repository authority rather than assume either state.

---

# 11. V4-12～V4-15 Capability Debt

Current authority must keep visible that accepted engineering stages can coexist with limited real capability.

Examples:

```text
V4-12/V4-13 real owner-dependent capabilities =
DEGRADED / UNKNOWN where applicable

V4-14 historical PIT =
NOT_GRANTED

V4-15 current real maturity =
NONE

PROVED_HORIZONS = []

UNPROVED_HORIZONS =
[1,3,5,10,20]
```

These are not reasons to reopen the stages.

---

# 12. Runtime / Business Permission Boundary

The new current audit head is governance metadata.

It must not itself grant:

```text
Production
Shadow
Focus
V4-16 runtime
formal consumer cutover
```

Consumer permission still comes from the appropriate accepted capability contract.

Explicitly freeze:

```text
audit_status_authority
!=
business_runtime_authority
```

---

# 13. Stage Head Protection

Preferred approach:

```text
DO NOT mutate V4_STAGE_ACCEPTED_HEAD
```

for this reconciliation.

Create a separate current cross-stage audit-status authority that future stage-entry contracts bind explicitly.

Reason:

R21 has already externally sealed the current V4-15 Stage Head.

Do not invalidate the exact R21 promotion seal merely to rename a registry pointer.

Only mutate Stage Head if an independently justified versioned promotion/amendment mechanism proves it is necessary; otherwise keep it byte-identical.

---

# 14. CurrentStageAuthority Protection

Keep byte-identical unless strictly required:

```text
config/v4_current_stage_authority_v2.json
src/workbench_analysis/v4_current_stage_authority.py
```

This task should not change stage selection or V4-14 replay routing.

The future V4-16 R22 contract may separately bind the new cross-stage audit head.

---

# 15. Independent Consistency Oracle

Create an oracle that does not trust status labels.

It must independently verify at least:

1. every `ACCEPTED_*` entry has exact accepted/external authority;
2. every open entry cannot be upgraded from implementation-only evidence;
3. historical R1 registry remains byte-identical;
4. current Data Head status is derived from current Data Head;
5. current Stage remains V4-15;
6. V4-10～V4-15 Accepted Heads remain byte-identical;
7. scoped/degraded limitations are retained;
8. Production/Shadow/Focus remain false;
9. V4-16 remains false;
10. no historical PIT or real maturity overclaim;
11. current authority contains all mandatory original A01–A09/OWNER/READER entries;
12. current authority contains the V4-15 maturity/PIT/test-enhancement debts;
13. supersession chain is machine-readable and acyclic.

---

# 16. Consumer Scan

Perform a repository-wide scan proving whether the old:

```text
V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R1
```

is consumed by current runtime/business logic.

Required result classes:

```text
HISTORICAL_EVIDENCE_ONLY
GOVERNANCE_REFERENCE_ONLY
CURRENT_RUNTIME_CONSUMER
UNKNOWN
```

Any current runtime/business consumer of the stale historical registry is a P0 and must be repaired in a narrowly scoped way.

Do not replace it with “latest file” discovery.

---

# 17. Required Tests

At minimum:

```text
test_historical_r1_registry_immutable
test_current_a01_not_taken_from_stale_r1
test_current_a02_exact_scoped_acceptance
test_a02_as_recorded_not_upgraded
test_a04_scope_not_overclaimed
test_a08_a09_implementation_only_does_not_close_audit
test_current_stage_is_v4_15
test_data_head_is_2026_09_30
test_v4_10_to_v4_15_heads_unchanged
test_historical_pit_not_granted
test_real_maturity_none
test_nonblocking_debt_not_promoted_to_pass
test_permissions_all_false
test_v4_16_false
test_supersession_graph_acyclic
test_no_latest_glob_discovery
```

If later exact evidence changes A08/A09/A04 current status, adjust the expected state to that exact authority, not to convenience.

---

# 18. Required Evidence

Recommended:

```text
reports/pre16_governance/
  CURRENT_STATUS_SOURCE_INVENTORY.json
  HISTORICAL_REGISTRY_CLASSIFICATION.json
  CURRENT_CROSS_STAGE_AUDIT_STATUS.json
  CONSUMER_SCAN.json
  INDEPENDENT_CURRENT_STATUS_ORACLE.json
  PROTECTED_BYTES.json
  LOCAL_TEST_SUMMARY.json
  PRE16_GOVERNANCE_CANDIDATE_SEAL.json

docs/audits/
  V4_PRE16_CROSS_STAGE_GOVERNANCE_RECONCILIATION_20261004.md
```

---

# 19. Protected Bytes

Must keep byte-identical:

```text
data/v4/V4_STAGE_ACCEPTED_HEAD.json
data/v4/V4_DATA_ACCEPTED_HEAD.json
data/v4/V4_10_ACCEPTED_HEAD.json
data/v4/V4_11_ACCEPTED_HEAD.json
data/v4/V4_12_ACCEPTED_HEAD.json
data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json
data/v4/V4_14_ACCEPTED_HEAD.json
data/v4/V4_15_ACCEPTED_HEAD.json
config/v4_current_stage_authority_v2.json
```

and the historical R1 cross-stage registry.

---

# 20. Required End State

Only:

```text
PRE16_CROSS_STAGE_GOVERNANCE_RECONCILIATION =
PASS_LOCAL

CURRENT_CROSS_STAGE_AUDIT_AUTHORITY =
READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

V4_10_TO_V4_15 =
PASS_KEEP_NO_REOPEN

V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_15_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

Production = false
Shadow = false
Focus = false
V4_16 = false

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

Do not start R22/V4-16 in this task.
