# V4-17 R26｜Shadow UI Engineering Task｜2026-10-04

## 0. Mission
Implement V4-17 Shadow UI engineering without waiting for the first real V4-16 Shadow session.

Baseline: `60b17524596918b66456fdd48dbc1beb068ab28a`

Authority:
`V4_R25_FIRST_REAL_SHADOW_ACTIVATION_PACKET_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md`

This task is engineering-only. It MUST NOT claim V4-17 final acceptance or V4-17G stability.

## 1. Contract Boundary
REV4 §78:
```text
V4-17 = Shadow UI
same context token
display complete implemented components
must not write production Focus
```

V4-17 UI is a read-only projection of accepted Shadow data. It is not a new algorithm owner and must not change V4-10 through V4-16 business semantics.

## 2. Existing UI / Service Reuse
Reuse:
```text
src/workbench_service/app.py
src/workbench_service/research_context.py
src/workbench_service/static/research-v3.html
src/workbench_service/static/focus-tracker.html
```

Do not create a second web framework.

A separate Shadow page is preferred, e.g.:
```text
src/workbench_service/static/shadow-v4.html
```

Existing V3 / Focus pages must remain operational.

## 3. Machine Contract
Create a versioned contract, recommended:
```text
config/v4_17_shadow_ui_contract_v1.json
```

Freeze:
```text
context identity fields
read-only endpoint registry
component registry
field/source mapping
quality/UNKNOWN behavior
evidence-origin labels
no-production-write policy
no-fallback policy
```

## 4. One Immutable Context Token
Every component on one Shadow view must use the same immutable context token.

Recommended logical identity:
```text
namespace = SHADOW_V4
trade_date
publication_id
publication_revision
model_contract_id
state_lineage_id
daily_input_digest
source_manifest_digest
```

Freeze the exact field list in the machine contract.

No component may silently switch publication, revision, trade date or namespace.

## 5. Context Reader
Implement a read-only Shadow context reader.

Real mode may resolve only:
```text
accepted SHADOW_V4 publication
PIT_OBSERVED evidence origin
```

When no real Shadow data exists, return:
```text
NO_REAL_SHADOW_DATA
```

Forbidden fallback:
```text
R24/R24R1 activation simulation
engineering fixtures
legacy Focus
V3 production data
latest file
latest DB
mtime-selected publication
```

Explicit simulation fixtures are allowed only through a test-only injection path and must remain labeled:
```text
ACTIVATION_SIMULATION
NOT_REAL_EVIDENCE
```

## 6. Read-Only API
Add an isolated V4 Shadow API, e.g.:
```text
/api/v4/shadow/context
/api/v4/shadow/summary
/api/v4/shadow/radar
/api/v4/shadow/entity
/api/v4/shadow/cohort
/api/v4/shadow/settlement
/api/v4/shadow/health
```

Exact route names may differ, but the route registry must be frozen.

All components must use the same context token or one exact immutable context resolution.

No POST/PUT/PATCH/DELETE path may mutate production Focus or Shadow evidence.

## 7. UI Components
The Shadow page must expose the complete implemented research chain, not only a ranking.

### Context / Status
```text
trade date
publication/revision
SHADOW badge
PIT/evidence origin
model/parameter/lineage
source quality
```

### Today / Why Now
```text
what changed today
prior accepted state
current state
reason codes / observable evidence
```

### Radar
```text
eligible objects
state
priority primitives
quality
Why Now
not-display reason where applicable
```

### Stock / Sector State
```text
trend
position
relative state
structure
breakout/pullback/recovery
support/acceptance
sector context where authorized
```

### Cohort / Forward
```text
enrollment
T0
due horizons
pending/observed
benchmark/control identities
outcome revisions
right-censor state
```

### Health / Data Quality
```text
slot status
source receipts
publication lineage
late/missing/UNKNOWN
capability scope
blocked capabilities
rollback/stop state
```

Do not invent unavailable fields.

## 8. No Production Focus Write
V4-17 must not:
```text
create Focus membership
pin/unpin Focus
change production source
modify Legacy/V3 run state
write algorithm eligibility
change cohort enrollment
change settlement
```

Cross-links may be navigation-only.

## 9. No Trading-Recommendation Semantics
Do not introduce:
```text
BUY
SELL
recommended position
expected profit
confidence score
```
unless independently accepted upstream.

## 10. Explicit No-Data State
Current repository has no real Shadow publication.

Required current behavior:
```text
status = NO_REAL_SHADOW_DATA
real_sample_count = 0
```

Do not populate the real page from simulation merely to avoid an empty screen.

## 11. Simulation Engineering Fixture
For engineering/E2E only:
```text
ACTIVATION_SIMULATION
NOT_REAL_EVIDENCE
```

UI must visibly identify simulation status.

Real mode must never discover this fixture implicitly.

## 12. Context / Write / Fallback Negative Matrix
At minimum:
```text
U01 context token digest mismatch
U02 publication mismatch
U03 revision mismatch
U04 trade-date mismatch
U05 namespace mismatch
U06 evidence-origin mismatch
U07 component from another context
U08 simulation fallback in real mode
U09 Legacy/V3 fallback in real mode
U10 latest/mtime discovery attempt
U11 UNKNOWN silently rendered as known
U12 missing source quality
U13 stale outcome revision
U14 right-censored outcome shown as observed
U15 Focus write attempt
U16 production-state mutation attempt
U17 mixed model/state lineage
U18 context deep-link readback mismatch
```

Fail closed by affected scope.

## 13. API / UI Readback Tests
Test:
```text
NO_REAL_SHADOW_DATA on current repository
explicit simulation context
same context token across all components
refresh/deep-link deterministic readback
pagination/filter does not change context
UNKNOWN propagation
pending outcome handling
corrected outcome revision readback
read-only HTTP methods
```

## 14. Allowed Files
May add/modify:
```text
config/v4_17_*.json
src/workbench_service/*
src/workbench_service/static/*
tests/test_v4_17_*.py
docs/evidence/r26/*
reports/r26/*
```

Shared `app.py` changes must be additive and preserve existing routes.

## 15. Forbidden State
Do not modify accepted business implementations under V4-10 through V4-15 or `scripts/v4_16_go_forward_shadow_runtime.py` unless a new independently proven blocker exists.

Do not change:
```text
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_15_ACCEPTED_HEAD
V4_16 activation authority
real Shadow counters
```

Do not create `V4_17_ACCEPTED_HEAD` in this engineering round.

## 16. R25 Parallel State
Carry:
```text
R25_REAL_ACTIVATION_PACKET = WAIT_ACCEPTED_DAILY_INPUT
```

V4-17 engineering must not manufacture data to close R25.

## 17. Required Evidence
Recommended:
```text
reports/r26/
  SHADOW_UI_CONTRACT_GATE.json
  CONTEXT_IDENTITY_GATE.json
  NO_REAL_DATA_GATE.json
  READ_ONLY_API_GATE.json
  COMPONENT_REGISTRY_GATE.json
  CONTEXT_NEGATIVE_MATRIX.json
  SIMULATION_UI_E2E.json
  EXISTING_UI_REGRESSION.json
  PROTECTED_BYTES.json
  LOCAL_TEST_SUMMARY.json
  CLEAN_REGRESSION.json
  R26_CANDIDATE_SEAL.json
```

## 18. Exit
```text
V4_17_ENGINEERING = PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

V4_17_REAL_SHADOW_READBACK = NOT_GRANTED_NO_REAL_PUBLICATION
V4_17_FINAL_ACCEPTANCE = NOT_GRANTED
V4_17G = NOT_GRANTED

R25_REAL_ACTIVATION_PACKET = WAIT_ACCEPTED_DAILY_INPUT

Production = false
Focus source cutover = false

NEXT = STOP_WAIT_R26_INDEPENDENT_EXTERNAL_AUDIT
```
