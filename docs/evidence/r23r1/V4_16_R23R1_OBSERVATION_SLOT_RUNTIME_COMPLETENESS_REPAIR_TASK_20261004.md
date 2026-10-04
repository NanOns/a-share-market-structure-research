# V4-16 R23R1｜Observation Slot Runtime Completeness Repair Task｜2026-10-04

## 0. Mission

Repair the only P0 runtime-contract gap found in R23 external audit and repair same-day observation revision lineage in the same round.

Execution baseline:

`9724b0b2091b0d1e0ca55af17e1fc8c3948fdf42`

External audit authority:

`V4_R23_REALTIME_SHADOW_RUNTIME_ENGINEERING_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md`

# 1. PASS_KEEP

Keep unchanged:

```text
disabled activation authority
clock resolver
source readiness registry identity
source freeze
SHADOW_V4 prior reader
transaction atomicity
cohort original enrollment
membership non-PIT capture
due/settlement orchestration
health receipts
rollback
Legacy isolation
N01–N24
independent SQLite oracle architecture
```

# 2. P0 Repair｜Persist Full Observation Slot V2

The accepted contract:

`config/v4_16_observation_slot_contract_v2.json`

contains the machine list `fields[]`.

Every persisted accepted slot revision must contain every field in that list. Runtime must bind that exact accepted contract and validate against its `fields[]`.

# 3. Required Slot Fields

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

# 4. Exact Field Semantics

```text
parameter_set_id =
exact request/accepted parameter identity

execution_mode =
SHADOW

namespace =
SHADOW_V4

source_provider_available_at =
max(first_observed_at)
across exact mandatory consumed receipts

system_available_at =
max(system_available_at)
across exact mandatory consumed receipts

computation_started_at / computation_finished_at / accepted_at =
exact validated request timestamps

core_revision =
explicit deterministic publication/core revision identity

source_manifest_digest =
exact MandatorySourceFreezeBuilder digest

capability_scope =
explicit sorted/canonical evaluated scope
```

Required ordering:

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

# 5. Planned / Blocked / Missed Slots

For:

```text
PLANNED
BLOCKED_SOURCE_NOT_READY
MISSED_OBSERVATION_SLOT
```

the slot schema must remain structurally complete.

Fields not yet available must be explicitly represented with contract-defined null/quality semantics rather than omitted.

For a missed slot, preserve the source-timing facts that caused the miss.

# 6. Slot Revision Identity

The original key remains:

```text
(model_contract_id, state_lineage_id, trade_date)
```

Same-day publication revisions append slot revisions, preserve slot_id/cutoff/deadline/namespace/execution identity, and do not create a second original sample.

# 7. Observation Revision Lineage

For a correction where an earlier observation for the same logical event exists:

```text
source_correction = true
supersedes_observation = previous observation_id
```

Require:

```text
previous observation exists
same logical_event_id
same slot_id
previous revision < current revision
no cycles
```

First observation keeps `supersedes_observation = null`.

# 8. Independent Oracle Upgrade

The independent validator must not import the runtime writer.

For each persisted accepted slot revision:

1. load exact Observation Slot V2;
2. read `fields[]`;
3. require all fields present;
4. recompute slot_id;
5. recompute source_provider_available_at;
6. recompute system_available_at;
7. validate time ordering;
8. validate source_manifest_digest binding;
9. validate capability_scope normalization;
10. validate publication/core revision identity;
11. verify zero real counters/PIT claim.

Also validate the observation supersedes chain independently.

# 9. Positive E2E

Rerun the complete persisted R23 positive E2E.

Required oracle output:

```text
required_slot_field_count = len(V2.fields)
missing_slot_fields = []
```

For revision 2:

```text
same slot_id
revision = 2
supersedes_observation = revision-1 observation_id
no second original enrollment
```

# 10. Negative Additions

Add at minimum:

```text
N25 missing required slot field -> reject
N26 wrong source_provider_available_at aggregate -> reject
N27 wrong system_available_at aggregate -> reject
N28 source_manifest_digest mismatch -> reject
N29 capability_scope missing/mutated -> reject
N30 corrected observation missing supersedes -> reject
N31 supersedes points to different logical event -> reject
N32 supersedes cycle -> reject
```

N01–N24 must remain passing.

# 11. Receipt Timestamp Hygiene

Tighten accepted receipt chronology to:

```text
first_observed_at
<= integrity_passed_at
<= system_available_at
<= created_at
```

if `created_at` is the durable accepted receipt creation timestamp.

If the existing semantic is intentionally different, freeze and rename it explicitly and introduce a separate finalized/accepted receipt timestamp.

# 12. Protected State

Keep exact:

```text
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_10～V4_15 Accepted Heads
V4_16_CONTRACT_ACCEPTED_HEAD_R1
V4_16_CLOCK_GOVERNANCE_ACCEPTED_HEAD_R1
V4_16_CLOCK_CONTRACT_V1
V4_16_OBSERVATION_SLOT_CONTRACT_V2
PRE16 V1/V2/V3
R22/R22R1 accepted evidence
Legacy runtime
```

Do not create `V4_16_ACCEPTED_HEAD`.

# 13. Permissions

Must remain:

```text
runtime_authorized = false
real_shadow_authorized = false

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

Production = false
Shadow = false
Focus = false
V4_16 = false
```

# 14. Regression

Run all prior PRE16/R21/R22/R22R1/R23 tests plus new R23R1 tests in clean detached checkout. No broad deselection. Preserve `ATTEMPT_R1_DISPOSITION`.

# 15. Required Evidence

Recommended:

```text
reports/r23r1/
  SLOT_CONTRACT_FIELD_GATE.json
  SLOT_VISIBILITY_AGGREGATION_ORACLE.json
  SLOT_REVISION_GATE.json
  OBSERVATION_SUPERSEDES_GATE.json
  RECEIPT_TIMESTAMP_HYGIENE_GATE.json
  POSITIVE_E2E_ENGINEERING.json
  NEGATIVE_E2E_MATRIX.json
  INDEPENDENT_RUNTIME_ORACLE.json
  PROTECTED_BYTES.json
  LOCAL_TEST_SUMMARY.json
  CLEAN_REGRESSION.json
  R23R1_CANDIDATE_SEAL.json
```

# 16. Required Exit

```text
R23R1_SLOT_RUNTIME_COMPLETENESS =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

R23_RUNTIME_ENGINEERING =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

R23_RUNTIME_IMPLEMENTED =
ENGINEERING_CANDIDATE_DISABLED

V4_16_RUNTIME_ACTIVATION =
NOT_AUTHORIZED

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_15_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

Production = false
Shadow = false
Focus = false
V4_16 = false

NEXT =
STOP_WAIT_R23R1_INDEPENDENT_EXTERNAL_AUDIT
```

Do not begin real Shadow activation in this repair.
