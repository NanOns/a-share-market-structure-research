# R19C｜V4-15 Settlement / Benchmark / Controls Contract Freeze｜2026-10-03

## 0. Entry Gate

Execute only after:

```text
R19A_V4_14_PROMOTION = PASS_LOCAL
```

This task is contract-first only.

No actual settlement run, no enrollment write, no production/shadow execution and no formal DB migration are authorized.

## 1. Goal

Freeze the complete machine-readable contract family for:

- due planner;
- forward price path;
- horizon identity;
- outcome quality/status;
- evaluation revisions;
- competing outcomes;
- market benchmark;
- sector benchmark;
- rotation pulse basket benchmark;
- Control A/B/C;
- matched controls;
- settlement readback;
- append-only correction semantics.

## 2. Master Contract Sections

At minimum encode:
- §46 Forward Outcomes;
- §46A Horizon / formulas;
- §47 maturity / censoring;
- §48 competing outcomes;
- §49 Controls;
- §49A market / sector / rotation forward benchmark;
- §49B matched controls;
- source/quality/temporal rules;
- Definition of Done / no future leakage.

## 3. Required Contract Artifacts

Recommended minimum set:

```text
config/v4_15_due_planner_contract_v1.json
config/v4_15_forward_price_path_contract_v1.json
config/v4_15_outcome_status_contract_v1.json
config/v4_15_competing_outcome_contract_v1.json
config/v4_15_forward_market_benchmark_contract_v1.json
config/v4_15_forward_sector_benchmark_contract_v1.json
config/v4_15_rotation_pulse_basket_contract_v1.json
config/v4_15_control_assignment_contract_v1.json
config/v4_15_settlement_revision_contract_v1.json
config/v4_15_settlement_readback_contract_v1.json
config/v4_15_settlement_field_registry_v1.json
config/v4_15_settlement_machine_vectors_v1.json
```

Names may follow repository conventions, but no semantic family may remain implicit.

## 4. Horizon / Calendar

Freeze horizons:

```text
N = 1 / 3 / 5 / 10 / 20 accepted market sessions
```

T0 is the signal close.

T0 is explicitly **not** a tradable strategy-entry return.

Due dates must use the accepted market calendar and never count weekends/holidays as sessions.

Same-day revision does not reset T0.

## 5. Price Basis

`evaluation_basis_date = T+N`.

T0 and all later OHLC must be transformed to one verified common evaluation basis using the accepted local adjustment authority.

Freeze and persist:
- original signal reference;
- comparison reference;
- adjustment identity;
- transformation coefficient/digest;
- source_asof;
- available_at.

Never divide values from different QFQ snapshots without proving the same basis.

## 6. Forward Price Path Formula

For P0..PN on one common basis:

```text
R_N = P_N / P_0 - 1

MFE_N =
max(0, max(High_j / P_0 - 1))
for j = 1..N

MAE_N =
min(0, min(Low_j / P_0 - 1))
for j = 1..N

D_j =
P_j / max(P_0 ... P_j) - 1

PATH_MDD_CLOSE_N =
min(D_0 ... D_N)
```

T0 intraday high/low must not enter future MFE/MAE.

Mandatory frozen examples:

```text
[100,110,120] -> MDD 0
[100,80,90]   -> MDD -0.20
[100,120,90]  -> MDD -0.25
```

Also freeze N=1, flat path, corporate-action, confirmed suspension and unknown-gap cases.

## 7. Maturity / Quality

Freeze states at minimum:

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

Rules:
- not-yet-due is PENDING, not failure;
- report-cutoff unfinished time-to-event may be RIGHT_CENSORED;
- matured missing data is not RIGHT_CENSORED;
- suspension at endpoint does not move the horizon to the later resume date;
- delisting without verified terminal value is not -100% and not 0;
- unknown/missing never silently becomes zero return.

## 8. Competing Outcomes

For each PREWATCH episode freeze first observed market-date time of:

```text
CONFIRMED
INVALIDATED
EXPIRED
```

Same-day conflict follows the accepted state reducer’s hard invalidation priority.

RIGHT_CENSORED is an observation state, not a competing event.

Price settlement continues through the configured horizon after confirmation/invalidation; do not stop collecting path data because the research state changed.

## 9. Outcome Identity / Revision

Freeze unique outcome identity:

```text
(enrollment_id,
 horizon,
 outcome_contract_id,
 evaluation_source_digest)
```

Same source repeated:
`idempotent`.

Corrected source:
`append new evaluation_revision`.

Keep separate:

```text
FIRST_OBSERVED
LATEST_CORRECTED
```

Do not overwrite the original signal/enrollment.

Every revision must carry:
- source identity;
- available_at;
- evaluation revision;
- supersedes;
- evidence class;
- reason codes.

## 10. Forward Market Benchmark

Freeze independent contract:

`FORWARD_MARKET_BENCHMARK_V1`

It is not the Core market reference.

At T0:
- freeze eligible Research Universe;
- equal initial capital weights;
- fixed shares / original weights;
- no later reweighting because members become weak, suspended or delisted.

Benchmark identity must include:
- T0 members;
- initial weights;
- adjustment identity;
- constituent policy;
- parameter/source digest.

## 11. Benchmark Constituent Quality

Freeze mutually exclusive main states:

```text
IDENTITY_UNKNOWN
ADJUSTMENT_UNKNOWN
DELISTED
CONFIRMED_SUSPENSION
DATA_MISSING
ACTUAL_ENDPOINT
```

Preserve:
- endpoint coverage;
- missing weight;
- suspended weight;
- delisted weight;
- unknown weight;
- valuation coverage;
- marked weight;
- benchmark quality.

Do not renormalize remaining observed members.

## 12. MARKED_ESTIMATE Boundary

The current capability policy has benchmark coverage / suspension quote-age numeric thresholds unset.

Therefore this task must **not invent percentages or days**.

Until separately frozen/accepted:

```text
OBSERVED relative benchmark = allowed only with fully observed/contract-qualified endpoint

MARKED_ESTIMATE relative output =
CONTRACT_DEFINED_BUT_PERMISSION_BLOCKED_IF_REQUIRED_NUMERIC_GATES_UNSET

PARTIAL_UNVALUED =
explicit partial diagnostic only
```

Absolute-return settlement remains independent and must not be globally blocked by unavailable marked-relative capability.

## 13. Sector / Rotation Benchmark

Freeze:
- `FORWARD_SECTOR_BENCHMARK_V1`;
- `ROTATION_PULSE_BASKET_V1`.

Rules:
- T0 frozen member set;
- stock relative-sector excludes target stock;
- n<2 => unavailable/UNKNOWN;
- sector and stock outcomes reported separately;
- sector daily line data only supports close-based MFE/MAE;
- never aggregate member intraday highs as if synchronized;
- rotation pulse basket uses members known before pulse and accepted price basis.

## 14. Controls

### Control A
Actual same-day Legacy model eligible objects only.

If no real Legacy same-day output exists:
`NOT_AVAILABLE`.

Never reconstruct a fake observed Legacy control after the fact.

### Control B
Same Hard Safety, `delta3` Top-N where N equals the same-day count for the corresponding stock signal event type.

Stable `security_id` tie-break.

### Control C / CONTROL_ASSIGNMENT_V1
Candidate pool:
- same Hard Safety;
- not same-day PREWATCH final eligible;
- not the signal entity.

Prefer same primary industry if T0-known; otherwise market-wide and label:

`MATCH_SCOPE_MARKET`.

Distance:

```text
abs(pct_rank(log prior20_mean_amount)_signal - control)
+
abs(pct_rank(vol20)_signal - control)
+
abs(pct_rank(RPS20)_signal - control)
```

At most 3 nearest controls.

Do not future-refill missing controls.

Later crossing into signal status only appends `crossed_signal_at`; ITT control assignment remains frozen.

## 15. Readback / Due Planner

Freeze interfaces that can answer:
- what is due today;
- what is pending;
- what matured;
- what is first-observed;
- what has a corrected revision;
- which benchmark/control identities were frozen at T0;
- why a result is unavailable/degraded.

Readback must never rewrite T0 facts.

## 16. Field Registry

Every field declares:
- producer;
- consumer;
- type/unit;
- time role;
- source binding;
- evidence class;
- quality states;
- UNKNOWN / NOT_APPLICABLE semantics;
- revision behavior;
- identity participation.

## 17. Machine Vectors

At minimum cover:
- all five horizons;
- flat/up/down paths;
- MDD examples;
- confirmed suspension;
- unknown gap;
- delisting with and without terminal evidence;
- adjustment mismatch;
- future source leakage;
- repeated idempotent settlement;
- corrected source revision;
- first-observed preserved;
- benchmark missing member;
- benchmark no reweighting;
- marked estimate blocked by unset gates;
- sector n<2;
- Control A unavailable;
- Control B exact N;
- Control C same-industry match;
- market fallback match;
- no future refill;
- control later crosses signal;
- Focus/UI exclusion still settles;
- invalidated signal still settles.

Expected outputs must be frozen statically.

## 18. Completion

Required:

```text
R19C_V4_15_SETTLEMENT_CONTRACT_FREEZE = PASS_LOCAL
SETTLEMENT_CONTRACT_COMPLETENESS = PASS_LOCAL
V4_15_RUNTIME = NOT_IMPLEMENTED
V4_15_ACCEPTED_HEAD = NOT_CREATED

NEXT = R19D_AFTER_R19B_AND_R19C
```
