# V4-16 R22R1｜Clock Authority + Source Visibility + PRE16 V3 Normalization｜2026-10-04

## 0. Mission

Close the only P0 affected-scope blocker remaining after R22 Contract Freeze and clean the PRE16 V2 descriptive inconsistency before V4-16 Runtime engineering.

This task does not implement V4-16 Runtime.

Execution baseline:

`3fd69721fa8f61aa278b275cb9250bb6829c85a5`

External authority:

`V4_R22_V4_16_CONTRACT_FREEZE_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md`

---

# 1. R22 Acceptance Formalization

Create a contract-freeze acceptance head, recommended:

```text
data/v4/V4_16_CONTRACT_ACCEPTED_HEAD_R1.json
```

Bind:

```text
audited remote HEAD =
3fd69721fa8f61aa278b275cb9250bb6829c85a5

tested source =
2456f6cdae99431bb475f077d4eaccd5f24c3b75

tested tag =
codex/r22-contract-tested-source-20261004-r1

external decision =
PASS_FINAL_V4_16_CONTRACT_FREEZE_CAPABILITY_SCOPED
```

Acceptance scope is `CONTRACT_FREEZE_ONLY`.

No runtime permission is granted.

---

# 2. New Clock Contract

Create:

```text
config/v4_16_clock_contract_v1.json
```

Required identity:

```text
contract_id =
V4_16_CLOCK_CONTRACT_V1

policy_origin =
POST_REV4_V4_16_EXTERNAL_GOVERNANCE_POLICY

historical_v4_00c_claim =
false

timezone =
Asia/Shanghai

timestamp_storage =
UTC_RFC3339
```

Do not modify historical V4-00C evidence.

---

# 3. Frozen Clock Values

Freeze:

```text
scheduled_source_cutoff_local =
21:00:00

observation_publication_deadline_local =
22:30:00
```

Per market session derive:

```text
scheduled_cutoff_at =
trade_date 21:00:00+08:00
=
13:00:00Z

observation_deadline =
trade_date 22:30:00+08:00
=
14:30:00Z
```

These are ex-ante project policy values.

---

# 4. Clock Invariants

Only accepted exchange market sessions create slots.

Required:

```text
source_provider_available_at
<=
system_available_at
<=
scheduled_cutoff_at
<
observation_deadline
```

For an accepted publication:

```text
computation_started_at
<=
computation_finished_at
<=
accepted_at
<=
observation_deadline
```

Publication may complete before cutoff if the exact frozen mandatory source set is already available and accepted.

---

# 5. Source Visibility Timestamp Semantics

Freeze:

```text
source_provider_available_at
```

as the earliest project-observed authoritative readiness timestamp for the mandatory source actually consumed.

Remote official package:

```text
first accepted provider-readiness observation receipt
```

Local/project source:

```text
accepted local source observation/acquisition receipt
```

Freeze:

```text
system_available_at =
time exact source bytes are locally available
and pass required source acceptance/integrity checks
```

No later reconstruction may backdate these timestamps.

---

# 6. Missing / Late Source

If mandatory source readiness cannot be proven by 21:00:

```text
MISSED_OBSERVATION_SLOT
PIT_OBSERVED = false
```

If source arrives later:

```text
RECONSTRUCTED_ASOF
or
RECONSTRUCTED_CORRECTED
```

only.

Never move cutoff retrospectively.

---

# 7. Optional BaoStock

BaoStock remains optional supplemental.

Its failure/lateness must not move the Core cutoff or deadline and must not invalidate an otherwise valid Pure-Core slot.

---

# 8. Clock Revision Governance

Any future change to the time values or visibility semantics requires a new versioned clock contract.

It must create a new policy identity, reset the affected Shadow stability window, and never rewrite old slots.

---

# 9. Observation Slot Contract V2

Create a versioned successor:

```text
config/v4_16_observation_slot_contract_v2.json
```

that binds the new clock contract.

Keep V1 as historical R22 evidence.

No real slot may yet be produced.

---

# 10. PRE16 Current Audit Authority V3

Create:

```text
data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3.json
config/v4_cross_stage_current_audit_authority_v3.json
```

Do not modify V2.

Only normalize current-facing descriptive semantics.

Machine state must remain identical to V2.

Remove stale current-facing wording that says GOV_PRE16_01 is still an active hold.

Normalize GOV_PRE16_01 scope/limitations to state that governance is externally closed, grants no runtime permission, and no longer blocks V4-16 contract/runtime entry.

No capability state, blocker boolean, evidence binding or permission may change.

---

# 11. Independent Clock Oracle

Prove:

```text
timezone exact
cutoff exact 21:00 Asia/Shanghai
deadline exact 22:30 Asia/Shanghai
UTC conversion exact
market-session-only slots
cutoff < deadline
visibility ordering
no backdating
late source => missed/reconstructed only
BaoStock cannot move Core clock
clock revision requires new version
historical V4-00C bytes unchanged
```

---

# 12. Required Machine Vectors

At minimum:

```text
CLOCK-01 source ready 20:59, accepted 22:00 -> eligible
CLOCK-02 source ready 21:00 exact -> eligible
CLOCK-03 source first observed 21:00:01 -> MISSED
CLOCK-04 source ready before cutoff, accepted 22:30 exact -> eligible
CLOCK-05 accepted 22:30:01 -> MISSED/reconstructed only
CLOCK-06 backdated provider timestamp -> reject
CLOCK-07 missing readiness receipt -> no PIT
CLOCK-08 BaoStock unavailable -> Pure-Core clock unaffected
CLOCK-09 non-market day -> no slot
CLOCK-10 clock v2 changes time -> new policy identity + stability reset
```

All are engineering vectors only.

---

# 13. Protected State

Keep exact:

```text
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_10～V4_15 Accepted Heads
V4_15_ACCEPTED_HEAD
config/v4_current_stage_authority_v2.json
V4-14/V4-15 business runtime
PRE16 V1/V2 heads/configs
R22 V1 contract package
historical registries
```

Do not create `V4_16_ACCEPTED_HEAD`.

---

# 14. Permissions

Must remain:

```text
Production = false
Shadow = false
Focus = false
V4_16 = false
V4_16 runtime = NOT_AUTHORIZED
REAL_SHADOW_OBSERVATIONS = 0
```

---

# 15. Regression

Run all prior PRE16 tests, R21 promotion tests, R22 contract tests, and new R22R1 clock/V3 tests in a clean detached checkout.

No broad deselection.

---

# 16. Required Evidence

Recommended:

```text
reports/r22r1/
  R22_EXTERNAL_ACCEPTANCE_BINDING.json
  CLOCK_POLICY_GATE.json
  SOURCE_VISIBILITY_TIME_GATE.json
  CLOCK_MACHINE_VECTORS.json
  PRE16_V3_NORMALIZATION_GATE.json
  PROTECTED_BYTES.json
  LOCAL_TEST_SUMMARY.json
  CLEAN_REGRESSION.json
  R22R1_CANDIDATE_SEAL.json
```

---

# 17. Required Exit

```text
R22R1_CLOCK_AUTHORITY =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

V4_16_CONTRACT_ACCEPTANCE =
FORMALIZED_CONTRACT_ONLY

CLOCK_POLICY =
21:00 / 22:30 Asia/Shanghai

V4_16_OBSERVATION_SLOT_V2 =
CLOCK_BOUND_CANDIDATE

PRE16_CURRENT_AUDIT_AUTHORITY =
V3_NORMALIZED_CANDIDATE

V4_16_RUNTIME =
NOT_AUTHORIZED

REAL_SHADOW_OBSERVATIONS =
0

Production = false
Shadow = false
Focus = false

NEXT =
STOP_WAIT_R22R1_INDEPENDENT_EXTERNAL_AUDIT
```

Do not implement V4-16 runtime in this task.
