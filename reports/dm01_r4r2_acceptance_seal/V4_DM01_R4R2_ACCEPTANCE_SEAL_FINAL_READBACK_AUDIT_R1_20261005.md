# DM01-R4R2 Acceptance Head Seal｜Independent Final Readback Audit R1｜2026-10-05

## 0. Target
Repository: `NanOns/a-share-market-structure-research`
Branch: `codex/v4-system-reform`
Seal baseline: `3a562b9d3cd447e365993164988386f8a04cc018`
Audited HEAD: `57ddef0dc21b48c27ccaab0b4d12b08616f85765`

## 1. Unique Decision
```text
DM01_R4R2_ACCEPTANCE_SEAL_FINAL_READBACK =
BLOCKED_ONE_GOVERNANCE_RECONCILIATION

ACCEPTANCE_HEAD_CONTENT = PASS_EXTERNAL
EXTERNAL_AUDIT_BYTE_BINDING = PASS_EXTERNAL
R4R2_EXTENSION_BINDINGS = PASS_EXTERNAL
ACCEPTED_ENVELOPE_REAL_READBACK = PASS_EXTERNAL
FUTURE_WAIT_ZERO_SOURCE = PASS_EXTERNAL
PROTECTED_STAGE_DATA_PERMISSION_STATE = PASS_EXTERNAL

AUTHORIZED_OLD_TEST_UPDATE =
SEMANTICALLY_REASONABLE_BUT_GOVERNANCE_INCOMPATIBLE

R25_CURRENT_WAIT_SELECTION =
BLOCKED_BY_HISTORICAL_PROTECTED_BYTES_CHANGED

NEXT =
DM01_R4R2_ACCEPTANCE_SEAL_GOVERNANCE_RECONCILIATION_R1
```

This is not an R4R3 runtime repair.

## 2. Acceptance Head｜PASS
Created:

`data/v4/DM01_R4_RUNTIME_ACCEPTANCE_HEAD_V1.json`

Readback:
```text
contract_id = DM01_R4_RUNTIME_ACCEPTANCE_HEAD_V1
status = EXTERNALLY_ACCEPTED_DM01_R4_RUNTIME
external_verdict = PASS_DM01_R4R1_GO_FORWARD_RUNTIME
r4r2_external_verdict = PASS_DM01_R4R2_R25_BRIDGE_INTEGRATION
permissions = production=false, shadow=false, focus=false
```

Exact binding:
```text
bytes = 2278
sha256 = 694a48e94c52b8fee89e467520d8616d257eef7cb537a4407522fa01715e9ada
```

## 3. Real Repository Byte Readback｜PASS
`reports/dm01_r4r2_acceptance_seal/ACCEPTED_ENVELOPE_READBACK.json` reports:

```text
status = PASS_REAL_REPOSITORY_BYTES
mocked_acceptance = false
```

It exact-readbacks runtime contract, promotion policy, calendar head, successor daily contract, runtime dependencies v4, packet preflight v2, bridge oracle, bridge producer, runtime consumer, runtime writer and independent external authority.

No runtime source byte was modified by the seal.

## 4. External Audit Repository Copy｜PASS
Repository copy exists at:

`docs/evidence/dm01_r4r2/V4_DM01_R4R2_R25_BRIDGE_INTEGRATION_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md`

Acceptance Head binds:

```text
bytes = 10423
sha256 = b6ee5940f5a01d889d535615483c1e91cad12fdc7f021cf7633009872f7405ed
```

## 5. Future WAIT｜PASS
For 2026-10-08:

```text
status = WAIT_MARKET_CLOSE
bridge_created = false
source_requests = 0
r25_grant = false
future_real_capture = false
```

No real target package was manufactured.

## 6. Protected Business State｜PASS
Still:

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_15_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_16_ACCEPTED_HEAD = NOT_CREATED

runtime_authorized = false
real_shadow_authorized = false

Production = false
Shadow = false
Focus = false

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

real DB = absent
TDX writes = 0
```

## 7. Exact Governance Conflict
The user explicitly authorized updating the obsolete pre-seal assertion in:

`tests/v4_dm01_r4/test_runtime.py`

The change is narrow and semantically correct for the post-seal state.

However the already-audited R25 preflight contains:

```python
BASE = '54a214167cfd4414901d2002b0a3cf5da45f4e36'
check(
  not set(names) & set(changed)
      - {'.gitattributes',
         'scripts/validate_r25_preflight.py',
         'tests/test_r25_packet.py'},
  'HISTORICAL_PROTECTED_BYTES_CHANGED'
)
```

Therefore changing `tests/v4_dm01_r4/test_runtime.py` causes `protected()` and current no-target `selection()` to fail.

Observed affected nodes:

```text
tests.test_r25_packet::test_actual_authority_inventory_waits_without_target
tests.v4_dm01_r4r2.test_acceptance_seal::test_sealed_future_wait_has_no_source_or_publication
```

This is a real current-state blocker because `selection()` is part of the R25 wait/preflight path.

## 8. Why validate_r25_preflight.py Must Not Be Modified
`config/v4_16_runtime_dependencies_v4.json` exact-binds:

```text
scripts/validate_r25_preflight.py
bytes = 21423
sha256 = 89907094d1de4c11000ecb530f80316ce03bc98c0ec82e9d2d9a6aa3921c7afb
```

Changing its whitelist would invalidate the accepted dependency set and force a new version/re-audit. That is unnecessary for this seal.

## 9. Correct Resolution
Restore:

`tests/v4_dm01_r4/test_runtime.py`

to baseline bytes:

```text
bytes = 12735
sha256 = 22c96a78c97495b0a98c2cc10e639ab371b518c4c8546d63deedb24286884eec
```

Do not modify the Acceptance Head.
Do not modify `validate_r25_preflight.py`.

The old node:

`tests/v4_dm01_r4/test_runtime.py::test_current_real_v2_parent_and_future_wait`

contains a pre-seal expectation `PENDING_DM01_R4_EXTERNAL_ACCEPTANCE`.
That premise was correct before the seal and is intentionally obsolete after external acceptance.

Register it as:

`SUPERSEDED_PRE_SEAL_ASSERTION`

and explicitly deselect only this exact node from post-seal acceptance regression.

The successor current-state assertion is:

`tests/v4_dm01_r4r2/test_acceptance_seal.py`

## 10. Regression Policy After Reconciliation
Post-seal targeted accounting:

```text
R4 historical suite:
24 PASS
1 SUPERSEDED_PRE_SEAL_ASSERTION
0 active failures

R4R1:
15 PASS

R4R2 bridge:
18 PASS

Acceptance Seal:
3 PASS
```

Do not report `R4=25 PASS`.

Wider regression requirement:

```text
existing registered debt = 43
new active failure nodes = 0
```

## 11. Current State
```text
DM01_R4_RUNTIME_ACCEPTANCE_HEAD =
CREATED_AND_BYTE_VALID

DM01_R4_GO_FORWARD_RUNTIME =
NOT_YET_ACTIVE_RECOVERY_ENTRY

R25 =
WAIT_STATE_SEMANTICALLY_VALID_BUT_SELECTION_BLOCKED_BY_GOVERNANCE

REAL_TARGET_SESSION_PACKAGE =
NOT_CREATED

REAL_SHADOW_EXECUTION =
NOT_STARTED

NEXT =
DM01_R4R2_ACCEPTANCE_SEAL_GOVERNANCE_RECONCILIATION_R1
```
