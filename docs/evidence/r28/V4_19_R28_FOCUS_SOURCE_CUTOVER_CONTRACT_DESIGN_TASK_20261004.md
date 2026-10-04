# V4-19 R28｜Focus Source Cutover Contract Design Task｜2026-10-04

## 0. Mission

Freeze the machine contract for V4-19 Focus Source Cutover while real Shadow / V4-17G / V4-18 runtime gates are still pending.

This round is:

```text
CONTRACT_DESIGN_ONLY
```

It MUST NOT cut production Focus to V4.

Execution baseline:

`94635fa369c60b3f8182cb4d813751a453682d88`

External authority:

`V4_R27_V4_18_MIGRATION_REPLAY_CONTRACT_DESIGN_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md`

## 1. Normative Policy

Freeze REV4 §52A `CUTOVER_V2`.

Production permission is capability-scoped:

```text
production_permission[capability] =
    SHADOW_STABLE_PASS[capability]
AND FORWARD_GATE[capability]
AND MIGRATION_REPLAY_PASS[capability]
AND required_dependency_permissions
```

No GLOBAL V4 PASS.

## 2. Capability Registry

At minimum distinguish:

```text
STOCK_CORE
STOCK_SECTOR_DEPENDENT
SECTOR_STAGE
ROTATION
SECTOR_RISK_CHANGE
```

Each capability must define:

```text
required_dependencies
shadow gate
forward gate
migration gate
production permission
fallback mode
UI label
Focus eligibility
rollback scope
```

## 3. Machine Contract

Create, recommended:

```text
config/v4_19_focus_source_cutover_contract_v1.json
```

Freeze:

```text
CUTOVER_V2 identity
capability registry
permission formula
receipt schema
dependency graph
Focus source routing
mixed production/shadow UI policy
cutover CAS
rollback routing
prohibited global promotion
```

## 4. Shadow Stable Gate Binding

Do not invent results.

Contract must bind future accepted receipts for:

```text
same model_contract_id
20 consecutive accepted market sessions
0 temporal leakage
0 duplicate episode corruption
0 Core identity/P0 violation
rollback drill pass
```

Missed/non-evaluable sessions do not count.

Model/parameter change resets affected capability window.

Current actual status remains NOT_GRANTED.

## 5. Forward Gate Binding

For STOCK_CORE, freeze future required evidence from §52A:

```text
>=5 distinct signal dates
>=30 distinct stocks
positive event types:
FIRST_PREWATCH
REENTRY_PREWATCH
NEW_CONFIRMED
T5 OBSERVED
same model
settlement no P0
```

Controls/benchmark coverage and quality receipts must be present.

Estimated/reconstructed results cannot count as OBSERVED.

Sector/Rotation gates must use their separately frozen event/type policy and must not borrow stock sample counts.

## 6. Migration Gate Binding

Future production permission must require:

```text
MIGRATION_REPLAY_PASS[capability]
```

from an externally accepted V4-18 runtime replay.

R27 contract-design PASS does NOT satisfy this gate.

## 7. Dependency Permission Matrix

Must prove examples such as:

```text
STOCK_CORE = production
SECTOR_STAGE = shadow only
```

without accidentally promoting:

```text
STOCK_SECTOR_DEPENDENT
ROTATION
```

Any consumer that depends on an unaccepted capability remains Shadow.

Shared raw sources do not imply shared production permission.

## 8. Focus Source Routing

Freeze exact future routing states:

```text
LEGACY_PRODUCTION
V4_PRODUCTION[capability]
SHADOW_V4
```

Focus may consume only a V4 accepted publication whose source capability has production permission.

No page/UI selection may change source authority.

User pin remains product state and is not algorithm evidence.

## 9. Mixed Mode UI

The same UI may contain:

```text
production modules
shadow modules
```

but every module must label its mode and share exact context identity without mixing permissions.

Example:

```text
Stock Core = PRODUCTION
Sector = SHADOW
Rotation = SHADOW
```

UI must not present global “V4 production” when only one capability is authorized.

## 10. Cutover Receipt

Freeze required fields:

```text
capability
status
shadow_sessions
unique_signal_dates
matured_events
forward_quality
migration_gate
production_permission
dependency_scope
parameter_digest
model_contract_id
state_lineage_id
source_publication
cutover_authority_id
previous_route
new_route
expected_route_head
receipt_digest
```

## 11. Cutover CAS

Future source cutover must be atomic and CAS-protected.

Freeze:

```text
expected_route_head
new_route
accepted_permission_receipts
cutover_authority
```

CAS mismatch:

```text
NO_CUTOVER
NO_PARTIAL_ROUTE_CHANGE
```

## 12. Rollback

Freeze capability-scoped rollback.

Rollback must:

```text
fence new V4 Focus writes for affected capability
restore exact previous accepted route
preserve accepted V4 facts
preserve user pins/manual work
preserve pending settlement ownership
append rollback receipt
```

A rollback in one capability must not globally disable independently valid capabilities.

## 13. Prohibited Promotions

Contract must explicitly forbid:

```text
GLOBAL_V4_PASS
GLOBAL_FOCUS_CUTOVER
sample-count borrowing across capabilities
historical replay counted as SHADOW_STABLE
RECONSTRUCTED_ASOF counted as PIT_OBSERVED
user pin counted as algorithm evidence
UI display counted as production permission
```

## 14. Design Vectors

At minimum define:

```text
C01 STOCK_CORE all gates pass -> permission true
C02 stock gate pass, sector insufficient -> sector false
C03 sector pass, stock insufficient -> only sector scope true if dependencies permit
C04 STOCK_SECTOR_DEPENDENT blocked by Sector dependency
C05 migration gate missing -> no production
C06 shadow stable missing -> no production
C07 forward gate missing -> no production
C08 model/parameter digest mismatch
C09 source publication capability mismatch
C10 route-head CAS conflict
C11 mixed UI labels production/shadow correctly
C12 user pin does not create permission
C13 historical replay cannot satisfy shadow sessions
C14 RECONSTRUCTED_ASOF cannot satisfy real gate
C15 rollback one capability only
C16 global-pass attempt rejected
C17 cutover receipt missing dependency scope
C18 stale permission receipt
C19 corrected outcome does not double-count matured event
C20 shared source does not imply permission inheritance
```

All are contract-design vectors only.

## 15. No Runtime Implementation

Allowed:

```text
machine contract
pure validator
static vector evaluator
evidence generator
tests
```

Forbidden:

```text
production routing writer
Focus source mutation
real cutover receipt
V4_19_ACCEPTED_HEAD
production permission grant
```

## 16. Current Gate State

Carry current truth:

```text
R25 = WAIT_ACCEPTED_DAILY_INPUT
REAL_SHADOW_OBSERVATIONS = 0
V4_17_FINAL_ACCEPTANCE = NOT_GRANTED
V4_17G = NOT_GRANTED
V4_18_IMPLEMENTATION_ENTRY = BLOCKED_WAIT_REAL_SHADOW_GATE
MIGRATION_REPLAY_PASS = NOT_GRANTED
```

Therefore every current capability must remain:

```text
production_permission = false
```

## 17. Protected State

Do not modify:

```text
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_15_ACCEPTED_HEAD
V4_16 activation authority
V4_17 source authority
V4_18 contract authority
production Focus route
user pins
real Shadow counters
```

Do not create:

```text
V4_19_ACCEPTED_HEAD
```

## 18. Required Evidence

Recommended:

```text
reports/r28/
  CUTOVER_CONTRACT_GATE.json
  CAPABILITY_REGISTRY.json
  PERMISSION_FORMULA_GATE.json
  DEPENDENCY_MATRIX.json
  FOCUS_ROUTING_GATE.json
  MIXED_MODE_UI_POLICY.json
  CUTOVER_RECEIPT_SCHEMA.json
  ROLLBACK_POLICY.json
  CUTOVER_VECTOR_REGISTRY.json
  CURRENT_PERMISSION_GATE.json
  PROTECTED_BYTES.json
  LOCAL_TEST_SUMMARY.json
  CLEAN_REGRESSION.json
  R28_CONTRACT_CANDIDATE_SEAL.json
```

## 19. Exit

Required:

```text
V4_19_CONTRACT_DESIGN =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

V4_19_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_REAL_GATES

production_permission[*] =
false

Focus source cutover =
false

V4_19_ACCEPTED_HEAD =
NOT_CREATED

NEXT =
STOP_WAIT_R28_INDEPENDENT_EXTERNAL_AUDIT
```
