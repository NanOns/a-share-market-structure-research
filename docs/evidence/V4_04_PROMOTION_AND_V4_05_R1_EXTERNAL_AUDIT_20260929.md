# V4-04 Promotion + V4-05 Replay Gate A R1 External Audit Report

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Audit Date:** 2026-09-29  
**Reviewed HEAD:** `52ff45b138fa536e802168a11aebbba6d1cb1d9d`

---

# 0. Final Disposition

## Phase A — V4-04 Accepted-Head Promotion

**Result**

`V4_04_ACCEPTED_HEAD_PROMOTION_PASS`

Promotion commit:

`6aa0bdd737e918148978d5d99e9ec4df17187ebb`

V4-04 is now formally accepted in the repository.

## Phase B — V4-05 Replay Gate A R1

**Stage result**

`V4_05_EXTERNAL_ACCEPTANCE_BLOCKED_R1`

**Block evidence disposition**

`V4_05_R1_BLOCK_EVIDENCE_ACCEPTED`

Exact blocker:

`V4_05_BLOCKED_UPSTREAM_DEFECT_HISTORICAL_ADJUSTED_PRICE_PIT_LINEAGE`

This means:

- the R1 blocker is real;
- the blocker evidence is internally consistent;
- `DATA_FACTOR_REPLAY_PASS` is **not** granted;
- V4-05 is **not accepted**;
- V4-06+ receive no new authorization from V4-05 R1.

However, the historical PIT defect must not be interpreted as a permanent global block on all future/current capabilities. REV2 §52B explicitly requires capability-scoped gating and states that missing historical completion must not automatically block an otherwise independent current/go-forward capability.

---

# 1. Commit / Stage Boundary Audit

Commits after the previously accepted V4-04 evidence-seal HEAD:

```text
6aa0bdd737e918148978d5d99e9ec4df17187ebb
[V4-04] Promote externally accepted R4 core profile

78f9f596e76797b7fefe2f7834f7ce7d04bdc5e0
[V4-05] Freeze Replay Gate A entry matrix

30b0de6485c6b590bffd11fabcbd99cfd4af1fd3
[V4-05] Audit historical replay prerequisites and independent postcheck

52ff45b138fa536e802168a11aebbba6d1cb1d9d
[V4-05] Seal Replay Gate A upstream PIT blocker evidence
```

The promotion commit is cleanly separated from V4-05 work.

No V4-05 business output was present before the promotion validator.

**PASS**

---

# 2. V4-04 Accepted Head Promotion

Created:

`data/v4/V4_04_ACCEPTED_HEAD.json`

Formal status:

```text
stage = V4-04
status = FULL_PASS_REQUIRED_SCOPE
external_acceptance = EXTERNALLY_ACCEPTED
```

Accepted artifact:

`reports/v4_04/staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R4.jsonl.gz`

SHA256:

`b1ce4e4cb227f7cc25271005debfc9fc7bfaf61d39e20c96592921dd361e3b52`

Implementation commit:

`044dc637f90b35c6097bb800b1d4d755fdfb792c`

Historical R1/R2/R3 hashes remain bound and preserved.

**PASS**

---

# 3. Global Accepted Head Promotion

`data/v4/V4_STAGE_ACCEPTED_HEAD.json` now records:

```text
accepted_stage_range =
V4_00_TO_V4_04_ACCEPTED; V4_05_NOT_ACCEPTED

v4_04_status =
FULL_PASS_REQUIRED_SCOPE

v4_04_external_acceptance =
EXTERNALLY_ACCEPTED

v4_04_entry =
COMPLETED_EXTERNALLY_ACCEPTED

v4_05_entry =
AUTHORIZED_REPLAY_GATE_A
```

V4-08 remains:

`BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION`

Foundation bindings were not changed.

**PASS**

---

# 4. Promotion Validator

Receipt:

`reports/v4_joint/V4_04_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json`

Result:

`PASS`

Validated:

- accepted R4 artifact identity;
- exact R4 manifest;
- 13 evidence receipts;
- external acceptance document;
- unchanged V4-01/02/03 bindings;
- unchanged TDX archive;
- preserved V4-08 block;
- no premature V4-05 business output;
- historical R1/R2/R3 candidate hashes.

**PASS**

---

# 5. V4-05 Frozen Replay Matrix

R1 froze the replay matrix before replay evaluation.

The matrix includes:

- recent cutoff;
- Monday weekly-ASOF case;
- mid-month monthly-ASOF case;
- all four required boards;
- recent listing / short-history case;
- adjustment-sensitive security;
- suspension/resumption case;
- accepted code-change identity case `300114 → 302132`.

The selection rules are recorded before output evaluation.

This is materially better than choosing examples after results are known.

**PASS as frozen-entry evidence**

It is not by itself a Replay Gate pass.

---

# 6. G01 — TDX Source Identity

R1 resolves V4-05 inputs through:

```text
V4_STAGE_ACCEPTED_HEAD
→ V4_04_ACCEPTED_HEAD
→ accepted R4 production receipt
→ accepted V4-01 / V4-02 / V4-03 source identities
```

Accepted source hashes are checked before use.

G01 result:

`PASS`

**PASS**

---

# 7. G02 — Historical Universe

R1 checked:

- one later-listing boundary;
- recent membership;
- four required-board identities.

Result:

`PASS_SAMPLED_BOUNDARY`

This is truthful but narrower than a full historical-universe replay acceptance.

Therefore:

**PASS only as sampled prerequisite evidence**

It does not independently certify all historical universe dates.

---

# 8. G03 — Historical Adjustment Reproducibility

This is the real blocker.

The accepted V4-02 daily artifact contains:

```text
knowledge_lineage =
DIAGNOSTIC_NON_PIT_CURRENT_METADATA_SNAPSHOT
```

for all:

`4,026,611` rows.

The accepted V4-02 records independently confirm that historical adjusted prices were never claimed as strict PIT:

`reports/v4_02/V4_02_DATA_PERIOD_MAINLINE_FINAL_ACCEPTANCE_R2.json`

states:

```text
historical_adjusted_lineage =
DIAGNOSTIC_NON_PIT_CURRENT_METADATA_SNAPSHOT

historical_pit_adjusted =
NOT_AVAILABLE_PRE_PROJECT; NOT_CLAIMED
```

The earlier PIT stage receipt also records:

```text
AS_RECORDED_CONSUMED_SOURCE_HISTORY_UNAVAILABLE
```

and:

```text
adjusted_daily_periods = UNAVAILABLE
historical_pit_observed = UNAVAILABLE
```

Therefore a historical target date T cannot prove that every adjustment/corporate-action fact used in the reconstructed QFQ coordinate was already available at T.

This violates the REV2 historical replay rule that company actions must be:

```text
effective <= T
AND
visible in the selected consumption manifest at T
```

and that later corrections must not leak backward.

G03 result:

`BLOCKED`

**BLOCK CONFIRMED**

---

# 9. Why the Existing QFQ Math Does Not Cure the PIT Defect

The V4-02 adjustment engine itself has real mathematical evidence:

- affine QFQ reconstruction;
- cash-dividend samples;
- bonus/transfer samples;
- rights-issue samples;
- combined-action samples;
- suspension/resumption sample;
- recent-listing samples.

Those tests prove that the current snapshot can be interpreted consistently.

They do **not** prove when each historical corporate-action record first became available to the system.

The repository explicitly records that limitation.

Therefore:

```text
correct reconstruction math
!=
historical AS_RECORDED source visibility
```

The R1 blocker is semantically valid.

---

# 10. Go-Forward Snapshot Evidence

V4-02 already created:

`V4_02_GBBQ_FORWARD_SNAPSHOT_FREEZE_20260926.json`

It records:

```text
status =
GO_FORWARD_SNAPSHOT_FROZEN

system_available_at =
2026-09-26T13:07:05Z

first_eligible_formal_trade_date =
2026-09-28

historical_pit_claim =
NOT_CLAIMED
```

The underlying source contract states:

```text
PIT_OBSERVED_ELIGIBLE_FROM_FIRST_FORMAL_PUBLICATION_AFTER_SYSTEM_AVAILABLE_AT
```

and:

```text
historical effective dates before availability
=
DIAGNOSTIC_NON_PIT_ONLY
```

This creates an important scope distinction:

```text
pre-forward historical AS_RECORDED
→ still blocked

go-forward PIT beginning from the frozen snapshot system
→ may be independently proven
```

---

# 11. Scope Error / Over-Broad Interpretation in R1

R1 correctly stopped under the explicit task-card stop condition.

However, its capability table marks:

- STOCK_CORE
- MARKET_REFERENCE
- MARKET_REGIME
- WEEKLY_PERIOD
- MONTHLY_PERIOD

as BLOCKED because G04–G08 were not run after G03.

That is correct **for this R1 historical replay run**.

It must not be interpreted as a permanent architectural statement that historical first-availability must be reconstructed for two years before any go-forward capability can proceed.

REV2 §52B explicitly allows capability-scoped outcomes and states, in substance:

```text
current TDX / adjustment valid,
historical evidence incomplete
→ current Core / complete-window algorithms / forward may proceed

missing-evidence historical adjusted output
→ remains prohibited
```

and:

```text
historical completion is not automatically a global gate
for an independent current capability
```

Therefore the next repair should **split scopes**, not fabricate historical PIT.

---

# 12. G04–G08

Current R1 status:

```text
G04 DAILY DETERMINISM
NOT_RUN_BLOCKED_BY_G03

G05 FORMAL PERIOD ASOF
NOT_RUN_BLOCKED_BY_G03

G06 FACTOR MAX SOURCE DATE
NOT_RUN_BLOCKED_BY_G03

G07 CORE PROFILE REPLAY
NOT_RUN_BLOCKED_BY_G03

G08 REVISION IDEMPOTENCY
NOT_RUN_BLOCKED_BY_G03
```

This is a truthful stop.

No pass may be inferred.

---

# 13. Independent Postcheck

`V4_05_INDEPENDENT_POSTCHECK_RECEIPT_R1.json`

independently confirms:

- accepted hash chain;
- exact accepted daily source;
- all 4,026,611 rows use diagnostic non-PIT lineage;
- G03 is BLOCKED;
- G04–G08 were not run;
- `DATA_FACTOR_REPLAY_PASS = false`.

Result:

`PASS_FOR_BLOCK_EVIDENCE_ONLY`

This label is accurate.

**PASS for block evidence**

---

# 14. V4-05 R1 Final Acceptance Status

V4-05 itself is **not accepted**.

Final status:

`V4_05_EXTERNAL_ACCEPTANCE_BLOCKED_R1`

Accepted finding:

`HISTORICAL_AS_RECORDED_ADJUSTED_PRICE = BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`

Accepted R1 evidence status:

`BLOCK_EVIDENCE_VALID`

Not granted:

`DATA_FACTOR_REPLAY_PASS`

---

# 15. Impact on Earlier Stages

## V4-04

Do **not** revoke V4-04 Accepted Head.

V4-04 was accepted for its contracted full-market Core Profile scope on the accepted V4-02/V4-03 chain.

What V4-05 now proves is narrower:

> that the existing historical adjusted chain cannot be upgraded into strict historical AS_RECORDED replay evidence.

V4-04 acceptance does not equal historical Replay Gate A acceptance.

## V4-02

Do not rewrite the historical V4-02 acceptance record.

Its historical non-PIT limitation was already explicitly disclosed.

A new go-forward PIT amendment may be created without pretending the old historical artifact was PIT.

## V4-08

Sector PIT remains separately blocked.

No change.

---

# 16. Required Next Direction

Do **not** attempt to “repair” two years of historical first-availability by inventing announcement times or assuming:

```text
effective_date == first_available_date
```

Do not silently use a later GBBQ snapshot as if it were available at historical T.

Instead:

1. preserve historical replay as `DIAGNOSTIC_NON_PIT`;
2. build and externally accept a real go-forward PIT adjustment/source amendment;
3. start from the first eligible complete trading day after the frozen snapshot system;
4. rerun Replay Gate A on the go-forward scope;
5. keep historical AS_RECORDED capability blocked until genuine first-availability evidence exists.

Given the frozen source record, the first target date is:

`2026-09-28`

As of the current audit time on 2026-09-29, 2026-09-28 is the first completed eligible trading day. The in-progress 2026-09-29 session must not be used as a completed daily publication.

---

# 17. Final Status

```text
V4_04_ACCEPTED_HEAD_PROMOTION_PASS

V4_04 =
FULL_PASS_REQUIRED_SCOPE / EXTERNALLY_ACCEPTED

V4_05_R1_BLOCK_EVIDENCE =
ACCEPTED

V4_05 =
EXTERNAL_ACCEPTANCE_BLOCKED_R1

HISTORICAL_AS_RECORDED_ADJUSTED_PRICE =
BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE

GO_FORWARD_PIT =
NOT_YET_ACCEPTED

DATA_FACTOR_REPLAY_PASS =
FALSE

NEXT =
GO_FORWARD_PIT_ADJUSTMENT_SOURCE_AMENDMENT_CANDIDATE
```
