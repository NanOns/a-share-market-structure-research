# V4 Runtime Resume + DM01 Go-Forward Readiness Independent Audit R1｜2026-10-05

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`

Current audited HEAD:

`41d40692149055b7518751ff0916dbc0e2ff0d12`

Prior externally accepted R31R2 head:

`6f05278f50ee58bc904f5949c503de9223835463`

Drive authorities synchronized first:

- `V4_R31R2_V4_22_FAIL_CLOSED_REPAIR_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md`
- `V4_RUNTIME_RESUME_RETURN_TO_R25_FIRST_REAL_SHADOW_20261005.md`

## 1. Unique External Decision

```text
RUNTIME_RESUME_AUTHORITY_SYNC = PASS

R31R2_EXTERNAL_ACCEPTANCE_READBACK = PASS
R25_CURRENT_WAIT_STATE = PASS
R25_RETRY_EXECUTED = FALSE
REAL_SHADOW_EXECUTION = NOT_STARTED
REAL_SHADOW_OBSERVATIONS = 0

DM01_GO_FORWARD_RUNTIME_READINESS =
BLOCKED_R4_REPAIR_REQUIRED

DM01_CALENDAR_AUTHORITY_COVERAGE = FAIL_P0_RUNTIME
DM01_DAILY_ENTRYPOINT_ALL_NINE_WIRING = FAIL_P0_RUNTIME
DM01_CURRENT_V2_PARENT_ROLLOVER = FAIL_P0_RUNTIME
DM01_GO_FORWARD_PIT_LINEAGE_MODE = FAIL_P0_RUNTIME
DM01_ROUTINE_V2_DATA_HEAD_PROMOTION = FAIL_P0_RUNTIME

STALE_PARALLEL_V1_INCREMENT_FRAMEWORK = OPEN_P1_DO_NOT_USE

NEXT =
DM01_R4_GO_FORWARD_PIT_DAILY_CHAIN_RUNTIME_REPAIR
```

The Runtime Resume commit itself is safe and does not manufacture real evidence.

However, the repository does not currently contain a ready routine pipeline that can take the next accepted market session and produce the exact accepted target-session package required by R25.

Therefore the project must not simply wait until 2026-10-08.

## 2. Runtime Resume Commit｜PASS

Compared with `6f05278f...`, current HEAD `41d4069...` changes evidence/readback files only:

```text
docs/evidence/runtime_resume_20261005/*
reports/runtime_resume_20261005/*
```

No business code changed.

The commit correctly preserves:

```text
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_16..V4_22_ACCEPTED_HEAD = absent
production_permission[*] = false
Focus_source_cutover = false
DEFAULT_UI_CUTOVER = false
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
```

## 3. Blocker A｜Accepted Calendar Authority Stops at 2026-09-30

Current accepted go-forward calendar head:

`data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_ACCEPTED_HEAD_R1.json`

states:

```text
coverage_end = 2026-09-30
```

The legacy daily entrypoint:

`scripts/run_v4_dm01_daily_increment.py`

reads:

```text
reports/v4_dm01/2026-09-28/calendar_bridge_receipt.json
```

whose `official_sessions_after_base_cutoff` contains only:

```text
2026-09-28
```

Therefore `--target-date 2026-10-08` would currently hit:

```text
BLOCKED_OFFICIAL_SESSION_NOT_VERIFIED
```

before the real source/build path begins.

Classification:

```text
DM01_CALENDAR_AUTHORITY_COVERAGE = FAIL_P0_RUNTIME
```

## 4. Blocker B｜Daily Entrypoint Does Not Wire the Accepted All-Nine Builders

`scripts/run_v4_dm01_daily_increment.py` executes:

```python
builder_registry_result = validate_registry(project_root=ROOT)
```

without passing actual builder callables.

`validate_registry()` therefore yields all nine builders missing.

Even after source freeze succeeds, the entrypoint explicitly returns:

```text
BLOCKED_COMPONENT_BUILDERS_NOT_WIRED
next_blocker = NO_REAL_ACCEPTED_COMPONENT_BUILDER_CALLABLES
```

It does not invoke the externally tested R3/R3_3 all-nine candidate orchestrator.

Historical R3 already externally accepted a real continuous all-nine chain for 2026-09-28 / 09-29 / 09-30. Therefore this is a runtime wiring/governance defect, not absence of algorithms.

Classification:

```text
DM01_DAILY_ENTRYPOINT_ALL_NINE_WIRING = FAIL_P0_RUNTIME
```

## 5. Blocker C｜Accepted R3 Chain Is Anchored to the Old V1 / 2026-09-24 Data Head

The accepted historical R3_3 contract binds:

```text
accepted_data_head =
old 2026-09-24 V4_DATA_ACCEPTED_HEAD bytes
```

Its parent validator allows only:

```text
ACCEPTED_ANCHOR
```

equal to that frozen V1 anchor, or a candidate chain recursively tied to it.

Current formal Data Head is:

```text
contract_id = V4_DATA_ACCEPTED_HEAD_V2
accepted_trade_date = 2026-09-30
sha256 = 38e7c9...
```

It is not an authorized R3_3 anchor.

Classification:

```text
DM01_CURRENT_V2_PARENT_ROLLOVER = FAIL_P0_RUNTIME
```

The current real go-forward parent must become the exact current externally accepted V2 Data Head with exact CAS/digest binding. V1/2026-09-24 remains history-only.

## 6. Blocker D｜R3_3 Is Reconstructed-Only, Not PIT-Observed Go-Forward

The accepted R3_3 chain is correctly scoped as reconstructed history:

```text
status = CANDIDATE_CONTINUOUS_RECONSTRUCTED_ONLY
AS_RECORDED = false
```

R3_3 component output explicitly records:

```text
knowledge_lineage = RECONSTRUCTED_CORRECTED
AS_RECORDED = false
first_available_at_target_proven = false
```

That is correct for historical catch-up, but cannot be silently reused as first real Shadow input.

A future real target session must preserve exact runtime availability/observation lineage. Historical/reconstructed data can never be upgraded into PIT merely by running through the new runtime.

Classification:

```text
DM01_GO_FORWARD_PIT_LINEAGE_MODE = FAIL_P0_RUNTIME
```

## 7. Blocker E｜No Accepted Routine V2 Data Head Promotion Path

The formal V2 Data Head was created by a fixed historical promotion workflow:

`scripts/promote_dm01_a01_r3_data_head.py`

specific to 2026-09-24 → 09-28 → 09-29 → 09-30.

A separate older generic framework exists:

`src/workbench_analysis/daily_increment_builder.py`

but it builds `V4_DATA_ACCEPTED_HEAD_V1`, uses a different builder signature, and is not the externally accepted R3/R3_3 all-nine path.

It must not be wired as a shortcut.

The project therefore lacks a routine accepted V2 promotion owner that can perform:

```text
current V2 Data Head
+ exact accepted target-session sources
+ all-nine exact receipts
+ independent postcheck
+ no session gap
+ CAS parent digest
→ next V2 Data Head
```

Classification:

```text
DM01_ROUTINE_V2_DATA_HEAD_PROMOTION = FAIL_P0_RUNTIME
```

## 8. What Must Be Preserved

Do not reopen:

```text
R3/R3_3 business formulas
all-nine capability meanings
independent component postchecks
cross-component postcheck
atomic all-nine rule
same-day revision rule
BaoStock source-authority boundaries
V4_DATA_ACCEPTED_HEAD_V2 schema
Stage/Data head separation
Production/Shadow/Focus false permissions
```

## 9. Correct Next Architecture

```text
accepted go-forward calendar authority
        ↓
exact next session after current V2 Data Head
        ↓
WAIT_MARKET_CLOSE before allowed time
        ↓
exact target-session source freeze
        ↓
go-forward PIT authority validation
        ↓
accepted R3 business kernels via R4 wrapper
        ↓
all-nine immutable candidate
        ↓
independent postchecks
        ↓
machine-verifiable V2 promotion gate
        ↓
CAS current Data Head
        ↓
new V4_DATA_ACCEPTED_HEAD_V2
Stage Head unchanged
        ↓
R25 exact daily input authority becomes constructible
```

## 10. Final

```text
R31R2 = EXTERNALLY_ACCEPTED_SCOPED
V4_22_CONTRACT_DESIGN = EXTERNALLY_ACCEPTED_SCOPED

R25 = WAIT_ACCEPTED_DAILY_INPUT

But:
WAIT_EXACT_ACCEPTED_TARGET_SESSION_INPUT
is not the only remaining action.

NEXT =
DM01_R4_GO_FORWARD_PIT_DAILY_CHAIN_RUNTIME_REPAIR
```
