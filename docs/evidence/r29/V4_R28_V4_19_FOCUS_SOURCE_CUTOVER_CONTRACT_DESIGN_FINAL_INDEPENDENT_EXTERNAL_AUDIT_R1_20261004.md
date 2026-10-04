# V4 R28｜V4-19 Focus Source Cutover Contract Design Independent External Audit R1｜2026-10-04

## 0. Audit Target
Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`  
Execution baseline: `94635fa369c60b3f8182cb4d813751a453682d88`  
Audited remote HEAD: `7f637644546a59b4cd28650def63be942f81b32a`  
Exact tested source: `52b374c5721df9d5b6b70c88d1f7a6bce3f2adac`  
Immutable tested tag: `refs/tags/codex/r28-focus-cutover-contract-tested-source-20261004`

## 1. Unique External Decision

```text
R28_EXTERNAL_AUDIT =
PASS_FINAL_V4_19_FOCUS_SOURCE_CUTOVER_CONTRACT_DESIGN_SCOPED

V4_19_CONTRACT_DESIGN = PASS_EXTERNAL
CUTOVER_V2_PERMISSION_FORMULA = PASS_EXTERNAL
CAPABILITY_REGISTRY = PASS_EXTERNAL
DEPENDENCY_PERMISSION_MATRIX = PASS_EXTERNAL
FOCUS_ROUTING_CONTRACT = PASS_EXTERNAL
MIXED_PRODUCTION_SHADOW_UI_POLICY = PASS_EXTERNAL
CUTOVER_RECEIPT_SCHEMA = PASS_EXTERNAL
CUTOVER_CAS = PASS_EXTERNAL
CAPABILITY_ROLLBACK_POLICY = PASS_EXTERNAL
C01_C20_DESIGN_VECTORS = PASS_EXTERNAL_DESIGN_ONLY
R28_TESTED_SOURCE_GOVERNANCE = PASS_EXTERNAL

R28_P2_ROLLBACK_TRANSITIVE_VECTOR_COVERAGE =
OPEN_NONBLOCKING

V4_19_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_REAL_GATES

production_permission[*] =
false

Focus source cutover =
false

V4_19_ACCEPTED_HEAD =
NOT_CREATED
```

## 2. Change Scope

R28 adds only:

```text
config/v4_19_focus_source_cutover_contract_v1.json
tests/test_v4_19_focus_cutover_contract.py
R28 design oracle/evidence/seal
```

No production routing writer or Focus source mutation is implemented.

`PROTECTED_BYTES.json` confirms:

```text
changed = []
production_databases_opened = false
production_routing_writer_implemented = false
tdx_writes = false
```

## 3. CUTOVER_V2 Permission Formula

The machine contract freezes:

```text
production_permission[capability] =
    SHADOW_STABLE_PASS[capability]
AND FORWARD_GATE[capability]
AND MIGRATION_REPLAY_PASS[capability]
AND ALL(required_dependency_permissions)
```

Global permission is explicitly forbidden.

Missing, unknown, stale or conflicting gate state is:

```text
FALSE / NO_CUTOVER
```

A shared raw source grants read capability only and never production permission inheritance.

## 4. Capability Registry

The five minimum capabilities are independently registered:

```text
STOCK_CORE
STOCK_SECTOR_DEPENDENT
SECTOR_STAGE
ROTATION
SECTOR_RISK_CHANGE
```

Dependency graph:

```text
STOCK_CORE -> []
SECTOR_STAGE -> []
STOCK_SECTOR_DEPENDENT -> [STOCK_CORE, SECTOR_STAGE]
ROTATION -> [SECTOR_STAGE]
SECTOR_RISK_CHANGE -> [SECTOR_STAGE]
```

Every capability carries independent:

```text
shadow gate
forward gate
migration gate
dependencies
fallback
Focus eligibility
UI label
rollback scope
```

This is capability-scoped, not a hidden global V4 switch.

## 5. Current Permission State

Current repository truth is preserved:

```text
R25 = WAIT_ACCEPTED_DAILY_INPUT
REAL_SHADOW_OBSERVATIONS = 0
V4_17_FINAL_ACCEPTANCE = NOT_GRANTED
V4_17G = NOT_GRANTED
MIGRATION_REPLAY_PASS = NOT_GRANTED
```

Therefore:

```text
STOCK_CORE = false
STOCK_SECTOR_DEPENDENT = false
SECTOR_STAGE = false
ROTATION = false
SECTOR_RISK_CHANGE = false
```

No capability receives an actual production grant.

## 6. Shadow Stable Gate

The design correctly freezes future requirements:

```text
PIT_OBSERVED + SHADOW
same model_contract_id
minimum 20 consecutive accepted market sessions
0 temporal leakage
0 duplicate episode corruption
0 Core identity violation
0 P0 state violation
rollback drill pass
```

Missed/non-evaluable sessions do not count toward the consecutive accepted window.

Affected model/parameter/shared-dependency changes reset only the relevant capability/consumers.

Current status remains NOT_GRANTED.

## 7. Forward Gate

### STOCK

The contract freezes:

```text
>= 5 distinct signal dates
>= 30 distinct stock ids
T5 OBSERVED
same model
settlement P0 = 0
```

Positive event types:

```text
FIRST_PREWATCH
REENTRY_PREWATCH
NEW_CONFIRMED
```

Revisions do not double-count logical events.

Excluded:

```text
INVALIDATION
ESTIMATED
RECONSTRUCTED_ASOF
REPLAY
```

Controls and benchmark quality receipts are required.

### SECTOR / ROTATION

Sector and Rotation do not borrow stock sample counts.

Their gates require separately frozen policy/threshold receipts and per-event-type evidence/quality.

No sector threshold receipt currently exists, so these capabilities remain Shadow-only.

## 8. Migration Gate

R27 contract-design acceptance explicitly does not satisfy the runtime migration gate.

Future permission requires:

```text
MIGRATION_REPLAY_PASS[capability]
```

from externally accepted V4-18 runtime replay.

Current:

```text
MIGRATION_REPLAY_PASS = NOT_GRANTED
```

## 9. Focus Routing

Allowed future routes:

```text
LEGACY_PRODUCTION
V4_PRODUCTION[capability]
SHADOW_V4
```

Only a V4 publication whose exact capability/model/parameter/lineage/digest matches active permission receipts may become the Focus source.

Shadow remains read-only.

UI/page actions have no source-authority power.

User pins remain product state only and cannot create algorithm evidence or production permission.

## 10. Mixed Production / Shadow UI

The contract explicitly supports states such as:

```text
STOCK_CORE = PRODUCTION
SECTOR_STAGE = SHADOW
ROTATION = SHADOW
```

Each module retains native namespace/mode identity.

A shared immutable context manifest may coordinate the page, but it cannot relabel Shadow evidence or grant dependencies.

A global "V4 production" label is forbidden.

## 11. Cutover Receipt

The receipt schema freezes:

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

Additional identity/freshness fields bind active gate and dependency receipt heads.

No real R28 cutover receipt exists.

## 12. Cutover CAS

Future cutover must atomically:

```text
append exact capability cutover receipt
+
change exact capability route head
```

after verifying all read heads.

CAS mismatch yields:

```text
NO_CUTOVER
NO_PARTIAL_ROUTE_CHANGE
```

No route change is performed in R28.

## 13. Rollback

Rollback is capability scoped.

It must preserve:

```text
accepted V4 facts
historical Shadow context
user pins/manual work
pending settlement ownership
outbox/receipts
```

Transitive dependent consumers fail closed while independent valid capabilities stay active.

### P2 coverage note

The contract correctly freezes transitive rollback semantics, but the design-vector set demonstrates only a direct ROTATION rollback.

It does not separately demonstrate a `SECTOR_STAGE` rollback propagating to:

```text
ROTATION
SECTOR_RISK_CHANGE
STOCK_SECTOR_DEPENDENT
```

Classification:

```text
R28_P2_ROLLBACK_TRANSITIVE_VECTOR_COVERAGE =
OPEN_NONBLOCKING
```

The future V4-19 implementation/acceptance vector set must add this case.

Do not reopen R28 contract design.

## 14. C01-C20

The design oracle computes all five hypothetical capability permissions using the dependency graph.

Important examples are correctly separated:

```text
C02:
STOCK_CORE=true
SECTOR_STAGE=false
dependent sector paths=false

C03:
STOCK_CORE=false
SECTOR_STAGE=true
ROTATION/SECTOR_RISK_CHANGE may be true when their own gates pass
STOCK_SECTOR_DEPENDENT=false

C11:
mixed UI labels STOCK_CORE=PRODUCTION, sector modules=SHADOW

C16:
GLOBAL_V4_PASS attempt rejected

C20:
shared source does not inherit permission
```

Every vector remains:

```text
CONTRACT_DESIGN_SIMULATION_NOT_REAL_GATE
```

and produces:

```text
production_grant = false
route_changes = []
```

## 15. Regression

Clean source:

```text
280 tests
277 passed
3 inherited failures
0 errors
0 skipped
0 deselected
```

The same historical R26-A01 failures remain and no new R28 failures are introduced.

## 16. Tested Source Governance

Annotated tag:

`codex/r28-focus-cutover-contract-tested-source-20261004`

resolves exactly to:

`52b374c5721df9d5b6b70c88d1f7a6bce3f2adac`

Final remote HEAD is one evidence-only commit ahead.

No implementation drift exists after the tested source.

## 17. Protected State

Still:

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_15_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30

V4_16_ACCEPTED_HEAD = NOT_CREATED
V4_17_ACCEPTED_HEAD = NOT_CREATED
V4_18_ACCEPTED_HEAD = NOT_CREATED
V4_19_ACCEPTED_HEAD = NOT_CREATED

Focus source cutover = false
production_permission[*] = false
```

## 18. Final

```text
R28_EXTERNAL_AUDIT =
PASS_FINAL_V4_19_FOCUS_SOURCE_CUTOVER_CONTRACT_DESIGN_SCOPED

V4_19_CONTRACT_DESIGN =
EXTERNALLY_ACCEPTED

V4_19_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_REAL_GATES
```

Next independent work may continue only as V4-20 Default UI Cutover contract design; no UI default switch is authorized.
