# V4 PRE16 Governance Independent External Audit R1｜2026-10-04

## 0. Audit Target

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Execution baseline:

`a1bb12f19e758784e55a1a93acaad1954861a0fc`

Audited remote HEAD:

`0109d7f6c8b9f4cea6cde32b2342e4b6d4e0526b`

Exact tested source:

`66f148d56109bbabb4ec4f9304b92738337c6705`

Immutable tested tag:

`refs/tags/codex/pre16-governance-tested-source-20261004-r1`

---

# 1. Unique External Audit Decision

```text
PRE16_GOVERNANCE_EXTERNAL_AUDIT =
PARTIAL_PASS_CANONICAL_BLOCK_SCOPE_REPAIR_REQUIRED

CURRENT_AUDIT_HEAD_BUILD = PASS_KEEP
HISTORICAL_REGISTRY_IMMUTABILITY = PASS
CURRENT_STATUS_SOURCE_SELECTION = PASS_KEEP
A01_CURRENT_STATUS = PASS_KEEP_SCOPED
A02_CURRENT_STATUS = PASS_KEEP_SCOPED
A04_CURRENT_STATUS = PASS_KEEP_SCOPED
A08_A09_SCOPE_DISCIPLINE = PASS_KEEP
HISTORICAL_PIT_LIMITATION = PASS_KEEP
REAL_MATURITY_DEBT = PASS_KEEP
OLD_R1_CURRENT_RUNTIME_CONSUMER = NONE_CONFIRMED
PROTECTED_ACCEPTED_BYTES = PASS
TESTED_SOURCE_REMOTE_ADDRESSABILITY = PASS
CLEAN_GOVERNANCE_REGRESSION = PASS_81
V4_10_TO_V4_15 = PASS_KEEP_NO_REOPEN
V4_STAGE_ACCEPTED_HEAD = KEEP_V4_00_TO_V4_15_ACCEPTED
V4_DATA_ACCEPTED_HEAD = KEEP_2026_09_30

GOV_PRE16_02_CANONICAL_BLOCK_SCOPE =
P0_REPAIR_REQUIRED

V4_16_CONTRACT_ENTRY =
HOLD_PENDING_R1_1_EXTERNAL_AUDIT
```

This is not a rejection of the PRE16 governance architecture. The current-status authority is substantially correct and preserves accepted business state. One governance-schema ambiguity must be repaired before this object can become the unique current authority used by V4-16 entry contracts.

---

# 2. Change Scope｜PASS

Relative to baseline `a1bb12f...`, the submitted repair is two commits ahead.

Changed scope is limited to:

- new PRE16 governance config/head;
- PRE16 evidence/reports;
- PRE16 builder/reader/validator/tests;
- `.gitattributes` exact-byte handling additions.

No V4-10～V4-15 Accepted Head, Stage Head, Data Head, V4-14/V4-15 business runtime or CurrentStageAuthority implementation was modified.

Therefore:

```text
NO_ACCEPTED_STAGE_REWRITE = PASS
NO_DATA_HEAD_REWRITE = PASS
NO_BUSINESS_RUNTIME_REWRITE = PASS
```

---

# 3. Exact Tested Source / Seal Discipline｜PASS

Tested source:

`66f148d56109bbabb4ec4f9304b92738337c6705`

Tag:

`codex/pre16-governance-tested-source-20261004-r1`

Remote tag resolves exactly to the tested source.

Final branch HEAD is one commit ahead and that final commit adds only reconciliation audit/evidence files. No implementation/config/current-head bytes changed after the tested source.

Therefore:

```text
TESTED_SOURCE_REMOTE_ADDRESSABILITY = PASS
POST_TEST_IMPLEMENTATION_DRIFT = NONE
```

---

# 4. Historical Registry Preservation｜PASS

The original `reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R1.json` remains exact historical evidence.

The new authority explicitly declares:

```text
historical_registry_semantics =
HISTORICAL_GOVERNANCE_SNAPSHOT
```

Sixteen historical registries are retained as literal protected evidence. No in-place rewriting of old OPEN/ACCEPTED statuses was found.

---

# 5. Current Audit Head｜PASS_KEEP

Created:

`data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V1.json`

and:

`config/v4_cross_stage_current_audit_authority_v1.json`

The authority is explicitly:

```text
audit_status_authority = true
business_runtime_authority = false
automatic_stage_permission = false
requires_explicit_future_stage_binding = true
```

The reader returns governance metadata only and `stage_permission()` remains false.

---

# 6. Source-Selection Discipline｜PASS_KEEP

## A01

```text
current_state = ACCEPTED_SCOPED
accepted_trade_date = 2026-09-30
external_acceptance =
EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN
AS_RECORDED = false
```

## A02

```text
current_state = ACCEPTED_SCOPED
AS_RECORDED = false
historical_first_availability_proven = false
knowledge_lineage = RECONSTRUCTED_CORRECTED
```

## A04

```text
current_state = ACCEPTED_SCOPED
scope = Go-forward Amount-A producer engineering only
formal_consumer_enabled = false
historical_formal_capability = BLOCKED
accepted_sessions = 1
missing_H21 = 20
known_amount_a = 0
consumer_auto_activation_after_H21 = false
```

## A08

```text
current_state = ACCEPTED_SCOPED
scope = REPAIR_FREEZE_AUTHORITY_HARDENING_AUDIT_ONLY
current_runtime_accepted = false
```

## A09

```text
current_state = ACCEPTED_SCOPED
scope = ACCEPTED_FUTURE_SCHEMA_HARDENING
production_database_deployed = false
```

No implementation-only evidence was upgraded into broader acceptance.

---

# 7. Open Capability Debt｜PASS_KEEP

The following remain explicit:

```text
HISTORICAL_PIT_EFFECTIVENESS =
PERMANENT_CAPABILITY_LIMITATION / NOT_GRANTED

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME =
NONBLOCKING_VALIDATION_DEBT

REALTIME_ACCEPTED_COHORT_MATURITY =
NONBLOCKING_VALIDATION_DEBT

CURRENT_REAL_MATURITY_EVIDENCE = NONE
PROVED_HORIZONS = []
UNPROVED_HORIZONS = [1,3,5,10,20]

V4_15_FWD_ADJ_VECTOR_01 =
NONBLOCKING_VALIDATION_DEBT
```

---

# 8. Stale R1 Consumer Scan｜PASS

Baseline scan:

```text
CURRENT_RUNTIME_CONSUMER = 0
UNKNOWN = 0
GOVERNANCE_REFERENCE_ONLY = 5
HISTORICAL_EVIDENCE_ONLY = 123
```

Post-change review also reports:

```text
current_runtime_consumers = 0
business_sources_unchanged = true
```

So the stale R1 registry is not a hidden live permission selector.

---

# 9. Protected Bytes / Regression｜PASS

Protected evidence confirms unchanged exact bytes for Stage/Data Heads, V4-10～V4-15 Accepted Heads, current stage authority, V4-14/V4-15 business runtime, and historical audit registries.

Local and clean detached regression both report:

```text
81 passed
0 failed
0 errors
0 skipped
0 deselected
```

---

# 10. P0 Finding｜GOV-PRE16-02

The new current audit head contains two records for the same underlying Amount-A H21 consumer issue:

```text
A04_H21_CONSUMER
scope =
Consumer-specific H21 acceptance remains pending

blocks_shadow_entry = true
```

and:

```text
AUD_A04_AMOUNT_A_FORWARD_CONSUMER
scope =
Independent Amount-A consumer H21 warmup;
producer scoped acceptance does not authorize formal consumer

blocks_shadow_entry = false
```

Both describe the same unresolved H21 formal-consumer capability, but the current head defines neither:

```text
canonical_issue_id
alias_of
blocking_scope
affected_capability
```

So the supposedly unique current authority returns conflicting Shadow-blocking semantics for one logical issue.

The validator currently hardcodes this difference instead of rejecting it.

---

# 11. Why This Matters

REV4 §79 requires failures to block only the affected successor scope, not the whole project; BLOCKED scope must not enter its scanner/consumer.

The current boolean `blocks_shadow_entry` cannot distinguish:

1. blocking all V4-16 contract-stage entry;
2. blocking all V4-16 runtime activation;
3. blocking only one affected capability inside Shadow;
4. blocking only future Production cutover.

This ambiguity also affects interpretation of:

```text
A04_HISTORICAL_AMOUNT_A
A08_CURRENT_RUNTIME
GOV_PRE16_01
```

These are different blocker types and must not share one ambiguous global boolean.

---

# 12. Required Repair

Create a canonical blocker model. At minimum each current item must distinguish:

```text
canonical_issue_id
alias_of

blocks_v4_16_contract_entry
blocks_v4_16_runtime_activation
blocks_affected_capability_in_shadow
blocks_production_cutover_for_scope

affected_capabilities[]

blocking_scope =
GLOBAL_STAGE
CAPABILITY_ONLY
NONE
```

Equivalent naming is acceptable if semantics are exact and machine-checkable.

For Amount-A, `A04_H21_CONSUMER` should be canonical or explicitly map to another canonical id. `AUD_A04_AMOUNT_A_FORWARD_CONSUMER` must become an alias/reference or carry exactly identical blocker semantics.

---

# 13. Required Semantics

## GOV_PRE16_01

Before external closure:

```text
blocking_scope = GLOBAL_STAGE
blocks_v4_16_contract_entry = true
```

## A04_H21_CONSUMER

```text
blocking_scope = CAPABILITY_ONLY
blocks_v4_16_contract_entry = false
blocks_affected_capability_in_shadow = true
```

Missing H21 observation accumulation must not block unrelated V4-16 contract engineering.

## A04_HISTORICAL_AMOUNT_A

```text
blocking_scope = CAPABILITY_ONLY
blocks_v4_16_contract_entry = false
```

Historical Amount-A unavailability cannot globally block realtime Shadow contract engineering.

## A08_CURRENT_RUNTIME

Must explicitly separate V4-16 contract design/implementation from actual PREWATCH current-runtime Shadow activation.

At minimum:

```text
blocks_v4_16_contract_entry = false
blocks_affected_capability_in_shadow = true
```

If full V4-16 runtime activation requires this capability, encode that separately as `blocks_v4_16_runtime_activation = true`.

---

# 14. Acceptance Boundary

Everything else from the submitted PRE16 repair is PASS_KEEP.

Do not reopen V4-10～V4-15, Data Head, Stage Head, R21 promotion, or any accepted business runtime.

---

# 15. Next

```text
PRE16-GOV-R1.1
Canonical Audit Issue / Blocking Scope Repair

→ clean targeted regression
→ exact protected-byte check
→ commit + push
→ independent external audit

R22 / V4-16 contract entry
remains HOLD until R1.1 passes external audit.
```
