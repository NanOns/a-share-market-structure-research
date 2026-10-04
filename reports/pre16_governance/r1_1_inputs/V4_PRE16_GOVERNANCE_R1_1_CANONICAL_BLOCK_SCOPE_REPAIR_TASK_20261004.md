# PRE16-GOV-R1.1｜Canonical Audit Issue / Blocking Scope Repair Task｜2026-10-04

## 0. Mission

Repair one governance ambiguity found by the PRE16 independent external audit.

Do not change any accepted business stage.

Baseline:

`0109d7f6c8b9f4cea6cde32b2342e4b6d4e0526b`

External audit authority:

`V4_PRE16_GOVERNANCE_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md`

---

# 1. P0 Defect

The current audit head contains two representations of the same Amount-A H21 consumer issue:

```text
A04_H21_CONSUMER
AUD_A04_AMOUNT_A_FORWARD_CONSUMER
```

but they disagree on `blocks_shadow_entry`.

The blocker schema also cannot distinguish global V4-16 contract-entry block, global runtime-activation block, affected-capability-only Shadow block, and production-cutover-only block.

---

# 2. Allowed Changes

Only PRE16 governance files:

```text
config/v4_cross_stage_current_audit_authority_v1.json
data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V1.json
reports/pre16_governance/**
scripts/build_pre16_governance.py
scripts/pre16_current_audit_reader.py
scripts/validate_pre16_governance.py
tests/test_pre16_governance.py
docs/audits/pre16 governance evidence
```

Version the current audit head/config if needed.

---

# 3. Forbidden Changes

Keep exact bytes for:

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

src/workbench_analysis/v4_14_authority.py
src/workbench_analysis/v4_15_radar_cohort.py
src/workbench_analysis/v4_15_settlement.py
src/workbench_analysis/v4_current_stage_authority.py
```

Also keep all historical audit registries exact.

---

# 4. Canonical Issue Identity

Every current issue must have a canonical identity.

Recommended:

```text
canonical_issue_id
alias_of
```

Rules:

```text
canonical entry:
alias_of = null

alias/reference entry:
alias_of = canonical_issue_id
```

Preferred mapping:

```text
canonical_issue_id = A04_H21_CONSUMER

AUD_A04_AMOUNT_A_FORWARD_CONSUMER.alias_of =
A04_H21_CONSUMER
```

An alias must not independently define conflicting state or blocker semantics.

---

# 5. Blocking Scope Schema

Replace or supplement ambiguous `blocks_shadow_entry` with exact machine fields equivalent to:

```text
blocking_scope =
GLOBAL_STAGE
CAPABILITY_ONLY
NONE

blocks_v4_16_contract_entry
blocks_v4_16_runtime_activation
blocks_affected_capability_in_shadow
blocks_production_cutover_for_scope

affected_capabilities[]
```

The old field may remain only if its exact derived meaning is frozen and cannot conflict with these fields.

---

# 6. Required Semantics

## GOV_PRE16_01

```text
blocking_scope = GLOBAL_STAGE
blocks_v4_16_contract_entry = true
```

This is the only PRE16 global contract-entry blocker before external acceptance.

## A04_H21_CONSUMER

```text
blocking_scope = CAPABILITY_ONLY
blocks_v4_16_contract_entry = false
blocks_affected_capability_in_shadow = true
```

Observation accumulation must not block unrelated engineering.

## AUD_A04_AMOUNT_A_FORWARD_CONSUMER

Alias/reference to the canonical Amount-A H21 issue. It must not create a contradictory second blocker.

## A04_HISTORICAL_AMOUNT_A

```text
blocking_scope = CAPABILITY_ONLY
blocks_v4_16_contract_entry = false
```

## A08_CURRENT_RUNTIME

Explicitly separate contract work from actual Shadow activation.

```text
blocks_v4_16_contract_entry = false
blocks_affected_capability_in_shadow = true
```

If full V4-16 runtime activation requires this capability, encode:

```text
blocks_v4_16_runtime_activation = true
```

without blocking contract freeze or unrelated engineering.

---

# 7. Current Audit Reader

Add APIs or equivalent machine-readable access:

```text
global_contract_entry_blockers()
runtime_activation_blockers()
capability_shadow_blockers()
production_cutover_blockers()
canonical_entry(issue_id)
```

The reader must resolve aliases deterministically, never merge contradictory aliases, never grant stage/runtime permission, and return copies.

`stage_permission()` remains false.

---

# 8. Validator Requirements

Reject:

1. duplicate logical issues with conflicting canonical identity;
2. alias cycles;
3. missing alias targets;
4. alias state mismatch;
5. alias blocker mismatch;
6. `ACCUMULATION_CONTINUES` globally blocking contract engineering without exact authority;
7. historical limitation globally blocking unrelated realtime engineering;
8. any non-GOV_PRE16 item claiming PRE16 global contract-entry block without exact authority;
9. current-runtime open capability upgraded from implementation-only evidence.

---

# 9. Mandatory Tests

Add at minimum:

```text
test_a04_h21_single_canonical_issue
test_a04_h21_alias_consistent
test_alias_cycle_rejected
test_alias_target_missing_rejected
test_alias_block_semantics_mismatch_rejected

test_only_gov_pre16_blocks_global_contract_entry
test_a04_h21_does_not_block_contract_entry
test_historical_amount_a_does_not_block_contract_entry
test_a08_current_runtime_does_not_block_contract_entry
test_a08_current_runtime_remains_shadow_capability_blocked

test_accumulation_does_not_block_unrelated_engineering
test_capability_only_block_not_global_shadow_block
test_reader_resolves_canonical_issue

test_v4_10_to_v4_15_heads_unchanged
test_stage_head_unchanged
test_data_head_unchanged
test_business_runtime_sources_unchanged
```

Keep all existing PRE16 and R21 tests passing.

---

# 10. Evidence

Create:

```text
reports/pre16_governance_r1_1/
  CANONICAL_ISSUE_MAP.json
  BLOCKING_SCOPE_MATRIX.json
  ALIAS_INTEGRITY_ORACLE.json
  CURRENT_STATUS_REBUILD.json
  PROTECTED_BYTES.json
  CONSUMER_RESCAN.json
  LOCAL_TEST_SUMMARY.json
  CLEAN_GOVERNANCE_REGRESSION.json
  PRE16_GOV_R1_1_CANDIDATE_SEAL.json
```

---

# 11. Required Exit State

```text
PRE16_GOV_R1_1 = PASS_LOCAL

GLOBAL_V4_16_CONTRACT_ENTRY_BLOCKERS =
[GOV_PRE16_01]

AMOUNT_A_H21 =
ONE_CANONICAL_CURRENT_ISSUE

A04_H21_CONSUMER =
CAPABILITY_ONLY_BLOCK

A04_HISTORICAL_AMOUNT_A =
CAPABILITY_ONLY_BLOCK

A08_CURRENT_RUNTIME =
NO_CONTRACT_ENTRY_BLOCK
+
SHADOW_CAPABILITY_LIMIT_RETAINED

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

Do not start R22 in this repair.
