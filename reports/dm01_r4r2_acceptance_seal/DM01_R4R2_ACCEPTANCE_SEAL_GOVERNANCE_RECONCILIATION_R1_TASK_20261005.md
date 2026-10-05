# DM01-R4R2 Acceptance Seal｜Governance Reconciliation R1 Task｜2026-10-05

## 0. Mission

Execution baseline:

`57ddef0dc21b48c27ccaab0b4d12b08616f85765`

Authority:

`V4_DM01_R4R2_ACCEPTANCE_SEAL_FINAL_READBACK_AUDIT_R1_20261005.md`

This is a narrow governance reconciliation.

Do not create R4R3.

Do not modify runtime/preflight business bytes.

## 1. Required Repair

Restore exactly:

`tests/v4_dm01_r4/test_runtime.py`

to its baseline `3a562b9...` bytes:

```text
bytes = 12735
sha256 = 22c96a78c97495b0a98c2cc10e639ab371b518c4c8546d63deedb24286884eec
```

This intentionally withdraws the previously authorized test-file edit because that edit conflicts with the audited R25 historical-byte protection.

## 2. Do Not Touch

Do not modify:

```text
scripts/validate_r25_preflight.py
config/v4_16_runtime_dependencies_v4.json
config/v4_16_r25_packet_preflight_v2.json
config/v4_16_go_forward_input_authority_v1_1.json
scripts/r25_bridge_oracle_r4r2.py
scripts/build_r25_bridge_r4r2.py
scripts/v4_16_go_forward_input_authority_r4r2.py
scripts/v4_16_go_forward_shadow_runtime_r4r2.py
src/workbench_analysis/dm01_runtime_r4.py
src/workbench_analysis/dm01_lineage_r4r1.py
data/v4/DM01_R4_RUNTIME_ACCEPTANCE_HEAD_V1.json
```

## 3. Register the Superseded Historical Assertion

Create:

`reports/dm01_r4r2_acceptance_seal/SUPERSEDED_PRE_SEAL_ASSERTION.json`

Required content semantics:

```text
node =
tests/v4_dm01_r4/test_runtime.py::
test_current_real_v2_parent_and_future_wait

status =
SUPERSEDED_PRE_SEAL_ASSERTION

reason =
The assertion requires PENDING_DM01_R4_EXTERNAL_ACCEPTANCE,
which was correct before the externally accepted runtime head existed
and is no longer a current-state invariant after the seal.

replacement_current_state_test =
tests/v4_dm01_r4r2/test_acceptance_seal.py

historical_test_bytes =
PRESERVED_EXACTLY
```

This registry is evidence only.

## 4. R25 Current WAIT Readback

After restoring the historical test bytes, independently run:

```python
scripts.validate_r25_preflight.protected()
scripts.validate_r25_preflight.selection()
```

Required:

```text
protected() = PASS
selection().status = WAIT_ACCEPTED_DAILY_INPUT
target_trade_date = null
```

No `HISTORICAL_PROTECTED_BYTES_CHANGED`.

## 5. Acceptance Head Readback

Re-run:

```python
dm01_runtime_r4.accepted_envelope(ROOT)
```

Required:

```text
status = EXTERNALLY_ACCEPTED_DM01_R4_RUNTIME
permissions =
production=false
shadow=false
focus=false
```

Re-read all R4R2 extension exact bindings.

## 6. Future WAIT

Re-run:

```text
2026-10-08
→ WAIT_MARKET_CLOSE
→ source_requests=0
→ bridge_created=false
→ r25_grant=false
```

No source/network capture caused by the check.

## 7. Targeted Regression

Run:

```text
tests/v4_dm01_r4
tests/v4_dm01_r4r1
tests/v4_dm01_r4r2
```

but explicitly deselect exactly:

`tests/v4_dm01_r4/test_runtime.py::test_current_real_v2_parent_and_future_wait`

because it is the immutable pre-seal assertion registered above.

Expected accounting:

```text
R4 =
24 PASS + 1 SUPERSEDED_PRE_SEAL_ASSERTION

R4R1 =
15 PASS

R4R2 bridge =
18 PASS

Acceptance Seal =
3 PASS
```

Do not claim `R4=25 PASS`.

## 8. Wider Regression

Run the same R4R2 scoped regression with the same exact one-node deselection.

Required:

```text
existing registered debt = 43
new active failure nodes = 0
```

Do not hide or delete the 43 debts.

## 9. Protected State

Must remain:

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_15_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_16_ACCEPTED_HEAD = absent

runtime_authorized = false
real_shadow_authorized = false

Production = false
Shadow = false
Focus = false

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
```

No real DB.
No TDX writes.
No real target-session package.

## 10. Allowed Changes

Only:

```text
tests/v4_dm01_r4/test_runtime.py
  → restore exact baseline bytes only

reports/dm01_r4r2_acceptance_seal/*
  → reconciliation evidence / updated summaries only
```

No other existing source/config/test file modifications.

## 11. Required Exit

```text
DM01_R4R2_ACCEPTANCE_SEAL_GOVERNANCE_RECONCILIATION =
PASS_LOCAL_READY_FOR_FINAL_READBACK

DM01_R4_RUNTIME_ACCEPTANCE_HEAD =
CREATED_EXTERNALLY_ACCEPTED

R25_PROTECTED_WAIT_SELECTION =
PASS_WAIT_ACCEPTED_DAILY_INPUT

DM01_R4_GO_FORWARD_RUNTIME =
EXTERNALLY_ACCEPTED_SCOPED_READY_FOR_NEXT_REAL_SESSION

REAL_TARGET_SESSION_PACKAGE =
NOT_CREATED

REAL_SHADOW_EXECUTION =
NOT_STARTED

REAL_SHADOW_OBSERVATIONS =
0

NEXT =
STOP_WAIT_FINAL_INDEPENDENT_READBACK
```

Commit and push. Do not continue to real R25/Shadow.
