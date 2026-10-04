# V4 Runtime Resume Card｜Return to R25 Accepted Daily Input + First Real Shadow Activation｜2026-10-05

## 0. Purpose

R31/R31R1/R31R2 have completed the required V4-22 independent-audit contract-design repair chain.

Do not create another design stage merely to keep development moving.

The next mainline is the already accepted R25 runtime entry:

```text
Accepted target-session daily input
        ↓
R25 exact activation packet retry
        ↓
R25 independent external audit
        ↓
separate first Real Shadow execution authorization
```

Repository baseline for the next retry:

`6f05278f50ee58bc904f5949c503de9223835463`

---

## 1. Current State

```text
V4_22_CONTRACT_DESIGN = EXTERNALLY_ACCEPTED_SCOPED
V4_22_FINAL_AUDIT_ENTRY = BLOCKED_WAIT_REAL_GATES
V4_22_FINAL_PASS = NOT_GRANTED

R25 = WAIT_ACCEPTED_DAILY_INPUT
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
REAL_CONTINUED_FORWARD_OBSERVATION = NOT_STARTED

production_permission[*] = false
Focus_source_cutover = false
DEFAULT_UI_CUTOVER = false
```

---

## 2. Do Not Execute a Fake Retry

Do not rerun R25 solely because the calendar date advanced.

Retry only after an exact accepted target-session input exists.

Earliest market-calendar opportunity:

```text
2026-10-08
```

but this date is only a calendar opportunity.

Required actual authority:

```text
target market session confirmed
previous market session confirmed
TDX_RAW_DAILY accepted
ADJUSTED_DAILY accepted
OWNER_OUTPUT accepted
T0_SNAPSHOT accepted
exact source manifest
exact daily input digest
accepted target-session authority
```

If any required source is absent:

```text
WAIT_ACCEPTED_DAILY_INPUT
```

remains the correct result.

---

## 3. Upstream First

The R25 packet builder is not the upstream data producer.

Before retrying R25, use the already accepted daily incremental/data-owner pipeline to produce and externally accept the exact target-session package.

Do not:

```text
promote local unaccepted files
use filename latest
use mtime discovery
relabel historical/reconstructed data as PIT_OBSERVED
reuse 2026-09-30 Data Head as a real target-session authority
```

---

## 4. R25 Retry

Once exact target-session authority exists, rerun the already accepted R25 selection/preflight logic.

Do not redesign R25.

Expected READY exit:

```text
R25_REAL_ACTIVATION_PACKET =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

AUTHORITY_PACKET_EXECUTION =
BLOCKED_PENDING_EXTERNAL_ACCEPTANCE_DIGEST

REAL_SHADOW_EXECUTION =
NOT_STARTED

REAL_SHADOW_OBSERVATIONS =
0

PIT_OBSERVED_REAL_SAMPLES =
0
```

Then stop for independent external audit.

---

## 5. Real Shadow Is a Separate Step

Even after the R25 packet becomes externally accepted:

```text
packet ready != runtime authorized
```

The first real Shadow execution must be separately authorized against the exact accepted packet/digest.

No automatic:

```text
Shadow=true
V4_16=true
production permission
Focus cutover
default UI cutover
```

---

## 6. Nonblocking Carry

Carry without blocking the runtime retry:

```text
R26-A01 historical V3 regression debt
OPEN_NONBLOCKING_P2_GOVERNANCE_HELPER_GENERALIZATION
OPEN_NONBLOCKING_P2_TEST_HOOK_HARDENING
```

These may be cleaned before the final unified V4-22 project audit, but they do not justify another contract-design repair round now.

---

## 7. Next

```text
NOW =
WAIT_EXACT_ACCEPTED_TARGET_SESSION_INPUT

WHEN_READY =
RETRY_R25_FIRST_REAL_SHADOW_ACTIVATION_PACKET

AFTER_R25_READY_EXTERNAL_AUDIT =
SEPARATE_FIRST_REAL_SHADOW_EXECUTION_AUTHORIZATION
```
