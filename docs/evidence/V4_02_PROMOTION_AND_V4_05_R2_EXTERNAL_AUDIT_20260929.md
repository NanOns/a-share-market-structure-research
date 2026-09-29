# V4-02 Go-Forward PIT Promotion + V4-05 Replay Gate A R2 External Audit

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Audit Date:** 2026-09-29  
**Reviewed HEAD:** `7943596a800e9ac9234885b0dad77b06c87e1e25`  
**Previous Baseline:** `a54154e5e25b149fd35a09935435dcaa40ad8b8b`

---

# 0. Final Disposition

This audit contains two independent conclusions.

## Phase A — V4-02 Go-Forward PIT Accepted Seal

`V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD_PROMOTION_PASS_R1`

**PASS**

## Phase B — V4-05 Replay Gate A R2

`V4_05_EXTERNAL_ACCEPTANCE_BLOCKED_R2_INCOMPLETE_EXECUTION`

The R2 blocker evidence is truthful and may be retained, but R2 is **not** a completed Replay Gate A candidate.

Accepted R2 partial capability:

`CURRENT_FORWARD_ADJUSTED_PRICE = FULL_PASS`

Not completed:

- G05 Weekly / Monthly AS-OF
- G06 Sep-28 factors + source-time traceability
- Market Reference / Market Regime
- G07 Sep-28 Core Profile replay
- G08 revision idempotency
- required temporal-negative execution

No `DATA_FACTOR_REPLAY_PASS` is authorized.

---

# 1. Commit Ordering

Two commits exist after the prior accepted R3 external audit:

```text
fb6a367c432270449cc3d65d0827b3fc159b6b33
Promote accepted V4-02 go-forward PIT amendment

7943596a800e9ac9234885b0dad77b06c87e1e25
Record capability-scoped V4-05 replay gate A R2 evidence
```

Promotion and V4-05 work are separated.

This satisfies the required ordering.

**PASS**

---

# 2. Phase A — Separate Accepted Amendment Head

Created:

`data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json`

It correctly preserves:

```text
stage =
V4-02-GO-FORWARD-PIT-AMENDMENT

status =
FULL_PASS_GO_FORWARD_SCOPE

external_acceptance =
EXTERNALLY_ACCEPTED

first_accepted_target_trade_date =
2026-09-28

publication_mode =
DELAYED_FORMAL_PUBLICATION

knowledge_lineage =
PIT_OBSERVED_AFTER_FORMAL_PUBLICATION

historical_as_recorded_adjusted_price =
BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE
```

Accepted candidate:

```text
path =
reports/v4_02/staging/V4_02_GO_FORWARD_ADJUSTED_T0_CANDIDATE_R3.jsonl.gz

SHA256 =
7d87f5164c11f791ad24ad7c05139dca949f1c891523616ece907cd0f28fd8c8

logical_digest =
a5600d7f1416434bd54e778c2e7e847e309de1c21d71df5677f92daee1791400
```

**PASS**

---

# 3. Original Foundation Heads Preserved

The original:

`data/v4/V4_02_ACCEPTED_HEAD.json`

continues to represent the Sep-24 foundation.

The accepted V4-04 head also remains unchanged.

The new go-forward capability is additive, not a rewrite of historical V4-02 acceptance.

**PASS**

---

# 4. Global Accepted Head

`data/v4/V4_STAGE_ACCEPTED_HEAD.json`

now contains:

```text
v4_02_go_forward_pit_status =
FULL_PASS_GO_FORWARD_SCOPE

v4_02_go_forward_pit_external_acceptance =
EXTERNALLY_ACCEPTED

v4_02_go_forward_first_target =
2026-09-28

historical_as_recorded_adjusted_price =
BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE

v4_05_entry =
AUTHORIZED_REPLAY_GATE_A_R2
```

Original V4-02 foundation binding is retained.

V4-08 remains:

`BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION`

**PASS**

---

# 5. Promotion Validation

`V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json`

independently verifies:

- foundation V4-02 unchanged;
- V4-04 unchanged;
- all R3 evidence bindings;
- candidate SHA;
- external decision;
- official source identity;
- historical AS_RECORDED block;
- global binding;
- V4-08 block;
- V4-05 ordering.

Result:

`PASS`

**Phase A formally accepted.**

---

# 6. V4-05 R2 G01–G04

## G01 Source Identity

Official Sep-28 package:

```text
SHA256 =
70b79898325ef6c67ea697f922d38fa3fd523e2ad62879b1b9fcb59fce52bf0c

max_source_trade_date =
20260928

future_raw_rows =
0
```

**PASS**

## G02 Universe / Identity

```text
candidate_entities = 5222
actual_target_bars = 5210
no_target_bar = 12
```

R3 identity and code-change evidence are bound.

**PASS_CURRENT_FORWARD**

## G03 Adjustment

```text
CURRENT_FORWARD_ADJUSTED_PRICE = PASS

HISTORICAL_AS_RECORDED_ADJUSTED_PRICE =
BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE

ADJUSTED_READY = 5195
UNKNOWN = 27
```

**PASS / correctly scope-split**

## G04 Daily Determinism

Two builds reproduce:

`a5600d7f1416434bd54e778c2e7e847e309de1c21d71df5677f92daee1791400`

and match the accepted go-forward head.

**PASS**

---

# 7. R2 Capability Matrix Is Truthful

The R2 capability matrix correctly does **not** emit an unqualified Replay-A pass.

It reports:

```text
CURRENT_FORWARD_ADJUSTED_PRICE = FULL_PASS

CURRENT_FORWARD_STOCK_CORE = BLOCKED
WEEKLY_PERIOD = BLOCKED
MONTHLY_PERIOD = BLOCKED
MARKET_REFERENCE = BLOCKED
MARKET_REGIME = BLOCKED

HISTORICAL_AS_RECORDED_ADJUSTED_PRICE = BLOCKED
```

`data_factor_replay_pass = []`

This is preferable to fabricating a global PASS.

**PASS as blocker evidence**

---

# 8. Why R2 Is Not a Completed V4-05 Candidate

The remaining reports are not failed replay calculations.

They explicitly state that the calculations were **not run**:

```text
TARGET_DATE_ACCEPTED_INPUT_SERIES_NOT_MATERIALIZED
```

The implementation in:

`scripts/close_v4_05_replay_gate_a_r2.py`

constructs G05/G06/B9/G07/G08/temporal receipts as blocked placeholders after G01–G04.

It does not attempt to materialize:

- Sep-28 T0-coordinate daily history;
- Sep-28 weekly/monthly periods;
- Sep-28 Pure-Core factors;
- Sep-28 market reference;
- Sep-28 market regime;
- Sep-28 V4-04 Core Profile.

Therefore this is an **execution incompleteness**, not a newly discovered upstream data defect.

---

# 9. The Missing Series Are Buildable from Current Accepted Inputs

The repository already has:

- official Sep-28 complete TDX package;
- complete `.day` history inside the official package;
- accepted Sep-26 frozen GBBQ;
- accepted identity map;
- accepted V4-02 period contracts;
- accepted V4-03 factor contracts;
- accepted V4-04 Core Profile contracts;
- existing V4-02/03/04 production/staging builders.

The old builders are hard-bound to the Sep-24 accepted foundation and must not simply be run unchanged as Sep-28 production evidence.

But their accepted algorithms/libraries can be reused through a V4-05 target-date replay adapter.

Thus:

`TARGET_DATE_ACCEPTED_INPUT_SERIES_NOT_MATERIALIZED`

is not a valid terminal blocker for the next attempt.

R3 must actually build the missing target-date chain.

---

# 10. Important Current-Coordinate Boundary

The go-forward accepted adjustment capability is:

`T0_CURRENT_COORDINATE`

Historical lookback bars may be transformed into the Sep-28 current coordinate for the purpose of computing Sep-28 factors.

This does **not** make historical bar dates historical AS_RECORDED PIT publications.

Every replay artifact must retain:

```text
historical_as_recorded_claim = false
coordinate_basis = T0_CURRENT_COORDINATE
formal_publication_at = accepted Sep-28 forward publication time
```

Historical replay outputs remain diagnostic unless separately proven PIT.

---

# 11. Period Calendar Boundary

The Sep-24 accepted calendar cannot be silently treated as a Sep-28 accepted calendar.

For G05, R3 must bind a go-forward calendar basis sufficient to decide period status at Sep-28.

It must not infer a future exchange session from future price bars.

If a calendar extension is needed, it must be sourced/frozen under an explicit authoritative market-calendar contract.

Sep-28 current week/month must not become CLOSED_ONLY merely because later bars are absent from the T0 dataset.

---

# 12. Relative / Market Reference Bootstrap Boundary

V4-03 relative and market-reference fields may depend on historical start-universe / prior-RPS identities.

R3 must explicitly prove the provenance of every such prerequisite.

Do not silently turn a retrospective historical cross-section into `PIT_OBSERVED`.

If an accepted current-forward factor cannot yet be fully supported at the first forward date, propagate:

```text
UNKNOWN / BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY
```

or the existing contract-equivalent reason.

Then capability status may be `DEGRADED_PASS` or `BLOCKED` according to §52B and field requiredness.

Do not change the factor algorithm merely to obtain PASS.

---

# 13. Runtime Test Receipt Limitation

R2 runtime receipt reports:

```text
403 passed
2 skipped
0 failed
```

This verifies current tests, but only two V4-05 tests exist in the new file, and they mainly enforce:

- daily digest equality;
- no false Replay-A PASS.

They do not prove G05–G08.

This is consistent with the blocked result.

---

# 14. Independent Postcheck

The independent postcheck truthfully reports:

```text
PASS_SCOPED_BLOCKED_CANDIDATE
```

with unverified:

```text
G05
G06
B9
G07
G08
temporal negatives
```

This receipt is accepted as an honest incompleteness record, not as V4-05 external acceptance.

---

# 15. External Decision

## Phase A

```text
V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD_PROMOTION_PASS_R1
```

## Phase B

```text
V4_05_EXTERNAL_ACCEPTANCE_BLOCKED_R2_INCOMPLETE_EXECUTION
```

Accepted partial capability:

```text
CURRENT_FORWARD_ADJUSTED_PRICE = FULL_PASS
```

Still required before Replay Gate A can be externally accepted:

```text
G05
G06
MARKET_REFERENCE
MARKET_REGIME
G07
G08
TEMPORAL_NEGATIVES
```

No V4-05 Accepted Head is authorized.

No V4-06/V4-07 entry is authorized from this R2 result.

---

# 16. Next Stage

Proceed to:

`V4_05_REPLAY_GATE_A_R3_FORCED_COMPLETION`

R3 must materialize the missing target-date chain and execute the gates.

It may stop early only for a **specific demonstrated source/contract defect**.

It may not stop again merely because an artifact has not yet been built.
