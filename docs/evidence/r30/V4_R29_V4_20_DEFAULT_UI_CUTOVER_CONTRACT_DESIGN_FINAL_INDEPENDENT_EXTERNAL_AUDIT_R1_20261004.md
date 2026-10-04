# V4 R29｜V4-20 Default UI Cutover Contract Design Independent External Audit R1｜2026-10-04

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`  
Execution baseline: `7f637644546a59b4cd28650def63be942f81b32a`  
Audited remote HEAD: `c38c25dd189b3996f53e85dc64bbc142db1c188e`  
Exact tested source: `0e8281abb27bb17ea00d089422f0ac92a8e44f37`  
Immutable tested tag: `refs/tags/codex/r29-default-ui-contract-tested-source-20261004`

## 1. Unique External Decision

```text
R29_EXTERNAL_AUDIT =
PASS_FINAL_V4_20_DEFAULT_UI_CUTOVER_CONTRACT_DESIGN_SCOPED

V4_20_CONTRACT_DESIGN = PASS_EXTERNAL
MODULE_CAPABILITY_MATRIX = PASS_EXTERNAL
SOURCE_RESOLUTION_CONTRACT = PASS_EXTERNAL
MIXED_PAGE_POLICY = PASS_EXTERNAL
DEEP_LINK_POLICY = PASS_EXTERNAL
CACHE_SESSION_INVALIDATION = PASS_EXTERNAL
FOCUS_WRITE_POLICY = PASS_EXTERNAL
UI_ROLLBACK_POLICY = PASS_EXTERNAL
U20_01_U20_20_DESIGN_VECTORS = PASS_EXTERNAL_DESIGN_ONLY
R28_P2_TRANSITIVE_ROLLBACK_VECTOR_COVERAGE = CLOSED
R29_TESTED_SOURCE_GOVERNANCE = PASS_EXTERNAL

V4_20_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_PRODUCTION_PERMISSION

DEFAULT_UI_CUTOVER =
false

V4_20_ACCEPTED_HEAD =
NOT_CREATED
```

## 2. Change Scope

R29 adds only:

```text
config/v4_20_default_ui_cutover_contract_v1.json
tests/test_v4_20_default_ui_contract.py
R29 pure design resolver/evidence/seal
```

No existing web router, default page, Focus route, production database, V4-16 runtime or accepted business implementation changed.

`PROTECTED_BYTES.json` confirms:

```text
actual_focus_route_changed = false
actual_ui_router_changed = false
production_databases_opened = false
changed = []
tdx_writes = false
```

## 3. Default UI Rule

The contract correctly freezes REV4 V4-20 semantics:

```text
module may default to V4
ONLY IF
all required capability production permissions are active and exact
```

Otherwise the module remains:

```text
LEGACY_PRODUCTION
```

Explicit Shadow views remain:

```text
SHADOW_V4
```

and are never production fallback.

No global V4 default flag exists.

## 4. Module Registry

Registered modules include:

```text
Today Overview
Sector Research
Stock Research
Focus Tracking
Market / Events
Data / Diagnostics
Stock Research / Sector-dependent
Sector Research / Rotation
Sector Research / Risk Change
```

Each module freezes:

```text
required capabilities
optional capabilities
fallback source
default source
shadow-only subcomponents
write policy
context identity
resolution granularity
```

Page names themselves do not grant production permission.

## 5. Empty Required-Capability Containers

Composite containers such as:

```text
Today Overview
Focus Tracking
Market / Events
Data / Diagnostics
```

have an empty top-level `required_capabilities`.

The contract explicitly prevents vacuous truth:

```text
EMPTY_REQUIRED_LIST_NEVER_GRANTS_V4_BY_VACUOUS_TRUTH
```

These containers remain Legacy at the aggregate level while child components/items are resolved independently.

This avoids a hidden global cutover through a composite page.

## 6. Capability-Scoped Source Resolution

Source resolver logic is:

```text
all required accepted production permissions active
→ exact accepted V4 production publication

otherwise
→ exact accepted Legacy production route
```

Forbidden discovery includes:

```text
latest publication
mtime
page-local source choice
browser state as authority
global V4 flag
```

Binding conflict yields:

```text
UNKNOWN_AFFECTED_MODULE_NO_DISPLAY_NO_WRITE
```

rather than guessing another publication.

## 7. Mixed Legacy / V4 / Shadow Page

A page may contain:

```text
PRODUCTION_V4_PROVISIONAL
LEGACY_PRODUCTION
SHADOW
```

simultaneously.

Every component retains its own native:

```text
source mode
namespace
publication id/revision
capability scope
model/parameter lineage
permission receipt digests
route heads
native context digest
```

A shared page token composes these sub-contexts but grants no permission itself.

Global `V4_PRODUCTION` page labeling is rejected.

## 8. Deep Links

Deep links pin:

```text
module
trade_date
source_mode
publication_id
publication_revision
capability_scope
permission_receipt_digests
context_digest
```

After a later cutover/rollback, an old deep link reproduces the exact archived context read-only.

It does not silently resolve the newest default.

Tampering or missing exact context fails closed.

## 9. Cache / Session Invalidation

Route/permission changes invalidate affected live bindings.

The cache/session namespace includes:

```text
contract version
module
source mode
native context digest
publication id/revision
route head/version
permission receipt head
capability scope
```

A stale token:

```text
cannot write
cannot silently merge/rebase
requires explicit refresh/new page token
```

Historical archived context remains readable.

## 10. Focus Write Safety

Shadow modules reject algorithmic Focus writes.

Legacy production retains existing Legacy write authority until exact capability cutover.

V4 write requires all of:

```text
active accepted capability production permission
active accepted V4-19 Focus source route
endpoint authority agreement
exact model/parameter/lineage
exact context digest
exact permission receipt head
exact route head
```

The check is repeated at write CAS, not only at page render.

User pins remain independent product state.

## 11. UI Rollback

Rollback follows capability routing rollback.

For a capability rollback the contract requires:

```text
fence affected module writes
restore exact previous accepted UI source
invalidate affected V4 live bindings
append scoped UI rollback receipt
preserve historical contexts
preserve user pins/manual work
preserve accepted V4 history
```

Independent modules remain on their valid source.

## 12. R28 P2 Is Closed

R28 left one nonblocking coverage gap: no explicit design vector for `SECTOR_STAGE` rollback cascading through all dependents.

R29 U20-18 now proves:

```text
SECTOR_STAGE rollback
→ SECTOR_STAGE
→ ROTATION
→ SECTOR_RISK_CHANGE
→ STOCK_SECTOR_DEPENDENT
```

all fall back to Legacy while:

```text
STOCK_CORE
```

remains independently on V4 production in the hypothetical design fixture.

Therefore:

```text
R28_P2_TRANSITIVE_ROLLBACK_VECTOR_COVERAGE =
CLOSED
```

## 13. U20-01 through U20-20

The vectors correctly cover:

```text
all-Legacy current state
single-capability V4 default
sector-only V4 default
dependency blocking
shared-source non-inheritance
Shadow never production fallback
stale permission
binding conflict
route/session invalidation
historical deep link
latest/mtime prohibition
mixed labels
global-label rejection
Shadow Focus write rejection
user-pin preservation
cache invalidation
capability rollback
transitive rollback
independent Stock Core survival
UNKNOWN permission fail-closed
```

All vectors remain:

```text
CONTRACT_DESIGN_SIMULATION_NOT_UI_RUNTIME
```

and never mutate the actual router.

## 14. Current Real State

Current truth remains:

```text
production_permission[*] = false
Focus source cutover = false
R25 = WAIT_ACCEPTED_DAILY_INPUT
V4_17G = NOT_GRANTED
MIGRATION_REPLAY_PASS = NOT_GRANTED
```

Therefore every current default production module remains:

```text
LEGACY_PRODUCTION
```

with the explicit engineering Shadow page non-default.

## 15. Regression

Clean source:

```text
306 tests
303 passed
3 inherited failures
0 errors
0 skipped
0 deselected
```

The same historical R26-A01 failures remain.

No new R29 regression exists.

## 16. Tested Source Governance

Annotated tag:

`codex/r29-default-ui-contract-tested-source-20261004`

resolves exactly to:

`0e8281abb27bb17ea00d089422f0ac92a8e44f37`

Final remote HEAD is one evidence-only commit ahead.

No implementation drift exists after the clean tested source.

## 17. Protected State

Still:

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_15_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30

V4_16_ACCEPTED_HEAD = NOT_CREATED
V4_17_ACCEPTED_HEAD = NOT_CREATED
V4_18_ACCEPTED_HEAD = NOT_CREATED
V4_19_ACCEPTED_HEAD = NOT_CREATED
V4_20_ACCEPTED_HEAD = NOT_CREATED

DEFAULT_UI_CUTOVER = false
Focus source cutover = false
production_permission[*] = false
```

## 18. Final

```text
R29_EXTERNAL_AUDIT =
PASS_FINAL_V4_20_DEFAULT_UI_CUTOVER_CONTRACT_DESIGN_SCOPED

V4_20_CONTRACT_DESIGN =
EXTERNALLY_ACCEPTED

V4_20_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_PRODUCTION_PERMISSION
```

Next independent nonblocking work may continue only as V4-21 Continued Forward Observation contract design. No real evidence accumulation may be fabricated.
