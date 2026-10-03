# V4 R20R1 Independent External Audit R2｜2026-10-03

## 0. Audit Target

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Current remote HEAD:

`555409d79c58517761472531404f0ee5cccd81af`

R20R1 exact tested source:

`a49b7d6695857617dcf143aabd47625e58a5c99b`

Immutable tested tag:

`codex/r20r1-tested-source-20261003-r1`

R20R1 execution baseline:

`7f97f4487e2c8aaccb7e7701af4ccfddfa7ddec9`

---

# 1. Audit Scope Correction

The local disk cleanup has been completed by the user and is no longer part of the R20R1/R20R1R1 external acceptance gate.

Therefore:

```text
PRECLEAN_EXTERNAL_VERIFICATION = OUT_OF_SCOPE
PRECLEAN_RECOVERY_TASK = REMOVED
DISK_CLEANUP = NON_BLOCKING
```

No further disk-cleanup task, report recovery, or free-space evidence is required by this audit.

---

# 2. Unique External Audit Decision

```text
R20R1_EXTERNAL_AUDIT =
BLOCKED_FORWARD_MATURITY_DEBT_PATH_UNREACHABLE

R20R1_SCOPE_DECOMPOSITION = PASS_KEEP
R20R1_REAL_MATURITY_FEASIBILITY = PASS_KEEP
R20R1_CURRENT_FAIL_CLOSED_SCOPE = PASS_KEEP
R20R1_TESTED_SOURCE_GOVERNANCE = PASS_KEEP
R20R1_PROTECTED_STATE = PASS_KEEP

R20R1_FORWARD_MATURITY_DEBT_CLOSURE = FAIL_P0
R20R1_HORIZON_SCOPED_DEBT_STATE = FAIL_P1

PRECLEAN_EXTERNAL_VERIFICATION = OUT_OF_SCOPE

V4_15_ACCEPTED_HEAD_PROMOTION = BLOCKED
V4_16 = BLOCKED
```

The blocker is only the newly introduced go-forward maturity validation mechanism.

---

# 3. Passed Items

## 3.1 Capability decomposition｜PASS KEEP

The R20R1 scope gate correctly replaces the ambiguous R20 generic labels with:

```text
V4_15_RUNTIME_ENGINEERING = PASS

REAL_ACCEPTED_SOURCE_T0_INTEGRATION =
PASS_CAPABILITY_SCOPED

REAL_ACCEPTED_SOURCE_PENDING_DUE_READBACK =
PASS_CAPABILITY_SCOPED

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED
```

Historical R20 evidence remains immutable.

---

## 3.2 Real maturity feasibility oracle｜PASS KEEP

The feasibility oracle establishes:

```text
accepted V4-14 real publication count = 1
real accepted T0 = 2026-09-30
Data Head cutoff = 2026-09-30
accepted future endpoint reads = 0
all real 1/3/5/10/20 outcomes = PENDING
earlier accepted real matured lineage = 0
```

Earlier replay dates are correctly classified as engineering/synthetic and are not promoted to real historical evidence.

---

## 3.3 Current fail-closed scope｜PASS KEEP

Current R20R1 state correctly remains:

```text
REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED
```

The current fail-closed protections against capability widening are valid.

---

## 3.4 Protected stage state｜PASS KEEP

Current repository state remains:

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_14_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

V4_15_ACCEPTED_HEAD =
NOT_CREATED

Production = false
Shadow = false
Focus = false
V4_16 = false
```

---

## 3.5 Tested source governance｜PASS KEEP

The immutable tested tag:

`codex/r20r1-tested-source-20261003-r1`

resolves to:

`a49b7d6695857617dcf143aabd47625e58a5c99b`

The final branch HEAD is one evidence-only commit ahead.

No implementation source changed after the tested source.

---

## 3.6 Clean regression｜PASS KEEP

R20R1 reports:

```text
51 new R20R1 tests PASS
107 current R20 tests PASS
158 clean detached tests PASS
0 failed
0 errors
0 skipped
0 deselected
```

---

# 4. P0 Finding｜Forward Maturity Debt Closure Is Unreachable

R20R1 advertises an incremental real-maturity validation path through:

```text
python -m scripts.r20r1_maturity_debt <exact_packet_list.json>
```

But the validator simultaneously requires:

```text
packet.owner_publication
IN
V4-14 frozen runtime seal replay_publications
```

and:

```text
enrollment.cohort_namespace =
REALTIME_ACCEPTED
```

The only sealed real V4-14 publication is T0=2026-09-30 and its accepted enrollment is:

```text
RECONSTRUCTED_ASOF
```

not `REALTIME_ACCEPTED`.

Future genuinely new real-time publications cannot be inserted into the already frozen V4-14 seal without rewriting accepted history.

Therefore no legitimate future packet can satisfy the advertised positive path under the current authority model.

Current behavior is safe but not reachable:

```text
OPEN
→ no valid positive packet exists
→ debt cannot close through advertised path
```

---

# 5. Required Capability Split

The fix must distinguish:

## 5.1 Real accepted-source settlement-runtime maturity

Introduce an explicit capability such as:

```text
REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME
```

The existing accepted Sept-30 trajectory:

```text
REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED
+
RECONSTRUCTED_ASOF
```

may later prove real accepted-source settlement/runtime behavior after accepted future endpoints mature.

It must retain:

```text
T0_OBSERVATION_SCOPE = RECONSTRUCTED_ASOF
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED
```

This does not prove historical signal availability.

## 5.2 Real-time cohort maturity

A separate capability may require:

```text
REALTIME_ACCEPTED
```

and remains NOT_GRANTED until a true future real-time cohort exists.

Do not require this stronger capability for settlement-runtime maturity.

---

# 6. P1 Finding｜Global Closure After One Horizon

Current debt refresh semantics close the aggregate maturity state after any positive proof.

That is too broad.

Required aggregate state:

```text
OPEN
PARTIAL_MATURITY_EVIDENCE
FULL_REQUIRED_HORIZONS_PROVEN
```

Required explicit fields:

```text
required_horizons = [1,3,5,10,20]
proved_horizons
unproved_horizons
capability_by_horizon
```

Example:

```text
T+1 proved
T+3/T+5/T+10/T+20 unproved
```

must produce:

```text
PARTIAL_MATURITY_EVIDENCE
```

and must not globally unblock unqualified real-maturity claims.

---

# 7. Required Positive Reachability Test

R20R1R1 must include a positive engineering reachability test using an isolated exact-authority fixture representing:

```text
accepted Sept-30 real publication
accepted RECONSTRUCTED_ASOF enrollment
immutable T0 freeze
later accepted Data Head
complete accepted T+1 endpoint
independently recomputed observed T+1 outcome
```

Expected:

```text
proved_horizons = [1]
unproved_horizons = [3,5,10,20]

aggregate =
PARTIAL_MATURITY_EVIDENCE

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED

stage_promotion_authorized =
false
```

The fixture proves code-path reachability only and must not upgrade current real evidence.

---

# 8. Final External Audit State

```text
R20R1_EXTERNAL_AUDIT =
BLOCKED_FORWARD_MATURITY_DEBT_PATH_UNREACHABLE

R20R1_CURRENT_SCOPE_CORRECTION =
PASS_KEEP

PRECLEAN_EXTERNAL_VERIFICATION =
OUT_OF_SCOPE

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

V4_15_ACCEPTED_HEAD =
NOT_CREATED

V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_14_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

Production = false
Shadow = false
Focus = false
V4_16 = false

NEXT =
R20R1R1_FORWARD_MATURITY_DEBT_REPAIR
```
