# V4 R21 Final Independent External Audit R1｜2026-10-04

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`

Branch: `codex/v4-system-reform`

Current remote HEAD: `a1bb12f19e758784e55a1a93acaad1954861a0fc`

R21 exact promotion tested source: `78aca3bdaa651455ffbf5320b6d50418855ecfb9`

Immutable promotion tag: `codex/r21-tested-source-20261004-r1`

Execution baseline: `14b183dedf8a55b12e9368229482ab4bdb3395b1`

---

# 1. Unique External Audit Decision

```text
R21_EXTERNAL_AUDIT =
PASS_FINAL_V4_15_PROMOTION_CAPABILITY_SCOPED

V4_15_ACCEPTED_HEAD = PASS
V4_STAGE_ACCEPTED_HEAD_V4_15 = PASS
CURRENT_STAGE_AUTHORITY_V4_15 = PASS
V4_14_REPLAY_PREDECESSOR_COMPATIBILITY = PASS
ROLLBACK_VALIDATION = PASS
SCOPED_CLEAN_REGRESSION = PASS

V4_15_STAGE =
CLOSED_ACCEPTED_CAPABILITY_SCOPED

V4_16_CONTRACT_FREEZE_ENTRY =
AUTHORIZED

V4_16_RUNTIME =
NOT_AUTHORIZED_YET
```

This audit closes V4-15 as an accepted capability-scoped engineering stage.

It does not grant real matured forward evidence, historical PIT effectiveness, realtime cohort maturity, Production, Focus, or V4-16 runtime permission.

---

# 2. V4-15 Accepted Head｜PASS

`data/v4/V4_15_ACCEPTED_HEAD.json` exists and is exact-bound from the global Stage Head.

Accepted semantics:

```text
contract_id =
V4_15_ACCEPTED_HEAD_V1

stage =
V4-15

status =
RUNTIME_ENGINEERING_PASS_CAPABILITY_SCOPED

external_acceptance =
EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED

external_audit_decision =
PASS_FINAL_V4_15_RUNTIME_CANDIDATE_CAPABILITY_SCOPED

accepted_trade_date =
2026-09-30

tested_source =
81d989af438bdeda583a581f1ef7f311205e6139
```

It binds the V4-14 predecessor, V4-15 contract package, R20/R20R1/R20R1R1/R20R1R2 candidate seals, external audit, Data Head, maturity readback, forward projection, membership/identity/calendar and open validation debt.

Capabilities are restricted to the previously externally accepted engineering/scoped set.

---

# 3. Global Stage Head Promotion｜PASS

The live `data/v4/V4_STAGE_ACCEPTED_HEAD.json` now states:

```text
accepted_stage_range =
V4_00_TO_V4_15_ACCEPTED

v4_15_entry =
COMPLETED_EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED_RUNTIME

v4_15_external_acceptance =
PASS_FINAL_V4_15_RUNTIME_CANDIDATE_CAPABILITY_SCOPED
```

The exact V4-15 binding matches `V4_15_ACCEPTED_HEAD.json`.

All prior V4-00 ... V4-14 stage bindings and statuses are retained.

The Data Head remains `2026-09-30` and is not moved by stage promotion.

---

# 4. Current Stage Authority Transition｜PASS

A new versioned authority exists:

`config/v4_current_stage_authority_v2.json`

with:

```text
contract_id =
V4_CURRENT_STAGE_AUTHORITY_V2

accepted_stage_range =
V4_00_TO_V4_15_ACCEPTED

current_head =
data/v4/V4_15_ACCEPTED_HEAD.json

predecessor_v4_14 =
data/v4/V4_14_ACCEPTED_HEAD.json

V4_15_accepted = true
V4_16 = false

production = false
shadow = false
focus = false
```

`CurrentStageAuthority` now chooses the v1/v2 governance contract according to the exact current Stage range and verifies the selected Head.

For V4-15 it enforces:

```text
CURRENT_REAL_MATURITY_EVIDENCE = NONE
PROVED_HORIZONS = []
UNPROVED_HORIZONS = [1,3,5,10,20]

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

REALTIME_ACCEPTED_COHORT_MATURITY =
NOT_GRANTED

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED
```

No permission widening was observed.

---

# 5. V4-14 Replay Compatibility｜PASS

The promotion does not reinterpret V4-15 as a V4-14 replay contract.

`ReplayAuthority` explicitly reads:

```text
CurrentStageAuthority = V4-15 governance
Replay predecessor = V4-14 Accepted Head
```

and obtains the replay-specific package from V4-14.

`publication_authority()` exposes an explicit V4-14 publication view while the current governance object remains V4-15.

This closes the key atomic-promotion risk identified before R21.

---

# 6. Historical Current-Stage Tests｜PASS

The promotion invalidates the assumption in some historical R20/R20R1 tests that “V4-14 is the current stage”.

R21 did not silently weaken these tests.

It explicitly registered 55 affected exact node IDs in:

`reports/r21/SUPERSEDED_CURRENT_STAGE_TESTS.json`

with:

```text
historical_context =
14b183dedf8a55b12e9368229482ab4bdb3395b1

action =
SUPERSEDED_CURRENT_STAGE_TEST_RERUN_UNCHANGED_IN_EXACT_ARCHIVED_CONTEXT
```

All 55 were rerun unchanged in that exact historical checkout.

Current V4-15 regression separately ran the remaining current-applicable tests.

This is an acceptable stage-promotion testing model.

---

# 7. Clean Regression｜PASS

Current V4-15 checkout:

```text
196 PASS
0 failed
0 errors
0 skipped
```

Historical exact V4-14 current-stage cases:

```text
55 PASS
0 failed
0 errors
0 skipped
```

Total verified:

```text
251 PASS
```

There is no broad pattern deselection and no unrelated exclusion.

---

# 8. Tested Source Governance｜PASS

Immutable promotion tag:

`codex/r21-tested-source-20261004-r1`

resolves to:

`78aca3bdaa651455ffbf5320b6d50418855ecfb9`

The final branch HEAD is one evidence-only commit ahead.

The final delta contains only the R21 seal and clean-regression evidence. No implementation code changed after the tested source.

---

# 9. Rollback｜PASS

R21 preserves exact pre-promotion bytes for the Stage Head, v1 current authority config, CurrentStageAuthority reader, ReplayAuthority reader and Radar/Cohort authority adapter.

Rollback validation restores those exact bytes in an isolated fixture and verifies V4-14 governance coherence.

The successful live promotion was not rolled back.

---

# 10. Capability Boundary｜PASS

V4-15 remains capability-scoped.

Still not granted:

```text
CURRENT_REAL_MATURITY_EVIDENCE =
NONE

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

REALTIME_ACCEPTED_COHORT_MATURITY =
NOT_GRANTED

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED

PROVED_HORIZONS = []

UNPROVED_HORIZONS =
[1,3,5,10,20]
```

Permissions remain:

```text
Production = false
Shadow = false
Focus = false
V4_16 = false
```

These are intentionally deferred real-observation/cutover capabilities.

---

# 11. Open Non-Blocking Audit Item

Retain:

```text
V4_15_FWD_ADJ_VECTOR_01 =
OPEN_NONBLOCKING_TEST_ENHANCEMENT
```

Scope:

```text
SUPPORTED_CORPORATE_ACTION_NON_IDENTITY_PROJECTION_VECTOR
```

It remains non-blocking for V4-16 contract/engineering work and cannot itself grant maturity or PIT capability.

---

# 12. V4-16 Entry Authority

The V4.2.2 executable baseline §78 defines V4-16 as:

```text
V4-16 =
Realtime Shadow Dual-Run

PIT_OBSERVED + SHADOW

真实冻结日账本
+
每日运行 settlement

旧系统继续 production
```

The baseline also requires:

```text
PIT_OBSERVED+SHADOW
may enter the real Shadow cohort

RECONSTRUCTED_ASOF+REPLAY
must not be relabeled as observed
```

and:

```text
Shadow must read its own prior-session state
not Legacy prior state
```

Therefore R21 authorizes only V4-16 contract freeze / stage-entry engineering work.

---

# 13. Final External State

```text
R21_EXTERNAL_AUDIT =
PASS_FINAL_V4_15_PROMOTION_CAPABILITY_SCOPED

V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_15_ACCEPTED

CURRENT_STAGE_AUTHORITY =
V4_15

V4_14_REPLAY_PREDECESSOR =
PASS

V4_15 =
CLOSED_ACCEPTED_CAPABILITY_SCOPED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

Production = false
Shadow = false
Focus = false

NEXT =
R22_V4_16_REALTIME_SHADOW_CONTRACT_FREEZE_ENTRY
```
