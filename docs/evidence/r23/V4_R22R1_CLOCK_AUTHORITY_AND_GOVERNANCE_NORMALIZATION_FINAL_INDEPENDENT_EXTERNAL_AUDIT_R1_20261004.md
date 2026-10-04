# V4 R22R1｜Clock Authority + PRE16 V3 Final Independent External Audit R1｜2026-10-04

## 0. Audit Target

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Execution baseline:

`3fd69721fa8f61aa278b275cb9250bb6829c85a5`

Audited remote HEAD:

`942997f8a5bce06e34a6e37d013e4d27e7175438`

Exact tested source:

`319d598ef372ac52829083567e41188a15c053a3`

Immutable tested tag:

`refs/tags/codex/r22r1-clock-tested-source-20261004-r1`

---

# 1. Unique External Decision

```text
R22R1_EXTERNAL_AUDIT =
PASS_FINAL_CLOCK_AUTHORITY_AND_GOVERNANCE_NORMALIZATION

R22_CONTRACT_FREEZE =
PASS_KEEP_EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED

V4_16_CLOCK_CONTRACT_V1 =
PASS_EXTERNAL

V4_16_OBSERVATION_SLOT_CONTRACT_V2 =
PASS_EXTERNAL_CONTRACT_ONLY

SOURCE_VISIBILITY_TIME_SEMANTICS =
PASS_EXTERNAL

PRE16_CURRENT_AUDIT_AUTHORITY_V3 =
PASS_EXTERNAL_DESCRIPTIVE_NORMALIZATION

R22_CLOCK_AUTHORITY_REPAIR_01 =
CLOSED_EXTERNALLY_ACCEPTED

REALTIME_OBSERVATION_CLOCK_BLOCK =
CLOSED_FOR_RUNTIME_ENGINEERING_ENTRY

V4_16_RUNTIME_ENGINEERING_ENTRY =
AUTHORIZED

V4_16_RUNTIME_ACTIVATION =
NOT_AUTHORIZED

REAL_SHADOW_EXECUTION =
NOT_AUTHORIZED

REAL_SHADOW_OBSERVATIONS =
0

PIT_OBSERVED_REAL_SAMPLES =
0

Production = false
Shadow = false
Focus = false
V4_16 = false
```

This audit authorizes V4-16 Runtime Engineering only. It does not authorize a real Shadow publication.

---

# 2. Change Scope｜PASS

Relative to `3fd69721...`, R22R1 adds only:

- `V4_16_CLOCK_CONTRACT_V1`;
- clock machine vectors;
- `V4_16_OBSERVATION_SLOT_CONTRACT_V2`;
- V4-16 contract-freeze accepted head;
- PRE16 current audit V3/config V3;
- R22R1 validators/readers/tests/evidence.

No V4-10～V4-15 Accepted Head, Stage Head, Data Head, current-stage business router, V4-14/V4-15 business runtime, or R22 V1 contract artifact was rewritten.

Therefore:

```text
HISTORICAL_ACCEPTED_STATE_REWRITE = NONE
R22_V1_REWRITE = NONE
V4_10_TO_V4_15_REOPEN = NO
```

---

# 3. R22 Contract Acceptance Formalization｜PASS

Created:

`data/v4/V4_16_CONTRACT_ACCEPTED_HEAD_R1.json`

It binds exactly:

```text
audited remote HEAD =
3fd69721fa8f61aa278b275cb9250bb6829c85a5

tested source =
2456f6cdae99431bb475f077d4eaccd5f24c3b75

tested tag =
codex/r22-contract-tested-source-20261004-r1

external decision =
PASS_FINAL_V4_16_CONTRACT_FREEZE_CAPABILITY_SCOPED

acceptance_scope =
CONTRACT_FREEZE_ONLY
```

and retains:

```text
runtime_authorized = false
shadow = false
production = false
focus = false
V4_16 = false
```

No contract-freeze acceptance was misused as runtime permission.

---

# 4. Clock Policy｜PASS

`config/v4_16_clock_contract_v1.json` correctly freezes:

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

scheduled_source_cutoff_local =
21:00:00

observation_publication_deadline_local =
22:30:00

scheduled_source_cutoff_utc =
13:00:00Z

observation_publication_deadline_utc =
14:30:00Z

market_session_only =
true
```

The new policy is correctly represented as a post-REV4 V4-16 policy, not a fabricated historical V4-00C fact.

---

# 5. Source Visibility Time Semantics｜PASS

The contract freezes:

```text
source_provider_available_at =
EARLIEST_PROJECT_OBSERVED_AUTHORITATIVE_READINESS_FOR_EXACT_CONSUMED_MANDATORY_SOURCE

system_available_at =
EXACT_BYTES_LOCALLY_AVAILABLE_AND_REQUIRED_ACCEPTANCE_INTEGRITY_PASSED
```

and requires:

```text
source_provider_available_at
<= system_available_at
<= scheduled_cutoff_at
< observation_deadline
```

as well as:

```text
system_available_at
<= computation_started_at
<= computation_finished_at
<= accepted_at
<= observation_deadline
```

The independent oracle additionally requires:

```text
provider_at == first_observed_at
```

and exact digest equality between consumed source and readiness receipt.

This prevents later backdating of a source-readiness timestamp.

---

# 6. Mandatory Source Fail-Closed｜PASS

For each mandatory source the independent predicate requires:

```text
receipt = true
accepted = true
integrity_pass = true

consumed_digest == receipt_digest

receipt_kind in:
FIRST_ACCEPTED_PROVIDER_READINESS_OBSERVATION
ACCEPTED_LOCAL_OBSERVATION_ACQUISITION
```

Missing proof:

```text
REJECT_NO_PIT
```

Source locally accepted after 21:00:

```text
MISSED_RECONSTRUCTED_ONLY
```

Publication after 22:30:

```text
MISSED_RECONSTRUCTED_ONLY
```

No later reconstruction can upgrade that date to a real PIT observation.

---

# 7. Optional BaoStock Isolation｜PASS

The clock policy explicitly keeps BaoStock:

```text
SUPPLEMENTAL_ONLY
```

and forbids its failure or delay from moving the Pure-Core clock or invalidating an otherwise valid Pure-Core slot.

This is consistent with the accepted architecture.

---

# 8. Observation Slot V2｜PASS

Created:

`config/v4_16_observation_slot_contract_v2.json`

It binds the new clock contract and keeps:

```text
runtime_authorized = false
runtime_implemented = false
shadow = false
production = false
focus = false
V4_16 = false
```

The validator proves all non-clock/non-version semantics remain identical to V1.

V1 remains immutable historical R22 evidence.

V2 is accepted as the runtime-engineering clock-bound observation-slot contract, but not as a runtime grant.

---

# 9. Clock Revision Governance｜PASS

Any change to:

```text
cutoff time
deadline
provider-availability semantics
system-availability semantics
```

requires:

```text
new contract_id
new version
new policy identity
affected Shadow stability reset
old slots unchanged
```

The dedicated `CLOCK-10` vector proves this rule.

---

# 10. Machine Vectors｜PASS

R22R1 covers the required boundary cases plus extra failure cases.

At minimum it proves:

```text
20:59 ready -> eligible engineering case
21:00 exact -> eligible engineering case
21:00:01 -> missed
22:30 exact accepted -> eligible engineering case
22:30:01 -> missed
backdated provider time -> reject
missing readiness receipt -> reject
BaoStock unavailable -> Pure-Core unaffected
non-market day -> no slot
clock revision -> new identity + reset
```

All vector results explicitly carry:

```text
PIT_OBSERVED = false
```

and:

```text
actual_runtime_executed = false
```

so no engineering fixture is counted as a real observation.

---

# 11. PRE16 V3 Normalization｜PASS

Created:

```text
data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3.json
config/v4_cross_stage_current_audit_authority_v3.json
```

The independent validator proves the V3 change is descriptive only.

Machine states, blocker booleans, evidence bindings and permissions are identical to V2.

The stale wording around GOV_PRE16_01 has been normalized to the current state:

```text
GOV_PRE16_01/GOV_PRE16_02 externally closed
no global entry/runtime hold from PRE16 governance
no runtime permission is granted
A04/A08 capability limitations remain
```

---

# 12. Nonblocking Metadata Note｜P2

The V3 config intentionally preserves several V2 metadata fields to satisfy the "descriptive-only" equality check, including the older `execution_baseline` and inherited `supersedes_current_config` field, while adding an exact:

```text
descriptive_normalization_predecessor =
V4_CROSS_STAGE_CURRENT_AUDIT_AUTHORITY_V2
```

This does not create a machine-state or permission ambiguity because:

1. the current head binding is exact;
2. the descriptive predecessor points directly to V2;
3. the validator proves no permission/capability mutation;
4. the R23 runtime must bind the exact V3 file/digest directly.

Classification:

```text
GOV_METADATA_LINEAGE_STYLE =
P2_NONBLOCKING
```

Do not reopen R22R1 for this alone.

Future governance versions should prefer one unambiguous version-chain field rather than carrying inherited legacy lineage labels indefinitely.

---

# 13. Tested Source / Clean Regression｜PASS

Exact tested source:

`319d598ef372ac52829083567e41188a15c053a3`

Immutable tag:

`codex/r22r1-clock-tested-source-20261004-r1`

The tag resolves exactly to the tested source.

Final HEAD is one evidence-only commit ahead.

Post-tested-source delta contains only:

```text
clean regression
candidate seal
runner log
JUnit result
```

No contract or implementation bytes changed.

Clean regression:

```text
250 passed
0 failed
0 errors
0 skipped
0 deselected
```

---

# 14. Protected State｜PASS

Still:

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_15_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

V4_16_ACCEPTED_HEAD =
NOT_CREATED

REAL_SHADOW_OBSERVATIONS =
0

Production = false
Shadow = false
Focus = false
V4_16 = false
```

Historical PIT and matured real evidence remain ungranted.

---

# 15. Runtime Engineering Entry Boundary

R22R1 closes the contract blocker required before implementing V4-16 runtime.

The next stage may therefore implement:

```text
Shadow runtime infrastructure
transactional Shadow publication
observation slot execution
source freeze/readiness receipts
SHADOW_V4 prior-state handling
realtime cohort wiring
daily membership capture
settlement orchestration
health receipts
rollback/stop-shadow
```

but the next engineering stage must still produce:

```text
REAL_SHADOW_OBSERVATIONS = 0
```

during acceptance testing.

Real market-session Shadow activation requires a later external authorization.

---

# 16. Final Decision

```text
R22R1_EXTERNAL_AUDIT =
PASS_FINAL_CLOCK_AUTHORITY_AND_GOVERNANCE_NORMALIZATION

R22_CLOCK_AUTHORITY_REPAIR_01 =
CLOSED_EXTERNALLY_ACCEPTED

V4_16_RUNTIME_ENGINEERING_ENTRY =
AUTHORIZED

NEXT =
R23_V4_16_RUNTIME_ENGINEERING
```
