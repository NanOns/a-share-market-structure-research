# V4-04 Accepted-Head Promotion + V4-05 Replay Gate A Entry Task R1

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Date:** 2026-09-29  
**Task Type:** Accepted-head promotion followed by V4-05 Replay Gate A entry

---

# 0. Starting Authority

Current reviewed HEAD:

`b7dc52d94d7bd81b8f55e1009d3eb271689f0943`

Accepted V4-04 implementation commit:

`044dc637f90b35c6097bb800b1d4d755fdfb792c`

V4-04 external acceptance:

`V4_04_EXTERNAL_ACCEPTANCE_PASS_R4`

Accepted V4-04 artifact:

`reports/v4_04/staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R4.jsonl.gz`

Accepted SHA256:

`b1ce4e4cb227f7cc25271005debfc9fc7bfaf61d39e20c96592921dd361e3b52`

Current global Accepted Head Git blob:

`data/v4/V4_STAGE_ACCEPTED_HEAD.json`

Git blob SHA:

`76025c6668d42043261766d2618fed439be30760`

Current V4-04 R4 manifest Git blob:

`reports/v4_04/V4_04_STAGE_CANDIDATE_MANIFEST_R4.json`

Git blob SHA:

`091515764ef4976cb8639297f12dc2cfafb7d3b6`

Authority:

- `AGENTS.md`
- `A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md`
- accepted V4-00 through V4-03 heads
- `V4_04_FINAL_EXTERNAL_ACCEPTANCE_R1_20260929.md`
- R4 candidate manifest and all R4 receipts

---

# 1. Mandatory Execution Order

This task has two phases.

They must be executed in order:

```text
Phase A
V4-04 Accepted-Head Promotion

        ↓ only if Phase A PASS

Phase B
V4-05 Replay Gate A Entry / Execution
```

If Phase A fails, Phase B is forbidden.

Do not mix promotion writes and Replay Gate A business outputs into one atomic publication.

---

# 2. Phase A — Publish V4-04 Final External Acceptance Evidence

Add the externally accepted audit record to repository evidence:

```text
docs/evidence/V4_04_FINAL_EXTERNAL_ACCEPTANCE_R1_20260929.md
```

The file must preserve the external acceptance result exactly:

```text
V4_04_EXTERNAL_ACCEPTANCE_PASS_R4
FULL_PASS_REQUIRED_SCOPE
EXTERNALLY_ACCEPTED
```

It must bind:

- implementation commit `044dc637...`
- evidence-seal HEAD `b7dc52d...`
- R4 artifact SHA256
- R4 manifest
- R4 independent postcheck
- R4 machine semantic coverage
- R4 deterministic receipt
- R4 focused test gate

Do not rewrite business artifacts during this step.

---

# 3. Phase A — Create V4-04 Accepted Head

Create:

```text
data/v4/V4_04_ACCEPTED_HEAD.json
```

Minimum required fields:

```text
contract_id
stage
status
external_acceptance
accepted_at_date
source_cutoff
accepted_artifact
accepted_manifest
implementation_commit
external_acceptance_evidence
contract_bindings
upstream_identities
capabilities
historical_candidate_hashes
stage_record
next_stage
```

Required values:

```text
stage = V4-04

status = FULL_PASS_REQUIRED_SCOPE

external_acceptance = EXTERNALLY_ACCEPTED

source_cutoff = 2026-09-24

implementation_commit =
044dc637f90b35c6097bb800b1d4d755fdfb792c
```

Accepted artifact must bind:

```text
path =
reports/v4_04/staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R4.jsonl.gz

sha256 =
b1ce4e4cb227f7cc25271005debfc9fc7bfaf61d39e20c96592921dd361e3b52
```

Accepted manifest must bind the exact R4 manifest.

Do not promote R1/R2/R3.

They remain immutable historical candidates.

---

# 4. Phase A — Capability Declaration

At minimum record:

```text
STOCK_CORE_FULL_MARKET_PROFILE = PASS

PURE_CORE_TREND = PASS
PURE_CORE_POSITION = PASS
PURE_CORE_MA_STRUCTURE = PASS
PURE_CORE_RELATIVE = PASS
PURE_CORE_COMPRESSION = PASS
PURE_CORE_PARTICIPATION = PASS
PURE_CORE_EXTENSION = PASS
MARKET_REGIME_UI = PASS
TECHNICAL_WINDOW_TRACEABILITY = PASS
```

Explicitly record excluded / not-yet-owned capabilities:

```text
TURNOVER_CONTEXT = NOT_IN_V4_04_SCOPE

STOCK_BASE_SEED = NOT_IN_V4_04_SCOPE

SECTOR_ROTATION_PRODUCTION = NOT_IN_V4_04_SCOPE

STOCK_PREWATCH = NOT_IN_V4_04_SCOPE

ADVANCED_STRUCTURE = NOT_IN_V4_04_SCOPE

DATA_FACTOR_REPLAY_PASS = PENDING_V4_05
```

Do not mislabel later-stage capabilities as passed.

---

# 5. Phase A — Update Global Accepted Head

Update:

```text
data/v4/V4_STAGE_ACCEPTED_HEAD.json
```

Preserve all existing accepted V4-00 through V4-03 bindings.

Add an exact V4-04 binding:

```text
v4_04_binding:
  path
  sha256
  byte_count
```

Add / update:

```text
v4_04_status = FULL_PASS_REQUIRED_SCOPE

v4_04_external_acceptance = EXTERNALLY_ACCEPTED

v4_05_entry = AUTHORIZED_REPLAY_GATE_A
```

Preserve:

```text
v4_08_sector_entry =
BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION
```

Do not convert global stage status into a misleading “all V4 passed” state.

A suitable global status may remain foundation-oriented or be versioned to a state meaning:

```text
V4_00_TO_V4_04_ACCEPTED
```

but the meaning must be explicit and must not imply V4-05+ acceptance.

---

# 6. Phase A — Promotion Validator

Create a read-only validator for the promotion.

It must prove:

1. V4-04 accepted artifact hash exact;
2. R4 manifest hash exact;
3. R4 evidence receipt hashes exact;
4. external acceptance evidence exists and is hash-bound;
5. V4-01/02/03 accepted heads unchanged;
6. current global head points uniquely to the new V4-04 accepted head;
7. no V4-04 required capability remains PENDING;
8. V4-08 sector block remains preserved;
9. no V4-05 business output was written before promotion validation;
10. no TDX source write occurred;
11. R1/R2/R3/R4 candidate history remains immutable.

Create:

```text
reports/v4_joint/V4_04_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json
```

Required result:

`PASS`

---

# 7. Promotion Commit Boundary

Promotion should have its own commit.

Recommended commit purpose:

```text
[V4-04] Promote externally accepted R4 core profile
```

The promotion commit must contain only:

- final external acceptance evidence;
- V4-04 accepted head;
- global accepted-head update;
- promotion validator / receipt;
- minimal governance evidence.

It must not contain V4-05 replay implementation.

After the promotion commit:

```text
V4-04 = formally accepted
V4-05 = authorized to start
```

---

# 8. Phase B — V4-05 Replay Gate A Authority

V4-05 stage name:

`Replay Gate A — Data / Factor`

Contract position:

```text
Canonical Facts
+ Factors
+ Core Daily Profile
completed
```

Required pass alias:

`DATA_FACTOR_REPLAY_PASS`

This is an engineering/PIT/replay correctness gate.

It is **not** a stock-selection-performance gate and must not use future price performance as acceptance evidence.

---

# 9. V4-05 Required Input Chain

V4-05 must resolve from accepted heads only.

Minimum authority:

```text
V4_STAGE_ACCEPTED_HEAD
    ↓
V4-01 accepted history/universe
V4-02 accepted canonical Daily / formal periods / status
V4-03 accepted factors / market primitives
V4-04 accepted Full-Market Core Profile
```

Do not consume:

- unaccepted staging alternatives;
- future V4-06 turnover;
- V4-07 Seed;
- V4-08 Sector/Rotation;
- PREWATCH;
- Focus;
- Forward outcomes.

---

# 10. V4-05 Mandatory Gate Matrix

Replay Gate A must independently verify:

## G01 — TDX Source Identity

Prove that replay uses the accepted TDX archive / accepted local source identity.

Detect:

- changed archive;
- stale archive;
- unaccepted source substitution;
- silent source correction.

## G02 — Historical Universe

For target date T:

- later-listed securities cannot appear early;
- delisted securities cannot be removed using future knowledge;
- code/lifecycle identity must use accepted PIT semantics;
- historical universe identity must be explicit.

## G03 — Adjustment Reproducibility

For sampled and required historical dates:

- adjustment identity reproducible;
- corporate-action effective time respected;
- no future corporate-action knowledge leaks into AS_RECORDED;
- accepted raw/adjusted coordinate identities agree with V4-02.

## G04 — Daily Deterministic Replay

Freeze:

```text
source identity
code commit
contract
parameter set
trade_date
```

Two runs must yield the same logical digest.

Any mismatch:

`NON_DETERMINISTIC_OUTPUT`

and affected capability is BLOCKED.

## G05 — Weekly / Monthly AS-OF

Must automatically prove at minimum:

```text
Monday T0 cannot read future Friday close
mid-month T0 cannot read future month-end
only formally available CLOSED_ONLY periods may be consumed
```

## G06 — Factor max_source_trade_date

Every replayed factor/provider must expose or resolve:

```text
max_source_trade_date
source_asof
evidence_origin
```

Required:

```text
max_source_trade_date <= target_trade_date
```

Any actual violation is a temporal-leakage blocker for affected capability.

## G07 — Core Profile Deterministic Replay

Rebuild V4-04 Core Profile at frozen historical target dates using only facts available at T.

Check:

- field values;
- state values;
- UNKNOWN propagation;
- window lineage;
- source identity;
- contract identity;
- logical digest.

## G08 — Revision Idempotency

Replaying the same accepted logical publication / revision must not create a different logical result.

Prove:

```text
same logical input identity
→ same logical digest
```

and no duplicate logical revision.

---

# 11. Temporal Leakage Gate

Implement explicit automated negative tests.

T0 output must not contain or depend on:

```text
T+1 price
future membership
future Focus outcome
future state
future publication
future corporate-action availability
future weekly close
future monthly close
```

At minimum test:

### Weekly AS-OF
Monday cannot read Friday.

### Monthly AS-OF
Mid-month cannot read month-end.

### Historical Universe
Later listing / later delisting knowledge cannot alter earlier cross-section improperly.

### Corporate Action
Future adjustment availability cannot change an AS_RECORDED replay.

### Supplemental Enrichment
A provider with:

```text
provider_asof > core cutoff
```

must not alter accepted Pure-Core state.

Even though BaoStock is outside V4-05 Core input, this negative test should prove the Core boundary.

---

# 12. Capability-Scoped Result

Per §52B every Replay Gate A result must be:

```text
status:
  FULL_PASS
  DEGRADED_PASS
  BLOCKED

capability_scope

affected_dates
affected_entities
affected_fields
reasons
evidence
```

Do not emit only one global PASS if different capabilities have different evidence quality.

At minimum distinguish:

```text
STOCK_CORE
MARKET_REFERENCE
MARKET_REGIME
WEEKLY_PERIOD
MONTHLY_PERIOD
HISTORICAL_ADJUSTED_PRICE
```

V4-08 historical Sector PIT remains separately blocked and cannot be silently certified by V4-05.

---

# 13. Replay-Date Coverage

Do not validate only the final cutoff `2026-09-24`.

Create a frozen replay date matrix spanning materially different conditions.

At minimum include cases representing:

- recent normal trading date;
- Monday weekly-ASOF boundary;
- mid-month monthly-ASOF boundary;
- security with short history / recent listing;
- confirmed suspension / resumption;
- corporate-action / adjustment-sensitive sample;
- identity/code-change-sensitive sample if available in accepted history;
- required-board coverage.

Record the exact date/entity selection rule before evaluating outputs.

Do not choose dates after seeing which ones pass.

If a full historical replay is operationally feasible within the accepted runtime budget, prefer full covered-history execution and retain the frozen edge-case matrix as independent targeted evidence.

---

# 14. V4-05 Replay Output Contract

Create a V4-05 replay artifact/receipt family under versioned paths such as:

```text
reports/v4_05/
```

At minimum generate:

```text
V4_05_STAGE_ENTRY_R1.md

V4_05_ACCEPTED_INPUT_MANIFEST_R1.json

V4_05_REPLAY_DATE_MATRIX_R1.json

V4_05_SOURCE_IDENTITY_R1.json

V4_05_UNIVERSE_PIT_REPLAY_R1.json

V4_05_ADJUSTMENT_REPRODUCIBILITY_R1.json

V4_05_DAILY_DETERMINISM_R1.json

V4_05_PERIOD_ASOF_R1.json

V4_05_FACTOR_MAX_SOURCE_DATE_R1.json

V4_05_CORE_PROFILE_REPLAY_R1.json

V4_05_REVISION_IDEMPOTENCY_R1.json

V4_05_TEMPORAL_LEAKAGE_R1.json

V4_05_CAPABILITY_GATE_R1.json

V4_05_INDEPENDENT_POSTCHECK_R1.json

V4_05_STAGE_CANDIDATE_MANIFEST_R1.json
```

Names may be versioned differently if repo conventions require it, but all semantic evidence must remain independently identifiable.

---

# 15. Independent V4-05 Postcheck

The independent postcheck must not simply call the production Replay Gate and trust its PASS result.

It must independently verify at minimum:

- accepted-head input identities;
- source hashes;
- date matrix;
- max_source_trade_date rule;
- weekly/monthly AS-OF;
- deterministic logical digests;
- Core Profile replay equality;
- capability status;
- no unaccepted dependency;
- no future-data dependency.

If independent postcheck disagrees with production gate:

`V4_05_BLOCKED_EXTERNAL_POSTCHECK_DIVERGENCE`

---

# 16. Test Gate

Run the existing accepted regression plus new V4-05 tests.

At minimum:

```text
python -m pytest
  tests/v4_01
  tests/v4_02
  tests/v4_03
  tests/v4_04
  tests/v4_05
  tests/v4_joint
  tests/v4_phase0
  -q
```

Generate runtime receipts from actual execution.

Do not hardcode pass counts.

The separate repository-wide M14 collection problem remains a cross-cutting audit item unless V4-05 changes its status.

---

# 17. V4-05 Acceptance Semantics

A stage candidate may declare:

`V4_05_DATA_FACTOR_REPLAY_PASS_CANDIDATE`

only if required Replay Gate A checks pass for their declared capability scope.

If some scope is degraded:

```text
V4_05_DEGRADED_PASS_<SCOPE>
```

must state exactly what is allowed and what remains blocked.

If an actual temporal leakage is found:

```text
V4_05_BLOCKED_TEMPORAL_LEAKAGE_<SCOPE>
```

and affected successors may not proceed.

Do not convert a scope failure into a global waiver.

---

# 18. Successor Authorization

V4-05 does not automatically authorize every future V4 stage.

After independent external acceptance of V4-05:

- V4-06 remains optional Supplemental Enrichment;
- V4-07 Stock Base Seed may enter according to §78;
- V4-08 remains subject to its own accepted PIT-membership prerequisite;
- later PREWATCH / State / Structure / Radar work remains stage-gated.

No later business logic should be implemented in this task.

---

# 19. Forbidden Work

During this task do not:

- alter accepted V4-01/02/03 business artifacts;
- rebuild accepted V4-04 business rules unless Replay A exposes a genuine defect;
- change V4-04 thresholds to make replay pass;
- use future prices as replay acceptance criteria;
- start V4-06 business enrichment;
- start V4-07 Seed;
- start V4-08 Sector/Rotation;
- start PREWATCH;
- start State/Structure/Focus;
- weaken the existing V4-08 PIT-membership block;
- modify TDX source roots;
- delete historical candidate evidence.

If V4-05 discovers a predecessor defect, stop and issue:

```text
V4_05_BLOCKED_UPSTREAM_DEFECT_<SCOPE>
```

with exact evidence.

Do not silently patch predecessor semantics inside Replay Gate A.

---

# 20. Required Closure Report

At completion record:

## Promotion
- starting HEAD;
- promotion commit;
- V4-04 Accepted Head SHA;
- updated global Accepted Head SHA;
- external acceptance evidence SHA;
- promotion validator result.

## Replay Gate A
- V4-05 implementation commit;
- accepted input manifest;
- replay-date matrix;
- source-identity result;
- universe PIT result;
- adjustment reproducibility result;
- daily determinism result;
- weekly/monthly AS-OF result;
- factor max-source-date result;
- Core Profile replay result;
- revision-idempotency result;
- temporal-leakage result;
- capability-scoped gate result;
- focused runtime test result;
- independent postcheck result;
- exact terminal status.

Stop at the V4-05 candidate.

Await independent external acceptance before successor-stage implementation.
