# V4-05 Replay Gate A R3
## Forced Target-Date Materialization and Completion Task

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Date:** 2026-09-29  
**Starting HEAD:** `7943596a800e9ac9234885b0dad77b06c87e1e25`

---

# 0. Current Authority

Already accepted:

```text
V4-00..V4-04 foundation
V4-02 Go-Forward PIT Amendment
first accepted target = 2026-09-28
publication mode = DELAYED_FORMAL_PUBLICATION
```

R2 accepted partial capability:

`CURRENT_FORWARD_ADJUSTED_PRICE = FULL_PASS`

R2 did **not** finish Replay Gate A.

---

# 1. Hard Execution Rule

The following is **not** a valid R3 terminal blocker by itself:

`TARGET_DATE_ACCEPTED_INPUT_SERIES_NOT_MATERIALIZED`

R3's purpose is precisely to materialize those inputs.

R3 may stop only when it demonstrates a specific non-repairable-within-stage defect such as:

```text
accepted source hash mismatch
accepted contract inconsistency
required authoritative calendar unavailable
identity ambiguity
actual temporal leakage
non-deterministic output
required factor dependency lacks accepted provenance
```

Each blocker must identify:

```text
exact source
exact field/capability
affected entities/dates
why the artifact cannot be built without violating contract
```

---

# 2. Do Not Modify Accepted Semantics

Do not change V4-02, V4-03 or V4-04 formulas/thresholds to make Replay pass.

Reuse accepted contracts and libraries.

Old Sep-24 scripts may be refactored or wrapped only to parameterize:

```text
target date
input artifact paths
publication identity
current-coordinate lineage
```

Do not rewrite old accepted artifacts.

Prefer new V4-05-specific replay adapters.

---

# 3. Build R3 Target-Date Daily History

The existing R3 accepted amendment artifact contains current T0 rows and lookback digests, but G05–G07 need actual target-coordinate history.

Build an immutable replay-only daily history for the Sep-28 target.

Source:

```text
official TDX Sep-28 package SHA =
70b79898325ef6c67ea697f922d38fa3fd523e2ad62879b1b9fcb59fce52bf0c

frozen GBBQ =
sha256-775d82c58b5b46ec1d21478f86ba8ef90302691982e68d5c4cfcd51fddda666e
```

For every required security, materialize sufficient historical bars for all accepted V4-03/V4-04 windows.

Prefer the full accepted research range if practical; otherwise prove that the retained window covers every required formula plus prior-state dependency.

Every row must preserve:

```text
security_id
source_security_key
board_scope
trade_date
raw OHLC
T0-coordinate QFQ OHLC
volume
amount
adjusted_quality
blocking reason
raw package identity
GBBQ snapshot identity
max_source_trade_date
coordinate_basis = T0_CURRENT_COORDINATE
historical_as_recorded_claim = false
formal_publication_at
```

Historical lookback rows are inputs to the T0 calculation; they are not historical PIT publications.

---

# 4. T0 Trading-Status Rule

Do not infer:

`NO_BAR = SUSPENDED`

For the 12 Sep-28 identities without a target raw bar:

- use an accepted/authoritative trading-status source if available;
- otherwise preserve `UNKNOWN_NO_T0_BAR`.

Do not manufacture zero returns or zero OHLC.

The profile must keep the identities and propagate UNKNOWN.

---

# 5. Go-Forward Calendar Extension

The accepted Sep-24 calendar cannot silently be extended using future price observations.

Create a hash-bound go-forward calendar input sufficient for Sep-28 period classification.

Preferred authority:

- existing formally accepted exchange-calendar mechanism if it already supports future scheduled sessions;
- otherwise official SSE/SZSE trading-calendar / holiday schedule under a versioned source receipt.

Required metadata:

```text
source URL / authority
observed_at
schedule effective range
SHA/source digest
target_date
publication availability
```

No future price data is allowed merely to decide whether Sep-28 week/month was complete.

---

# 6. G05 — Weekly / Monthly AS-OF

Using the R3 T0-current-coordinate daily history and bound calendar:

materialize:

```text
WEEKLY RAW
WEEKLY QFQ
MONTHLY RAW
MONTHLY QFQ
```

under accepted `PERIOD_ASOF_V1`.

Required fields include:

```text
period_start_date
period_end_date
period_last_session
asof_trade_date
period_view
period_status
max_source_trade_date
source_daily_digest
calendar_count
actual_count
suspended_count
unknown_count
adjusted_quality
```

For V4-04 trend consumption:

`CLOSED_ONLY` only.

Current incomplete week/month may exist as `AS_OF_PARTIAL` but must not leak into CLOSED_ONLY trend.

Mandatory negatives:

- Monday cannot read later week sessions;
- mid-month cannot read month-end;
- deletion of post-T0 daily rows leaves T0 period result unchanged.

Report WEEKLY and MONTHLY separately.

---

# 7. G06 — Sep-28 Pure-Core Factor Replay

Rebuild Sep-28 factor outputs using accepted V4-03 contracts.

Do not reuse Sep-24 factor rows as Sep-28 rows.

For every factor/provider record:

```text
target_trade_date
max_source_trade_date
source_asof
available_at / formal_publication_at
evidence_origin
contract_id
parameter_set_id
input/window identity
quality_state
unknown_reason
```

Require:

`max_source_trade_date <= 20260928`

---

# 8. Historical Bootstrap / Prior-RPS Provenance

Any Sep-28 factor requiring:

- prior RPS;
- historical start-universe;
- historical cross-sectional membership;
- other pre-first-forward state

must explicitly classify its provenance.

Allowed:

1. dependency already externally accepted for this exact current-forward use; or
2. field becomes `UNKNOWN` with explicit bootstrap reason.

Forbidden:

`retrospective reconstructed history → silently PIT_OBSERVED`

Suggested explicit reason:

`BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY`

Do not modify the formula to avoid the dependency.

Capability outcome may legitimately become scoped `DEGRADED_PASS` if contracts allow it.

---

# 9. Market Reference

Rebuild the accepted V4-03 market-relative reference for Sep-28.

Use the accepted algorithm:

`MARKET_RELATIVE_REFERENCE_V1`

Bind:

```text
start_session
end_session
start_universe_snapshot_id
evaluable_set_identity
adjustment_basis_id
input_source_digest
coverage
missing_count
max_source_trade_date
```

Do not substitute an index price for the formal equal-weight research reference unless the accepted contract says so.

Any historical universe dependency must follow §8 above.

---

# 10. Market Regime

Rebuild Sep-28 accepted market-regime primitives under:

`MARKET_REGIME_V1_PRIMITIVES`

Use the accepted contracts/errata.

Required source identities must include the Sep-28 target facts.

Do not carry forward Sep-24 regime.

If a required primitive is unknown, propagate field-local UNKNOWN.

Report:

```text
MARKET_REFERENCE
MARKET_REGIME
```

separately in the capability matrix.

---

# 11. G07 — Full-Market Sep-28 Core Profile

Build the Sep-28 full-market Core Profile from:

- R3 current-coordinate Daily history;
- R3 periods;
- R3 factors;
- R3 market reference/regime;
- accepted V4-04 contracts and parameter set.

Do not change V4-04 algorithm semantics.

Keep all target identities.

At minimum preserve the known 27 upstream adjustment-unavailable identities as UNKNOWN where dependent fields require QFQ.

Do not drop incomplete rows to improve completeness.

Record:

```text
total rows
board counts
COMPLETE
PARTIAL_UNKNOWN
UNKNOWN by field/reason
source digest
contract digest
max_source_trade_date
formal_publication_at
logical digest
```

---

# 12. V4-04 Builder Hard-Cutoff Rule

Existing accepted V4-04 scripts are hard-coded to Sep-24.

Do not edit the accepted historical output in place.

Create a V4-05 replay adapter / parameterized build path that calls the same accepted library functions while binding:

```text
TARGET = 2026-09-28
R3 replay input paths
accepted V4-04 contract hashes
```

Any semantic divergence from the accepted V4-04 algorithm is a blocker.

---

# 13. G07 Determinism

Run the full Sep-28 Core Profile build twice.

Require:

```text
same row set
same logical digest
same quality counts
same output digest
```

---

# 14. G08 — Revision Idempotency

Create a replay publication identity for Sep-28.

For identical:

```text
target date
source package SHA
GBBQ SHA
calendar identity
contract hashes
parameter set
formal publication identity
```

re-run twice.

Require:

```text
no new revision
no duplicate publication
no output drift
same logical digest
```

Then create one controlled source-revision fixture and verify that a genuine changed source identity creates a new revision rather than overwriting the old one.

Do not mutate accepted history.

---

# 15. Temporal Leakage Suite

Mandatory executable negatives:

```text
A. T+1 raw price injected -> must not affect T0
B. later week sessions removed/added -> Monday CLOSED_ONLY unchanged
C. month-end future rows -> Sep-28 monthly CLOSED_ONLY unchanged
D. future listing/delisting metadata -> cannot alter T0 universe
E. later GBBQ <=T0 event -> cannot rewrite accepted T0 input
F. provider available_at > formal_publication_at -> cannot enter publication
G. max_source_trade_date > target -> hard block
H. future market-regime input -> hard block
```

All cases require machine-readable receipts.

---

# 16. Capability Matrix

Create one machine-readable matrix with at least:

```text
CURRENT_FORWARD_ADJUSTED_PRICE
WEEKLY_PERIOD
MONTHLY_PERIOD
PURE_CORE_FACTORS
MARKET_REFERENCE
MARKET_REGIME
CURRENT_FORWARD_STOCK_CORE
HISTORICAL_AS_RECORDED_ADJUSTED_PRICE
```

Each row:

```text
capability_scope
status = FULL_PASS | DEGRADED_PASS | BLOCKED
affected_dates
affected_entities
affected_fields
reasons
evidence
```

Historical AS_RECORDED remains blocked unless genuinely new evidence exists.

---

# 17. Replay Alias

Only emit:

`DATA_FACTOR_REPLAY_PASS`

with a scope.

Examples:

```text
DATA_FACTOR_REPLAY_PASS
scope = CURRENT_FORWARD_STOCK_CORE
```

or, if some current factors are known bootstrap-unknown:

```text
DATA_FACTOR_REPLAY_PASS
scope = <precisely accepted degraded subset>
status = DEGRADED_PASS
```

Never emit an unqualified global pass.

---

# 18. Independent Postcheck

A separate verifier must independently recompute/verify:

- accepted-head bindings;
- source package and GBBQ identities;
- calendar identity;
- daily-history digest;
- period AS-OF samples;
- factor max-source dates;
- market reference sample;
- market regime;
- Core Profile row set and digest;
- UNKNOWN propagation;
- repeated deterministic build;
- idempotency;
- temporal negatives;
- capability statuses;
- historical AS_RECORDED block;
- V4-08 block.

It must not simply read PASS flags from the production receipts.

---

# 19. Runtime Tests

Add V4-05 R3 tests for every new gate.

Run:

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

Create a formal runtime receipt binding:

```text
implementation commit
exact command
test file hashes
runtime versions
start/end
passed/failed/skipped
```

---

# 20. Required R3 Evidence Family

At minimum:

```text
reports/v4_05/V4_05_R3_STAGE_ENTRY.md
reports/v4_05/V4_05_R3_ACCEPTED_INPUT_MANIFEST.json
reports/v4_05/V4_05_R3_DAILY_HISTORY_RECEIPT.json
reports/v4_05/V4_05_R3_CALENDAR_RECEIPT.json
reports/v4_05/V4_05_R3_PERIOD_ASOF.json
reports/v4_05/V4_05_R3_FACTOR_SOURCE_TIME.json
reports/v4_05/V4_05_R3_MARKET_REFERENCE.json
reports/v4_05/V4_05_R3_MARKET_REGIME.json
reports/v4_05/V4_05_R3_CORE_PROFILE_REPLAY.json
reports/v4_05/V4_05_R3_DETERMINISM.json
reports/v4_05/V4_05_R3_REVISION_IDEMPOTENCY.json
reports/v4_05/V4_05_R3_TEMPORAL_LEAKAGE.json
reports/v4_05/V4_05_R3_CAPABILITY_GATE.json
reports/v4_05/V4_05_R3_RUNTIME_TEST_RECEIPT.json
reports/v4_05/V4_05_R3_INDEPENDENT_POSTCHECK.json
reports/v4_05/V4_05_R3_STAGE_CANDIDATE_MANIFEST.json
reports/v4_05/V4_05_R3_CLOSURE.md
```

Staging artifacts should be versioned R3 and must not overwrite R2.

---

# 21. Terminal Status

If Replay Gate A is successfully completed for the accepted current-forward scope:

`V4_05_DATA_FACTOR_REPLAY_PASS_CANDIDATE_R3`

with explicit capability scope.

If only a subset passes, use the exact scoped DEGRADED/BLOCKED status.

Do not claim V4-05 acceptance.

Stop for independent external audit.

---

# 22. Forbidden Work

Do not:

- reuse `TARGET_DATE_ACCEPTED_INPUT_SERIES_NOT_MATERIALIZED` as a terminal reason without attempting the build;
- relabel pre-project history as PIT;
- use future price data to extend calendar;
- infer suspension from missing bar;
- use BaoStock QFQ fallback;
- change V4-03/V4-04 formulas;
- weaken UNKNOWN propagation;
- use later GBBQ to rewrite Sep-28;
- start V4-06/V4-07/V4-08;
- promote a V4-05 Accepted Head;
- modify the user's TDX root.

---

# 23. Stop Point

Stop only after:

1. G05–G08 and temporal suite are actually executed, or
2. a specific demonstrated source/contract defect makes an affected capability impossible without violating accepted semantics.

Then await independent external audit.
