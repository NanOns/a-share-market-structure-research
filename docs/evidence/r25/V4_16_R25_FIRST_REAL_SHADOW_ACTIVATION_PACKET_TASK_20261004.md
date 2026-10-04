# V4-16 R25｜First Real Shadow Activation Packet Task｜2026-10-04

## 0. Mission

Prepare the exact target-session activation packet for the first real:

```text
PIT_OBSERVED + SHADOW_V4
```

session.

This round MUST NOT execute the real Shadow session.

Execution baseline:

`31db7c17463d7a314c4dbfb10023f701c1a9387b`

External authority:

`V4_R24R1_GO_FORWARD_INPUT_AUTHORITY_COHORT_IDENTITY_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md`

## 1. Valid Exit

READY:

```text
R25_REAL_ACTIVATION_PACKET =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

REAL_SHADOW_EXECUTION = NOT_STARTED
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

NEXT =
STOP_WAIT_R25_INDEPENDENT_EXTERNAL_AUDIT
```

Source not ready:

```text
R25_REAL_ACTIVATION_PACKET =
WAIT_ACCEPTED_DAILY_INPUT

REAL_SHADOW_EXECUTION = NOT_STARTED
NEXT = RETRY_ON_NEXT_ELIGIBLE_ACCEPTED_MARKET_SESSION
```

`WAIT_ACCEPTED_DAILY_INPUT` is not a stage failure and must not block unrelated engineering.

## 2. Select Exact Target Session

Do not hardcode a target merely because wall-clock time advanced.

Require:

```text
target market session confirmed
previous market session confirmed
mandatory target-date Pure-Core sources accepted
exact daily input authority constructible
```

If any mandatory target-date source is unavailable, return `WAIT_ACCEPTED_DAILY_INPUT`.

Do not fabricate a READY packet.

## 3. Build Real Daily Input Authority

Use externally accepted `V4_16_GO_FORWARD_INPUT_AUTHORITY_V1`.

Build one exact REAL-environment daily input object binding:

```text
target_trade_date
revision
accepted_at
calendar
previous_trade_date
identity / universe
membership or NOT_REQUIRED_FOR_SCOPE

TDX_RAW_DAILY
ADJUSTED_DAILY
OWNER_OUTPUT
T0_SNAPSHOT

day_package
snapshot_identity
source_manifest_digest
daily_input_digest
immutable algorithm bindings
model/parameter identity
```

Do not use simulation fixtures.

Do not relabel reconstruction as real evidence.

## 4. Source Acceptance vs Runtime Readiness

R25 may bind already accepted upstream source artifacts.

It must not create future runtime readiness receipts.

Distinguish:

```text
UPSTREAM_SOURCE_ACCEPTANCE_TIMES
```

from:

```text
RUNTIME_FIRST_OBSERVED_AT
```

`RUNTIME_FIRST_OBSERVED_AT` is created only when the next externally authorized launch actually consumes the exact source bytes.

No backdating.

## 5. Target-Specific Activation Candidate

Create a non-executable candidate, recommended:

```text
reports/r25/activation_candidate/authority.json
```

Do not overwrite committed disabled authority.

Freeze exact grant fields:

```text
authority_id
effective_trade_date
effective_from
model_contract_id
parameter_set_id
state_lineage_id
capability_scope
clock
slot
runtime_dependency_contract_id
dependency_set_digest
storage
storage_identity
source_adapters
source_authority
rollback_identity
expected_prior_activation_head
initialization_boundary
predecessor
first_trade_date
daily_input_authority
daily_input_digest
target_trade_date
daily_input_boundary
minimum_daily_input_revision
```

## 6. Candidate Is Not Executable

Require:

```text
external_acceptance = null
execution_authorized = false
```

Do not put the candidate at the committed authority path.

Do not alter:

```text
runtime_authorized = false
real_shadow_authorized = false
grant = null
external_acceptance = null
```

in `config/v4_16_runtime_activation_authority_v3.json`.

## 7. Storage Identity

Freeze future real storage identity but do not create/open the DB.

Require:

```text
namespace = SHADOW_V4
execution_mode = SHADOW
evidence_origin = PIT_OBSERVED
migration = exact accepted migration
database_path = exact path under accepted real root
```

No collision with engineering, simulation or Legacy storage.

No real database file may exist after R25.

## 8. First-Session Predecessor

Freeze:

```text
first_trade_date
previous_trade_date
predecessor binding
predecessor evidence class
counts_as_prior_real_observation = false
```

No `R23_ISOLATED_SEED`.

No Legacy prior.

The boundary predecessor may initialize state only under the already accepted initialization contract.

## 9. Source Authority Packet

Freeze exact REAL source authority for the target session:

```text
environment_class = REAL
adapter_id
owner_heads
OWNER_OUTPUT binding
T0_SNAPSHOT binding
target_trade_date
source identity / revision
accepted upstream provider
future settlement source policy
```

Do not prefill runtime `first_observed_at`.

## 10. Capability Scope

Initial real activation remains narrow:

```text
PURE_CORE_STOCK
```

Keep blocked:

```text
A04_H21_CONSUMER
A04_HISTORICAL_AMOUNT_A
A08_CURRENT_RUNTIME
```

Do not silently add sector-dependent scope.

## 11. Exact Activation Packet Manifest

Bind:

```text
R24R1 external acceptance
R24R1 tested source/tag
runtime dependencies V3
go-forward authority contract
real daily input object
activation candidate
source authority
storage identity
initialization boundary
predecessor
rollback identity
protected Stage/Data/V4-15 bytes
```

Compute exact:

```text
packet_digest
authority_digest
daily_input_digest
dependency_set_digest
```

No latest/glob/mtime discovery.

## 12. Independent R25 Preflight Oracle

Must not import:

```text
runtime writer
activation packet writer
daily-input writer
```

Independently recompute:

```text
target session
previous session
daily-input digest
source manifest
nested max_source_trade_date
source timestamp boundary
model/parameter identity
capability scope
storage path/root
predecessor
authority digest
dependency digest
protected state
```

## 13. F12 Governance Improvement

Replace the weak prior F12 test:

1. create a valid decoy `latest.json`;
2. make it different from the exact grant binding;
3. prove runtime cannot resolve it by naming convention;
4. exact binding must win;
5. failure reason should be governance-specific, not FileNotFoundError.

No runtime behavior change is required.

## 14. Target-Date Negative Matrix

At minimum:

```text
R25-01 target source not ready
R25-02 stale previous-day package
R25-03 calendar target missing
R25-04 previous session mismatch
R25-05 daily digest mismatch
R25-06 nested future source date
R25-07 model/parameter mismatch
R25-08 capability scope expansion
R25-09 storage outside real root
R25-10 engineering/simulation storage collision
R25-11 predecessor mismatch
R25-12 predecessor counted as real observation
R25-13 runtime first_observed prefilled/backdated
R25-14 candidate external acceptance prefilled
R25-15 committed disabled authority mutated
R25-16 implicit latest decoy
```

All fail closed.

## 15. Protected State

R25 must preserve:

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_15_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_16_ACCEPTED_HEAD = NOT_CREATED

runtime_authorized = false
real_shadow_authorized = false
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
```

No real Shadow DB is created.

## 16. Parallel Development Rule

If source is not ready:

```text
WAIT_ACCEPTED_DAILY_INPUT
```

does not block unrelated V4-17 UI engineering.

However V4-17 acceptance / V4-17G still require real Shadow evidence.

## 17. Required Evidence

Recommended:

```text
reports/r25/
  TARGET_SESSION_SELECTION.json
  DAILY_INPUT_REAL_GATE.json
  SOURCE_AUTHORITY_REAL_GATE.json
  PREDECESSOR_GATE.json
  STORAGE_IDENTITY_GATE.json
  ACTIVATION_CANDIDATE.json
  ACTIVATION_PACKET_MANIFEST.json
  TARGET_NEGATIVE_MATRIX.json
  INDEPENDENT_R25_PREFLIGHT_ORACLE.json
  PROTECTED_BYTES.json
  LOCAL_TEST_SUMMARY.json
  CLEAN_REGRESSION.json
  R25_CANDIDATE_SEAL.json
```

## 18. Exit

READY:

```text
R25_REAL_ACTIVATION_PACKET =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

AUTHORITY_PACKET_EXECUTION =
BLOCKED_PENDING_EXTERNAL_ACCEPTANCE_DIGEST

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

NEXT =
STOP_WAIT_R25_INDEPENDENT_EXTERNAL_AUDIT
```

If no accepted target-date input exists, return `WAIT_ACCEPTED_DAILY_INPUT` and do not fake PASS.
