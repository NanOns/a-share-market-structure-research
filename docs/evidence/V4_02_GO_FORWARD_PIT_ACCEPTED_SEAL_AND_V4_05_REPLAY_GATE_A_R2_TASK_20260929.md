# V4-02 Go-Forward PIT Accepted Seal + V4-05 Replay Gate A R2 Task

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Date:** 2026-09-29  
**Starting HEAD:** `a54154e5e25b149fd35a09935435dcaa40ad8b8b`

---

# 0. Mandatory execution order

```text
Phase A: V4-02 Go-Forward PIT Amendment Accepted Seal
  ↓ only if Phase A PASS
Phase B: V4-05 Replay Gate A R2
```

If Phase A fails, V4-05 R2 must not start.

---

# Phase A — V4-02 Go-Forward PIT Amendment Accepted Seal

## A1. External acceptance authority

Add:

`docs/evidence/V4_02_GO_FORWARD_PIT_AMENDMENT_R3_FINAL_EXTERNAL_ACCEPTANCE_20260929.md`

Preserve exact external status:

`V4_02_GO_FORWARD_PIT_AMENDMENT_EXTERNAL_ACCEPTANCE_PASS_R3`

## A2. Do not replace the original V4-02 Accepted Head

The existing:

`data/v4/V4_02_ACCEPTED_HEAD.json`

continues to represent the accepted V4-02 foundation with cutoff `2026-09-24`.

Do not rewrite that historical foundation as PIT.

Create a separate accepted amendment head, suggested:

`data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json`

## A3. Accepted amendment head

At minimum bind:

```text
contract_id
stage = V4-02-GO-FORWARD-PIT-AMENDMENT
status = FULL_PASS_GO_FORWARD_SCOPE
external_acceptance = EXTERNALLY_ACCEPTED
first_accepted_target_trade_date = 2026-09-28
publication_mode = DELAYED_FORMAL_PUBLICATION
knowledge_lineage = PIT_OBSERVED_AFTER_FORMAL_PUBLICATION
```

Source identities:

```text
official_tdx_package_sha256 =
70b79898325ef6c67ea697f922d38fa3fd523e2ad62879b1b9fcb59fce52bf0c

candidate_path =
reports/v4_02/staging/V4_02_GO_FORWARD_ADJUSTED_T0_CANDIDATE_R3.jsonl.gz

candidate_sha256 =
7d87f5164c11f791ad24ad7c05139dca949f1c891523616ece907cd0f28fd8c8

logical_digest =
a5600d7f1416434bd54e778c2e7e847e309de1c21d71df5677f92daee1791400
```

Historical scope must remain:

`HISTORICAL_AS_RECORDED_ADJUSTED_PRICE = BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`

Bind the R3 external acceptance, manifest, independent postcheck, publication-time receipt, remote-LFS restore receipt, runtime test receipt, R2→R3 diff, frozen Sep-26 GBBQ source and official Sep-28 raw package.

## A4. Global Stage Accepted Head

Update:

`data/v4/V4_STAGE_ACCEPTED_HEAD.json`

without removing or replacing the original V4-02 foundation binding.

Add an explicit binding such as:

`v4_02_go_forward_pit_binding`

and explicit statuses:

```text
v4_02_go_forward_pit_status = FULL_PASS_GO_FORWARD_SCOPE
v4_02_go_forward_pit_external_acceptance = EXTERNALLY_ACCEPTED
v4_02_go_forward_first_target = 2026-09-28
historical_as_recorded_adjusted_price = BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE
v4_05_entry = AUTHORIZED_REPLAY_GATE_A_R2
```

Preserve:

`v4_08_sector_entry = BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION`

## A5. Promotion validator

Create an independent promotion validator and receipt, suggested:

`reports/v4_joint/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json`

Verify:

- external acceptance doc hash;
- candidate SHA;
- official package SHA / LFS identity;
- frozen GBBQ identity;
- R3 manifest/postcheck;
- original V4-02 Accepted Head unchanged;
- V4-04 Accepted Head unchanged;
- V4-08 block preserved;
- V4-05 R2 not started before promotion validation.

Promotion commit must be separate from V4-05 implementation.

---

# Phase B — V4-05 Replay Gate A R2

## B0. Governing semantics

REV2 §52B applies.

Do not seek one fake global historical PASS.

Replay A R2 must report capability-scoped outcomes.

At minimum separate:

```text
CURRENT_FORWARD_STOCK_CORE
HISTORICAL_AS_RECORDED_ADJUSTED_PRICE
WEEKLY_PERIOD
MONTHLY_PERIOD
MARKET_REFERENCE
MARKET_REGIME
```

Known prior state:

`HISTORICAL_AS_RECORDED_ADJUSTED_PRICE = BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`

This must not automatically block independent current/go-forward capabilities.

## B1. Accepted input chain

V4-05 R2 may consume only:

1. accepted V4-01/V4-02/V4-03/V4-04 foundation heads;
2. the newly promoted V4-02 go-forward PIT amendment head;
3. exact accepted contracts and parameter sets.

No unaccepted later-stage output may enter Replay A.

## B2. Formal replay target

`2026-09-28`

Publication semantics:

`PIT_OBSERVED_AFTER_FORMAL_PUBLICATION`

All replay logic must distinguish `target_trade_date` from `formal_publication_at`.

## B3. G01 — TDX source identity

Verify:

- accepted historical source chain;
- accepted Sep-28 official package;
- package SHA / LFS recoverability;
- no future raw rows;
- source publication/capture identity.

## B4. G02 — universe / identity

For current-forward scope verify:

- 5222 candidate identities;
- 5210 actual T0 bars;
- 12 no-target-bar states;
- new-listing fail-closed logic;
- `300114 → 302132` identity continuity;
- no future identity knowledge.

Historical full-PIT universe capability must retain its actual evidence level.

## B5. G03 — adjustment reproducibility

Split result explicitly:

```text
CURRENT_FORWARD_ADJUSTED_PRICE
HISTORICAL_AS_RECORDED_ADJUSTED_PRICE
```

Expected known structure:

```text
CURRENT_FORWARD = eligible for PASS
HISTORICAL_AS_RECORDED = BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE
```

Do not collapse them into one status.

## B6. G04 — Daily deterministic replay

From accepted source identities and exact contract:

- rebuild the Sep-28 current-coordinate daily inputs;
- run twice;
- compare logical digest;
- verify no future raw row;
- verify quality propagation.

## B7. G05 — Weekly / Monthly AS-OF

For Sep-28 current-forward scope:

- derive weekly/monthly under `PERIOD_ASOF_V1`;
- use frozen exchange calendar;
- CLOSED_ONLY must not consume incomplete future periods;
- Sep-28 Monday must not read later week sessions;
- Sep monthly state must not read future Sep month-end.

Generic Monday/mid-month temporal fixtures may prove algorithm semantics, but must not be mislabeled as historical AS_RECORDED production evidence.

Report WEEKLY_PERIOD and MONTHLY_PERIOD separately.

## B8. G06 — factor source time

Rebuild target-date V4-03 Pure-Core factors for `2026-09-28`.

Every factor/provider must expose and satisfy:

`max_source_trade_date <= target_trade_date`

and carry publication-relevant fields:

```text
source_asof
available_at / formal_publication_at
evidence_origin
model_namespace where applicable
```

Do not reuse Sep-24 factors as Sep-28 factors.

## B9. Market reference / market regime

Explicitly rebuild and bind target-date benchmark/index inputs through Sep-28.

Do not silently carry forward the Sep-24 market regime.

Report:

```text
MARKET_REFERENCE
MARKET_REGIME
```

as explicit capabilities.

## B10. G07 — Core Profile deterministic replay

Using accepted V4-04 contracts/parameters:

- build the Sep-28 full-market Core Profile;
- preserve UNKNOWN where upstream adjusted input is unavailable;
- do not drop the 27 affected identities merely to obtain a full PASS;
- run twice from identical inputs;
- require same logical digest.

Record full field/quality counts.

## B11. G08 — revision idempotency

For identical source identity, contract, parameter set, target date and publication identity, re-running must not create:

- duplicate publication;
- duplicate revision;
- output drift;
- duplicate event semantics.

Same source revision must be idempotent.

## B12. Temporal leakage tests

At minimum prove:

```text
T0 cannot read T+1 price
Monday weekly view cannot read later week sessions
monthly logic cannot read future month-end
future listing/delisting knowledge cannot alter T0 cross-section
later GBBQ revision cannot rewrite accepted T0 QFQ
provider available_at after formal publication cannot alter accepted Core
max_source_trade_date <= target_trade_date
```

Actual temporal leakage is a hard block for the affected capability.

## B13. Capability matrix

Create a machine-readable capability receipt.

Each row must include:

```text
capability_scope
status = FULL_PASS | DEGRADED_PASS | BLOCKED
affected_dates
affected_entities
affected_fields
reasons
evidence
```

Do not emit only a global PASS/FAIL.

Minimum scopes:

```text
CURRENT_FORWARD_STOCK_CORE
HISTORICAL_AS_RECORDED_ADJUSTED_PRICE
WEEKLY_PERIOD
MONTHLY_PERIOD
MARKET_REFERENCE
MARKET_REGIME
```

## B14. DATA_FACTOR_REPLAY_PASS alias

Only emit `DATA_FACTOR_REPLAY_PASS` with scope qualification.

Example if current-forward stock core fully passes while historical AS_RECORDED stays blocked:

```text
DATA_FACTOR_REPLAY_PASS
scope = CURRENT_FORWARD_STOCK_CORE
```

Never write an unqualified global `DATA_FACTOR_REPLAY_PASS`.

## B15. Replay case matrix

Required current-forward/semantic cases:

- Sep-28 current-forward target;
- Monday weekly AS-OF;
- incomplete-month negative;
- no-T0-bar security;
- unsupported adjustment security;
- code-change identity;
- synthetic valid new listing;
- synthetic unresolved new key;
- later GBBQ revision negative;
- future raw row negative.

Historical reconstructed cases remain diagnostic only.

## B16. Required evidence family

Suggested under `reports/v4_05/`:

```text
V4_05_R2_STAGE_ENTRY.md
V4_05_R2_ACCEPTED_INPUT_MANIFEST.json
V4_05_R2_REPLAY_CASE_MATRIX.json
V4_05_R2_SOURCE_IDENTITY.json
V4_05_R2_UNIVERSE_IDENTITY.json
V4_05_R2_ADJUSTMENT_REPRODUCIBILITY.json
V4_05_R2_DAILY_DETERMINISM.json
V4_05_R2_PERIOD_ASOF.json
V4_05_R2_FACTOR_SOURCE_TIME.json
V4_05_R2_MARKET_REFERENCE_REGIME.json
V4_05_R2_CORE_PROFILE_REPLAY.json
V4_05_R2_REVISION_IDEMPOTENCY.json
V4_05_R2_TEMPORAL_LEAKAGE.json
V4_05_R2_CAPABILITY_GATE.json
V4_05_R2_INDEPENDENT_POSTCHECK.json
V4_05_R2_STAGE_CANDIDATE_MANIFEST.json
V4_05_R2_CLOSURE.md
```

## B17. Independent postcheck

Must independently verify:

- accepted-head hashes;
- go-forward amendment binding;
- package / GBBQ identities;
- target universe;
- benchmark/index inputs;
- factor max source dates;
- period cutoffs;
- profile digest;
- UNKNOWN propagation;
- repeated replay digest;
- revision idempotency;
- temporal negative cases;
- capability-scope statuses;
- historical AS_RECORDED remains blocked;
- V4-08 block remains unchanged.

## B18. Runtime test gate

Run at minimum:

```text
python -m pytest -q
  tests/v4_01
  tests/v4_02
  tests/v4_03
  tests/v4_04
  tests/v4_05
  tests/v4_joint
  tests/v4_phase0
```

Add V4-05 R2-specific tests and create a hash-bound runtime receipt.

## B19. Candidate terminal status

If current-forward stock core fully passes:

`V4_05_DATA_FACTOR_REPLAY_PASS_CANDIDATE_R2`

must still carry exact capability scope.

Historical AS_RECORDED may simultaneously remain blocked; this is valid under §52B.

If actual temporal leakage appears:

`V4_05_BLOCKED_TEMPORAL_LEAKAGE_<SCOPE>`

If an accepted upstream source defect appears:

`V4_05_BLOCKED_UPSTREAM_DEFECT_<SCOPE>`

## B20. Forbidden work

Do not:

- rewrite historical V4-02 data as PIT;
- modify accepted V4-04 thresholds;
- consume future prices;
- use BaoStock QFQ as Core fallback;
- use later GBBQ to rewrite Sep-28 T0;
- weaken the V4-08 sector PIT block;
- start V4-06/07/08;
- start PREWATCH/state/structure/focus;
- overwrite prior candidate/evidence history;
- write into the user's TDX root.

## B21. Stop point

Stop after producing the V4-05 R2 candidate and evidence.

Do not promote V4-05 in the same task.

Await independent external acceptance.

If externally accepted, the next task card will handle:

```text
V4-05 Accepted Head Promotion
+
next authorized stage entry
```

with V4-06 optional and V4-07 authorization determined from the governing contract and current project plan.
