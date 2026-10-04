# DM01-R4R2｜R25 Exact Target-Session PIT Bridge Integration Repair Task｜2026-10-05

## 0. Mission

Execution baseline:

`54a214167cfd4414901d2002b0a3cf5da45f4e36`

External authority:

`V4_DM01_R4R1_PIT_LINEAGE_REPAIR_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md`

R4R1 lineage repair is PASS_KEEP.

Repair only the missing cross-stage integration:

```text
R4R1 exact target-session PIT bridge
        ↓
formal daily-input schema
        ↓
R25 producer
        ↓
independent R25 preflight
        ↓
GoForwardInputAuthority runtime consumer
```

Do not reopen calendar, V2 parent rollover, all-nine wiring, lineage composition, first availability or CAS promotion core.

## 1. Hard Boundary

Do not:

```text
rewrite R3/R3_3 formulas
change all-nine capability meanings
change lineage composition semantics
change first-availability semantics
change calendar dates/sources
change current V2 parent topology
move V4_DATA_ACCEPTED_HEAD
move Stage Head
create a real 2026-10-08 package now
grant R25
authorize Shadow
increment real counters
grant Production / Focus / Default UI
```

## 2. Version the Daily-Input Contract

Current `V4_16_GO_FORWARD_INPUT_AUTHORITY_V1` is already a historical accepted authority surface.

Do not silently mutate its semantics.

Create a versioned successor or additive accepted extension, recommended:

```text
V4_16_GO_FORWARD_INPUT_AUTHORITY_V1_1
```

or:

```text
V4_16_GO_FORWARD_INPUT_AUTHORITY_V2
```

with exact predecessor binding.

The REAL daily input must require:

```text
target_session_pit_binding
```

Contract:

```text
DM01_R25_TARGET_SESSION_PIT_BINDING_R4R1_V1
```

The field must participate in:

```text
daily_input_digest
packet digest
exact binding identity
independent preflight
runtime readback
```

No implicit latest/glob/mtime resolution.

## 3. Formal Bridge Producer

Create one deterministic producer.

Inputs:

```text
exact parent accepted Data Head
exact current child V2 Data Head
child final candidate
target-session source manifest
all-nine component receipts
target-session observation receipt
```

Output:

```text
DM01_R25_TARGET_SESSION_PIT_BINDING_R4R1_V1
```

Required exact fields:

```text
parent_data_head
child_data_head
candidate
target_trade_date
target_session_source_manifest
target_session_all_nine_receipts
target_session_observation_receipt
```

The producer must never grant R25.

## 4. Bridge Producer Admission

REAL bridge production only when:

```text
child is current accepted V2 Data Head
child parent archive matches exact parent
child final candidate exact-readbacks
candidate target date matches child target date
candidate real_forward_evidence = true
observation real_forward_evidence = true
child target_session_real_forward_evidence = true
all-nine receipts exact
source manifest exact
current R4 external envelope accepted
```

Engineering fixture path remains separate and cannot create REAL READY evidence.

## 5. Integrate Bridge Into REAL Daily Input

The real daily-input path must set:

```text
daily_input.target_session_pit_binding =
exact bridge binding
```

Changing the bridge must change `daily_input_digest`.

Missing bridge must fail.

Wrong target / parent / child / candidate bridge must fail.

## 6. Independent R25 Preflight Parity

Update `scripts/validate_r25_preflight.py`.

The preflight must independently verify exact bridge semantics and must not rely on the runtime writer or packet writer.

Required rule:

```text
R25 preflight PASS
⇒
the same exact daily input cannot later fail solely because
target_session_pit_binding is absent or structurally invalid
```

It may share a pure read-only validator only if that module:
- cannot write;
- cannot grant;
- performs no implicit discovery;
- imports no runtime execution path.

Prefer independent R25 bridge oracle logic.

## 7. Runtime / Preflight Contract Parity

`GoForwardInputAuthority` and R25 preflight must bind the same versioned daily-input contract.

Forbidden split:

```text
preflight accepts old V1
runtime requires successor
```

Freeze exact successor binding in:
- runtime dependencies;
- activation packet;
- R25 manifest.

Do not change current disabled real authority permissions.

## 8. Mandatory Vectors

At minimum:

```text
R4R2-01 missing target_session_pit_binding → BLOCK
R4R2-02 wrong bridge contract id → preflight + runtime BLOCK
R4R2-03 bridge target date mismatch → BLOCK
R4R2-04 bridge parent mismatch → BLOCK
R4R2-05 bridge child not current accepted V2 → BLOCK
R4R2-06 candidate real_forward_evidence=false → producer BLOCK
R4R2-07 observation real_forward_evidence=false → producer BLOCK
R4R2-08 one all-nine receipt digest changed → BLOCK
R4R2-09 source manifest changed after bridge → BLOCK
R4R2-10 whole-head lineage only/no bridge → BLOCK
R4R2-11 valid ENGINEERING bridge → engineering PASS only, never REAL READY
R4R2-12 valid REAL-shaped synthetic bridge → preflight/runtime parity PASS, still not real evidence
R4R2-13 bridge changes but daily_input_digest not recomputed → BLOCK
R4R2-14 old V1 daily-input object → historical/compatibility only
R4R2-15 preflight and runtime bind same contract digest
R4R2-16 future/pre-close target creates no bridge and no source request
```

## 9. Regression Scope

Mandatory include:

```text
tests/v4_dm01_r4
tests/v4_dm01_r4r1
new tests/v4_dm01_r4r2
tests/test_r25_packet.py
tests/test_r24r1_authority.py
tests/test_r24_activation.py
tests/test_r23_runtime.py
```

plus prior scoped regression baseline.

No new failures.

## 10. Protected State

Must remain:

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_15_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_16_ACCEPTED_HEAD = absent

R25 = WAIT_ACCEPTED_DAILY_INPUT

runtime_authorized = false
real_shadow_authorized = false

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
```

No real DB.

## 11. Required Evidence

Recommended:

```text
reports/dm01_r4r2/
  STAGE_CONTRACT.json
  DAILY_INPUT_SCHEMA_GATE.json
  BRIDGE_PRODUCER_GATE.json
  R25_PREFLIGHT_PARITY_GATE.json
  RUNTIME_CONSUMER_PARITY_GATE.json
  NEGATIVE_MATRIX.json
  FUTURE_SESSION_WAIT_READBACK.json
  PROTECTED_STATE.json
  LOCAL_TEST_SUMMARY.json
  CLEAN_REGRESSION.json
  TESTED_SOURCE_GOVERNANCE.json
  DM01_R4R2_CANDIDATE_SEAL.json
```

## 12. Required Local Exit

```text
DM01_R4R2_LOCAL_REPAIR =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

R25_DAILY_INPUT_SCHEMA_BRIDGE_INTEGRATION =
PASS_LOCAL_REPAIRED

R25_PACKET_PREFLIGHT_BRIDGE_PARITY =
PASS_LOCAL_REPAIRED

R25_BRIDGE_PRODUCER_PATH =
PASS_LOCAL_REPAIRED

REAL_TARGET_SESSION_PACKAGE =
NOT_CREATED

R25 =
WAIT_ACCEPTED_DAILY_INPUT

REAL_SHADOW_EXECUTION =
NOT_STARTED

REAL_SHADOW_OBSERVATIONS =
0

NEXT =
STOP_WAIT_DM01_R4R2_INDEPENDENT_EXTERNAL_AUDIT
```

Commit/push is not external acceptance.
