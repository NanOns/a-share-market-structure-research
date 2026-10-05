# V4-15E2｜FEP Conditional Statistics Final Capability-Scoped Independent External Audit R1｜2026-10-05

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`

E2 R1R2 execution baseline:

`f8708c34063238547127cab4baefb17c2e5825ac`

Audited remote HEAD:

`7a10c0a3b1563532b7f1eda5af9b90f204fd03d6`

Commit:

`fix(fep-e2): stratify ENTRY events and isolate prior-episode owner gaps`

Frozen design authority:

```text
DA-MSR-V4.2.2-FEP-R2
CONDITIONAL_EXPECTANCY_V1
```

## 1. Unique Final Decision

```text
V4_15E2_FINAL_EXTERNAL_AUDIT =
PASS_FINAL_CAPABILITY_SCOPED

E2 =
ENGINEERING_ACCEPTED_CAPABILITY_SCOPED

ADMITTED_SCOPE =
FEP_STOCK_ENTRY_CORE
FIRST_PREWATCH
ABS_RETURN_N:T1
CORE
RECONSTRUCTED_CORRECTED

E2_FIRST_PREWATCH_T1 =
PASS_EXTERNAL

E2_POOLED_ENTRY_BASELINE =
SUPERSEDED_DIAGNOSTIC_ONLY

E2_REENTRY =
UNSET_OWNER_INPUT_NOT_AVAILABLE

E2_NEW_CONFIRMED =
UNSET_DIAGNOSTIC_ONLY

FEP_REAL_FIRST_OBSERVED_ENTRY =
NOT_GRANTED

FEP_REAL_MATURED_LABEL_EVIDENCE =
NOT_GRANTED

FEP_MODEL_DISPLAY =
UNGRANTED

FEP_PRIORITY_USE =
UNGRANTED

FEP_PRODUCTION =
UNGRANTED

E3_ENTRY =
AUTHORIZED_FOR_ADMITTED_SCOPE_ONLY

NEXT =
V4_15E3_INTERPRETABLE_MODEL_TIME_SPLIT
```

No E2 R1R3 repair is required for the admitted FIRST_PREWATCH:T1 capability.

---

## 2. Historical Replay Foundation｜PASS_KEEP

R1R1 historical real-source replay remains valid engineering evidence:

```text
window = 2024-07-15 → 2026-09-24
entities scanned = 5337
date/entity states = 2,860,632
```

Lineage remains:

```text
RECONSTRUCTED_CORRECTED
HISTORICAL_SIMULATION
AS_RECORDED = false
FIRST_OBSERVED = false
REAL_OOS = false
production = false
shadow = false
```

No historical PIT/OOS claim is granted.

Feature replay and V4-15 `SettlementRuntime` label adapter are byte-preserved from the prior accepted repair scope.

---

## 3. FIRST_PREWATCH Event Semantics｜PASS

The accepted V4-15 Radar owner already defines:

```text
ENROLLED + PREWATCH + no parent_episode
→ FIRST_PREWATCH

ENROLLED + PREWATCH + parent_episode
→ REENTRY_PREWATCH
```

R1R2 does not invent a new FEP-local entry definition.

The event-strata successor maps the exact V4-15 owner identity into:

```text
observation_scope = FEP_STOCK_ENTRY_CORE
signal_type = FIRST_PREWATCH
logical_event_id = exact owner event
episode_id = exact owner episode
observation_id = exact V4-15 enrollment id
```

and rejects:

```text
wrong episode
parent episode on FIRST_PREWATCH
pooled ENTRY signal
lineage overclaim
```

Result:

```text
FIRST_PREWATCH owner events = 4553
eligible T1 labels = 4552
pending = 1
```

---

## 4. FIRST_PREWATCH Population Completeness｜PASS

The R1R2 population gate checks all:

```text
5337 entities
2,860,632 reconstructed daily states
```

For the pre-first-episode state:

```text
FULL_OWNER_EVALUATION is required
```

and no normal pre-episode evaluation may be suppressed.

The exact first-event predicate is compared against the exact V4-15 enrollment records.

The resulting FIRST_PREWATCH denominator is therefore accepted for the reconstructed engineering scope.

This acceptance does not extend to later episodes.

---

## 5. Prior-Episode Owner Gap｜PASS_FAIL_CLOSED

The accepted provenance contract still says:

```text
frozen_invalidation
implemented = false
required = true
producer = V4_12_EPISODE_INVALIDATION_NOT_IMPLEMENTED
```

R1R2 does not fabricate this fact.

Current capability dispositions are:

```text
REENTRY =
NOT_ENABLED_OWNER_INPUT_UNAVAILABLE

NEW_CONFIRMED =
UNSET_DIAGNOSTIC_ONLY
```

The blocked later transition opportunities remain visible in the denominator/state ledger and are explicitly not converted into observed events.

Open debt remains:

```text
FEP_E2_PRIOR_EPISODE_OWNER_CAPABILITY
```

This debt blocks only the affected event strata and does not block FIRST_PREWATCH:T1 engineering acceptance.

---

## 6. Pooled ENTRY Baseline｜SUPERSEDED

The prior pooled R1R1 baseline and policy are retained byte-for-byte.

Independent readback:

```text
config/fep_e2_support_policy_registry_v1.json
baseline blob == current blob

reports/fep_e2_r1r1/CONDITIONAL_BASELINE_GATE.json
baseline blob == current blob
```

They are now explicitly:

```text
SUPERSEDED_DIAGNOSTIC_ONLY
may_feed_E3 = false
```

The successor registry rejects pooled:

```text
signal_type = ENTRY
```

for formal E2 statistics.

---

## 7. Event-Scoped Support Policy｜PASS

Successor:

```text
config/fep_e2_support_policy_registry_v1_1.json
```

admits only:

```text
FEP_STOCK_ENTRY_CORE
FIRST_PREWATCH
ABS_RETURN_N:T1
horizon = 1
feature_variant = CORE
evidence_origin = RECONSTRUCTED_CORRECTED
target_kind = CONTINUOUS
```

Other event strata remain UNSET.

FIRST_PREWATCH support discovery:

```text
eligible rows = 4552
dates = 220
non-overlap blocks = 142
entities = 4552
episodes = 4552

NEG = 2118
POS = 2271
ZERO = 163
```

The support threshold derivation remains explicitly:

```text
ENGINEERING_SUPPORT_HEURISTIC
```

and consumes no:

```text
mean return
positive-rate comparison
quantile attractiveness
best backoff performance
Priority result
```

The pooled thresholds were not reused.

---

## 8. Freeze Ordering｜PASS

Machine evidence proves:

```text
FIRST_PREWATCH dataset seal
→ support discovery
→ event-scoped policy freeze
→ statistics start
```

The runtime also enforces strict chronological ordering.

No support policy is selected after seeing conditional return results.

---

## 9. Conditional Baseline｜PASS_ENGINEERING

Formal admitted baseline:

```text
scope = FIRST_PREWATCH:T1
support_state = SUPPORTED
selected_level = L1
```

Counts:

```text
rows = 4552
dates = 220
blocks = 142
entities = 4552
episodes = 4552
```

Descriptive reconstructed-history result:

```text
weighted mean ≈ 0.3405%
weighted positive empirical frequency ≈ 48.31%
p25 ≈ -1.6341%
p50 ≈ -0.0722%
p75 ≈ 2.0247%
```

These values are historical reconstructed descriptive statistics only.

They are NOT:

```text
individual-stock probability
real OOS effectiveness
tradable expected profit
model confidence
production signal
```

The fact that L2–L4 are unavailable because regime is not admitted does not invalidate L1; fixed backoff explicitly permits the first supported level down to L1.

---

## 10. Determinism / Registry｜PASS

The FIRST_PREWATCH:T1 baseline has identical original/rebuilt logical digest:

```text
f790f96b8bd29772cff55c0bec2296214c86409cb00dd12762804e268a11113f
```

Created time does not alter the logical identity.

The old pooled artifact is preserved separately.

---

## 11. Negative Matrix｜PASS

R1R2 negative vectors cover, among others:

```text
pooled ENTRY policy rejected
FIRST_PREWATCH exact signal binding
FIRST_PREWATCH policy cannot serve REENTRY
same entity / different episodes remain distinct
same episode / different events not independent episodes
missing invalidation never becomes FALSE
REENTRY without owner stays disabled
owner-gap ledger retained
pooled R1R1 artifact preserved and superseded
freeze before statistics
no performance-derived support
owner bytes preserved
FIRST_OBSERVED overclaim blocked
PRIORITY_V1 unchanged
owner episode mismatch blocked
parent episode rejected for FIRST_PREWATCH
```

Result:

```text
21/21 PASS
```

---

## 12. Regression｜PASS

Final targeted:

```text
194 passed
1 skipped
0 failed
```

Final scoped regression:

```text
2553 passed
4 skipped
52 existing debt failures
0 introduced active failures
```

The 52 failures remain pre-existing governed debt.

No new active E2 failure is introduced.

---

## 13. Protected State｜PASS

Protected state remains:

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_15_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

V4_16_ACCEPTED_HEAD =
NOT_CREATED

REAL_SHADOW_OBSERVATIONS =
0

PIT_OBSERVED_REAL_SAMPLES =
0

real FEP database rows =
0

PRIORITY_V1 =
UNCHANGED

R25 =
WAIT_ACCEPTED_DAILY_INPUT

Production =
false

Shadow =
false

Focus =
false

MODEL_DISPLAY =
UNGRANTED

PRIORITY_USE =
UNGRANTED
```

No TDX mutation occurred.

---

## 14. E2 Acceptance Boundary

E2 is formally accepted only for:

```text
FEP_STOCK_ENTRY_CORE
FIRST_PREWATCH
ABS_RETURN_N:T1
CORE
RECONSTRUCTED_CORRECTED
historical engineering descriptive baseline
```

E2 does NOT accept:

```text
REENTRY
NEW_CONFIRMED
T3/T5/T10/T20
MARKET_EXCESS
SECTOR_EXCESS
FIRST_EXIT
ANY event targets
DAILY_LANDMARK
real FIRST_OBSERVED
production display
Priority use
```

Those scopes remain independently gated.

---

## 15. Final State

```text
V4_15E2_FINAL_EXTERNAL_AUDIT =
PASS_FINAL_CAPABILITY_SCOPED

E2 =
ENGINEERING_ACCEPTED_CAPABILITY_SCOPED

E3_ENTRY =
AUTHORIZED_FOR_FIRST_PREWATCH_T1_ONLY

NEXT =
V4_15E3_INTERPRETABLE_MODEL_TIME_SPLIT
```
