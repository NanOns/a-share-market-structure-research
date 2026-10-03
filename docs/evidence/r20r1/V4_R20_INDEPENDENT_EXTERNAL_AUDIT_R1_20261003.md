# V4 R20 Independent External Audit R1｜2026-10-03

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`

Branch: `codex/v4-system-reform`

Audited remote HEAD:

`7f97f4487e2c8aaccb7e7701af4ccfddfa7ddec9`

R20 execution baseline:

`2020234020e09020aca13fd84cdabde6fbb81f50`

R20 exact clean-tested implementation source:

`30f2e559a57529cbb16df431863fa6722fa0a13a`

Final remote HEAD is one evidence-only seal commit after the tested source; no R20 runtime implementation code is changed after the clean-tested implementation source.

---

## 1. Unique External Audit Decision

```text
R20_EXTERNAL_AUDIT =
PARTIAL_PASS_REAL_MATURED_ACCEPTED_SOURCE_SCOPE_REPAIR_REQUIRED

R20A_CURRENT_STAGE_AUTHORITY = PASS_KEEP
R20B_BYTE_IDENTITY_PORTABILITY_CURRENT_SCOPE = PASS_KEEP
R20C_RADAR_COHORT_RUNTIME = PASS_KEEP

R20D_SETTLEMENT_ENGINEERING_RUNTIME = PASS_KEEP
R20D_REAL_T0_ACCEPTED_SOURCE_BINDING = PASS_KEEP_CAPABILITY_SCOPED
R20D_REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT = NOT_PROVEN_P0

R20E_PERSISTED_ENGINEERING_E2E = PASS_KEEP
R20E_INDEPENDENT_ORACLE_ENGINEERING_SCOPE = PASS_KEEP

R19_AUDIT_01_BYTE_IDENTITY_PORTABILITY = CLOSED_CURRENT_RUNTIME_SCOPE
R19_AUDIT_02_CURRENT_STAGE_READER_COMPATIBILITY = CLOSED

TESTED_SOURCE_REMOTE_ADDRESSABILITY = PASS

V4_15_RUNTIME_ENGINEERING_CANDIDATE =
PASS_KEEP_CAPABILITY_SCOPED

V4_15_ACCEPTED_HEAD_PROMOTION =
BLOCKED_PENDING_R20R1_SCOPE_CLOSURE

V4_16 = BLOCKED

HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED
```

This audit does **not** reject the R20 runtime implementation. The blocker is a capability/evidence boundary mismatch in the claimed real accepted-source settlement scope.

---

## 2. What Passed

### 2.1 R20A｜PASS KEEP

The moving Stage Head is coherent:

```text
accepted_stage_range = V4_00_TO_V4_14_ACCEPTED
v4_14_entry =
COMPLETED_EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED_REPLAY_GATE_B
```

The current runtime authority is rooted at:

`data/v4/V4_14_ACCEPTED_HEAD.json`

Historical V4-13 replay validation remains isolated in historical context rather than being weakened to consume the moving current pointer.

Therefore the R19 P0 current-stage reader incompatibility is closed.

### 2.2 R20B｜PASS KEEP for current runtime scope

The representation registry freezes 2,946 files and verifies the current authority graph with explicit representation rules.

Current runtime authority edges pass exact/registered representation admission.

The disclosed 22 historical noncurrent path/version mismatches and three unavailable historical leaf descriptors remain outside current runtime authority and are not silently normalized or promoted.

This is acceptable for the current R20 runtime scope. It is not evidence of complete historical-content archival closure.

### 2.3 R20C｜PASS KEEP

The Radar/Cohort runtime is implemented as an append-only read-only projection over accepted owner state/events.

Key observed protections include:

- current V4-14 authority required;
- no owner recomputation;
- Focus/UI do not filter cohort admission;
- future/FEP feedback is rejected;
- same-day correction does not reset T0;
- changed-byte overwrite fails closed;
- persistent episode does not duplicate enrollment;
- stock WARM is not synthesized without an accepted owner;
- real reconstructed evidence remains explicitly non-PIT.

The R20C focused suite reports 25 passed tests.

### 2.4 R20D engineering settlement runtime｜PASS KEEP

The engineering runtime covers:

- 1/3/5/10/20 accepted-session due planning;
- common evaluation basis;
- R/MFE/MAE/PATH_MDD_CLOSE;
- suspension/gap/delisting/missing/identity/adjustment states;
- fixed-weight market/sector benchmarks without silent reweighting;
- Control A/B/C;
- append-only evaluation revisions;
- first/latest readback.

The focused suite reports 31 passed tests.

Mature numerical formula evidence is explicitly labeled:

```text
numerical_forward_scope = ENGINEERING_VECTORS_ONLY
```

This is acceptable evidence for engineering formula/runtime correctness.

### 2.5 R20E engineering persisted E2E/oracle｜PASS KEEP

The engineering E2E proves a persisted process boundary:

```text
producer
→ persisted T0 freeze
→ process exit
→ separate settlement process
→ future engineering source
→ settlement/revision/readback
```

The independent oracle does not use the runtime evaluators to derive expected results.

The R20 current suite reports:

```text
107 passed
0 failed
0 errors
0 skipped
0 deselected
```

The clean combined regression reports:

```text
1168 historical
+ 62 R19 contract
+ 107 R20 current
= 1337 passed
```

The exact clean-tested source `30f2e559...` is remotely reachable and is an ancestor of final branch HEAD `7f97f448...`.

The final one-commit delta is evidence/seal material only. Therefore the prior bundle-only tested-source defect is closed for R20.

---

## 3. P0 Finding｜Real Matured Accepted-Source Settlement Was Not Proven

### 3.1 What the R20D task contract required

R20D Section 14 required a real accepted-source capability-scoped run using accepted historical sources and explicitly stated:

```text
Choose T0 dates whose due horizons are already inside the accepted Data Head.
```

That requirement is materially different from only proving a current T0 freeze.

### 3.2 What R20 actually executed

The current accepted V4-14 Head has:

```text
accepted_trade_date = 2026-09-30
```

The Data Head also ends at:

```text
2026-09-30
```

The R20D real accepted-source gate records:

```text
future_read_count = 0

real_scope =
ACCEPTED_CURRENT_T0_RECONSTRUCTED_PROJECTION_AND_
FIVE_PENDING_HORIZONS_NO_ACCEPTED_FUTURE_BEYOND_DATA_HEAD

numerical_forward_scope =
ENGINEERING_VECTORS_ONLY
```

All five real accepted-source horizon outcomes are PENDING.

The R20E independent oracle explicitly requires the real outcomes to remain PENDING and checks that no future/PIT claim is made.

Therefore R20 successfully proves:

1. accepted current T0 source binding;
2. reconstructed enrollment/T0 freeze;
3. pending due-plan/readback behavior;
4. engineering-vector mature settlement formulas.

It does **not** prove:

```text
REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT
```

against a matured real accepted source.

### 3.3 Why this matters

The current labels:

```text
REAL_ACCEPTED_SOURCE_SETTLEMENT = PASS_CAPABILITY_SCOPED
REAL_ACCEPTED_SOURCE_V4_15 = PASS_CAPABILITY_SCOPED
```

are too broad unless their capability scope is explicitly decomposed.

A reader can reasonably interpret those fields as including real accepted-source matured settlement, while the evidence only supports current-T0/pending integration plus engineering mature vectors.

This is a governance/evidence-boundary defect, not a settlement-formula defect.

---

## 4. Required Scope Correction

R20R1 must replace the ambiguous promotion semantics with explicit capability decomposition.

Minimum required semantics:

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

Do not fabricate an earlier accepted V4-14 publication.

Do not use a synthetic engineering trajectory to upgrade `REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT`.

If a genuinely accepted earlier-T0 lineage exists and can be independently proven, R20R1 may use it. Otherwise the correct outcome is the narrower capability statement above.

This open maturity evidence is allowed to accumulate go-forward and must **not** block unrelated system development after the capability boundary is corrected.

---

## 5. Protected State

Until R20R1 is externally accepted:

```text
V4_15_ACCEPTED_HEAD = NOT_CREATED

V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_14_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

Production = false
Shadow = false
Focus = false
V4_16 = false

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED
```

Do not rewrite already accepted V4-08 through V4-14 business algorithms.

---

## 6. Authorized Next Round

Only R20R1 capability-scope closure is authorized now.

The purpose is **not** to wait for 20 trading days and not to force historical reconstruction.

The purpose is to make the acceptance contract truthfully distinguish:

```text
engineering mature settlement
vs
real current-T0 integration
vs
real matured accepted-source settlement
vs
historical PIT effectiveness
```

After R20R1 passes independent external audit, V4-15 Accepted Head may be promoted under the explicitly capability-scoped semantics without waiting for long-horizon real outcomes, provided the Accepted Head keeps the matured-real and historical-PIT capabilities NOT_GRANTED.
