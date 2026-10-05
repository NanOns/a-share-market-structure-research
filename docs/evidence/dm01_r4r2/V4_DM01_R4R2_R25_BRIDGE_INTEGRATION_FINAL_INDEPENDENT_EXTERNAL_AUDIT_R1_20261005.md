# DM01-R4R2｜R25 Exact Target-Session PIT Bridge Integration Final Independent External Audit R1｜2026-10-05

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`

Execution baseline:

`54a214167cfd4414901d2002b0a3cf5da45f4e36`

Audited remote HEAD:

`3a562b9d3cd447e365993164988386f8a04cc018`

Exact tested source:

`46bbc77164723ca272e0ae7ca896bd0b66f2fd80`

Tested tag:

`codex/dm01-r4r2-r25-bridge-tested-source-20261005`

## 1. Unique External Decision

```text
DM01_R4R2_EXTERNAL_AUDIT =
PASS_FINAL_R4R2_BRIDGE_INTEGRATION

PASS_DM01_R4R1_GO_FORWARD_RUNTIME
PASS_DM01_R4R2_R25_BRIDGE_INTEGRATION

R25_DAILY_INPUT_SCHEMA_BRIDGE_INTEGRATION = PASS_EXTERNAL
R25_PACKET_PREFLIGHT_BRIDGE_PARITY = PASS_EXTERNAL
R25_BRIDGE_PRODUCER_PATH = PASS_EXTERNAL

DM01_R4_LINEAGE_COMPOSITION = PASS_KEEP
DM01_R4_REAL_FORWARD_EVIDENCE_GATE = PASS_KEEP
DM01_R4_FIRST_AVAILABILITY_SEMANTICS = PASS_KEEP
DM01_R4_PROMOTED_HEAD_LINEAGE = PASS_KEEP
DM01_R4_CALENDAR_AUTHORITY_DESIGN = PASS_KEEP
DM01_R4_CURRENT_V2_PARENT_ROLLOVER = PASS_KEEP
DM01_R4_ALL_NINE_DAILY_WIRING = PASS_KEEP
DM01_R4_ROUTINE_V2_PROMOTION_CORE = PASS_KEEP
DM01_R4_FUTURE_SESSION_WAIT_GATE = PASS_KEEP

DM01_R4_RUNTIME_IMPLEMENTATION =
EXTERNALLY_ACCEPTED_SCOPED

DM01_R4_RUNTIME_ACCEPTANCE_HEAD =
NOT_CREATED

REAL_RUNTIME_ENTRY =
BLOCKED_PENDING_ACCEPTANCE_HEAD_SEAL

R25 =
WAIT_ACCEPTED_DAILY_INPUT

REAL_TARGET_SESSION_PACKAGE =
NOT_CREATED

REAL_SHADOW_EXECUTION =
NOT_STARTED

REAL_SHADOW_OBSERVATIONS =
0

NEXT =
DM01_R4R2_EXTERNAL_ACCEPTANCE_HEAD_SEAL
```

`PASS_DM01_R4R1_GO_FORWARD_RUNTIME` is intentionally retained as the canonical runtime-envelope verdict token required by the R4 runtime contract. R4R2 is the final bridge-integration layer; this does not roll the project back to R4R1.

## 2. Successor Daily-Input Contract｜PASS

R4R2 adds:

`config/v4_16_go_forward_input_authority_v1_1.json`

with:

```text
contract_id = V4_16_GO_FORWARD_INPUT_AUTHORITY_V1_1
version = 1.1.0
bridge_contract_id = DM01_R25_TARGET_SESSION_PIT_BINDING_R4R1_V1
required_real_bridge = true
```

`target_session_pit_binding` is now a mandatory field.

Historical V1 remains immutable predecessor:

```text
config/v4_16_go_forward_input_authority_v1.json
sha256 =
660d36616e0e28db5ed541e8f6111ccfe48140bb3e88c8a14647d67b26e32a07
```

Result:

```text
R25_DAILY_INPUT_SCHEMA_BRIDGE_INTEGRATION = PASS_EXTERNAL
```

## 3. Historical 2026-09-30 Data Head Rollover｜PASS

R4R2 archives the exact historical 2026-09-30 Data Head at:

```text
data/v4/r25_r4r2/historical_data_head_20260930.json
sha256 =
38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40
```

`ImmutableAlgorithmReader` maps the historical predecessor binding to this immutable archive for the frozen algorithm view.

Therefore future legal movement of:

```text
data/v4/V4_DATA_ACCEPTED_HEAD.json
```

from 2026-09-30 to 2026-10-08 does not invalidate the historical predecessor required by the successor input authority.

This resolves the real-session rollover risk identified during audit.

## 4. Deterministic Bridge Producer｜PASS

R4R2 adds:

`scripts/build_r25_bridge_r4r2.py`

It requires explicit exact inputs:

```text
parent
child
candidate
source manifest
all-nine receipts
observation receipt
target session
```

It:

- does not use latest/glob/mtime discovery;
- cannot grant R25;
- validates prospective bridge bytes before publication;
- requires current V2 child in REAL mode;
- confines REAL output to the accepted R25 target-session bridge path;
- keeps engineering bridge production isolated;
- returns `WAIT_MARKET_CLOSE` before eligible target-session close.

Result:

```text
R25_BRIDGE_PRODUCER_PATH = PASS_EXTERNAL
```

## 5. Independent R25 Bridge Oracle｜PASS

`scripts/r25_bridge_oracle_r4r2.py` independently verifies:

```text
successor contract and predecessor/archive binding
current V2 child
parent/child/candidate linkage
target date
source manifest
target observation receipt
all-nine receipts
artifact logical digests
mixed whole-head lineage
next-session relation
post-close timing
native source timestamp scope
R4 runtime external envelope
machine promotion acceptance record/chain
source authorities
independent cross-component postcheck
```

It is read-only and does not grant runtime permissions.

## 6. R25 Preflight / Runtime Consumer Parity｜PASS

`config/v4_16_runtime_dependencies_v4.json` binds the same successor contract and runtime surfaces used by both preflight and runtime:

```text
go_forward_input =
config/v4_16_go_forward_input_authority_v1_1.json

packet_contract =
config/v4_16_r25_packet_preflight_v2.json

input_authority =
scripts/v4_16_go_forward_input_authority_r4r2.py

runtime_writer =
scripts/v4_16_go_forward_shadow_runtime_r4r2.py
```

`validate_r25_preflight.py` now validates the exact bridge when the successor contract is used.

The runtime consumer validates the same successor contract before reusing the frozen historical constructor.

The previous split:

```text
preflight accepts old V1
runtime requires target_session_pit_binding
```

is closed.

Result:

```text
R25_PACKET_PREFLIGHT_BRIDGE_PARITY = PASS_EXTERNAL
```

## 7. Real Runtime Remains Fail-Closed｜PASS

The R4R2 real controller still requires:

```text
runtime_authorized = true
real_shadow_authorized = true
```

before source consumption or storage opening.

Current committed activation authority remains disabled.

No real target package exists.

No real Shadow database exists.

No real observation is written.

For 2026-10-08 before eligibility:

```text
WAIT_MARKET_CLOSE
source_requests = 0
bridge_created = false
```

## 8. R4R2 Required Vectors｜PASS

Exact R4-family targeted results:

```text
R4    = 25 passed
R4R1  = 15 passed
R4R2  = 18 passed
```

R4R2 covers the required bridge negatives, including:

```text
missing bridge
wrong bridge contract
target mismatch
parent mismatch
non-current child
candidate real_forward=false
observation real_forward=false
altered all-nine receipt
altered source manifest
whole-head-only admission
engineering bridge isolation
REAL-shaped synthetic preflight/runtime parity
bridge/daily digest mismatch
old V1 historical-only
contract digest parity
future/pre-close zero-source-request
```

## 9. Tested Source Governance｜PASS

Tag:

`codex/dm01-r4r2-r25-bridge-tested-source-20261005`

resolves exactly to:

`46bbc77164723ca272e0ae7ca896bd0b66f2fd80`

Current HEAD is one evidence-only closure commit ahead.

No runtime source changed after the tested source.

## 10. Protected State｜PASS

Current protected state remains:

```text
Stage = V4_00_TO_V4_15_ACCEPTED
Data = 2026-09-30
V4_16_ACCEPTED_HEAD = NOT_CREATED

Production = false
Shadow = false
Focus = false

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

real DB = absent
TDX writes = 0
```

R4/R4R1 core source bytes remain unchanged.

## 11. Regression Truth｜PASS_SCOPED, Not Full Green

Final scoped regression:

```text
total = 2181
passed = 2135
failed = 43
skipped = 3
errors = 0

introduced_failures = []
```

The expanded entry baseline at `54a214...` already contained 44 failures. R4R2 resolves one:

```text
tests.test_r25_packet::test_actual_authority_inventory_waits_without_target
```

and introduces no new failure node.

The remaining failures must remain explicit debt. They include:

- prior repository baseline debts;
- R23/R24R1 legacy simulation/dependency compatibility failures;
- `tests.test_r25_packet::test_f12_valid_latest_decoy`, which currently stops at legacy `EXACT_DEPENDENCY_MISMATCH` before reaching the old F12 decoy assertion;
- the separately tracked HTTP/DuckDB reproducibility flake may appear intermittently.

The F12 failure is not evidence that the new R4R2 successor resolves files implicitly: R4R2 has exact-binding/no-latest tests of its own. The legacy R24R1 simulation suite remains open debt.

Carry:

```text
DM01_R4R2_LEGACY_R23_R24R1_SIMULATION_COMPATIBILITY =
OPEN_NONBLOCKING_INDEPENDENT_DEBT
```

## 12. Exact External Acceptance Bindings

The machine-readable acceptance head must bind exactly:

```text
runtime_contract
config/dm01_go_forward_runtime_contract_r4r1.json
sha256 =
6452a8398800d2728df8bbfc7dfe84786790d988a70905ecc2c61b77a2201b17

promotion_policy
config/dm01_v2_promotion_policy_r4r1.json
sha256 =
93478038af8dfc57ea4915c6680c75aa0a095cf0f3a989bc29c9e6847c1ad7d2

calendar_head
data/v4/DM01_R4_CALENDAR_HEAD_V1.json
sha256 =
c02d5e553214667c2300bcc198ad36fdf37ec5f8a59d8391fd9851bd19549bc4

successor_daily_contract
config/v4_16_go_forward_input_authority_v1_1.json
sha256 =
63b7205ff159aca5a82702968ef1cf3d5ca19907125f05084d08d045b9801654

runtime_dependencies_v4
config/v4_16_runtime_dependencies_v4.json
sha256 =
af6d5270fd2fa5a3e515f8da8d0270a4a460372e77c184bc6e293f70de6f5d38

packet_preflight_v2
config/v4_16_r25_packet_preflight_v2.json
sha256 =
365571e9b9121e73b0aadc2af5518f68d0b0e786944d63a347d2970ceed7bee0

bridge_oracle
scripts/r25_bridge_oracle_r4r2.py
sha256 =
422bf2676623e9cd18cdde7fb060828aff5ab2c5abf67020ed74ca50503cc116

bridge_producer
scripts/build_r25_bridge_r4r2.py
sha256 =
8c7efe126bcc368008737e02b0ee2a05269b9f6d305b3fe7024057d8bc477067

runtime_consumer
scripts/v4_16_go_forward_input_authority_r4r2.py
sha256 =
a24f2e15f9d971461eb51c185c256e866adb4b91c9cbd9cc79cc3e99862eb921

runtime_writer
scripts/v4_16_go_forward_shadow_runtime_r4r2.py
sha256 =
e9c60574041350f64fabaa543e786a82147ac02bb5c11b458edeaa1b552266ac

tested_source =
46bbc77164723ca272e0ae7ca896bd0b66f2fd80

tested_tag =
codex/dm01-r4r2-r25-bridge-tested-source-20261005
```

## 13. Remaining Machine Seal

Current repository does not contain:

```text
data/v4/DM01_R4_RUNTIME_ACCEPTANCE_HEAD_V1.json
```

Both the real R4 machine promotion envelope and the real R25 bridge oracle require it.

Therefore the implementation is externally accepted, but real runtime entry remains fail-closed until the audit decision is converted into the machine-readable acceptance head.

This is governance formalization, not R4R3 development.

## 14. Final State

```text
DM01_R4R2_EXTERNAL_AUDIT =
PASS_FINAL_R4R2_BRIDGE_INTEGRATION

DM01_R4_RUNTIME_IMPLEMENTATION =
EXTERNALLY_ACCEPTED_SCOPED

DM01_R4_RUNTIME_ACCEPTANCE_HEAD =
NOT_CREATED

R25 =
WAIT_ACCEPTED_DAILY_INPUT

REAL_TARGET_SESSION_PACKAGE =
NOT_CREATED

REAL_SHADOW_EXECUTION =
NOT_STARTED

NEXT =
DM01_R4R2_EXTERNAL_ACCEPTANCE_HEAD_SEAL
```
