# V4-15E1 R2｜Final Owner & Governance Reconciliation Task｜2026-10-05

## 0. Mission

Repository:
`NanOns/a-share-market-structure-research`

Branch:
`codex/v4-system-reform`

Execution baseline:
`7474fb25c93286b0224635b77033451a81955ae1`

Authority:
`V4_15E1_R1_REPAIR_INDEPENDENT_EXTERNAL_AUDIT_R2_20261005.md`

This is intended to be the final E1 repair.

Do not start E2.

## 1. PASS_KEEP

Preserve:

```text
WP-A external design exact receipt
WP-C V4-15 three-time authority
WP-D V4-18 V1.1 successor contract
028 FEP schema
029 append-only
030 validation/CAS
031 roles
33 tables
32 guards
CAS/rollback/idempotency
dataset denominator/fold/revision mechanics
```

No database redesign.

## 2. Correct E1 Feature Acceptance Boundary

The R1 repair proved:

```text
historical_exact_value_paths = 47
current reconstructed owner paths = 40
```

and identified seven current missing owner fields:

```text
rel_market_1
rel_market_3
rel_market_5
rps20
rps20_delta3
rps5
rps5_delta1
```

Do not reduce the 47-field contract.

Do not wait for a future real trading session to finish E1 engineering.

E1 now distinguishes:

```text
FEP_FEATURE_MAPPING_ENGINEERING
from
FEP_REAL_FIRST_OBSERVED_ENTRY_ADMISSION
```

Required:

```text
47/47 formal owner mappings
= engineering gate

real FIRST_OBSERVED current-session observation
= future runtime gate
```

## 3. Build the 47-Field Feature Owner Adapter

Create a versioned adapter.

Suggested:

```text
src/workbench_analysis/fep_e1/feature_owner.py
config/fep_feature_owner_contract_v1.json
```

Use repository naming conventions if a better path exists.

The adapter must not implement new factor formulas.

It must consume the already accepted V4-03 algorithm/registry/output semantics.

For every field record exact:

```text
field_name
owner_stage
owner_head
owner_artifact/publication
trade_date/as-of identity
value_path
quality_path
source_digest
window identity
availability/evidence origin
unit
nullable/required
```

Required total:

```text
47 / 47
```

No guessed aliases.

No latest/mtime discovery.

## 4. Seven Relative/RPS Fields

The accepted V4-03 capability includes:

```text
STOCK_CORE = PASS
RELATIVE_RPS = PASS
MARKET_REFERENCE = PASS
MARKET_REGIME = PASS
```

The existing full-scope builder already produces:

```text
39 core + 8 relative/RPS = 47
```

Therefore use the accepted V4-03 owner logic.

Do not re-code RPS or relative-return formulas inside FEP.

### Allowed engineering path

Either:

#### Path A — Accepted historical owner
Use an exact accepted historical V4-03 full-scope owner where all 47 fields and quality/digest identities are present.

or:

#### Path B — Versioned current reconstructed owner
Create a dedicated owner materialization for 2026-09-30 using:

```text
V4_DATA_ACCEPTED_HEAD
accepted V4-03 algorithms/contracts
accepted historical prior RPS/market-reference identity
```

If Path B is used, the publication must be explicitly:

```text
RECONSTRUCTED_CORRECTED
AS_RECORDED = false
FIRST_OBSERVED = false
production = false
shadow = false
```

and must not modify:

```text
V4_03_ACCEPTED_HEAD
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
```

The materialization must contain all 47 field envelopes for the applicable universe, including UNKNOWN quality where inputs are legitimately unavailable.

A field being UNKNOWN is allowed.

A field being absent from the contract is not.

## 5. Engineering Observation / Snapshot

Create at least one reproducible E1 engineering observation/snapshot path using the 47-field adapter.

Allowed evidence origins:

```text
RECONSTRUCTED_ASOF
RECONSTRUCTED_CORRECTED
```

Forbidden overclaim:

```text
PIT_OBSERVED
FIRST_OBSERVED
AS_RECORDED=true
```

unless exact historical evidence independently proves those claims.

The immutable manifest must exact-bind:

```text
owner head(s)
owner artifact(s)
algorithm contract
parameter contract
calendar
universe
adjustment identity
feature contract
actual consumed row digests
```

Required:

```text
FEP_FEATURE_MAPPING_ENGINEERING = PASS
FEP_FEATURE_COUNT = 47
FEP_REAL_FIRST_OBSERVED_ENTRY = NOT_GRANTED
```

This distinction is mandatory.

## 6. Restore R25-Protected Historical Test

Restore:

`tests/test_v4_18_migration_contract.py`

to exact baseline bytes from:

`e4ea913d8926e904e55cbf16993ec63c0e90b031`

Baseline git blob:

`26369110c8ea35b9c1d216df17d11f981047fcef`

Do not modify:

```text
scripts/validate_r25_preflight.py
config/v4_16_runtime_dependencies_v4.json
config/v4_16_r25_packet_preflight_v2.json
```

## 7. Add V4-18 Successor Test

Create a new test, e.g.:

`tests/fep/test_v4_18_namespace_successor.py`

It must verify:

```text
V1 exact predecessor remains unchanged
V1_1 supersedes V1
all current SQL CREATE TABLE declarations
are explicitly covered in V1_1
all 33 FEP declarations are FEP engineering/reference scope
migration execution remains NOT_GRANTED
production cutover remains false
V4_18 accepted head remains absent
```

Do not remove the old V1 test file.

## 8. Register Superseded V1 Inventory Assertion

Create:

`reports/fep_e1_r2_final/SUPERSEDED_PRE_FEP_NAMESPACE_ASSERTION.json`

Exact node:

```text
tests/test_v4_18_migration_contract.py::
test_all_declared_tables_have_explicit_namespace_rules
```

Classification:

```text
SUPERSEDED_PRE_FEP_NAMESPACE_ASSERTION
```

Reason:

```text
The test binds V4_18_MIGRATION_REPLAY_CONTRACT_V1
as if it were the permanent complete repository-wide namespace inventory.

FEP was added later as an optional side branch.

V1 remains historically immutable;
V1_1 is the current successor inventory contract.
```

Replacement:

`tests/fep/test_v4_18_namespace_successor.py`

Post-FEP scoped regression may deselect only this exact obsolete V1 inventory node.

Do not call it PASS.

## 9. R25 WAIT Revalidation

After restoring the historical test bytes, independently run:

```text
protected()
selection()
```

Required:

```text
protected() = PASS

selection().status =
WAIT_ACCEPTED_DAILY_INPUT
```

No:

`HISTORICAL_PROTECTED_BYTES_CHANGED`

Future-session/acceptance-seal tests must return to expected WAIT behavior.

## 10. Full Regression Must Be Rerun

The prior report used a focused retest for one governance node.

That is insufficient for final E1 acceptance.

Run the full E1 scoped regression again after all code/config/test changes.

Allowed deselections only:

```text
1.
tests/v4_dm01_r4/test_runtime.py::
test_current_real_v2_parent_and_future_wait
→ SUPERSEDED_PRE_SEAL_ASSERTION

2.
tests/test_v4_18_migration_contract.py::
test_all_declared_tables_have_explicit_namespace_rules
→ SUPERSEDED_PRE_FEP_NAMESPACE_ASSERTION
```

No other deselections.

Required accounting:

```text
introduced_active_failures = 0
```

Existing debt may remain:

```text
43 prior registered failures
9 independently reproduced baseline failures
```

Report them explicitly.

## 11. Database Readback

Do not rebuild PASS_KEEP logic unnecessarily.

Still rerun minimal exact database checks proving:

```text
028–031 unchanged
33 tables
32 immutable guards
roles/search_path
CAS
rollback
fresh/upgrade schema equality
```

Any change to 028–031 requires explanation and re-audit.

## 12. Protected State

Must remain:

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_15_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

V4_16_ACCEPTED_HEAD =
NOT_CREATED

FEP_E1_ACCEPTED_HEAD =
NOT_CREATED

Production = false
Shadow = false
Focus = false
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
FEP_PRODUCTION = UNGRANTED
```

## 13. Evidence

Create:

```text
reports/fep_e1_r2_final/
  ENTRY_BASELINE.json
  FEATURE_OWNER_ADAPTER_GATE.json
  FEATURE_47_FIELD_READBACK.json
  ENGINEERING_SNAPSHOT_READBACK.json
  REAL_FIRST_OBSERVED_GATE.json
  V4_18_V1_BYTE_RESTORE.json
  V4_18_V1_1_SUCCESSOR_TEST_GATE.json
  SUPERSEDED_PRE_FEP_NAMESPACE_ASSERTION.json
  R25_WAIT_READBACK.json
  PASS_KEEP_DATABASE_READBACK.json
  TARGETED_SUMMARY.json
  SCOPED_REGRESSION_SUMMARY.json
  LOCAL_ACCEPTANCE_MATRIX.json
  FEP_E1_R2_CANDIDATE_SEAL.json
  COMPLETION_REPORT.md
```

## 14. Local Exit

Only if all final gates pass:

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

E2 =
NOT_AUTHORIZED_UNTIL_EXTERNAL_AUDIT

NEXT =
STOP_WAIT_FINAL_E1_EXTERNAL_AUDIT
```

Commit and push.

Do not create FEP E1 Accepted Head.

Do not start E2.
