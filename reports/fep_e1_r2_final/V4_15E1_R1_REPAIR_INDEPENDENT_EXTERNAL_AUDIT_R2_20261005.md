# V4-15E1 R1 Repair｜Independent External Audit R2｜2026-10-05

## 0. Audit Target
Repository: `NanOns/a-share-market-structure-research`
Branch: `codex/v4-system-reform`

Repair baseline:
`e4ea913d8926e904e55cbf16993ec63c0e90b031`

Audited remote HEAD:
`7474fb25c93286b0224635b77033451a81955ae1`

Commit:
`Repair FEP E1 receipt, label-time authority and namespace successor; retain owner blockers`

## 1. Unique Decision
```text
V4_15E1_R1_REPAIR_EXTERNAL_AUDIT_R2 =
PARTIAL_PASS_FINAL_RECONCILIATION_REQUIRED

WP_A_EXTERNAL_DESIGN_RECEIPT = PASS_KEEP
WP_C_V4_15_THREE_TIME_AUTHORITY = PASS_KEEP_ENGINEERING_REAL_PENDING
WP_D_V4_18_NAMESPACE_SUCCESSOR = PASS_KEEP
PASS_KEEP_DATABASE = PASS_KEEP

WP_B_FEATURE_MAPPING = PARTIAL_PASS_RESCOPING_REQUIRED
R25_HISTORICAL_GUARD = FAIL_CROSS_STAGE_GOVERNANCE
SCOPED_REGRESSION = FAIL_INTRODUCED_GOVERNANCE_NODES

V4_15E1_FEP_LOCAL_IMPLEMENTATION =
BLOCKED_PENDING_FINAL_RECONCILIATION

E2 = NOT_AUTHORIZED_YET

NEXT =
V4_15E1_R2_FINAL_OWNER_AND_GOVERNANCE_RECONCILIATION
```

This is intended to be the final E1 repair round.

## 2. WP-A｜External Design Receipt｜PASS_KEEP
The exact external FEP R2 design acceptance is now committed with:

```text
bytes = 14019
sha256 =
cd279e26fb9753eb1e333c7554f9f06393c9232ee44ff7be6d86e2f2f65d178e
```

Repository path:

`docs/evidence/fep_e1/V4_2_2_FEP_R2_EXTERNAL_DESIGN_ACCEPTANCE_20260930.md`

This closes the prior raw external-authority evidence gap.

## 3. WP-C｜V4-15 Three-Time Authority｜PASS_KEEP
A versioned additive authority now exists:

```text
config/v4_15_fep_label_time_authority_v1.json
src/workbench_analysis/v4_15_fep_label_time.py
```

Engineering semantics correctly separate:

```text
source_fact_available_at
label_training_mature_at
label_revision_available_at
```

The engineering fixture verifies:

```text
T3 → reject
T5 → reject if revision only visible T6
T6 → eligible
```

Current real V4-15 rows remain fail-closed:

```text
CURRENT_REAL_MATURITY_EVIDENCE = NONE
PROVED_HORIZONS = []
no real trainable binding manufactured
```

No Forward outcome is recomputed by FEP.

## 4. WP-D｜V4-18 Namespace Successor｜PASS_KEEP
A versioned successor now exists:

`config/v4_18_migration_replay_contract_v1_1.json`

The original:

`config/v4_18_migration_replay_contract_v1.json`

remains immutable.

The successor explicitly covers the 33 FEP declarations and keeps:

```text
migration execution = NOT_GRANTED
production cutover = false
V4_18 accepted head = absent
```

The namespace design repair is valid.

The remaining problem is only that the old static test file itself was modified, while R25 freezes that historical file.

## 5. PostgreSQL / Dataset PASS_KEEP｜PASS
Fresh:

```text
78 passed
1 skipped
0 failed
```

Upgrade:

```text
79 passed
0 failed
```

Fresh/upgrade schema identity remains equal.

Preserve:

```text
028_fep_schema_v1.sql
029_fep_append_only_v1.sql
030_fep_validation_cas_v1.sql
031_fep_roles_v1.sql
```

and all prior database PASS_KEEP conclusions.

## 6. Feature Mapping｜Rescoping Required
Current report says:

```text
required = 47
historical_exact_value_paths = 47
current_reconstructed_value_paths = 40
```

Current 2026-09-30 reconstructed Core owner is missing:

```text
rel_market_1
rel_market_3
rel_market_5
rps20
rps20_delta3
rps5
rps5_delta1
```

### 6.1 Algorithms/owners exist
The accepted V4-03 field registry defines exactly 47 fields.

The existing V4-03 full-scope builder explicitly performs:

```text
39 core + 8 relative/RPS
```

and hard-checks:

```python
if len(fields) != 47:
    raise RuntimeError(...)
```

The accepted V4-03 head grants:

```text
STOCK_CORE = PASS
RELATIVE_RPS = PASS
MARKET_REFERENCE = PASS
MARKET_REGIME = PASS
```

Therefore this is not a missing-algorithm problem.

It is a current operational owner-publication / evidence-time problem.

### 6.2 E1 must not be blocked on current FIRST_OBSERVED availability
The previous repair task over-constrained E1 by requiring a current 2026-09-30 accepted ENTRY owner as if it were necessary for database/dataset engineering acceptance.

That is too strong.

FEP R2 separates engineering/historical-as-of construction from real FIRST_OBSERVED / production prediction evidence.

The current V4 Data Head is itself:

```text
knowledge_lineage = RECONSTRUCTED_CORRECTED
AS_RECORDED = false
first_available_at_target_proven = false
```

Therefore it would be wrong to manufacture a FIRST_OBSERVED publication merely to close E1.

Correct E1 boundary:

```text
47/47 formal owner mapping = REQUIRED

historical/reconstructed-as-of adapter =
REQUIRED FOR ENGINEERING

current real FIRST_OBSERVED 47-field observation =
NOT_REQUIRED FOR E1 ENGINEERING ACCEPTANCE

real current admission =
NOT_GRANTED / WAIT FUTURE REAL SESSION
```

This does not reduce the 47-field contract.

It removes accidental coupling between engineering completion and future market time.

## 7. Required Feature-Side Closure
E1 still needs an actual adapter, not only a JSON mapping list.

The final repair must create a versioned feature owner adapter that binds all 47 V4-03 fields and their:

```text
value path
quality path
source digest
window identity
owner artifact/head
availability/evidence origin
```

For engineering acceptance it may consume:

```text
accepted historical V4-03 full-scope owner
and/or
explicit RECONSTRUCTED_ASOF / RECONSTRUCTED_CORRECTED owner materialization
```

but must never upgrade that materialization to:

```text
PIT_OBSERVED
FIRST_OBSERVED
AS_RECORDED=true
```

The seven current missing relative/RPS fields may only be produced through the already accepted V4-03 algorithms and exact accepted inputs.

No FEP-specific reimplementation of RPS/relative formulas is allowed.

## 8. Optional Current 2026-09-30 Engineering Owner
A versioned engineering successor may be created for 2026-09-30, for example:

`V4_03_CURRENT_FACTOR_OWNER_PUBLICATION_V1`

If created it must state:

```text
trade_date = 2026-09-30
knowledge_lineage = RECONSTRUCTED_CORRECTED
AS_RECORDED = false
FIRST_OBSERVED = false
production = false
shadow = false
```

It must bind:

```text
V4_DATA_ACCEPTED_HEAD @ 2026-09-30
accepted V4-03 algorithm/field registry
accepted historical prior RPS/market-reference identity
exact generated 47-field rows
```

It must not alter the V4-03 Accepted Head.

Its purpose is engineering owner/readback, not historical truth rewriting.

If 47/47 mapping can be independently proven directly from accepted historical V4-03 owner artifacts, a new current owner is not mandatory.

## 9. R25 Historical Guard Conflict｜FAIL, Narrow Fix
The E1R1 repair changed:

`tests/test_v4_18_migration_contract.py`

to read V1.1.

That test is in R25's protected historical-byte set.

Therefore:

```text
protected()
→ HISTORICAL_PROTECTED_BYTES_CHANGED
```

and two current-state nodes fail:

```text
tests.test_r25_packet::
test_actual_authority_inventory_waits_without_target

tests.v4_dm01_r4r2.test_acceptance_seal::
test_sealed_future_wait_has_no_source_or_publication
```

The implementation correctly did not patch the exact-bound preflight in place.

### Correct resolution
Restore:

`tests/test_v4_18_migration_contract.py`

to exact baseline bytes from:

`e4ea913d8926e904e55cbf16993ec63c0e90b031`

Baseline git blob:

`26369110c8ea35b9c1d216df17d11f981047fcef`

Do not modify R25 preflight/dependency bytes.

Create a new successor test, e.g.:

`tests/fep/test_v4_18_namespace_successor.py`

which validates:

```text
V1 remains immutable historical contract
V1_1 supersedes V1
all current SQL declarations including 33 FEP tables are covered by V1_1
V4-18 execution remains NOT_GRANTED
```

Register the old inventory node as:

```text
SUPERSEDED_PRE_FEP_NAMESPACE_ASSERTION
```

for post-FEP regression.

Do not call the old node PASS.

## 10. Regression Evidence Is Not Final
The current full-run summary still contains:

```text
tests.governance.test_no_symbol_specific_runtime_logic::
test_complete_repository_has_no_hard_gated_symbols_or_unclassified_paths
```

in its introduced set.

The completion report says a focused retest closed it after moving sample identity out of config.

That is not enough for final acceptance.

The final repair must rerun the complete scoped regression after all fixes.

Required:

```text
introduced_active_failures = 0
```

Allowed existing debt remains:

```text
43 prior registered
+
9 independently reproduced baseline failures
```

Superseded nodes must be listed separately and not counted as PASS.

## 11. Final Repair Scope
The next repair contains only:

```text
A. close 47/47 feature owner adapter at engineering scope
B. keep real FIRST_OBSERVED/current admission NOT_GRANTED
C. restore protected V4-18 V1 test bytes
D. add successor V1.1 namespace test
E. register old V1 namespace inventory assertion as superseded
F. rerun R25 WAIT gates
G. rerun full scoped regression
```

Do not touch the database PASS_KEEP foundation.

## 12. Required Exit
Only after final reconciliation:

```text
V4_15E1_R2_FINAL_RECONCILIATION =
PASS_LOCAL_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

FEP_DATABASE_ENGINEERING =
PASS_LOCAL

FEP_DATASET_ENGINEERING =
PASS_LOCAL_ENGINEERING

FEP_FEATURE_MAPPING =
47_OF_47_ENGINEERING_READY

FEP_REAL_FIRST_OBSERVED_ENTRY =
NOT_GRANTED_WAIT_REAL_SESSION

FEP_REAL_MATURED_LABEL_EVIDENCE =
NOT_GRANTED

R25 =
WAIT_ACCEPTED_DAILY_INPUT

introduced_active_failures =
0

FEP_MODEL_ENGINEERING =
NOT_STARTED

FEP_MODEL_DISPLAY =
UNGRANTED

FEP_PRIORITY_USE =
UNGRANTED

FEP_PRODUCTION =
UNGRANTED

NEXT =
STOP_WAIT_FINAL_E1_EXTERNAL_AUDIT
```

E2 remains unauthorized until that final external audit passes.
