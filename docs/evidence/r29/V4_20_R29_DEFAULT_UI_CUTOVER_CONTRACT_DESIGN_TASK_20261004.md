# V4-20 R29｜Default UI Cutover Contract Design Task｜2026-10-04

## 0. Mission

Freeze the V4-20 Default UI Cutover contract without changing the current default UI source.

This round is:

```text
CONTRACT_DESIGN_ONLY
```

Execution baseline:

`7f637644546a59b4cd28650def63be942f81b32a`

External authority:

`V4_R28_V4_19_FOCUS_SOURCE_CUTOVER_CONTRACT_DESIGN_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md`

## 1. Normative Rule

REV4 V4-20:

```text
only modules with production_permission default to V4
all other modules remain Legacy production or explicit Shadow
all switched modules remain PROVISIONAL by scope
```

No global V4 UI cutover.

## 2. Machine Contract

Create, recommended:

```text
config/v4_20_default_ui_cutover_contract_v1.json
```

Freeze:

```text
module registry
capability -> module mapping
source-mode resolution
context composition
default-route rules
deep-link rules
mixed Legacy/V4/Shadow policy
permission receipt binding
UI labels
cache/session invalidation
rollback
no-global-cutover rule
```

## 3. Module Registry

At minimum map product modules:

```text
Today Overview
Sector Research
Stock Research
Focus Tracking
Market / Events
Data / Diagnostics
```

to exact capability dependencies.

Do not infer module permission from page name.

Each module must list:

```text
required_capabilities
optional_capabilities
fallback source
default source
shadow-only subcomponents
write permissions
context identity fields
```

## 4. Source Resolution

Future source choice must be deterministic:

```text
if required capability has active accepted production permission:
    exact V4 production publication
else:
    exact Legacy production route
```

Explicit Shadow views remain Shadow and never become production fallback.

Forbidden:

```text
latest publication
mtime
page-local choice
user browser state as authority
global V4 flag
```

## 5. Mixed Page Policy

A single page may combine modules with different modes:

```text
PRODUCTION_V4
LEGACY_PRODUCTION
SHADOW_V4
```

but every component must carry its own:

```text
source mode
capability scope
publication identity
model/parameter lineage
permission receipt digest
```

One shared page token may compose native sub-contexts but cannot hide mixed permissions.

## 6. Default UI Labels

Freeze explicit labels:

```text
PRODUCTION_V4_PROVISIONAL
LEGACY_PRODUCTION
SHADOW
NO_PERMISSION
UNKNOWN
```

Do not show global:

```text
V4_PRODUCTION
```

unless every visible production-relevant module is independently authorized and the contract explicitly allows that aggregate label.

Default is to avoid aggregate production labels.

## 7. Deep Links

Deep links must bind exact:

```text
module
trade_date
source mode
publication id/revision
capability scope
permission receipt digest
context digest
```

Opening an old deep link after a new cutover must reproduce the old accepted context, not silently resolve the newest default.

## 8. Cache / Session Invalidation

When a capability route changes:

```text
old module cache/session source bindings become stale
```

The contract must define:

```text
route_head/version
permission receipt head
cache namespace
session token invalidation
```

No stale Legacy/V4 content may be silently merged.

## 9. Focus Write Safety

A UI module may write Focus only when:

```text
its exact capability source is production-permitted
AND V4-19 route is active
AND write endpoint authority agrees
```

Shadow modules remain read-only.

Legacy production modules retain existing Legacy write authority until their capability is cut over.

User pins remain product state and must survive source-mode changes.

## 10. Rollback

Default UI rollback must follow capability routing rollback.

For an affected capability:

```text
restore previous accepted UI source
invalidate V4 cache/session bindings
preserve deep-link historical context
preserve user pins/manual work
preserve accepted V4 history
```

Independent modules remain on their valid source.

## 11. Current State

Carry exact current truth:

```text
production_permission[*] = false
Focus source cutover = false
R25 = WAIT_ACCEPTED_DAILY_INPUT
V4_17G = NOT_GRANTED
MIGRATION_REPLAY_PASS = NOT_GRANTED
```

Therefore current default UI must remain:

```text
Legacy production
+
explicit Shadow engineering page
```

No V4 module becomes default in R29.

## 12. Design Vectors

At minimum:

```text
U20-01 all permissions false -> all production defaults remain Legacy
U20-02 STOCK_CORE true only -> stock-core module V4, sector modules Legacy/Shadow
U20-03 SECTOR_STAGE true only -> sector module V4, stock core remains Legacy
U20-04 STOCK_SECTOR_DEPENDENT requires both dependencies
U20-05 ROTATION permission false despite shared sector source
U20-06 Shadow page never becomes production fallback
U20-07 stale permission receipt blocks V4 default
U20-08 publication capability mismatch
U20-09 route-head changed after page context creation
U20-10 old deep link reproduces old context
U20-11 latest/mtime discovery forbidden
U20-12 mixed page exposes module mode labels
U20-13 global V4 label attempt rejected
U20-14 Focus write from Shadow module rejected
U20-15 user pin preserved during module cutover
U20-16 cache invalidation on route change
U20-17 one capability rollback only affects dependents
U20-18 SECTOR_STAGE rollback cascades to ROTATION/SECTOR_RISK_CHANGE/STOCK_SECTOR_DEPENDENT
U20-19 independent STOCK_CORE survives sector rollback
U20-20 UNKNOWN permission -> Legacy/NO_PERMISSION, never V4
```

This round must close the R28 P2 by explicitly covering U20-18.

## 13. Implementation Boundary

Allowed:

```text
machine contract
static/pure resolver
design vector evaluator
contract tests
evidence
```

Forbidden:

```text
changing default UI page
changing actual router
changing Focus write route
changing browser-facing production source
creating V4_20_ACCEPTED_HEAD
```

Do not modify existing production UI behavior in R29.

## 14. Implementation Entry

Future V4-20 implementation requires exact:

```text
externally accepted V4-19 production permission receipt for at least one capability
active accepted Focus source route
accepted UI cutover authority
accepted rollback receipt schema
```

Until then:

```text
V4_20_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_PRODUCTION_PERMISSION
```

## 15. Protected State

Do not modify:

```text
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_16/17/18/19 accepted-head absence
production Focus route
default UI route
V4_16 activation authority
real Shadow counters
```

Do not create:

```text
V4_20_ACCEPTED_HEAD
```

## 16. Required Evidence

Recommended:

```text
reports/r29/
  DEFAULT_UI_CONTRACT_GATE.json
  MODULE_CAPABILITY_MATRIX.json
  SOURCE_RESOLUTION_GATE.json
  MIXED_PAGE_POLICY.json
  DEEP_LINK_POLICY.json
  CACHE_SESSION_INVALIDATION.json
  FOCUS_WRITE_POLICY.json
  UI_ROLLBACK_POLICY.json
  UI_CUTOVER_VECTOR_REGISTRY.json
  CURRENT_DEFAULT_GATE.json
  PROTECTED_BYTES.json
  LOCAL_TEST_SUMMARY.json
  CLEAN_REGRESSION.json
  R29_CONTRACT_CANDIDATE_SEAL.json
```

## 17. Exit

Required:

```text
V4_20_CONTRACT_DESIGN =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

V4_20_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_PRODUCTION_PERMISSION

DEFAULT_UI_CUTOVER =
false

V4_20_ACCEPTED_HEAD =
NOT_CREATED

NEXT =
STOP_WAIT_R29_INDEPENDENT_EXTERNAL_AUDIT
```
