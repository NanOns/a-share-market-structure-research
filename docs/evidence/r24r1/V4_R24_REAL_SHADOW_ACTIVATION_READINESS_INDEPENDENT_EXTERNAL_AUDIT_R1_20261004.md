# V4 R24｜Real Shadow Activation Readiness Independent External Audit R1｜2026-10-04

## 0. Audit Target

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Execution baseline:

`b6b3105e713187462f49054e62fa70df8b9bd292`

Audited remote HEAD:

`0c9f59fbe723fe0fb0e9d1a6750c339894bc7a5b`

Exact tested source:

`c97b1d091370a236243fe2e7ce06a1dc6281cbf6`

Immutable tested tag:

`refs/tags/codex/r24-activation-tested-source-20261004-r2`

---

# 1. Unique External Decision

```text
R24_EXTERNAL_AUDIT =
PARTIAL_PASS_FORWARD_AUTHORITY_AND_COHORT_IDENTITY_REPAIR_REQUIRED

R24_ENGINEERING_ACCEPTANCE_BINDING = PASS_KEEP
R24_RUNTIME_DEPENDENCIES_V2 = PASS_KEEP
R24_REAL_STORAGE_SUCCESSOR = PASS_KEEP
R24_ACTIVATION_AUTHORITY_V2 = PASS_KEEP
R24_SOURCE_READINESS_ADAPTER = PASS_KEEP
R24_REAL_INITIALIZATION_BOUNDARY = PASS_KEEP
R24_AUTHORITY_FIRST_GATE = PASS_KEEP
R24_TRANSACTION_ATOMICITY = PASS_KEEP
R24_ROLLBACK = PASS_KEEP
R24_LEGACY_ISOLATION = PASS_KEEP
R24_OWNER_PROJECTION_SEMANTIC_EQUIVALENCE = PASS_KEEP
R24_NEGATIVE_MATRIX_A01_A20 = PASS_KEEP
R24_INDEPENDENT_ACTIVATION_ORACLE = PASS_KEEP
R24_TESTED_SOURCE_GOVERNANCE = PASS_KEEP

R24_FORWARD_DAILY_INPUT_AUTHORITY =
FAIL_P0_UNREACHABLE_AFTER_2026_09_30

R24_COHORT_ENROLLMENT_IDENTITY =
FAIL_P0_V4_15_IDENTITY_CONTRACT_MISMATCH

R24_REALTIME_ADMISSION_WRAPPER_SEMANTICS =
P1_FORMALIZATION_REQUIRED

V4_16_REAL_SHADOW_ACTIVATION_READINESS =
BLOCKED_PENDING_R24R1

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
```

R24 proves a large part of the real-activation control plane, but the candidate is not yet truly capable of launching on a future market session.

---

# 2. Scope / Tested Source｜PASS_KEEP

R24 is three commits ahead of the R23R1 baseline.

The exact tested source is:

`c97b1d091370a236243fe2e7ce06a1dc6281cbf6`

Tag:

`codex/r24-activation-tested-source-20261004-r2`

The tag resolves exactly to the tested commit.

Final HEAD is one evidence-only commit ahead.

Post-tested-source changes are limited to:

```text
CLEAN_REGRESSION
R24_CANDIDATE_SEAL
STAGE_CONTRACT_AND_AUDIT_ITEMS
clean runner
JUnit
```

No activation/runtime implementation changed after the tested source.

Clean detached regression:

```text
352 passed
0 failed
0 errors
0 skipped
0 deselected
```

---

# 3. Authority-First Real Entry Gate｜PASS_KEEP

`RealShadowController` loads the exact dependency manifest and exact activation authority before:

```text
source availability observation
storage creation/open
real source consumption
```

Committed authority remains:

```text
runtime_authorized = false
real_shadow_authorized = false
environment_class = REAL
grant = null
external_acceptance = null
```

Therefore the committed real path fails before source consumption.

Environment variables cannot grant permission.

This is correct.

---

# 4. Runtime Dependencies V2｜PASS_KEEP

`V4_16_RUNTIME_DEPENDENCIES_V2` correctly centralizes:

```text
R23/R23R1 engineering acceptance
clock
Observation Slot V2
R23R1 slot runtime policy
PRE16 V3 current audit
Stage/Data/V4-15 heads
owner heads
real storage contract
real migration
source-readiness adapter
initialization boundary
owner adapter
real runtime writer
activation authority
```

The R23R1 policy is no longer controller-local unregistered governance.

No latest/glob/mtime dependency discovery is used.

---

# 5. Engineering / Real Storage Isolation｜PASS_KEEP

R24 does not weaken or rewrite the R23 engineering migration.

It creates a separate real/simulation successor storage contract.

Database identity enforces:

```text
REAL
→ PIT_OBSERVED

ACTIVATION_SIMULATION
→ ACTIVATION_SIMULATION
```

and uses:

```text
namespace = SHADOW_V4
execution_mode = SHADOW
```

Append-only triggers, slot/publication revisions, original-event uniqueness and due-item identity are present.

Engineering-fixture rows cannot be silently admitted to the real storage origin.

---

# 6. Real Initialization Boundary｜PASS_KEEP

The R23 engineering seed is explicitly forbidden for real runtime.

The real boundary requires:

```text
exact first_trade_date in later grant
exact predecessor binding
predecessor evidence class = RECONSTRUCTED_ASOF
counts_as_prior_real_observation = false
```

After initialization, the runtime requires the immediately previous accepted Shadow market session.

Negative cases correctly reject:

```text
previous-session gap
engineering seed
Legacy namespace prior
```

---

# 7. Source Readiness Adapter｜PASS_KEEP

Source first-observed time is captured internally at first exact read.

Caller-supplied backdating is rejected.

Mandatory families are:

```text
OWNER_OUTPUT
T0_SNAPSHOT
```

and exact source digest/authority is required.

Late mandatory source creates:

```text
MISSED_OBSERVATION_SLOT
```

and cannot later be upgraded.

Publication rollback does not erase the source acquisition fact.

---

# 8. Owner Projection Semantic Equivalence｜PASS_KEEP

R24 creates `RealOwnerProjectionV1`.

This was audited beyond the submitted self-report.

The accepted V4-15 `_project()` implementation and the R24 successor were compared after removing exactly:

```text
or date > '2026-09-30'
```

from the accepted guard.

The remaining `_project()` method body is textually identical.

Therefore the successor does not change:

```text
event identities
eligibility conditions
revision behavior
feedback prohibition
control/benchmark inputs
diagnostics
logical-event construction
```

The historical demonstration date ceiling is the only projection-code semantic difference.

---

# 9. Negative Activation Matrix｜PASS_KEEP

A01–A20 all pass expected fail-closed behavior.

These remain PASS_KEEP.

---

# 10. P0 Finding 1｜Forward Daily Input Authority Is Unreachable

## 10.1 Runtime Dependency

The R24 real runtime still constructs:

```text
CurrentStageAuthority
```

and calls:

```text
request['trade_date'] in self.authority.sessions
```

for real execution.

## 10.2 CurrentStageAuthority Hard Freeze

`CurrentStageAuthority` currently requires:

```text
self.data['accepted_trade_date'] == '2026-09-30'
```

or it raises:

```text
DATA_HEAD_UNCHANGED_REQUIRED
```

It then loads the exact calendar from that accepted Data Head.

## 10.3 Accepted Calendar Range

The currently bound calendar contains:

```text
min_session = 2023-07-04
max_session = 2026-09-30
session_count = 789
```

There is no accepted session after 2026-09-30.

Therefore any future real launch date necessarily fails:

```text
ACCEPTED_MARKET_SESSION_REQUIRED
```

Even replacing `V4_DATA_ACCEPTED_HEAD` with a newer daily head would still fail because `CurrentStageAuthority` itself hard-requires the old 2026-09-30 date.

## 10.4 Why This Is P0

R24's target state is:

```text
ACTIVATION_CAPABLE_DISABLED_CANDIDATE
```

A candidate that is reachable only on historical September fixture dates is not activation-capable for future live Shadow.

REV4 §77B explicitly defines a daily incremental path with a target-date calendar, source revisions, cutoff, prior-session head and atomic accepted publication.

The Stage/algorithm authority may remain immutable, but the daily input/Data authority must advance by accepted target trade date.

Therefore:

```text
R24_FORWARD_DAILY_INPUT_AUTHORITY =
FAIL_P0
```

---

# 11. Required Authority Split

R24R1 must separate:

```text
IMMUTABLE ALGORITHM/STAGE AUTHORITY
```

from:

```text
GO-FORWARD DAILY INPUT AUTHORITY
```

Do not modify historical V4-15 Accepted Head or CurrentStageAuthority V2 in place.

Create a V4-16-specific successor input authority that can bind a future accepted daily input head while preserving immutable owners/contracts.

Recommended concepts:

```text
V4_16_GO_FORWARD_INPUT_AUTHORITY_V1
V4_16_DAILY_INPUT_HEAD
```

Equivalent naming is acceptable.

The go-forward authority must bind, per target date:

```text
target_trade_date
accepted market calendar containing target and previous session
accepted source package/snapshot
daily identity/universe
membership if capability requires it
accepted adjusted/raw daily source identity
source availability/cutoff receipts
immutable V4-10～V4-15 owner contracts
parameter/model/state lineage
```

Pure-Core STOCK must not be globally blocked by unavailable sector membership.

---

# 12. Forward Authority Must Be Versioned, Not "Latest"

A real runtime must receive an exact daily input-authority binding from the activation/session grant.

Forbidden:

```text
latest file
directory max date
mtime
implicit current Data Head
```

Each session grant binds exact:

```text
daily_input_authority
daily_input_digest
target_trade_date
calendar identity
source identities
```

A new market date means a new accepted daily input authority/revision.

Stage Head remains unchanged.

---

# 13. Required Future Reachability Engineering Proof

R24R1 must build an isolated future-session fixture whose trade date is:

```text
strictly greater than 2026-09-30
```

using an isolated accepted-like daily input authority.

The test must prove:

```text
old CurrentStageAuthority path would reject
new V4-16 go-forward authority accepts the future fixture
previous market session is explicit
source/readiness identities are exact
no real source is consumed
no real PIT sample is created
```

Do not use a 2026-09-28 or 2026-09-30 fixture as the sole real-path reachability proof.

---

# 14. P0 Finding 2｜Cohort Enrollment Identity Mismatch

## 14.1 Accepted COHORT_V1 Identity

Accepted V4-15 contract freezes:

```text
enrollment_key =
[
  logical_event_id,
  cohort_namespace
]

primary_namespace =
FIRST_OBSERVED
```

Accepted implementation computes:

```text
enrollment_id =
digest([
  logical_event_id,
  cohort_namespace
])
```

## 14.2 R24 Runtime Actual

R24 writes:

```text
cohort_namespace = FIRST_OBSERVED
```

but computes:

```text
enrollment_id =
digest([
  logical_event_id,
  "SHADOW_V4_FIRST_OBSERVED"
])
```

The persisted identity therefore cannot be recomputed from its own accepted key fields.

The independent R24 oracle currently enforces this new formula, so tests pass while the accepted V4-15 identity contract is violated.

## 14.3 Consequences

This can break:

```text
V4-15 / V4-16 enrollment continuity
settlement identity
deduplication
migration replay
cross-version readback
future cutover receipts
```

`enrollment_id` is T0-frozen and append-only.

Therefore:

```text
R24_COHORT_ENROLLMENT_IDENTITY =
FAIL_P0
```

---

# 15. Required Cohort Identity Repair

Use the accepted formula exactly:

```text
cohort_namespace = FIRST_OBSERVED

enrollment_id =
digest([
  logical_event_id,
  "FIRST_OBSERVED"
])
```

or call the accepted V4-15 identity helper with the accepted enrollment key.

The independent oracle must derive the key from:

`config/v4_15_cohort_contract_v1.json`

and independently recompute the ID.

Do not hardcode a new Shadow-specific namespace literal into the enrollment identity.

SHADOW_V4 belongs to runtime/storage namespace, not COHORT_V1 `cohort_namespace`.

---

# 16. P1 Finding｜Realtime Admission Wrapper Semantics

The owner projection is called with:

```text
evidence = REALTIME_ACCEPTED_SOURCE
```

but without V4-15's `accepted_observation_slot` metadata.

Therefore the accepted V4-15 projection internally emits candidate enrollment rows under:

```text
RECONSTRUCTED_ASOF
```

and R24 later promotes/wraps them into:

```text
FIRST_OBSERVED
```

based on its own slot/source transaction.

This can be a valid V4-16 successor admission architecture, because R24 possesses runtime slot/readiness evidence that V4-15's historical projection API cannot read directly.

But it must be explicit.

Required R24R1 semantics:

```text
V4-15 projected enrollment =
CANDIDATE TEMPLATE / ELIGIBILITY OUTPUT ONLY

V4-16 admission layer =
sole authority that creates real FIRST_OBSERVED enrollment
after accepted slot/readiness proof
```

The V4-15 reconstructed namespace must not itself be presented as the accepted cohort authority.

Independent validation must prove the final real enrollment was admitted by:

```text
accepted V4-16 slot
+
accepted mandatory-source receipts
+
accepted owner logical event
+
COHORT_V1 enrollment key
```

Classification:

```text
R24_REALTIME_ADMISSION_WRAPPER_SEMANTICS =
P1_FORMALIZATION_REQUIRED
```

Repair in the same R24R1 round.

---

# 17. PASS_KEEP Areas

Do not reopen:

```text
real/engineering storage isolation
activation authority structure
authority-first gate
source readiness internal clock
initialization-boundary concept
owner projection algorithm semantics
transaction atomicity
rollback
Legacy isolation
A01–A20
R23/R23R1 accepted engineering runtime
clock/slot policy
```

---

# 18. Protected State

R24 correctly preserves:

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_15_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

V4_16_ACCEPTED_HEAD =
NOT_CREATED

runtime_authorized = false
real_shadow_authorized = false

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

Production = false
Shadow = false
Focus = false
V4_16 = false
```

Keep all of this unchanged in R24R1.

---

# 19. Next

```text
R24R1
GO_FORWARD_DAILY_INPUT_AUTHORITY
+
COHORT_IDENTITY_REPAIR
+
REALTIME_ADMISSION_SEMANTICS_FORMALIZATION

→ independent external audit
→ PASS
→ first real V4-16 Shadow launch authorization round
```

Do not start a real Shadow session in R24R1.
