# V4 Next Round Execution Master R26｜V4-17 Shadow UI Engineering｜2026-10-04

## 0. Baseline
Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`  
Execution baseline: `60b17524596918b66456fdd48dbc1beb068ab28a`

## 1. Current External State
```text
R25_EXTERNAL_AUDIT = PASS_VALID_WAIT_ACCEPTED_DAILY_INPUT

R25_REAL_ACTIVATION_PACKET = WAIT_ACCEPTED_DAILY_INPUT
REAL_SHADOW_EXECUTION = NOT_STARTED
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

V4_17_ENGINEERING_ENTRY = AUTHORIZED
V4_17_ACCEPTANCE = NOT_GRANTED
V4_17G = NOT_GRANTED
```

## 2. Execute
Execute:
`V4_17_R26_SHADOW_UI_ENGINEERING_TASK_20261004.md`

R25 remains frozen in parallel.

## 3. Topology
```text
V4-17 machine UI contract
        ↓
immutable Shadow context token
        ↓
read-only Shadow context reader
        ↓
read-only /api/v4/shadow endpoints
        ↓
separate Shadow UI page
        ↓
NO_REAL_SHADOW_DATA state
        ↓
explicit simulation-only engineering fixture
        ↓
U01-U18 context/write/fallback negatives
        ↓
existing V3 / Focus UI regression
        ↓
protected-state verification
        ↓
clean regression
        ↓
candidate seal
        ↓
STOP_WAIT_R26_INDEPENDENT_EXTERNAL_AUDIT
```

## 4. Parallel R25 Rule
Do not retry R25 until an exact accepted target-session daily input exists.

Official 2026 exchange calendar reopens after the National Day closure on `2026-10-08`.

Calendar opening alone does not create authority; the target-session source chain must actually reach accepted state first.

## 5. Hard Prohibitions
Do not:
```text
fabricate real Shadow data
fallback from real UI to simulation/Legacy/V3
write production Focus
change algorithm eligibility
enable REAL activation authority
create V4_16_ACCEPTED_HEAD
create V4_17_ACCEPTED_HEAD
claim V4_17G stable
advance production cutover
```

## 6. Exit
```text
V4_17_ENGINEERING = PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

V4_17_REAL_SHADOW_READBACK = NOT_GRANTED_NO_REAL_PUBLICATION
V4_17_FINAL_ACCEPTANCE = NOT_GRANTED

R25_REAL_ACTIVATION_PACKET = WAIT_ACCEPTED_DAILY_INPUT

NEXT = STOP_WAIT_R26_INDEPENDENT_EXTERNAL_AUDIT
```
