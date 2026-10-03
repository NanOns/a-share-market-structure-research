# R17A｜Cross-stage Accepted-Chain / Historical Validator Repair｜2026-10-03

## 0. Baseline

Use current remote HEAD as the only execution baseline:

```text
f12315bf8e3142aa44e9068c5895004c35c4e23c
```

Read first:

```text
V4_R16R1_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md
V4_R17A_CROSS_STAGE_ACCEPTED_CHAIN_HISTORICAL_VALIDATOR_REPAIR_TASK_20261003.md
V4_NEXT_ROUND_EXECUTION_MASTER_R17_20261003.md
```

This is a narrow governance / validator maintenance card.

It must not change V4-08/V4-09/V4-10/V4-11/V4-12/V4-13 business algorithms.

## 1. Goal

Close:

```text
R16R1-AUD-DM01-STAGE-BINDING
R16R1-AUD-HISTORICAL-STAGE-GATES
```

and restore a meaningful expanded regression before V4-13 Stage Head promotion.

## 2. Historical Moving-Head Rule

A historical Accepted Head may contain a promotion-time binding whose path is a moving namespace such as:

```text
data/v4/V4_STAGE_ACCEPTED_HEAD.json
```

If exact SHA/bytes no longer match the current moving file, validators must NOT:

- compare the historical ref to current bytes;
- rewrite the historical accepted object to current SHA;
- silently accept any same-path object;
- directory-scan for a convenient file.

The resolver must bind the historical ref to an explicit immutable promotion-time archive with exact:

```text
path
sha256
bytes
accepted_stage_range
```

## 3. DM01 / Data Head Repair

Audit:

```text
src/workbench_analysis/dm01_accepted_chain_v1.py
data/v4/V4_DATA_ACCEPTED_HEAD.json
```

The current V4_DATA_ACCEPTED_HEAD must remain byte-identical.

If its historical `stage_head` binding points to an earlier SHA of the mutable Stage namespace:

1. recover the exact historical Stage Head bytes from repository history / previously sealed evidence;
2. materialize or register an immutable archive if one is not already present;
3. add a deterministic explicit resolver from the historical binding to that exact archive;
4. verify hash + bytes + semantic accepted stage range;
5. fail closed if no exact archive is registered.

Do not use current Stage Head as a substitute.

## 4. V4-10 Historical Parent Binding

`data/v4/V4_10_ACCEPTED_HEAD.json` already has historical parent archive information.

Validation must use the exact historical parent archive for promotion-time checks instead of expecting current:

```text
data/v4/V4_STAGE_ACCEPTED_HEAD.json
```

to still have the old SHA.

Audit and repair relevant scripts/readers, including the V4-10 promotion validators/tests.

Historical Accepted Head bytes remain immutable.

## 5. Obsolete Historical Stage Tests

### V4-09

The historical test that asserts V4-09 Accepted Head does not exist must not be executed as a current-state truth after V4-09 has been accepted.

Replace with either:

```text
archived pre-promotion baseline integrity test
```

or:

```text
explicit historical fixture / commit-bound validator
```

and add a separate current-state test proving the actually accepted V4-09 head.

### V4-12 R11 / R12

Tests designed as local pre-promotion gates must not keep asserting that later current accepted state equals an old local candidate state.

Preserve computational tests for:

- algorithm vectors;
- persisted snapshot integrity;
- transition identity;
- multi-anchor semantics;
- no duplicate episode;
- previous-session behavior.

Move only obsolete stage-current assertions into archived historical checks.

Do not delete useful computational tests.

## 6. Required Negative Tests

At minimum:

```text
historical moving path + current different SHA + exact registered archive
→ PASS

historical moving path + no archive
→ REJECT

archive path correct + hash wrong
→ REJECT

archive hash correct + semantic accepted_stage_range wrong
→ REJECT

historical accepted object mutated to current SHA
→ REJECT

current Stage Head used as historical substitute
→ REJECT
```

## 7. Regression Goal

Run the previously expanded R16R1 scope again.

Target:

```text
old 22 baseline failures
→ 0 unexplained failures
```

If an assertion is intentionally historical-only, replace it by an explicit archived historical test; do not merely deselect it.

Broad deselection is forbidden.

## 8. Protected State

Must remain byte-identical:

```text
AGENTS.md
data/v4/V4_DATA_ACCEPTED_HEAD.json
data/v4/V4_12_ACCEPTED_HEAD.json
data/v4/V4_STAGE_ACCEPTED_HEAD.json
```

Also preserve all V4-08 to V4-13 algorithm semantics.

R17A does not promote any stage.

## 9. Forbidden

```text
V4_13_ACCEPTED_HEAD creation
Stage Head advance
Data Head advance
V4-14 execution
Production
Shadow
Focus
Radar/Cohort/Settlement
algorithm threshold changes
raw/provider fallback
historical accepted-head rewriting
```

## 10. Completion State

Only after clean detached validation:

```text
R17A_CROSS_STAGE_GOVERNANCE_REPAIR = PASS

DM01_HISTORICAL_STAGE_BINDING = PASS
HISTORICAL_STAGE_VALIDATOR_MAINTENANCE = PASS
EXPANDED_CURRENT_REGRESSION = PASS

NEXT = R17B_V4_13_ACCEPTED_HEAD_PROMOTION
```

Continue directly to R17B in the same Codex round.
