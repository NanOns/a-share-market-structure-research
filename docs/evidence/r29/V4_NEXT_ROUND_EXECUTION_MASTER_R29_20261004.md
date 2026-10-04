# V4 Next Round Execution Master R29｜V4-20 Default UI Cutover Contract Design｜2026-10-04

## 0. Baseline

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`  
Execution baseline: `7f637644546a59b4cd28650def63be942f81b32a`

## 1. Current External State

```text
R28_EXTERNAL_AUDIT =
PASS_FINAL_V4_19_FOCUS_SOURCE_CUTOVER_CONTRACT_DESIGN_SCOPED

V4_19_CONTRACT_DESIGN =
EXTERNALLY_ACCEPTED

V4_19_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_REAL_GATES

production_permission[*] =
false

Focus source cutover =
false
```

## 2. Execute

Execute:

`V4_20_R29_DEFAULT_UI_CUTOVER_CONTRACT_DESIGN_TASK_20261004.md`

This is CONTRACT_DESIGN_ONLY.

## 3. Topology

```text
V4-20 machine contract
        ↓
module-capability registry
        ↓
deterministic source resolver
        ↓
mixed Legacy/V4/Shadow page policy
        ↓
deep-link context policy
        ↓
cache/session invalidation
        ↓
Focus write safety
        ↓
capability-scoped UI rollback
        ↓
U20-01 through U20-20
        ↓
current default all-Legacy gate
        ↓
protected-state verification
        ↓
clean regression
        ↓
contract candidate seal
        ↓
STOP_WAIT_R29_INDEPENDENT_EXTERNAL_AUDIT
```

## 4. Hard Boundary

Do not:

```text
change actual default UI source
change actual web router
switch production Focus
grant production permission
create V4_20_ACCEPTED_HEAD
```

R29 only freezes future UI-cutover semantics.

## 5. Exit

```text
V4_20_CONTRACT_DESIGN =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

V4_20_IMPLEMENTATION_ENTRY =
BLOCKED_WAIT_PRODUCTION_PERMISSION

DEFAULT_UI_CUTOVER =
false

NEXT =
STOP_WAIT_R29_INDEPENDENT_EXTERNAL_AUDIT
```
