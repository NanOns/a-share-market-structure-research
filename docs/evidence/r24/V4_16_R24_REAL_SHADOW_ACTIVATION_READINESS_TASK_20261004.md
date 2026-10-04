# V4-16 R24｜Real Shadow Activation Readiness Task｜2026-10-04

## 0. Mission

Convert the externally accepted R23/R23R1 engineering-only Shadow runtime into an **activation-capable but still disabled** real V4-16 Shadow candidate.

This round must make the real path reachable and auditable without starting a real market-session Shadow observation.

Execution baseline:

`b6b3105e713187462f49054e62fa70df8b9bd292`

External authority:

`V4_R23R1_OBSERVATION_SLOT_RUNTIME_COMPLETENESS_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md`

---

# 1. Required Exit

```text
V4_16_REAL_SHADOW_RUNTIME =
ACTIVATION_CAPABLE_DISABLED_CANDIDATE

V4_16_REAL_SHADOW_ACTIVATION =
NOT_AUTHORIZED

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

V4_16_ACCEPTED_HEAD =
NOT_CREATED

Production = false
Shadow = false
Focus = false
V4_16 = false

NEXT =
STOP_WAIT_R24_INDEPENDENT_EXTERNAL_AUDIT
```

Do not create the first real observation in R24.

---

# 2. Formalize R23/R23R1 Engineering Acceptance

Create a versioned engineering acceptance head, recommended:

```text
data/v4/V4_16_RUNTIME_ENGINEERING_ACCEPTED_HEAD_R1.json
```

It must bind:

```text
R22/R22R1 accepted clock governance
R23 external audit
R23R1 external audit
R23R1 tested source/tag
R23R1 slot runtime policy
current Stage/Data/V4-15 heads
```

Scope:

```text
ENGINEERING_RUNTIME_ONLY
REAL_ACTIVATION_NOT_GRANTED
```

Do not create `V4_16_ACCEPTED_HEAD`.

---

# 3. Create Runtime Dependencies V2

Create a successor dependency manifest, recommended:

```text
config/v4_16_runtime_dependencies_v2.json
```

It must explicitly bind:

```text
V4_16_RUNTIME_ENGINEERING_ACCEPTED_HEAD_R1
V4_16_CLOCK_CONTRACT_V1
V4_16_OBSERVATION_SLOT_CONTRACT_V2
V4_16_R23R1_SLOT_RUNTIME_POLICY_V1
V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3
V4_15_ACCEPTED_HEAD
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
owner accepted heads
real-storage contract/migration
activation authority
source-readiness adapters
```

No new runtime policy may remain as an unregistered controller-local hardcoded dependency.

No `latest`, glob, mtime or max-version discovery.

---

# 4. Separate Engineering and Real Evidence Origins

The R23 storage is intentionally hard constrained to:

```text
ENGINEERING_FIXTURE
```

Do not weaken that historical migration in place.

Create a successor real-Shadow storage contract/migration.

Real accepted rows must support only explicitly authorized evidence classes such as:

```text
PIT_OBSERVED
```

under:

```text
namespace = SHADOW_V4
execution_mode = SHADOW
```

Engineering fixture storage must remain physically isolated from real Shadow storage.

Forbidden:

```text
editing R23 historical migration to permit real data
sharing one DB where engineering rows can be mistaken for PIT rows
copying engineering rows into real tables
```

---

# 5. Real Activation Authority V2

Create a successor authority, recommended:

```text
config/v4_16_runtime_activation_authority_v2.json
```

Current committed value must remain:

```text
runtime_authorized = false
real_shadow_authorized = false
```

It must define the exact future grant fields required to authorize real execution, including:

```text
authority_id
effective_trade_date / effective_from
model_contract_id
parameter_set_id
state_lineage_id
capability_scope
clock contract
slot contract
runtime dependency manifest
storage identity
source adapters
rollback identity
expected prior activation head
external acceptance binding
```

An environment variable or CLI flag alone can never grant execution.

---

# 6. Make REAL_SHADOW Code Path Reachable

Current R23 controller physically rejects `REAL_SHADOW` unconditionally.

R24 must refactor this into:

```text
REAL_SHADOW requested
    ↓
exact activation authority read
    ↓
authority disabled -> reject before source read / DB open
    ↓
authority accepted+enabled -> continue
```

Production committed authority remains disabled.

The enabled branch must be proven only in an isolated activation-simulation fixture that uses an isolated successor authority, not by modifying the real committed authority.

The test proves the code path is reachable; it does not create a real sample.

---

# 7. Real Source Readiness Adapter

Implement a real source-readiness adapter for mandatory V4-16 inputs.

It must capture, append-only:

```text
source_identity
source_revision
source_digest
first_observed_at
integrity_passed_at
system_available_at
created_at
target_trade_date
provider/receipt kind
accepted source authority
```

Rules:

```text
first_observed_at cannot be caller-backdated
exact consumed bytes/digest must match
mandatory-source complete-set visibility drives slot aggregates
late source => MISSED_OBSERVATION_SLOT
later reconstruction never upgrades PIT status
```

No external/provider raw fallback outside accepted source authority.

---

# 8. Real Prior-State Initialization Boundary

R23 engineering uses:

```text
R23_ISOLATED_SEED
```

That seed is forbidden for real Shadow.

R24 must define a separately versioned real initialization boundary.

It must answer:

```text
what is the first real Shadow trade date?
what exact accepted state is used as predecessor?
what evidence class is that predecessor?
what fields may be initialized?
what fields remain UNKNOWN?
how is the boundary distinguished from later true SHADOW_V4 prior sessions?
```

A reconstructed predecessor may initialize state only under an explicit boundary contract and must not be counted as a prior real observation.

After the first real accepted Shadow session, every next session must use the immediately previous accepted Shadow market session.

---

# 9. Scheduler / Launch Controller

Implement a launch controller for one market session.

It must:

1. verify accepted market session;
2. verify activation authority;
3. create/lock the daily slot;
4. collect source readiness receipts;
5. freeze mandatory-source manifest;
6. run exact accepted owner adapters;
7. atomically publish SHADOW_V4;
8. create real cohort enrollments where eligible;
9. create due outbox;
10. write health receipt;
11. perform readback;
12. leave Legacy production unchanged.

R24 does not execute this controller against a real session.

---

# 10. Capability Scope

At real launch, preserve current capability isolation.

At minimum:

```text
A04_H21_CONSUMER = blocked
A04_HISTORICAL_AMOUNT_A = blocked
A08_CURRENT_RUNTIME = blocked unless separately accepted
```

Pure-Core independent stock path may continue when optional/scope-limited dependencies are unavailable.

The activation authority must enumerate allowed capabilities explicitly.

---

# 11. Real Cohort Rules

Future real enrollment requires all:

```text
PIT_OBSERVED
execution_mode = SHADOW
namespace = SHADOW_V4
slot_status = ACCEPTED_ON_TIME
first compliant publication
accepted model/parameter/state lineage
eligible accepted owner event
```

Same-day corrections:

```text
append observation
preserve original enrollment
preserve T0
preserve controls/benchmark
preserve FIRST_OBSERVED
set supersedes_observation correctly
```

No second original sample.

---

# 12. Real Storage Atomicity

Real storage must enforce, at database level where feasible:

```text
append-only accepted facts
unique original logical event
unique slot revision
unique publication revision
due-item idempotency
head CAS
no delete of accepted observations
no cross-namespace prior
```

Failure before commit must leave no partially visible publication/cohort/outbox/head.

---

# 13. Settlement Continuity

Reuse accepted V4-15 settlement logic.

Real due processing must require:

```text
due date reached
future source accepted by then-current Data Head
exact future endpoint binding
no raw provider fallback
T0 controls/benchmark frozen
append-only outcome revision
```

Stopping Shadow must not cancel already accepted settlement obligations.

---

# 14. Activation Simulation E2E

Build an isolated E2E in which:

```text
production committed authority = disabled
isolated simulated authority = enabled
isolated real-storage successor = temporary
source readiness = deterministic fixture
```

The test must prove:

```text
REAL_SHADOW code path is reachable
slot fields satisfy V2
PIT semantics are applied only inside simulation
transaction atomicity holds
rollback holds
no Legacy mutation
no committed real counters change
```

The simulation rows must be unmistakably tagged:

```text
ACTIVATION_SIMULATION
NOT_REAL_EVIDENCE
```

and must not enter any real cohort/session count.

---

# 15. Negative Activation Matrix

At minimum:

```text
A01 disabled authority
A02 authority digest mismatch
A03 authority effective date mismatch
A04 wrong model contract
A05 wrong parameter set
A06 wrong state lineage
A07 ungranted capability
A08 unaccepted storage identity
A09 unaccepted source adapter
A10 missing mandatory source
A11 source arrives after cutoff
A12 backdated first_observed_at
A13 previous Shadow session gap
A14 attempt to use engineering seed in real mode
A15 Legacy prior
A16 transaction failure
A17 second original enrollment
A18 same-day correction breaks supersedes chain
A19 activation head CAS conflict
A20 environment flag without accepted authority
```

All fail closed.

---

# 16. No Real Session in R24

Hard prohibition:

```text
do not read today's source availability as a real Shadow receipt
do not create a PIT_OBSERVED real row
do not increment REAL_SHADOW_OBSERVATIONS
do not create V4_16_ACCEPTED_HEAD
```

R24 is launch-readiness engineering only.

---

# 17. Independent Activation Oracle

The independent oracle must not import the activation/runtime writer.

It must inspect:

```text
authority bindings
storage schema
simulated slot
source receipts
manifest
publication/cohort/outbox/head
rollback
Legacy isolation
real counters
```

and distinguish:

```text
ACTIVATION_SIMULATION
vs
PIT_OBSERVED_REAL
```

---

# 18. Protected State

Keep:

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_15_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

V4_16_ACCEPTED_HEAD =
NOT_CREATED

Production = false
Shadow = false
Focus = false
V4_16 = false
```

---

# 19. Parallel-Development Boundary

Do not wait for 20 real market sessions before continuing unrelated engineering.

After R24 external acceptance:

- a later launch round may activate the first real V4-16 Shadow session;
- V4-17 Shadow UI engineering may proceed in parallel once the real runtime contract is accepted;
- V4-17G `SHADOW_STABLE` / Forward evidence remains gated by actual accumulated evidence.

No historical replay may substitute for the real Shadow window.

---

# 20. Required Evidence

Recommended:

```text
reports/r24/
  R23R1_EXTERNAL_ACCEPTANCE_BINDING.json
  RUNTIME_ENGINEERING_ACCEPTED_HEAD_GATE.json
  DEPENDENCY_MANIFEST_V2_GATE.json
  REAL_STORAGE_SCHEMA_GATE.json
  ACTIVATION_AUTHORITY_V2_GATE.json
  REAL_PATH_REACHABILITY_GATE.json
  REAL_INITIALIZATION_BOUNDARY_GATE.json
  SOURCE_READINESS_ADAPTER_GATE.json
  ACTIVATION_SIMULATION_E2E.json
  NEGATIVE_ACTIVATION_MATRIX.json
  INDEPENDENT_ACTIVATION_ORACLE.json
  LEGACY_ISOLATION_GATE.json
  ROLLBACK_GATE.json
  PROTECTED_BYTES.json
  LOCAL_TEST_SUMMARY.json
  CLEAN_REGRESSION.json
  R24_CANDIDATE_SEAL.json
```

---

# 21. Exit State

```text
R24_REAL_SHADOW_ACTIVATION_READINESS =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

REAL_SHADOW_RUNTIME =
ACTIVATION_CAPABLE_DISABLED_CANDIDATE

runtime_authorized = false
real_shadow_authorized = false

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

V4_16_ACCEPTED_HEAD = NOT_CREATED

Production = false
Shadow = false
Focus = false
V4_16 = false

NEXT =
STOP_WAIT_R24_INDEPENDENT_EXTERNAL_AUDIT
```
