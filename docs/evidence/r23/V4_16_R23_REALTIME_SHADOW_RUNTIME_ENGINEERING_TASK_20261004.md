# V4-16 R23｜Realtime Shadow Runtime Engineering Candidate Task｜2026-10-04

## 0. Mission

Implement the V4-16 Shadow runtime in a disabled, externally auditable engineering state.

This round builds the actual runtime machinery required by the accepted V4-16 contracts.

It must not start real Shadow on a market session and must not create any real `PIT_OBSERVED` sample.

Execution baseline:

`942997f8a5bce06e34a6e37d013e4d27e7175438`

External authority:

`V4_R22R1_CLOCK_AUTHORITY_AND_GOVERNANCE_NORMALIZATION_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md`

Required accepted inputs:

```text
V4_16_CONTRACT_ACCEPTED_HEAD_R1
V4_16_CLOCK_CONTRACT_V1
V4_16_OBSERVATION_SLOT_CONTRACT_V2
V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3
V4_15_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_STAGE_ACCEPTED_HEAD
```

---

# 1. Required End Goal

Build an executable runtime candidate for:

```text
PIT_OBSERVED + SHADOW
namespace = SHADOW_V4
```

while remaining physically disabled from real market-session activation.

Required final state:

```text
V4_16_RUNTIME_ENGINEERING =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

V4_16_RUNTIME_ACTIVATION =
NOT_AUTHORIZED

REAL_SHADOW_OBSERVATIONS =
0

PIT_OBSERVED_REAL_SAMPLES =
0

Shadow = false
Production = false
Focus = false
V4_16 = false
```

---

# 2. Architecture Rule

Do not create a second independent algorithm world.

The V4-16 runtime must orchestrate already accepted producers/contracts where applicable.

It must not reimplement accepted V4-10～V4-15 business semantics just to make Shadow run.

Use explicit versioned dependency bindings.

Forbidden:

```text
latest file discovery
mtime selection
implicit fallback to Legacy
raw provider fallback
automatic capability upgrade
historical replay as runtime seed
```

---

# 3. Runtime Components Required

Implement at minimum:

```text
A. ShadowRuntimeController
B. ClockPolicyResolver
C. SourceReadinessReceiptRegistry
D. ObservationSlotPlanner
E. MandatorySourceFreezeBuilder
F. ShadowPriorStateReader
G. ShadowPublicationBuilder
H. ShadowPublicationAcceptanceTransaction
I. RealtimeCohortEnrollmentWriter
J. DailyMembershipSnapshotWriter
K. DueOutboxScheduler
L. SettlementWorkerOrchestrator
M. ShadowHealthReceiptWriter
N. ShadowReadbackReader
O. StopShadow / RollbackController
```

Naming may follow repository conventions.

---

# 4. Runtime Activation Must Be Explicitly Disabled

The runtime candidate must require a separate future activation authority.

Recommended:

```text
config/v4_16_runtime_activation_authority_v1.json
```

with current value:

```text
runtime_authorized = false
real_shadow_authorized = false
```

Every real-runtime entrypoint must fail closed when these are false.

Do not use an environment variable alone as permission.

Permission requires a versioned accepted authority.

---

# 5. Engineering Modes

Support explicit modes:

```text
CONTRACT_TEST
ENGINEERING_FIXTURE
DRY_RUN_NO_ACCEPT
REAL_SHADOW
```

For this R23 round:

```text
REAL_SHADOW =
forbidden
```

Only the first three may execute.

Any attempt to use `REAL_SHADOW` without accepted runtime authority must fail before source consumption or database writes.

---

# 6. Clock Resolver

Bind exactly:

`config/v4_16_clock_contract_v1.json`

Per accepted market session derive:

```text
scheduled_cutoff_at =
21:00 Asia/Shanghai

observation_deadline =
22:30 Asia/Shanghai
```

stored as UTC.

No caller-supplied time may override these values.

Clock policy changes require a new accepted clock contract.

---

# 7. Source Readiness Receipts

Implement durable receipt schemas for mandatory consumed sources.

At minimum:

```text
receipt_id
receipt_kind
source_family
source_identity
source_revision
source_digest
first_observed_at
system_available_at
integrity_passed_at
accepted
integrity_pass
target_trade_date
created_at
```

Allowed receipt kinds:

```text
FIRST_ACCEPTED_PROVIDER_READINESS_OBSERVATION
ACCEPTED_LOCAL_OBSERVATION_ACQUISITION
```

Required rules:

```text
first_observed_at is append-only
source digest immutable
no backdating
no overwriting old receipt
exact consumed digest must equal receipt digest
```

A later more complete source must create a new revision/receipt.

---

# 8. Observation Slot Runtime

Use exact key:

```text
(
  model_contract_id,
  state_lineage_id,
  trade_date
)
```

Implement states:

```text
PLANNED
BLOCKED_SOURCE_NOT_READY
ACCEPTED_ON_TIME
MISSED_OBSERVATION_SLOT
```

Only future externally authorized REAL_SHADOW may transition into accepted real observation.

In R23 engineering tests:

```text
ACCEPTED_ON_TIME
```

must be marked:

```text
ENGINEERING_ONLY
```

and must not increment any real counter.

---

# 9. Source Freeze Manifest

For each candidate Shadow publication freeze:

```text
trade_date
calendar identity
universe identity
membership identity where applicable
mandatory source receipt ids
mandatory source digests
optional source receipts
model_contract_id
parameter_set_id
state_lineage_id
prior_session_state_head
scheduled_cutoff_at
observation_deadline
source_manifest_digest
```

Manifest must be immutable after accepted engineering fixture publication.

No future source may enter a frozen T0 manifest.

---

# 10. SHADOW_V4 Prior-State Reader

Read only:

```text
SHADOW_V4
exact previous accepted market session
same model/state lineage
```

Never read:

```text
PRODUCTION_LEGACY prior
latest reconstructed state
arbitrary previous calendar day
```

Missing required previous Shadow session:

```text
GAP_FAIL_CLOSED
```

No skip-day recovery.

An initialization boundary, when later needed, must be separately versioned and accepted.

---

# 11. Business Producer Wiring

Runtime may invoke accepted business producers only through exact versioned adapters.

At minimum preserve:

```text
V4-10 State Reducer
V4-11 Confirmation/Event
V4-12 Structure/Anchor/Support
V4-13 Advanced Projection/Context
V4-14 Replay-authority semantics
V4-15 Radar/Cohort/Settlement contracts
```

Do not reinterpret their algorithms.

If a required producer lacks runtime acceptance for a capability, mark the affected capability:

```text
BLOCKED_AFFECTED_SCOPE
or
UNKNOWN
```

rather than inventing output.

---

# 12. Existing Capability Restrictions

R23 must preserve at least:

```text
A04_H21_CONSUMER =
not active

A04_HISTORICAL_AMOUNT_A =
not active

A08_CURRENT_RUNTIME =
not active in Shadow until separately accepted

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

REALTIME_ACCEPTED_COHORT_MATURITY =
NOT_GRANTED
```

These restrictions must not block unrelated infrastructure engineering.

---

# 13. Realtime Cohort Enrollment

Reuse accepted V4-15 cohort identity.

Future real enrollment requires all:

```text
PIT_OBSERVED
execution_mode = SHADOW
namespace = SHADOW_V4
slot = accepted on time
eligible event under accepted producer capability
```

R23 engineering fixtures may simulate the transition but must store:

```text
evidence_origin =
ENGINEERING_FIXTURE
```

or equivalent non-PIT status.

They must never enter the real cohort tables/counters.

---

# 14. Same-Day Revision

First compliant publication defines original T0.

Later same-day revision must:

```text
append publication revision
append observation revision
preserve original enrollment id
preserve T0
preserve prior-session predecessor
preserve controls
preserve benchmark
preserve FIRST_OBSERVED
```

A corrected source may advance only the explicitly allowed latest-validated projection.

No overwrite.

---

# 15. Daily PIT Membership Capture

Implement a daily capture path for future sector-dependent Shadow capabilities.

Persist:

```text
sector_id
security_id
trade_date
observed_at
system_available_at
source_revision
source_digest
membership_basis
membership_quality
```

Only actual future observed capture may later be classified PIT-observed.

Historical/current-membership replay remains non-PIT.

If membership is unavailable:

```text
sector-dependent scope blocked/unknown
Pure-Core independent stock scope may continue
```

---

# 16. Transactional Shadow Publication

Implement a single acceptance transaction equivalent to:

```text
STAGING_INVISIBLE
→ quality/identity/coverage checks
→ source manifest freeze
→ publication rows
→ state rows
→ cohort rows
→ due outbox
→ health receipt
→ accepted head CAS
→ COMMIT_VISIBLE
```

On failure:

```text
whole batch invisible
no partial cohort enrollment
no visible accepted head
no due outbox leakage
```

Use database transactions and CAS/unique constraints, not application promises only.

---

# 17. Storage / Migration Scope

Create versioned migration(s) for Shadow runtime storage.

Required logical entities at minimum:

```text
shadow_observation_slots
shadow_source_readiness_receipts
shadow_source_freeze_manifests
shadow_publications
shadow_publication_heads
shadow_state_heads
shadow_observations
shadow_first_enrollments
shadow_membership_snapshots
shadow_due_outbox
shadow_outcome_revisions
shadow_health_receipts
```

Exact naming may follow repository schema conventions.

R23 may:

```text
create migration SQL
exercise migration in isolated test database
```

R23 must not:

```text
apply the migration to formal user production database
start persistent live Shadow scheduling
```

Persistent environment application is owned by a later externally authorized launch round.

---

# 18. Idempotency

Require unique/idempotent keys for:

```text
observation slot
source readiness receipt identity
source freeze manifest digest
publication revision
accepted head
original enrollment
due item
settlement revision
membership snapshot
health receipt
```

Repeated execution with identical inputs must produce no duplicate logical episode.

---

# 19. Settlement Orchestration

Reuse accepted V4-15 due/settlement runtime contracts.

R23 implements orchestration wiring only.

Rules:

```text
pre-due future read = reject
future Data Head must be accepted exact authority
raw provider fallback = forbidden
invalidated/exited enrolled events remain settleable
UI-hidden events remain settleable
control/benchmark frozen at T0
source correction -> append settlement revision
```

Engineering fixtures cannot prove real maturity.

---

# 20. Shadow Health Runtime

Implement per-capability receipts for:

```text
publication success/failure
source quality
temporal leakage
state integrity
duplicate episode
settlement backlog
clock compliance
parameter/model identity
capability blocked/unknown state
```

No health receipt may grant:

```text
SHADOW_STABLE
PROVISIONAL_FORWARD_EVIDENCE
FORWARD_SUPPORTED
```

R23 real session count remains zero.

---

# 21. Stop-Shadow / Rollback

Implement an engineering-tested stop path.

Required behavior:

```text
stop new Shadow acceptance
preserve all accepted Shadow artifacts
preserve pending settlement obligations
do not mutate Legacy production
reader can be switched away from Shadow candidate
restart requires explicit authority
```

Rollback must not delete observations.

---

# 22. Legacy Isolation

Prove:

```text
Legacy production reads unchanged
Legacy writes unchanged
Legacy default UI unchanged
Focus unchanged
```

Shadow engineering may not write to Legacy namespace.

No shared mutable prior-state table without namespace key.

---

# 23. No Real Source Consumption in Acceptance Tests

R23 validation must not depend on current wall-clock market state.

Use:

```text
immutable engineering fixtures
isolated test DB
frozen source receipts
frozen market calendar fixtures
```

Do not create real readiness receipts from today's actual source availability.

This prevents acceptance tests from accidentally creating the first real Shadow sample.

---

# 24. Required Positive E2E Engineering Fixture

Build one complete isolated E2E:

```text
accepted clock
→ source readiness receipts
→ source freeze manifest
→ Shadow prior
→ accepted producer fixture outputs
→ Shadow publication
→ original engineering enrollment
→ due outbox
→ health receipt
→ accepted engineering head
→ readback
```

Expected:

```text
transaction atomic
idempotent rerun
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
```

This fixture proves reachability only.

---

# 25. Required Negative E2E Families

At minimum:

```text
N01 runtime authority missing
N02 clock mismatch
N03 late mandatory source
N04 missing readiness receipt
N05 source digest mismatch
N06 backdated readiness
N07 Legacy prior attempted
N08 missing previous Shadow session
N09 same-day correction tries new original enrollment
N10 partial transaction failure
N11 duplicate logical event
N12 raw/provider fallback
N13 future read before due
N14 unaccepted future Data Head
N15 current-membership replay tries PIT
N16 blocked A04 capability used
N17 blocked A08 capability used
N18 BaoStock unavailable Pure-Core continues
N19 parameter change without new identity
N20 clock-policy change without new version
N21 UI exclusion tries removing cohort
N22 settlement tries redraw control/benchmark
N23 engineering fixture tries incrementing real session count
N24 rollback tries deleting accepted observations
```

Each must fail closed at the affected scope.

---

# 26. Independent Runtime Oracle

The independent validator must not import the runtime writer/orchestrator.

It must independently inspect:

```text
database rows
source digests
transaction receipts
slot identities
publication lineage
prior-state lineage
enrollment identity
due outbox
health receipts
readback
```

Do not validate the writer by calling the writer's own predicate helpers.

---

# 27. Current Authority Binding

Runtime must bind exact:

```text
V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3
```

by path + digest.

Do not use:

```text
latest audit head glob
max version discovery
mtime
directory scan
```

The P2 inherited lineage metadata noted in R22R1 external audit must not be used as runtime permission or predecessor discovery.

---

# 28. Protected State

Must keep exact:

```text
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_10～V4_15 Accepted Heads
V4_15_ACCEPTED_HEAD
V4_16_CONTRACT_ACCEPTED_HEAD_R1
V4_16_CLOCK_CONTRACT_V1
V4_16_OBSERVATION_SLOT_CONTRACT_V2
PRE16 V1/V2/V3 current-audit artifacts
R22/R22R1 evidence
Legacy business runtime
```

Do not create:

```text
V4_16_ACCEPTED_HEAD
```

---

# 29. Required Tests

Run all prior relevant suites plus new R23 tests.

At minimum include:

```text
all PRE16 governance tests
R21 promotion tests
R22 contract tests
R22R1 clock tests
R23 runtime unit tests
R23 isolated DB transaction tests
R23 E2E engineering tests
```

Clean detached checkout.

No broad deselection.

---

# 30. Required Evidence

Recommended:

```text
reports/r23/
  R22R1_EXTERNAL_ACCEPTANCE_BINDING.json
  RUNTIME_COMPONENT_INVENTORY.json
  STORAGE_SCHEMA_GATE.json
  MIGRATION_ISOLATED_DB_GATE.json
  SOURCE_RECEIPT_GATE.json
  SLOT_RUNTIME_GATE.json
  SHADOW_PRIOR_GATE.json
  TRANSACTION_ATOMICITY_GATE.json
  COHORT_ENROLLMENT_GATE.json
  MEMBERSHIP_CAPTURE_GATE.json
  SETTLEMENT_ORCHESTRATION_GATE.json
  HEALTH_RECEIPT_GATE.json
  LEGACY_ISOLATION_GATE.json
  ROLLBACK_DRILL.json
  POSITIVE_E2E_ENGINEERING.json
  NEGATIVE_E2E_MATRIX.json
  INDEPENDENT_RUNTIME_ORACLE.json
  PROTECTED_BYTES.json
  LOCAL_TEST_SUMMARY.json
  CLEAN_REGRESSION.json
  R23_RUNTIME_CANDIDATE_SEAL.json
```

---

# 31. Required Tested Source Governance

If runtime implementation changes after tests:

```text
rerun tests
```

Final tested source must have an immutable tag, recommended:

```text
codex/r23-runtime-tested-source-20261004-r1
```

Final branch may be evidence-only ahead of tested source.

No source code drift after tested source.

---

# 32. Required Exit State

Only:

```text
R22R1_EXTERNAL_ACCEPTANCE =
FORMALIZED

V4_16_RUNTIME_ENGINEERING =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

V4_16_RUNTIME_IMPLEMENTED =
ENGINEERING_CANDIDATE_DISABLED

V4_16_RUNTIME_ACTIVATION =
NOT_AUTHORIZED

REAL_SHADOW_OBSERVATIONS =
0

PIT_OBSERVED_REAL_SAMPLES =
0

SHADOW_STABLE =
NOT_GRANTED

PROVISIONAL_FORWARD_EVIDENCE =
NOT_GRANTED

FORWARD_SUPPORTED =
NOT_GRANTED

V4_16_ACCEPTED_HEAD =
NOT_CREATED

V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_15_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

Production = false
Shadow = false
Focus = false
V4_16 = false

NEXT =
STOP_WAIT_R23_INDEPENDENT_EXTERNAL_AUDIT
```

Do not launch real Shadow in R23.
