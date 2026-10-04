# V4-21 R30｜Continued Forward Observation Contract Design Task｜2026-10-04

## 0. Mission

Freeze the V4-21 Continued Forward Observation machine contract while real V4-16 Shadow evidence is still pending.

This round is:

```text
CONTRACT_DESIGN_ONLY
```

It MUST NOT manufacture forward evidence or reimplement the settlement engine.

Execution baseline:

`c38c25dd189b3996f53e85dc64bbc142db1c188e`

External authority:

`V4_R29_V4_20_DEFAULT_UI_CUTOVER_CONTRACT_DESIGN_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md`

## 1. Normative Boundary

REV4 V4-21:

```text
continue accumulating Shadow/Production stratified evidence
do not first develop settlement here
```

Existing accepted owners remain:

```text
V4-15 cohort / controls / due / settlement / outcome revision
V4-16 realtime Shadow runtime
V4-17G capability gates
V4-19 permission contracts
```

R30 only freezes how continued evidence is accumulated and read.

## 2. Machine Contract

Create, recommended:

```text
config/v4_21_continued_forward_observation_contract_v1.json
```

Freeze:

```text
observation namespace
evidence lane
capability scope
model/parameter/state lineage
accepted session identity
signal/event identity
enrollment identity
due/outcome identity
benchmark/control identity
right-censor status
source quality
revision semantics
aggregation windows
stratification keys
permission/gate readback
```

## 3. Separate Evidence Lanes

Never merge:

```text
SHADOW_REAL
PRODUCTION_REAL
HISTORICAL_REPLAY
RECONSTRUCTED_ASOF
ACTIVATION_SIMULATION
```

Only:

```text
PIT_OBSERVED + accepted real publication
```

may count toward real Shadow/Production forward evidence.

Historical/reconstructed/simulation may remain diagnostics but cannot increment real gate counts.

## 4. Capability Scope

Evidence must be tracked independently for:

```text
STOCK_CORE
STOCK_SECTOR_DEPENDENT
SECTOR_STAGE
ROTATION
SECTOR_RISK_CHANGE
```

A row may count only for the exact capability that owns the accepted event/publication.

Do not borrow:

```text
stock sample counts for sector
sector sample counts for rotation
shared source availability for production permission
```

## 5. Model / Parameter / Lineage Boundaries

Every evidence row binds exact:

```text
model_contract_id
parameter_digest
state_lineage_id
capability
```

A parameter/model change:

```text
does not rewrite prior evidence
starts a new compatible observation partition
resets affected consecutive-window gates
preserves old evidence for audit
```

Do not concatenate incompatible windows.

## 6. Accepted Session Ledger

Freeze one canonical accepted-session ledger.

For each market session record:

```text
trade_date
market_session_id
capability
execution_mode
evidence_origin
slot status
publication id/revision
source availability
evaluability
missed reason
model/parameter/lineage
```

Missed/non-evaluable sessions remain in the denominator ledger.

They do not silently disappear.

## 7. Event / Cohort Ledger

For every eligible accepted event carry:

```text
logical_event_id
event_type
entity id
capability
T0
enrollment_id
original revision
displayed/hidden status
control assignment
benchmark identity
model/parameter/lineage
```

Display exclusion never removes an eligible event from Validation Cohort evidence.

No duplicate original enrollment.

## 8. Due / Outcome Ledger

Reuse V4-15 identities.

Track:

```text
due_id
enrollment_id
horizon
due_date
status
outcome_revision
source identity
observed_at
right_censor_reason
suspension/delisting/missing handling
benchmark/control outcome
MFE/MAE/MDD where owned by accepted contract
```

Forward outcomes only append/revise under accepted settlement rules.

R30 must not create a new settlement owner.

## 9. Right Censor / Pending

Freeze exact states:

```text
PENDING_NOT_DUE
PENDING_SOURCE_UNAVAILABLE
RIGHT_CENSORED
OBSERVED
INVALIDATED_BY_CONTRACT
```

Do not convert pending or censored observations into failures or successes.

Do not drop them from denominators without an explicit contract rule.

## 10. Stratification

Evidence readback must support at least:

```text
capability
execution lane
model/parameter version
market regime
sector context where valid
event type
signal date
horizon
quality stratum
```

Stratification is readback/analysis only.

It must not retroactively alter event eligibility.

## 11. Shadow vs Production Continuity

When a capability later moves:

```text
SHADOW_REAL
→ PRODUCTION_REAL
```

keep both evidence lanes distinct.

Production evidence may continue the same model/capability lineage only if exact identities match.

Do not relabel historical Shadow rows as Production.

Combined reporting may aggregate compatible lanes only with explicit lane breakdown.

## 12. Continued Gate Readback

V4-21 may read, but never grant, gate state.

Freeze readback for:

```text
SHADOW_STABLE_PASS[capability]
FORWARD_GATE[capability]
MIGRATION_REPLAY_PASS[capability]
production_permission[capability]
```

Gate ownership stays with accepted V4-17G / V4-18 / V4-19 authorities.

V4-21 observation accumulation does not auto-cut over anything.

## 13. No Threshold Retuning

Explicitly forbid:

```text
lowering thresholds because sample is small
changing event definitions after seeing outcomes
dropping failed events from denominator
changing model boundary to preserve streak
using only winning market regimes
```

Any algorithm/parameter change requires a new model/cohort boundary.

## 14. Real-Time Daily Operation Contract

Define future daily sequence:

```text
accepted target-session publication
→ append accepted-session ledger
→ append new eligible events/cohort rows
→ process already-due obligations through existing settlement owner
→ append accepted outcome revisions
→ refresh read-only evidence aggregates
→ emit observation receipt
```

No same-day feedback from outcome to T0 eligibility.

## 15. Recovery / Idempotency

Freeze:

```text
session receipt id
event ledger id
due/outcome id
aggregate snapshot id
expected prior observation head
```

Rerun identical accepted inputs:

```text
NO DUPLICATE EVENTS
NO DUPLICATE DUE
NO DOUBLE COUNT
SAME RECEIPT
```

Changed accepted source revision creates an append-only superseding receipt, not an overwrite.

## 16. Observation Receipt

Freeze fields:

```text
receipt_id
trade_date
capability
evidence_lane
model_contract_id
parameter_digest
state_lineage_id
publication_id/revision
accepted_session_status
new_events
eligible_population_count
due_count
observed_outcomes
pending_outcomes
right_censored_outcomes
quality_summary
prior_observation_head
receipt_digest
accepted_at
```

Current R30 creates no real receipt.

## 17. Design Vectors

At minimum:

```text
F21-01 Shadow real accepted session counts
F21-02 simulation does not count
F21-03 historical replay does not count
F21-04 reconstructed-asof does not count
F21-05 missed session stays denominator and breaks consecutive gate
F21-06 non-evaluable session stays ledger
F21-07 hidden eligible event remains cohort
F21-08 duplicate original enrollment rejected
F21-09 T+5 pending not counted observed
F21-10 right-censored not treated failure
F21-11 corrected outcome supersedes without double-count
F21-12 model change starts new partition
F21-13 parameter change resets affected streak only
F21-14 Stock evidence cannot satisfy Sector gate
F21-15 Shadow rows not relabeled Production after cutover
F21-16 Production lane can continue compatible lineage separately
F21-17 source revision rerun idempotent
F21-18 stale prior observation head CAS conflict
F21-19 result cannot feed same-day eligibility
F21-20 aggregate report exposes lane/model/capability breakdown
```

All are contract-design vectors only.

## 18. Current State

Carry exact truth:

```text
R25 = WAIT_ACCEPTED_DAILY_INPUT
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
V4_17G = NOT_GRANTED
MIGRATION_REPLAY_PASS = NOT_GRANTED
production_permission[*] = false
DEFAULT_UI_CUTOVER = false
```

Therefore:

```text
REAL_CONTINUED_FORWARD_OBSERVATION =
NOT_STARTED
```

## 19. Implementation Boundary

Allowed:

```text
machine contract
pure ledger schema validator
design-vector evaluator
read-only aggregate specification
tests/evidence
```

Forbidden:

```text
new settlement engine
real observation writer
production permission change
Focus source change
default UI cutover
V4_21_ACCEPTED_HEAD
```

## 20. Implementation Entry

Future implementation requires:

```text
at least one accepted real V4-16 Shadow publication
accepted V4-15 settlement owner/runtime binding
accepted observation storage contract
accepted capability/model/lineage binding
```

Until then:

```text
V4_21_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_REAL_OBSERVATION
```

## 21. Protected State

Do not modify:

```text
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_16 through V4_20 accepted-head absence
V4_16 activation authority
Focus source route
default UI route
real Shadow counters
```

Do not create:

```text
V4_21_ACCEPTED_HEAD
```

## 22. Required Evidence

Recommended:

```text
reports/r30/
  FORWARD_OBSERVATION_CONTRACT_GATE.json
  EVIDENCE_LANE_REGISTRY.json
  ACCEPTED_SESSION_LEDGER_SCHEMA.json
  EVENT_COHORT_LEDGER_SCHEMA.json
  DUE_OUTCOME_LEDGER_SCHEMA.json
  RIGHT_CENSOR_POLICY.json
  STRATIFICATION_POLICY.json
  SHADOW_PRODUCTION_CONTINUITY.json
  GATE_READBACK_POLICY.json
  OBSERVATION_RECEIPT_SCHEMA.json
  FORWARD_VECTOR_REGISTRY.json
  CURRENT_OBSERVATION_GATE.json
  PROTECTED_BYTES.json
  LOCAL_TEST_SUMMARY.json
  CLEAN_REGRESSION.json
  R30_CONTRACT_CANDIDATE_SEAL.json
```

## 23. Exit

Required:

```text
V4_21_CONTRACT_DESIGN =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

V4_21_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_REAL_OBSERVATION

REAL_CONTINUED_FORWARD_OBSERVATION =
NOT_STARTED

V4_21_ACCEPTED_HEAD =
NOT_CREATED

NEXT =
STOP_WAIT_R30_INDEPENDENT_EXTERNAL_AUDIT
```
