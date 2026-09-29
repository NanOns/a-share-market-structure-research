# V4-04 R5 Contract-Semantics Final Repair Task

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Date:** 2026-09-29  
**Task Type:** V4-04 final contract-semantics repair before external acceptance

---

# 0. Current External-Audit Status

Previous external-audit baseline:

`1af58725b8c486904ed5149b6427739b9f2b051f`

Current reviewed branch HEAD:

`0915c9692791f8482d799ae671513e8b1a1ea5b3`

Current R3 implementation commit:

`e23d75012f319c6bd0c8b19d0f8f9e59cddf61c3`

Current R3 candidate:

`reports/v4_04/staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R3.jsonl.gz`

Current R3 SHA256:

`0c0fccd06fd2c2bad856b529d3ae2bcf64584f451e97961380997d72830b46b6`

Current external disposition:

`V4_04_EXTERNAL_ACCEPTANCE_BLOCKED_R3_CONTRACT_SEMANTICS_REPAIR_REQUIRED`

Do not reopen V4-00 through V4-03.

Do not start V4-05.

Do not create/promote V4-04 Accepted Head.

Preserve R1, R2 and R3 artifacts and receipts as immutable historical evidence.

---

# 1. Findings That Are Now Accepted

The following R4 repairs are accepted and should not be reworked except where necessary to support the fixes below.

## PASS — Technical Window Missing/UNKNOWN Gap Detection

The new `technical_window_status()` correctly validates dated trading-status rows against the full exchange-session calendar for production use.

It now distinguishes:

- `ACTUAL_TRADED`
- confirmed `SUSPENDED`
- unknown/unsupported status
- missing status row

for MA10, prior20 liquidity and pos250.

Confirmed suspensions may be skipped by actual-bar technical windows.

Unknown or missing session/status evidence fails the technical window closed.

## PASS — Direct Source Recompute for ATR-Derived Fields

The R3 independent verifier now directly reads:

- accepted QFQ current close
- accepted V4-03 MA20
- accepted V4-03 ATR20
- accepted V4-03 prior_high20

and independently recomputes:

- `bias20_atr`
- `dist_high20_atr`

without using candidate state evidence as the oracle.

## PASS — R3 Production / Determinism / Focused Regression

Accepted evidence:

- 5,222 required-scope rows
- SH_MAIN 1702
- SZ_MAIN 1494
- CHINEXT 1408
- STAR 618
- deterministic R3 artifact
- 374 passed / 2 skipped / 0 failed focused V4 regression
- no V4-04 Accepted Head
- V4-05 remains NOT_STARTED
- R1 and R2 preservation hashes remain intact

---

# 2. Blocking Finding S01 — minimum_liquidity Has an Undeclared amount_ratio20 Dependency

## 2.1 Formal Contract

The machine contract defines:

```text
minimum_liquidity
=
mean(prior20 accepted raw CNY amount, excluding T)
>= 20,000,000 CNY
```

The governing REV2 contract likewise defines this primitive from prior20 amount history.

Its formal inputs do **not** include `amount_ratio20`.

## 2.2 Current Runtime Error

Current `src/v4/profile_primitives.py` contains:

```python
amount_factor_ok = _factor(factors, "amount_ratio20") is not None

liquid_ok = (
    current
    and amount_factor_ok
    and len(prior_rows) == prior_window
    and ...
)
```

This introduces a hidden dependency:

```text
minimum_liquidity
→ amount_ratio20 must also be OBSERVED
```

That dependency is not present in:

- REV2 §10F / §72
- `V4_04_DERIVED_PRIMITIVES_V1.minimum_liquidity`
- `v4_04_field_registry_v2.json`
- `v4_04_field_window_mapping_v1.json`

The R3 full-market completeness evidence is consistent with this coupling:

```text
amount_ratio20 UNKNOWN       = 198
minimum_liquidity UNKNOWN    = 198
```

This does not prove every one of the 198 rows is wrong, but the code itself proves the extra dependency exists.

## 2.3 Required Repair

Remove the `amount_ratio20` availability requirement from `minimum_liquidity`.

`minimum_liquidity` must depend only on:

- valid T endpoint identity required by its time semantics;
- prior20 verified actual amount observations;
- valid complete technical-window status/calendar lineage;
- numeric raw CNY amount values;
- frozen 20,000,000 CNY threshold.

It must remain independently computable when:

```text
amount_ratio20 = UNKNOWN
```

if its own prior20 source window is valid.

Do not alter `compression_state` requirements. Compression may still become UNKNOWN because `amount_ratio20` itself is required by COMPRESSION_STATE_V1.

The key requirement is:

```text
minimum_liquidity field semantics
!=
compression eligibility semantics
```

## 2.4 Mandatory Tests

Add at least:

### Case A
Prior20 amount valid, T valid, status/calendar valid, `amount_ratio20=UNKNOWN`.

Expected:

```text
minimum_liquidity = OBSERVED
```

### Case B
Prior20 amount valid and mean >=20m, `amount_ratio20=UNKNOWN`.

Expected:

```text
minimum_liquidity = TRUE
compression_state = UNKNOWN
```

### Case C
Prior20 amount valid and mean <20m, `amount_ratio20=UNKNOWN`.

Expected:

```text
minimum_liquidity = FALSE
compression_state = UNKNOWN
```

### Case D
Prior20 amount/status window invalid.

Expected:

```text
minimum_liquidity = UNKNOWN
```

regardless of `amount_ratio20`.

## 2.5 Independent Audit Requirement

The next independent verifier must explicitly check for false UNKNOWN:

For every deterministic sampled row where the independent source can prove:

- T endpoint/time semantics valid;
- prior20 amount technical window valid;
- all 20 amount values numeric;

then the candidate must have:

```text
minimum_liquidity != UNKNOWN
```

even if upstream `amount_ratio20` is UNKNOWN.

Record:

```text
minimum_liquidity_source_evaluable_count
minimum_liquidity_false_unknown_count
amount_ratio20_unknown_but_liquidity_evaluable_count
```

Acceptance requires:

```text
minimum_liquidity_false_unknown_count = 0
```

---

# 3. Blocking Finding S02 — Machine Executor Still Does Not Model Enum UNKNOWN Semantics Faithfully

## 3.1 Relative State Problem

Production code correctly contains:

```python
if ... or "UNKNOWN" in (compression_state, ma_state):
    return UNKNOWN
```

because both dependency states are required.

But the independent generic machine executor treats the literal string:

```text
"UNKNOWN"
```

as an ordinary enum value.

For example:

```text
rps20_delta3 = 10
compression_state = "UNKNOWN"
ma_structure_state = "MIXED"
```

the AST `IN` predicates evaluate FALSE rather than UNKNOWN.

The machine executor can then continue to lower branches and potentially return:

```text
IMPROVING
```

instead of required `UNKNOWN`.

The current generic `{}` UNKNOWN vector does not test this case.

## 3.2 severe_extension Problem

Production semantics:

```text
core_extension_risk = UNKNOWN
→ severe_extension = UNKNOWN
```

The machine contract already contains an `unknown_policy` for this rule.

However the generic executor's `EQ` operation sees:

```text
"UNKNOWN" == "EXTREME"
```

and returns `FALSE`.

It does not enforce:

```text
UNKNOWN_IF_RISK_UNKNOWN
```

The existing machine-vector UNKNOWN case uses missing evidence (`None`), not the actual enum sentinel `"UNKNOWN"` used by production.

Therefore the current `machine_rule_coverage=1.0` and `rules_missing_vector_coverage=[]` still overstate semantic equivalence.

## 3.3 Required Repair

The formal machine execution layer must model typed UNKNOWN semantics explicitly.

Acceptable solutions include:

### Option A
Normalize required dependency state value `"UNKNOWN"` to machine UNKNOWN (`None`) before AST evaluation for rules whose registered input is a required state.

### Option B
Add explicit AST/DSL operators or required-field guards for enum state dependencies.

### Option C
Implement rule-specific `unknown_policy` handling in the independent executor where the machine contract already declares it.

Do not solve this only inside test vectors.

The executable machine contract itself must produce the same result as production.

## 3.4 Mandatory Machine Vectors

Add at minimum:

### Relative

```text
compression_state="UNKNOWN"
ma_structure_state valid
→ UNKNOWN
```

```text
compression_state valid
ma_structure_state="UNKNOWN"
→ UNKNOWN
```

Test with otherwise-valid numeric inputs that would fall into a lower positive branch if UNKNOWN propagation were ignored.

### severe_extension

```text
core_extension_risk="UNKNOWN"
→ UNKNOWN
```

not FALSE.

### Participation branch-specific UNKNOWN

```text
amount_ratio20 >= 1.2
ret1 > 0
clv = UNKNOWN
→ UNKNOWN
```

This must not fall through to `HIGH_PARTICIPATION_LOW_EFFICIENCY`.

### Trend branch-specific UNKNOWN

Provide otherwise-valid strong/uptrend inputs with:

```text
core_price_damage = UNKNOWN
```

and confirm required-input UNKNOWN semantics.

### Regime UI stateful UNKNOWN

Test:

- accepted last-known label;
- next observation UNKNOWN;
- output UNKNOWN while preserving last-known state as specified by the regime contract.

Also test interrupted pending hysteresis sequence.

---

# 4. Blocking Finding S03 — Drawdown Inclusive Threshold Boundaries Are Wrong Due to Float Arithmetic

## 4.1 Formal Contract

REV2 §10C defines:

```text
drawdownN = C / HHV_N - 1

>= -0.05  → SHALLOW
>= -0.15  → MODERATE
else       → DEEP
```

Therefore exact boundaries are:

```text
-5.00%  → SHALLOW
-15.00% → MODERATE
```

## 4.2 Current R3 Golden Vectors Are Incorrect

Current R3 machine vectors explicitly expect:

```text
close = 9.5, hhv = 10
→ MODERATE
```

and:

```text
close = 8.5, hhv = 10
→ DEEP
```

Those expectations contradict the formal inclusive thresholds.

The cause is ordinary binary-float arithmetic:

```text
9.5 / 10 - 1
≈ -0.050000000000000044

8.5 / 10 - 1
≈ -0.15000000000000002
```

so a direct floating `>= -0.05` / `>= -0.15` comparison misclassifies exact economic boundaries.

The machine-vector suite currently certifies this incorrect behavior instead of catching it.

## 4.3 Required Repair

Implement boundary-stable semantics shared by production and independent machine execution.

Preferred solution:

avoid unstable subtraction comparison by algebraically equivalent threshold checks, e.g. conceptually:

```text
C / HHV >= 0.95
→ SHALLOW

C / HHV >= 0.85
→ MODERATE
```

or use a formally frozen numeric comparison/tolerance policy.

Whichever method is selected must:

- preserve contract meaning;
- be deterministic;
- be machine-contract expressible;
- be used consistently by production and independent executor;
- not introduce arbitrary hidden epsilons.

If introducing a numeric tolerance policy, register and document it explicitly.

## 4.4 Mandatory Boundary Vectors

For N=20 and N=60 semantics:

```text
drawdown = -0.049999... → SHALLOW
drawdown = exactly -0.05 → SHALLOW
drawdown just below -0.05 → MODERATE

drawdown just above -0.15 → MODERATE
drawdown = exactly -0.15 → MODERATE
drawdown just below -0.15 → DEEP
```

Also retain:

- zero / invalid HHV → UNKNOWN
- missing close → UNKNOWN

The next machine-vector receipt must not encode mathematically incorrect boundary classifications.

---

# 5. Machine Vector Coverage Receipt Must Become Semantic, Not Merely Structural

The next vector receipt must continue to prove:

- every formal rule exists in vectors;
- every first-true branch is reached;
- threshold vectors exist;
- UNKNOWN vectors exist.

Additionally add explicit counters/flags for:

```text
branch_specific_unknown_vectors
enum_unknown_vectors
stateful_hysteresis_vectors
inclusive_boundary_vectors
```

Suggested receipt:

`reports/v4_04/V4_04_MACHINE_VECTOR_COVERAGE_R4.json`

Acceptance requires all semantic categories PASS.

---

# 6. Candidate Versioning

Do not overwrite R1/R2/R3.

Create a new candidate:

`reports/v4_04/staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R4.jsonl.gz`

Create corresponding R4 receipts and manifest.

At minimum:

- `V4_04_FULL_MARKET_CANDIDATE_RECEIPT_R4.json`
- `V4_04_INDEPENDENT_POSTCHECK_R4.json`
- `V4_04_MACHINE_VECTOR_COVERAGE_R4.json`
- `V4_04_WINDOW_TRACEABILITY_R4.json`
- `V4_04_REGISTRY_ARTIFACT_CONSISTENCY_R4.json`
- `V4_04_TEST_GATE_R4.json`
- `V4_04_FOCUSED_PYTEST_RUNTIME_R4.json`
- `V4_04_DETERMINISM_R4.json`
- `V4_04_FIELD_COMPLETENESS_R4.json`
- `V4_04_UNKNOWN_QUALITY_INVENTORY_R4.json`
- `V4_04_ROW_BOARD_COUNT_R4.json`
- `V4_04_INPUT_IDENTITY_R4.json`
- `V4_04_CONTRACT_PARAMETER_DIGEST_R4.json`
- `V4_04_CONSUMED_SOURCE_MANIFEST_R4.json`
- `V4_04_STAGE_CANDIDATE_MANIFEST_R4.json`

The R4 manifest must preserve and bind historical R1/R2/R3 artifact hashes.

---

# 7. Independent Postcheck R4

The R4 independent verifier must verify all previous requirements plus:

## minimum_liquidity independence

- source-evaluable prior20 window produces observed liquidity regardless of amount_ratio20 availability;
- false-UNKNOWN count is zero.

## enum UNKNOWN machine semantics

- Relative dependencies `"UNKNOWN"` propagate UNKNOWN;
- severe_extension risk `"UNKNOWN"` propagates UNKNOWN;
- branch-specific UNKNOWN vectors agree with production.

## drawdown inclusive boundaries

Independently evaluate exact -5% and -15% cases and compare:

- formal contract
- independent machine executor
- production function

All three must agree.

The postcheck must fail if any contract/machine/production divergence exists.

---

# 8. Regression Gate

Run:

```text
python -m pytest tests/v4_01 tests/v4_02 tests/v4_03 tests/v4_04 tests/v4_joint tests/v4_phase0 -q
```

Generate the receipt from actual runtime output.

Do not hardcode pass counts.

The existing repository-wide pytest collection issue remains separate unless this repair introduces a new cross-cutting failure.

---

# 9. External-Acceptance Candidate Gate

R4 may declare:

`V4_04_FULL_PASS_CANDIDATE_R4`

only if:

1. hidden `amount_ratio20` dependency is removed from minimum_liquidity;
2. no independently source-evaluable minimum_liquidity row is falsely UNKNOWN;
3. machine executor faithfully propagates enum `"UNKNOWN"` for required state dependencies;
4. severe_extension UNKNOWN does not become FALSE;
5. Relative UNKNOWN dependencies do not fall through to lower states;
6. branch-specific UNKNOWN vectors pass;
7. drawdown exact -5% = SHALLOW;
8. drawdown exact -15% = MODERATE;
9. production / machine / contract agree at those boundaries;
10. semantic machine-vector coverage receipt PASS;
11. independent postcheck PASS;
12. deterministic rerun PASS;
13. focused regression PASS;
14. R1/R2/R3 historical artifacts remain immutable;
15. V4-05 remains NOT_STARTED;
16. no V4-04 Accepted Head is created before independent external acceptance.

Otherwise terminal status:

`V4_04_BLOCKED_<EXACT_SCOPE>`

---

# 10. Forbidden Work

Do not:

- reopen V4-00 through V4-03;
- modify accepted upstream business semantics;
- modify TDX source roots;
- work on V4-08;
- add BaoStock turnover;
- add PREWATCH / Radar / Focus;
- add advanced structure;
- start V4-05;
- promote V4-04 Accepted Head;
- overwrite/delete R1/R2/R3 evidence.

---

# 11. Required Developer Closure Report

Record:

- starting HEAD;
- ending implementation HEAD;
- S01 disposition;
- S02 disposition;
- S03 disposition;
- minimum_liquidity false-UNKNOWN audit;
- enum UNKNOWN semantic vectors;
- drawdown exact-boundary vectors;
- machine semantic coverage;
- full-market row/board counts;
- R4 artifact SHA256;
- focused pytest runtime;
- independent postcheck;
- deterministic rerun;
- R1/R2/R3 preservation hashes;
- V4-05 state;
- exact terminal status.

Stop at R4 candidate production.

Await independent external acceptance.
