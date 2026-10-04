# V4 Next Round Execution Master R25｜2026-10-04

## 0. Baseline

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`  
Execution baseline: `31db7c17463d7a314c4dbfb10023f701c1a9387b`

## 1. External Authority

```text
R24R1_EXTERNAL_AUDIT =
PASS_FINAL_FUTURE_SESSION_ACTIVATION_CAPABLE_DISABLED_CANDIDATE

V4_16_REAL_SHADOW_RUNTIME =
FUTURE_SESSION_ACTIVATION_CAPABLE_DISABLED_CANDIDATE

V4_16_FIRST_REAL_SHADOW_ACTIVATION_PACKET_ENTRY =
AUTHORIZED

V4_16_REAL_SHADOW_EXECUTION =
NOT_YET_AUTHORIZED
```

## 2. Execute

Execute:

`V4_16_R25_FIRST_REAL_SHADOW_ACTIVATION_PACKET_TASK_20261004.md`

## 3. Topology

```text
target-session selection
        ↓
exact real daily-input authority
        ↓
exact source authority
        ↓
first-session predecessor
        ↓
future real storage identity
        ↓
target-specific activation authority candidate
        ↓
packet manifest + exact digests
        ↓
R25-01～R25-16 negatives
        ↓
independent preflight oracle
        ↓
protected state
        ↓
clean regression
        ↓
candidate seal
        ↓
STOP_WAIT_R25_INDEPENDENT_EXTERNAL_AUDIT
```

## 4. Valid Source-Not-Ready Exit

If no eligible target-date accepted source exists:

```text
WAIT_ACCEPTED_DAILY_INPUT
```

This is correct and non-blocking for unrelated engineering.

Do not fabricate an activation packet.

## 5. Hard Prohibition

R25 MUST NOT:

```text
enable committed activation authority
open/create real Shadow DB
create runtime first_observed receipts
write PIT_OBSERVED real enrollment
increment real counters
create V4_16_ACCEPTED_HEAD
advance Stage Head
grant Production
grant Focus
```

## 6. READY Exit

```text
R25_REAL_ACTIVATION_PACKET =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

REAL_SHADOW_EXECUTION = NOT_STARTED

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

NEXT =
STOP_WAIT_R25_INDEPENDENT_EXTERNAL_AUDIT
```
