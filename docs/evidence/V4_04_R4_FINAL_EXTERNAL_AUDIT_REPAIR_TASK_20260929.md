# V4-04 R4 Final External-Audit Repair Task

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Date:** 2026-09-29  
**Task Type:** V4-04 final targeted repair before external acceptance

---

# 0. External Audit Status

External-audit baseline:

`ace30af36ce5440bb989312fce3e4385e8f8e6e6`

Current branch HEAD reviewed:

`1af58725b8c486904ed5149b6427739b9f2b051f`

R2 implementation commit:

`c833c8119293beb6f213241b5296ff0919399faa`

Current candidate:

`reports/v4_04/staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R2.jsonl.gz`

Current R2 artifact SHA256:

`89ed21dbdcc5abf377d2fda8299c444e7cd687fabb0eb5648ef5f12b8c4c0f12`

External audit result:

`V4_04_EXTERNAL_ACCEPTANCE_BLOCKED_R2_FINAL_REPAIR_REQUIRED`

This result does **not** reopen V4-00 through V4-03.

V4-05 remains:

`NOT_STARTED / NOT_AUTHORIZED`

Preserve all R1 and R2 artifacts and receipts as immutable historical evidence.

---

# 1. Findings Already Accepted

Do not rework these unless necessary for the targeted fixes below.

## PASS — Producer / Contract Identity

The V2 field registry now correctly distinguishes producer identity from semantic consumer identity for:

- `bias20_atr`
- `dist_high20_atr`
- `pos250`
- `ma10`
- `minimum_liquidity`

Registry/artifact consistency is materially repaired.

## PASS — MA10 Hidden MA20 Dependency

The undeclared MA20 dependency was removed.

A 10–19 actual-bar history can now produce MA10 while MA20 remains UNKNOWN.

## PASS — Profile Component Status Mapping

The V2 schema freezes:

- READY
- PARTIAL
- UNKNOWN_DATA
- DEGRADED
- NOT_IMPLEMENTED
- NOT_APPLICABLE
- PENDING_SOURCE

and the current mapping is implemented and tested.

## PASS — R2 Candidate Production / Determinism

The following remain accepted as valid evidence:

- 5,222 required-scope rows
- SH_MAIN 1702
- SZ_MAIN 1494
- CHINEXT 1408
- STAR 618
- deterministic R2 SHA
- accepted-input source binding
- no V4-05 execution
- no V4-04 Accepted Head promotion
- focused pytest runtime: 366 passed, 2 skipped, 0 failed

---

# 2. Blocking Finding F01 — Technical Window UNKNOWN Gap Is Still Silently Skipped

## 2.1 Root Problem

The V4-04 derived technical fields are built from actual-bar-only rows.

In `src/v4/profile_primitives.py`, the current MA10 logic checks only that the current endpoint exists, 10 actual bars exist, adjusted quality is READY, and qfq_close exists.

It does **not** reject an unexplained UNKNOWN trading-status gap inside the effective 10-actual-bar window.

Likewise `minimum_liquidity` checks the prior 20 actual amount rows but does not fail closed when an unexplained UNKNOWN status exists inside that technical window.

Therefore a sequence such as:

```text
ACTUAL
ACTUAL
UNKNOWN
ACTUAL
...
```

can currently be treated as if the UNKNOWN session did not exist, because `_daily()` supplies only `ACTUAL_TRADED` bars.

That violates the frozen `TECHNICAL_BAR_WINDOW_V1` semantics inherited from V4-03:

- confirmed suspension may be skipped by the technical actual-bar window;
- unexplained UNKNOWN / identity / adjustment gap must not be silently skipped.

The existing R2 test only proves this fail-closed behavior for `pos250`; it does not prove it for MA10 or prior20 liquidity.

## 2.2 Required Repair

Create one reusable technical-window status validator for V4-04 derived actual-bar windows.

For MA10:

- Window = current 10 verified actual QFQ bars.
- Confirmed `SUSPENDED` sessions inside the calendar span may be skipped.
- `UNKNOWN`, `IDENTITY_UNKNOWN`, `ADJUSTMENT_UNKNOWN`, or an unexplained missing status row inside the span must make MA10 UNKNOWN.

For `minimum_liquidity`:

- Window = prior 20 verified actual amount bars excluding T.
- Apply the same status rule.

Preserve `pos250` fail-closed behavior and refactor to the common helper if appropriate.

## 2.3 Mandatory Tests

For MA10 and minimum_liquidity, add:

1. uninterrupted actual bars → OBSERVED
2. one confirmed suspension → OBSERVED
3. consecutive confirmed suspensions → OBSERVED
4. one UNKNOWN interior gap → UNKNOWN
5. missing status row in expected calendar span → UNKNOWN
6. insufficient actual bars → UNKNOWN
7. current T suspended / missing actual endpoint → UNKNOWN

Assert:

- `window_start_trade_date`
- `window_end_trade_date`
- `calendar_span`
- `actual_count`
- `suspended_count`
- `window_identity`
- `field_window_mapping_id`

---

# 3. Blocking Finding F02 — Machine Rule Coverage Is Rule-Level, Not Required Vector/Branch-Level

## 3.1 Current Evidence

R2 successfully added:

- support for all currently declared machine operators;
- 18 registered machine-rule paths;
- `unsupported_operators = []`;
- `unexecuted_machine_rules = []`;
- rule-level execution coverage = 1.0.

However the previous external-audit task explicitly required positive, negative, threshold and UNKNOWN vectors for every rule family.

The current `tests/v4_04/test_machine_executor_r2.py` does not meet that requirement.

It currently provides generic operator examples, one UNKNOWN execution for every rule key, and a small closed-period example.

Existing `test_all_rule_branches.py` primarily tests the production Python rule functions, not the independent machine executor against every frozen machine branch.

Therefore `machine_rule_coverage = 1.0` currently means every rule key ran at least once, not that every machine branch and threshold was independently validated.

## 3.2 Required Repair

Add independent-machine golden vectors covering all meaningful branches and thresholds for:

- `TREND_STATE_V1.daily`
- `TREND_STATE_V1.closed_period`
- `POSITION_STATE_V1`
- `POSITION_STATE_V1.near_high`
- `POSITION_STATE_V1.drawdown`
- `MA_STRUCTURE_V1`
- `COMPRESSION_STATE_V1`
- `RELATIVE_STATE_V1`
- `AMOUNT_VOLUME_STATE_V1.ratio`
- `AMOUNT_VOLUME_STATE_V1.participation`
- `EXTENSION_RISK_V1`
- `EXTENSION_RISK_V1.severe`
- all five `V4_04_DERIVED_PRIMITIVES_V1` rules
- `MARKET_REGIME_V1.regime_ui`

Include exact boundary and UNKNOWN cases, not just nominal examples.

## 3.3 Required Receipt

Create:

`reports/v4_04/V4_04_MACHINE_VECTOR_COVERAGE_R3.json`

It must include:

```text
machine_rule_count
branch_count
branches_tested
threshold_vectors
unknown_vectors
rules_with_full_vector_coverage
rules_missing_vector_coverage
status
```

Acceptance requires:

```text
rules_missing_vector_coverage = []
status = PASS
```

---

# 4. Blocking Finding F03 — Independent Source Recompute Still Omits bias20_atr and dist_high20_atr

## 4.1 Problem

The previous repair task required independent source recomputation for:

- MA10
- minimum_liquidity
- pos250
- bias20_atr
- dist_high20_atr
- weekly trend inputs
- monthly trend inputs

The R2 postcheck reports source checks for MA10, minimum_liquidity, pos250, weekly and monthly, but not for `bias20_atr` or `dist_high20_atr`.

Machine-checking those values against candidate state evidence is not the same as independently reading accepted upstream sources and recomputing them.

## 4.2 Required Repair

For the deterministic source sample, independently recompute:

```text
bias20_atr = (accepted current QFQ close - accepted V4-03 MA20) / accepted V4-03 ATR20
```

and:

```text
dist_high20_atr = (accepted V4-03 prior_high20 - accepted current QFQ close) / accepted V4-03 ATR20
```

Do not use the candidate state's own `close`, `ma20`, `prior_high20`, or `atr20` as the oracle.

The next independent postcheck must report positive check counts for:

- ma10
- minimum_liquidity
- pos250
- bias20_atr
- dist_high20_atr
- weekly
- monthly

---

# 5. R3 Candidate Versioning

Do not overwrite R1 or R2.

Create:

`reports/v4_04/staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R3.jsonl.gz`

Create R3 versions of the relevant receipts, including:

- `V4_04_FULL_MARKET_CANDIDATE_RECEIPT_R3.json`
- `V4_04_INDEPENDENT_POSTCHECK_R3.json`
- `V4_04_MACHINE_VECTOR_COVERAGE_R3.json`
- `V4_04_WINDOW_TRACEABILITY_R3.json`
- `V4_04_REGISTRY_ARTIFACT_CONSISTENCY_R3.json`
- `V4_04_TEST_GATE_R3.json`
- `V4_04_FOCUSED_PYTEST_RUNTIME_R3.json`
- `V4_04_DETERMINISM_R3.json`
- `V4_04_FIELD_COMPLETENESS_R3.json`
- `V4_04_UNKNOWN_QUALITY_INVENTORY_R3.json`
- `V4_04_ROW_BOARD_COUNT_R3.json`
- `V4_04_INPUT_IDENTITY_R3.json`
- `V4_04_CONTRACT_PARAMETER_DIGEST_R3.json`
- `V4_04_CONSUMED_SOURCE_MANIFEST_R3.json`
- `V4_04_STAGE_CANDIDATE_MANIFEST_R3.json`

Preserve R1 and R2 SHA identities explicitly.

---

# 6. Test Gate

Run:

```text
python -m pytest tests/v4_01 tests/v4_02 tests/v4_03 tests/v4_04 tests/v4_joint tests/v4_phase0 -q
```

Generate the test receipt from the actual runtime result.

The repository-wide global pytest issue remains a separate audit item unless V4-04 introduces a new global failure.

---

# 7. Final Acceptance Gate

The R3 candidate may declare `V4_04_FULL_PASS_CANDIDATE_R3` only if:

1. MA10 rejects unexplained technical-window gaps;
2. minimum_liquidity rejects unexplained technical-window gaps;
3. confirmed suspensions remain valid technical-window skips;
4. technical-window metadata is correct;
5. all 18 machine rules have full required vector/branch coverage;
6. machine-vector receipt PASS;
7. bias20_atr has direct independent source recomputation;
8. dist_high20_atr has direct independent source recomputation;
9. independent postcheck PASS;
10. deterministic rerun PASS;
11. focused V4 regression PASS;
12. R1 and R2 remain immutable;
13. V4-05 remains NOT_STARTED;
14. no V4-04 Accepted Head is promoted before external acceptance.

Otherwise use:

`V4_04_BLOCKED_<EXACT_SCOPE>`

---

# 8. Forbidden Work

Do not:

- reopen V4-00 through V4-03;
- modify accepted upstream semantics;
- modify TDX source roots;
- work on V4-08 sector membership;
- add BaoStock turnover;
- implement PREWATCH / Radar / Focus;
- implement advanced structure;
- start V4-05;
- create or promote V4-04 Accepted Head;
- delete or overwrite R1/R2 evidence.

---

# 9. Required Developer Closure Report

Record:

- starting HEAD;
- ending implementation HEAD;
- F01 disposition;
- F02 disposition;
- F03 disposition;
- machine branch/vector coverage;
- technical-window gap vectors;
- direct source-recompute counts;
- full-market row/board counts;
- artifact SHA256;
- focused pytest result;
- independent postcheck result;
- determinism result;
- R1/R2 preservation hashes;
- V4-05 state;
- exact terminal status.

Stop at candidate production and await independent external acceptance.
