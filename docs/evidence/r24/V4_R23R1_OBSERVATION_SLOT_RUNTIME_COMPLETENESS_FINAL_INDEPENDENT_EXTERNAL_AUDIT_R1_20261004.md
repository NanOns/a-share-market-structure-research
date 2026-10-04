# V4 R23R1｜Observation Slot Runtime Completeness Final Independent External Audit R1｜2026-10-04

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`

Execution baseline:

`9724b0b2091b0d1e0ca55af17e1fc8c3948fdf42`

Audited remote HEAD:

`b6b3105e713187462f49054e62fa70df8b9bd292`

Exact tested source:

`ee12bb7d0f1c89fe8f32aa55aaa385bcb5438ff4`

Immutable tested tag:

`refs/tags/codex/r23r1-slot-tested-source-20261004-r1`

---

# 1. Unique External Decision

```text
R23R1_EXTERNAL_AUDIT =
PASS_FINAL_OBSERVATION_SLOT_RUNTIME_COMPLETENESS

R23_SLOT_01 =
CLOSED_EXTERNALLY_ACCEPTED

R23_OBSERVATION_LINEAGE_P1 =
CLOSED_EXTERNALLY_ACCEPTED

R23_RUNTIME_ENGINEERING =
PASS_EXTERNAL_ENGINEERING_CANDIDATE_DISABLED

R23_DISABLED_ACTIVATION_BOUNDARY =
PASS_KEEP

R23_TRANSACTION_ATOMICITY =
PASS_KEEP

R23_SETTLEMENT_ORCHESTRATION =
PASS_KEEP

R23_LEGACY_ISOLATION =
PASS_KEEP

R23_NEGATIVE_E2E_N01_N32 =
PASS_EXTERNAL

R23_INDEPENDENT_RUNTIME_ORACLE =
PASS_EXTERNAL

V4_16_REAL_SHADOW_ACTIVATION_ENGINEERING_ENTRY =
AUTHORIZED

V4_16_REAL_SHADOW_ACTIVATION =
NOT_AUTHORIZED

V4_16_ACCEPTED_HEAD =
NOT_CREATED

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

Production = false
Shadow = false
Focus = false
V4_16 = false
```

R23R1 closes the last runtime-completeness blocker found in R23.

---

# 2. Change Scope｜PASS

Relative to the R23 baseline, only the following existing files changed:

```text
.gitattributes
scripts/v4_16_shadow_runtime.py
tests/test_r23_runtime.py
```

All other implementation/accepted business-state files remain unchanged.

New files are limited to:

```text
R23R1 slot runtime policy
R23R1 validator/tests
R23R1 evidence
R23R1 persisted engineering corruption fixtures
```

No V4-10～V4-15 business algorithm was reopened.

---

# 3. Accepted Observation Slot V2 Completeness｜PASS

The accepted contract requires exactly 18 fields:

```text
trade_date
model_contract_id
parameter_set_id
state_lineage_id
execution_mode
namespace
scheduled_cutoff_at
observation_deadline
source_provider_available_at
system_available_at
computation_started_at
computation_finished_at
accepted_at
slot_status
publication_id
core_revision
source_manifest_digest
capability_scope
```

R23R1 now creates every slot from the accepted V2 `fields[]` list rather than maintaining a separate runtime-only list.

Independent readback reports:

```text
required_slot_field_count = 18
missing_slot_fields = []
accepted_revisions = 2
same_slot = true
```

Accepted slot revisions contain no null contract field.

---

# 4. Visibility Aggregation｜PASS

For every persisted slot the independent oracle recomputes:

```text
source_provider_available_at =
max(first_observed_at)
over exact visibility_receipt_ids

system_available_at =
max(system_available_at)
over exact visibility_receipt_ids
```

and verifies:

```text
source_provider_available_at
<= system_available_at
<= scheduled_cutoff_at

system_available_at
<= computation_started_at
<= computation_finished_at
<= accepted_at
<= observation_deadline
```

The accepted slot also binds the exact mandatory-source manifest.

N26 and N27 independently corrupt the aggregate values after row digests are recomputed; the independent oracle rejects both.

---

# 5. Receipt Chronology｜PASS

Runtime now requires:

```text
first_observed_at
<= integrity_passed_at
<= system_available_at
<= created_at
```

A receipt whose creation time predates the finalized visibility state is rejected before persistence.

The independent oracle rechecks the same order from persisted rows.

---

# 6. Slot Identity / Revision｜PASS

Original slot identity remains:

```text
(
  model_contract_id,
  state_lineage_id,
  trade_date
)
```

The positive persisted E2E proves:

```text
revision 1 -> same slot_id
revision 2 -> same slot_id
one original enrollment only
```

and freezes:

```text
namespace = SHADOW_V4
execution_mode = SHADOW
sample_class = ENGINEERING_ONLY
```

Both revisions preserve cutoff/deadline identity.

`core_revision` is explicitly frozen to the deterministic publication identity for that revision and independently recomputed.

---

# 7. Manifest / Parameter / Capability Binding｜PASS

For every accepted slot the independent oracle verifies:

```text
parameter_set_id
=
request parameter
=
frozen manifest parameter
=
fixture registry accepted parameter

source_manifest_digest
=
recomputed manifest digest
=
publication manifest digest

capability_scope
=
sorted unique evaluated request capability set
```

Blocked capabilities cannot enter an accepted slot.

N28 and N29 corrupt manifest/scope semantics and are independently rejected.

---

# 8. Observation Supersedes Lineage｜PASS

R23R1 now wraps persisted observations with explicit revision lineage.

First observation:

```text
supersedes_observation = null
```

Correction:

```text
source_correction = true
supersedes_observation = previous observation_id
```

Independent validation proves:

```text
same logical_event_id
same slot_id
prior revision < current revision
publication revision matches
no missing predecessor
no cycle
```

N30–N32 independently corrupt missing predecessor, event lineage and cyclic/invalid predecessor relationships. All are rejected.

---

# 9. Negative Matrix｜PASS

R23 immutable N01–N24 remain PASS.

R23R1 adds:

```text
N25 missing required slot field
N26 wrong provider visibility aggregate
N27 wrong system visibility aggregate
N28 manifest digest mismatch
N29 capability scope mutation
N30 correction missing supersedes
N31 predecessor from different logical event
N32 cyclic/invalid supersedes relationship
```

All N01–N32 pass their expected fail-closed behavior.

The corruption fixtures recompute row digests, proving the independent oracle is checking semantics rather than merely detecting checksum failure.

---

# 10. Independent Oracle｜PASS

`scripts/validate_r23r1_runtime.py` does not import:

```text
v4_16_shadow_runtime
run_r23_engineering
```

It reads persisted SQLite state and independently recomputes the required slot/revision semantics.

It also reuses the prior R23 persisted-scope oracle, preserving the earlier atomicity/cohort/settlement checks.

---

# 11. Clean Regression / Tested Source｜PASS

Local suite:

```text
320 passed
0 failed
0 errors
0 skipped
0 deselected
```

Clean detached suite:

```text
320 passed
0 errors
0 skipped
0 deselected
```

Exact tested source:

`ee12bb7d0f1c89fe8f32aa55aaa385bcb5438ff4`

Immutable tag:

`codex/r23r1-slot-tested-source-20261004-r1`

The tag resolves exactly to the tested source.

Final branch HEAD is one commit ahead and the delta is evidence-only:

```text
CLEAN_REGRESSION
R23R1_CANDIDATE_SEAL
clean runner
JUnit
```

No implementation drift exists after the tested source.

---

# 12. Protected State｜PASS

Still:

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_15_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

V4_16_ACCEPTED_HEAD =
NOT_CREATED
```

Direct lookup of `data/v4/V4_16_ACCEPTED_HEAD.json` returns not found, as required.

Permissions remain:

```text
runtime_authorized = false
real_shadow_authorized = false
Production = false
Shadow = false
Focus = false
V4_16 = false
```

Real counters remain zero.

---

# 13. P2 Nonblocking Governance Note

R23R1 binds:

`config/v4_16_r23r1_slot_runtime_policy_v1.json`

with exact path + digest inside the controller.

This is safe and deterministic, but the new policy is not yet part of the central `v4_16_runtime_dependencies_v1.json` dependency manifest.

Classification:

```text
R23R1_DEPENDENCY_MANIFEST_STYLE =
P2_NONBLOCKING
```

Do not reopen R23R1.

The real-activation successor must create a versioned dependency manifest successor and include this policy there explicitly.

---

# 14. REV4 Stage Continuity

REV4 defines:

```text
V4-16 = Realtime Shadow Dual-Run
V4-17 = Shadow UI
V4-17G = Shadow Stable / Provisional Forward Gate
```

R23R1 has completed the engineering-runtime prerequisite only.

It has not yet created a real:

```text
PIT_OBSERVED + SHADOW
```

session.

Therefore the correct next step is not V4-17 acceptance. It is a controlled real-Shadow activation-readiness round.

Long real-data accumulation does not need to block unrelated engineering. After the real-activation path is accepted, V4-17 UI engineering may proceed in parallel with Shadow evidence accumulation, while V4-17G acceptance remains evidence-gated.

---

# 15. Final Decision

```text
R23R1_EXTERNAL_AUDIT =
PASS_FINAL_OBSERVATION_SLOT_RUNTIME_COMPLETENESS

R23_RUNTIME_ENGINEERING =
EXTERNALLY_ACCEPTED_DISABLED_CANDIDATE

NEXT =
R24_V4_16_REAL_SHADOW_ACTIVATION_READINESS
```
