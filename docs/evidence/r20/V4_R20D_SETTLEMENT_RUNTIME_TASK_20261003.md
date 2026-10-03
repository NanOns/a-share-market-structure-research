# R20D｜V4-15 Due Planner / Benchmark / Controls / Settlement Runtime｜2026-10-03

## 0. Entry Gate
Execute only after:

```text
R20A_CURRENT_STAGE_AUTHORITY = PASS_LOCAL
```

R20B may still run in parallel.

## 1. Authority
Use only:
- current V4-14 Accepted Head via R20A authority;
- externally accepted R19C settlement contracts;
- unified V4-15 contract package;
- accepted calendar / identity / adjustment / PIT authorities.

No raw/provider fallback.

## 2. Goal
Implement engineering runtime for:

```text
enrollment
→ frozen benchmark + controls
→ due planner
→ future accepted-source readback
→ price path / competing outcomes
→ outcome revision
→ readback
```

No V4-15 Accepted Head and no production settlement permission.

## 3. Suggested Modules
Recommended:
```text
src/workbench_analysis/v4_15_due_planner.py
src/workbench_analysis/v4_15_benchmark.py
src/workbench_analysis/v4_15_controls.py
src/workbench_analysis/v4_15_settlement.py
src/workbench_analysis/v4_15_outcome_revision.py
```

Names may follow repository conventions.

## 4. Due Planner
Implement horizons:
```text
1 / 3 / 5 / 10 / 20 accepted market sessions
```

Rules:
- use accepted market calendar;
- weekends/holidays do not count;
- same-day revision does not reset T0;
- suspension does not move the horizon;
- PENDING remains PENDING before due date.

## 5. Common Evaluation Basis
For each due horizon, transform:
- T0 reference;
- future close;
- future high/low path

onto one verified `evaluation_basis_date = T+N`.

Persist:
```text
comparison_reference
adjustment_identity
transform_coefficients
transform_digest
source_asof
available_at
```

Reject mixed QFQ snapshots / unverified basis changes.

## 6. Price Path
Implement exactly:
```text
R_N = P_N/P_0 - 1

MFE_N =
max(0, max(High_j/P_0 - 1))
for j = 1..N

MAE_N =
min(0, min(Low_j/P_0 - 1))
for j = 1..N

D_j = P_j/max(P_0..P_j)-1

PATH_MDD_CLOSE_N =
min(D_0..D_N)
```

T0 high/low must not enter future MFE/MAE.

## 7. Outcome States
Implement contracted states without coercion:
```text
PENDING
RIGHT_CENSORED
OBSERVED
SUSPENDED_AT_HORIZON
MATURED_DATA_MISSING
DELISTED_BEFORE_HORIZON
IDENTITY_UNKNOWN
ADJUSTMENT_UNKNOWN
```

Forbidden:
- missing -> 0;
- delisted unknown -> -100%;
- matured missing -> RIGHT_CENSORED;
- suspension endpoint -> later resumption date.

## 8. Competing Outcomes
For each PREWATCH episode track first:
```text
CONFIRMED
INVALIDATED
EXPIRED
```

Same-day conflict follows accepted state reducer priority.

Price-path settlement continues even after confirmation/invalidation.

## 9. Market Benchmark
Freeze benchmark at T0:
- eligible Research Universe;
- initial equal capital weights;
- fixed original weights/shares;
- no later renormalization.

Persist constituent status and quality.

MARKED_ESTIMATE permission remains blocked while accepted numeric coverage/quote-age gates are unset.

Do not invent them.

Absolute settlement must continue independently when relative benchmark is unavailable.

## 10. Sector / Rotation Benchmark
Implement:
- target-excluded sector benchmark;
- minimum n=2;
- T0 PIT membership;
- close-based sector MFE/MAE only;
- no sum of asynchronous member intraday highs/lows;
- rotation pulse basket from members known before pulse.

## 11. Controls
### A
Only actual T0 Legacy output.

If unavailable:
```text
NOT_AVAILABLE
```

### B
Same Hard Safety:
```text
delta3 DESC
security_id ASC
```

N equals same-day corresponding signal event count.

### C
Freeze T0 candidate pool and matched controls:
- same Hard Safety;
- not same-day final PREWATCH eligible;
- not signal entity;
- same primary industry if T0-known;
- otherwise `MATCH_SCOPE_MARKET`;
- exact contracted distance;
- max 3 controls;
- no future refill.

Later control crossing signal only appends `crossed_signal_at`.

ITT assignment remains frozen.

## 12. Outcome Revision
Unique identity:
```text
(enrollment_id,
 horizon,
 outcome_contract_id,
 evaluation_source_digest)
```

Same source rerun:
```text
IDEMPOTENT
```

Corrected source:
```text
APPEND_NEW_EVALUATION_REVISION
```

Never overwrite:
- T0;
- enrollment;
- original control assignment;
- first-observed settlement.

## 13. Engineering Persistence
Persist append-only engineering artifacts under:

```text
reports/v4_15_runtime_r20/settlement/
```

or repository-equivalent namespace.

No formal production DB migration.

## 14. Real Accepted-source Capability-scoped Run
Use accepted historical sources only.

Choose T0 dates whose due horizons are already inside the accepted Data Head.

Rules:
- T0 enrollment inputs may not see future sessions;
- future sessions are opened only by due-planner settlement;
- preserve reconstructed/corrected evidence limitations;
- no claim of real trading performance or historical PIT effectiveness.

Evidence class:
```text
REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED
```

## 15. Required Cases
At minimum:
- all 5 horizons;
- flat/up/down;
- MDD examples;
- corporate action basis change;
- endpoint suspension;
- interior suspension;
- unknown gap;
- delisting with/without terminal evidence;
- adjustment unknown;
- source available after evaluation cutoff;
- same source idempotency;
- corrected source revision;
- market benchmark fully observed;
- market benchmark missing member;
- MARKED_ESTIMATE gates unset;
- sector n<2;
- Control A unavailable;
- B exact N;
- C industry match;
- C market fallback;
- no future refill;
- later crossed control;
- invalidated enrollment still settles;
- Focus/UI exclusion still settles.

## 16. Independent Settlement Oracle
Must:
- recompute numerical formulas independently;
- reconstruct due dates from accepted calendar independently;
- verify frozen T0 controls/benchmark identities;
- verify no future source leakage;
- not import settlement evaluator for expected results.

## 17. Negative Cases
Reject:
- mixed evaluation basis;
- T0 intraday high in MFE;
- horizon shift after suspension;
- missing return filled 0;
- delisting filled -100 without evidence;
- benchmark reweighting;
- invented marked threshold;
- future-refilled controls;
- corrected source overwrites first observation;
- future data available before due;
- current authority V4-13;
- raw/provider fallback.

## 18. Completion
Required:
```text
R20D_V4_15_SETTLEMENT_RUNTIME = PASS_LOCAL
DUE_PLANNER_RUNTIME = IMPLEMENTED_ENGINEERING
BENCHMARK_CONTROL_RUNTIME = IMPLEMENTED_ENGINEERING
SETTLEMENT_RUNTIME = IMPLEMENTED_ENGINEERING
REAL_ACCEPTED_SOURCE_SETTLEMENT = PASS_CAPABILITY_SCOPED

HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED

V4_15_ACCEPTED_HEAD = NOT_CREATED
Production = false
Shadow = false
Focus = false

NEXT = R20E_AFTER_R20C_AND_R20B
```
