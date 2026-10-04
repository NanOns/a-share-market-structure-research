# V4-16 R22｜Realtime Shadow Dual-Run Contract Freeze / Entry Task｜2026-10-04

## 0. Mission

Freeze the executable V4-16 contract before implementing the real Shadow runtime.

V4-16 is defined by the V4.2.2 executable baseline as:

```text
Realtime Shadow Dual-Run

PIT_OBSERVED + SHADOW

真实冻结日账本
+
每日运行 settlement

旧系统继续 production
```

This R22 task is contract-first.

It does not yet grant Shadow execution permission.

---

# 1. Entry Gate

Execution baseline:

`a1bb12f19e758784e55a1a93acaad1954861a0fc`

Required external input:

```text
R21_EXTERNAL_AUDIT =
PASS_FINAL_V4_15_PROMOTION_CAPABILITY_SCOPED

V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_15_ACCEPTED

CURRENT_STAGE_AUTHORITY =
V4_15
```

Read first:

1. `V4_R21_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md`
2. V4.2.2 executable baseline, especially §4.6–4.8, §45–49, §51A, §52A, §77B–77C, §78 and §80
3. this task
4. `V4_NEXT_ROUND_EXECUTION_MASTER_R22_20261004.md`

---

# 2. R22 Scope

R22 must freeze contracts for:

```text
A. Shadow execution identity
B. daily observation slot
C. scheduled cutoff / observation deadline
D. real source freeze
E. PIT_OBSERVED classification
F. Shadow prior-session lineage
G. same-day revision handling
H. validation-cohort realtime enrollment
I. settlement due worker
J. missed observation slots
K. capability-scoped Shadow health
L. legacy-production isolation
M. daily PIT sector membership observation
N. rollback / stop-shadow semantics
```

Do not implement full V4-16 runtime in this round.

---

# 3. Evidence Origin and Execution Mode

Freeze exact enums from the executable baseline:

```text
evidence_origin =
PIT_OBSERVED
RECONSTRUCTED_ASOF
RECONSTRUCTED_CORRECTED
DIAGNOSTIC_NON_PIT

execution_mode =
PRODUCTION
SHADOW
REPLAY
```

V4-16 real observation requires:

```text
evidence_origin = PIT_OBSERVED
execution_mode = SHADOW
namespace = SHADOW_V4
```

Forbidden upgrade:

```text
RECONSTRUCTED_ASOF + REPLAY
→ PIT_OBSERVED + SHADOW
```

Historical replay never increments real Shadow observation counters.

---

# 4. Observation Slot Contract

Freeze:

```text
daily_observation_slot =
(
  model_contract_id,
  state_lineage_id,
  trade_date
)
```

For each market session persist at minimum:

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

The first compliant accepted publication within the frozen deadline is the only publication allowed to create the original realtime enrollment for that slot.

Later same-day revisions may append observations/corrections but cannot create a second original sample.

---

# 5. Cutoff / Deadline Authority

Do not invent a new daily cutoff or deadline in V4-16 implementation.

R22 must bind the accepted authority from V4-00C / publication governance that defines:

```text
scheduled cutoff
observation publication deadline
timezone = Asia/Shanghai
stored UTC timestamp
```

If the exact accepted cutoff/deadline contract cannot be located or is incomplete:

```text
V4_16_OBSERVATION_SLOT_CONTRACT =
BLOCKED_AFFECTED_SCOPE
```

and record a versioned contract-repair requirement.

This must not be bypassed by choosing a convenient new time.

---

# 6. Missed Observation Slot

Freeze:

```text
MISSED_OBSERVATION_SLOT
```

when the first compliant accepted Shadow publication does not exist before the frozen deadline.

A later replay/backfill for that date must be:

```text
RECONSTRUCTED_ASOF
or
RECONSTRUCTED_CORRECTED
```

as applicable.

It cannot retroactively become `PIT_OBSERVED`.

Do not silently reset the Shadow observation start date.

---

# 7. Shadow Namespace and Prior-State Lineage

All Shadow state must include:

```text
model_contract_id
execution_mode = SHADOW
namespace = SHADOW_V4
publication_id
core_revision
state_lineage_id
```

Shadow must read:

```text
SHADOW_V4 previous accepted market session
```

not:

```text
PRODUCTION_LEGACY previous state
```

and not an arbitrary reconstructed V4 prior.

Freeze:

```text
prior_session_state_head
same_day_revision_parent
```

semantics.

All revisions of the same trade date must preserve the same exact previous-market-session predecessor.

---

# 8. Model / Parameter Boundary

A change to any accepted model/parameter/source semantic that is part of model identity must create a new:

```text
model_contract_id
and/or
parameter_set_id
```

as contractually applicable.

It must not rewrite old Shadow observations.

For later Shadow stability accounting:

```text
affected capability stability window resets
```

when model identity changes.

R22 only freezes this rule; it does not declare any stability window passed.

---

# 9. Realtime Validation Cohort Enrollment

V4-16 must reuse the accepted V4-15 cohort identity rules.

Only:

```text
PIT_OBSERVED + SHADOW
```

may create original real Shadow enrollments.

The following must not control enrollment completeness:

```text
Focus
homepage display caps
manual pin
UI filter
ranking visibility
```

All final eligible events covered by the accepted V4-15 cohort contract must be enrolled independently of display.

---

# 10. Same-Day Revision Semantics

Freeze:

```text
original realtime enrollment
=
first compliant accepted observation slot publication
```

Later same-day accepted correction:

```text
append observation revision
mark source_correction
preserve original T0
preserve original enrollment_id
preserve original control assignment
preserve original benchmark basket
preserve FIRST_OBSERVED
advance LATEST_VALIDATED where contract permits
```

A same-day revision must not:

```text
create new original enrollment
reset T0
redraw frozen controls
rewrite prior observation
```

---

# 11. Daily Settlement Worker

V4-15 already delivered due planning and settlement runtime.

V4-16 must freeze the realtime worker contract:

```text
accepted Shadow publication
→ due planner
→ due-item queue/outbox
→ accepted future Data Head availability
→ settlement
→ immutable result revision/readback
```

Rules:

- run settlement daily after accepted source availability;
- use only exact accepted future source;
- never read a future session before due;
- unavailable endpoint remains pending with explicit reason;
- Focus/UI filters cannot stop settlement;
- signal invalidation/confirmation does not stop already enrolled future price settlement;
- source correction appends evaluation revision;
- T0 is never rewritten.

R22 must define idempotency keys and queue/outbox identity.

---

# 12. Current Real Maturity Debt

At R22 start:

```text
CURRENT_REAL_MATURITY_EVIDENCE = NONE
PROVED_HORIZONS = []
UNPROVED_HORIZONS = [1,3,5,10,20]
```

R22 must not fabricate a mature result.

When V4-16 later observes actual due horizons, those real receipts may increment the accepted maturity debt only through the already accepted V4-15 validation path.

Engineering vectors never increment current real maturity.

---

# 13. Legacy Production Isolation

Throughout V4-16:

```text
PRODUCTION_LEGACY
=
continues to be production
```

V4-16 must not:

- replace legacy production;
- change production Focus source;
- change default UI source;
- grant V4 production permission;
- write into Legacy namespace;
- consume Legacy prior state as Shadow V4 prior.

Freeze explicit read/write namespace permissions.

---

# 14. Capability-Scoped Shadow Health

Freeze Shadow health separately at least for:

```text
STOCK_CORE
STOCK_SECTOR_DEPENDENT
SECTOR_STAGE
ROTATION
SECTOR_RISK_CHANGE
```

Daily health receipt must record:

```text
status
capability_scope
trade_date
model_contract_id
parameter_digest
slot_status
source quality
publication status
temporal leakage status
duplicate episode status
state integrity status
P0 violations
settlement backlog
```

One degraded capability must not automatically overwrite an independently valid capability.

Shared dependency failure propagates only to its defined consumers.

---

# 15. Shadow Stable Is NOT R22 Acceptance

Per §52A:

```text
SHADOW_STABLE_PASS[capability]
```

later requires, among other things:

```text
same model_contract_id
20 consecutive market sessions accepted on time
0 temporal leakage
0 duplicate episode corruption
0 Core identity/P0 state violation
rollback drill pass
```

R22 must freeze the counters/receipts needed to measure this.

R22 must not claim:

```text
SHADOW_STABLE
PROVISIONAL_FORWARD_EVIDENCE
FORWARD_SUPPORTED
```

Historical replay cannot be used to fill the 20 sessions.

V4-16 engineering development must not wait 20 sessions to continue to V4-17 engineering work; the real observation counter remains an asynchronous validation gate for later cutover stages.

---

# 16. Provisional Forward Counters

Freeze the fields needed by later §52A gates.

For stock capability:

```text
unique_signal_dates
unique_stock_positive_events
T5_OBSERVED_count
controls_quality
benchmark_quality
```

Do not claim the gate passed in R22.

For sector/rotation, freeze per-event-type counters and do not invent numeric minimums that are still governed by the accepted parameter registry.

---

# 17. PIT Sector Membership From Shadow Start

Per §77C, from actual V4 observed operation begin append-only daily freezing of:

```text
industry_membership_snapshot
concept_membership_snapshot
sector_type_snapshot
```

The contract must preserve:

```text
membership_basis = PIT_OBSERVED
```

for actually observed future Shadow dates.

Pre-observation historical sector membership must remain its existing reconstructed/diagnostic class.

No current membership backfill may become PIT_OBSERVED.

---

# 18. Optional BaoStock Isolation

BaoStock remains Supplemental-only under current accepted capability.

Failure/unavailability:

```text
does not block Pure-Core Shadow publication
```

unless a separately accepted future contract promotes a specific field to mandatory.

Turnover enrichment revisions must not mutate Core eligibility or original observation identity.

---

# 19. Required Contract Artifacts

Create versioned contracts, recommended:

```text
config/v4_16_realtime_shadow_contract_v1.json
config/v4_16_observation_slot_contract_v1.json
config/v4_16_shadow_namespace_contract_v1.json
config/v4_16_shadow_health_contract_v1.json
config/v4_16_settlement_worker_contract_v1.json
config/v4_16_machine_vectors_v1.json
```

Exact filenames may follow repository conventions if semantics remain complete.

Each contract must include:

```text
contract_id
version
accepted predecessor
model/parameter identity
source authority
time semantics
namespace
PIT rules
UNKNOWN/degradation semantics
idempotency
revision behavior
negative vectors
acceptance criteria
```

---

# 20. Independent Frozen Vectors

Freeze expected vectors before runtime implementation.

At minimum:

```text
01 on-time first Shadow slot -> PIT_OBSERVED original enrollment
02 late backfill -> MISSED_OBSERVATION_SLOT + reconstructed only
03 same-day r2 -> correction observation, no second original enrollment
04 Legacy prior injected into SHADOW_V4 -> reject
05 missing exact previous Shadow session -> gap/fail-closed, no skip-day yesterday
06 model/parameter identity change -> new lineage / reset affected window
07 historical replay -> never increments real shadow sessions
08 Focus/UI exclusion -> enrollment and settlement still occur
09 future endpoint before due -> reject
10 due endpoint unavailable -> pending explicit reason
11 settlement rerun same source -> idempotent
12 corrected evaluation source -> append result revision
13 sector membership current-backfill -> cannot become PIT_OBSERVED
14 BaoStock unavailable -> Pure-Core independently continues
15 capability A blocked, independent capability B remains testable
16 P0 state violation -> affected stability window reset
17 missed market session -> not counted as consecutive accepted session
18 Legacy production state remains unchanged
19 source correction after original enrollment -> original T0/controls preserved
20 duplicate logical episode corruption -> P0 fail
```

Expected outputs must be authored independently of future V4-16 runtime helpers.

---

# 21. Independent Contract Oracle

Create an independent R22 contract-completeness oracle that checks:

- all required contracts exist;
- all mandatory semantics above are represented;
- no contract grants Shadow runtime yet;
- no contract grants Production/Focus/UI cutover;
- no historical replay can satisfy realtime counters;
- V4-15 Accepted Head remains current;
- Data Head remains unchanged;
- V4-16 Accepted Head does not exist;
- machine vectors cover every mandatory negative family.

The oracle must not use future runtime output to generate expected vectors.

---

# 22. Protected State

R22 must keep byte-identical:

```text
data/v4/V4_15_ACCEPTED_HEAD.json
data/v4/V4_STAGE_ACCEPTED_HEAD.json
data/v4/V4_DATA_ACCEPTED_HEAD.json
config/v4_current_stage_authority_v2.json
```

and all R20/R20R1/R20R1R1/R20R1R2/R21 accepted evidence.

Do not create:

```text
data/v4/V4_16_ACCEPTED_HEAD.json
```

---

# 23. Permissions

Must remain:

```text
Production = false
Shadow = false
Focus = false
V4_16 runtime = false
```

Important distinction:

R22 may define the Shadow contract.

It may not start claiming a real Shadow observation has occurred.

---

# 24. Regression

Run contract/governance tests in a clean detached checkout.

At minimum include:

- R21 current-stage authority/promotion tests;
- V4-14 replay compatibility;
- V4-15 accepted-head/current-authority tests;
- new R22 contract/vector tests;
- no-symbol/latest-discovery governance checks;
- protected-byte checks.

No broad deselection.

---

# 25. Required R22 Evidence

Recommended:

```text
reports/r22/V4_16_CONTRACT_COMPLETENESS_GATE.json
reports/r22/V4_16_OBSERVATION_SLOT_GATE.json
reports/r22/V4_16_NAMESPACE_GATE.json
reports/r22/V4_16_SETTLEMENT_WORKER_GATE.json
reports/r22/V4_16_VECTOR_COVERAGE.json
reports/r22/V4_16_INDEPENDENT_CONTRACT_ORACLE.json
reports/r22/PROTECTED_BASELINE_BINDINGS.json
reports/r22/LOCAL_TEST_SUMMARY.json
reports/r22/V4_16_CONTRACT_CANDIDATE_SEAL.json

docs/audits/V4_R22_V4_16_CONTRACT_FREEZE_20261004.md
```

---

# 26. Required End State

Only the following local claim is allowed:

```text
R22_V4_16_CONTRACT_FREEZE_ENTRY =
PASS_LOCAL

V4_16_CONTRACT_COMPLETENESS =
PASS_READY_FOR_EXTERNAL_AUDIT

V4_16_RUNTIME =
NOT_IMPLEMENTED_OR_NOT_AUTHORIZED

REAL_SHADOW_OBSERVATIONS =
0

SHADOW_STABLE =
NOT_GRANTED

PROVISIONAL_FORWARD_EVIDENCE =
NOT_GRANTED

V4_15_ACCEPTED_HEAD =
CURRENT

V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_15_ACCEPTED

Production = false
Shadow = false
Focus = false

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

Do not start the V4-16 runtime implementation before the next independent external contract audit.
