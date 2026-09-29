# V4-04 Final External Acceptance Report R1

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Acceptance Date:** 2026-09-29  
**Audit Type:** Independent external stage acceptance  
**Stage:** `V4-04 Full-Market Core Profile`

---

# 0. Final Disposition

**External Acceptance Result**

`V4_04_EXTERNAL_ACCEPTANCE_PASS_R4`

**Accepted implementation commit**

`044dc637f90b35c6097bb800b1d4d755fdfb792c`

**Evidence-seal HEAD reviewed**

`b7dc52d94d7bd81b8f55e1009d3eb271689f0943`

**Accepted R4 staging artifact**

`reports/v4_04/staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R4.jsonl.gz`

**Artifact SHA256**

`b1ce4e4cb227f7cc25271005debfc9fc7bfaf61d39e20c96592921dd361e3b52`

**Stage conclusion**

`FULL_PASS_REQUIRED_SCOPE / EXTERNALLY_ACCEPTED`

V4-04 has satisfied its contracted scope and is eligible for Accepted-Head promotion.

V4-05 is **not yet accepted** and remains a separate stage. It may start only after the V4-04 Accepted Head promotion succeeds.

---

# 1. Governing Authority

This acceptance is based on:

- `AGENTS.md`
- `docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md`
- accepted V4-00 through V4-03 heads
- V4-04 R2/R3/R4/R5 task cards
- R4 implementation and all R4 evidence receipts
- independent source, contract, semantic and governance cross-checks

The governing §78 stage boundary is respected:

```text
V4-04 = Full-Market Core Profile
§10B–10G + §10I Pure-Core fields
excludes §10H Turnover
does not depend on BaoStock / Sector Context / Advanced Structure
```

Replay Gate A remains V4-05.

---

# 2. Stage-Scope Acceptance

## PASS — Scope Boundary

V4-04 implements the required Full-Market Pure-Core profile family without expanding into later-stage logic.

Accepted scope includes:

- daily trend state
- weekly trend state
- monthly trend state
- position state
- near-high states
- drawdown states
- MA structure
- relative-market state
- compression state
- amount / volume states
- core participation result
- core extension risk
- severe extension
- regime UI
- derived Core primitives required by the above

Explicitly excluded and not required for V4-04 acceptance:

- turnover context / BaoStock enrichment
- Stock Base Seed
- Sector / Rotation production
- PREWATCH
- advanced structure
- Focus
- settlement / Forward
- V4-05 Replay Gate A

---

# 3. Accepted Input Authority

## PASS — Accepted-Head Resolution

V4-04 resolves inputs from the accepted foundation chain rather than arbitrary local outputs.

Accepted upstream authorities include:

- V4-01 historical universe / identity
- V4-02 canonical adjusted daily
- V4-02 trading-status history
- V4-02 formal weekly / monthly periods
- V4-03 accepted stock Core factors
- V4-03 accepted market-regime primitives
- accepted exchange calendars

Cutoff:

`2026-09-24`

The accepted source hashes in the R4 receipt match the previously accepted upstream identities.

No evidence was found that V4-04 rewrote or replaced accepted V4-00 through V4-03 business artifacts.

---

# 4. Full-Market Materialization

## PASS — Required Scope Coverage

R4 materializes:

| Board | Rows |
|---|---:|
| SH_MAIN | 1702 |
| SZ_MAIN | 1494 |
| CHINEXT | 1408 |
| STAR | 618 |
| **Total** | **5222** |

All 5,222 rows are unique by security identity in required scope.

BSE remains outside required V4-04 acceptance scope under the previously accepted optional-degraded policy.

---

# 5. Contract / Registry / Artifact Consistency

## PASS

The following are bound and mutually checked:

- `config/v4_04_field_registry_v2.json`
- `config/v4_04_output_schema_v2.json`
- `config/v4_04_algorithm_contracts_v3.json`
- `config/v4_04_parameter_set_v1.json`
- `config/v4_04_field_window_mapping_v1.json`

Producer identity, producer contract, parameter set and artifact envelope are aligned.

The earlier producer/consumer ambiguity for:

- `bias20_atr`
- `dist_high20_atr`
- `pos250`
- `ma10`
- `minimum_liquidity`

has been repaired.

---

# 6. Technical Window / PIT Semantics

## PASS

The final implementation validates actual-bar technical windows against dated trading-status rows and the complete exchange-session calendar.

Accepted semantics:

```text
confirmed SUSPENDED
→ may extend calendar span while actual-bar window remains valid

UNKNOWN / unsupported status / missing status row
→ fail closed
```

This is applied to:

- MA10
- prior20 minimum liquidity
- pos250

Lineage metadata is retained:

- window_start_trade_date
- window_end_trade_date
- actual_count
- calendar_span
- suspended_count
- window_identity
- field_window_mapping_id

The accepted V4-03 field-window mapping is hash-bound into the V4-04 chain.

---

# 7. Core Rule Semantics

## PASS — Daily / Position / MA / Relative / Compression / Participation / Extension

Independent machine execution covers all 18 registered machine rules.

Final R4 machine evidence reports:

- machine rules: 18 / 18
- branch positions: 70
- threshold vectors: 78
- UNKNOWN vectors: 32
- branch-specific UNKNOWN vectors: 2
- enum UNKNOWN vectors: 3
- stateful hysteresis vectors: 2
- inclusive-boundary vectors: 2
- rules missing vector coverage: `[]`

Semantic coverage status:

`PASS`

---

# 8. Specific Repaired Semantic Findings

## PASS — MA10 independence

MA10 no longer depends on MA20 availability.

A valid 10-actual-bar window may produce MA10 while MA20 remains UNKNOWN.

## PASS — minimum_liquidity independence

`minimum_liquidity` now depends on its own prior20 raw-CNY amount window and no longer requires `amount_ratio20` to be OBSERVED.

This preserves the distinction:

```text
minimum_liquidity field semantics
!=
compression eligibility semantics
```

## PASS — Enum UNKNOWN propagation

The independent machine layer now handles required enum dependencies explicitly.

Verified examples include:

- Relative with UNKNOWN compression state
- Relative with UNKNOWN MA-structure state
- severe_extension with UNKNOWN extension risk
- participation with branch-required UNKNOWN CLV
- trend with UNKNOWN core_price_damage

## PASS — Drawdown inclusive boundaries

Final production and independent machine logic agree with the formal §10C thresholds:

```text
exact -5%  → SHALLOW
exact -15% → MODERATE
```

The prior floating-point boundary misclassification is repaired.

---

# 9. Independent Source Recomputation

## PASS

R4 independent postcheck re-reads accepted upstream sources and recomputes selected values without treating candidate state evidence as the oracle.

Reported direct source checks include:

- MA10: 22
- minimum_liquidity: 21
- pos250: 19
- bias20_atr: 21
- dist_high20_atr: 21
- weekly: 21
- monthly: 23

Deterministic source sample count:

`36`

`minimum_liquidity_false_unknown_count = 0`

Independent postcheck status:

`PASS`

---

# 10. UNKNOWN / Quality Propagation

## PASS

Required unavailable inputs remain explicit UNKNOWN rather than being imputed into valid-looking states.

The artifact preserves per-field quality and unknown reasons.

Profile quality remains split into:

- COMPLETE
- PARTIAL_UNKNOWN

The profile component status mapping remains explicit and versioned.

No rule was accepted merely because the page or candidate needed to remain non-empty.

---

# 11. Determinism

## PASS

R4 was rebuilt twice from the same accepted input and contract identities.

Both runs produced:

`b1ce4e4cb227f7cc25271005debfc9fc7bfaf61d39e20c96592921dd361e3b52`

Determinism receipt:

`PASS`

---

# 12. Regression Gate

## PASS

Focused command:

```text
python -m pytest tests/v4_01 tests/v4_02 tests/v4_03 tests/v4_04 tests/v4_joint tests/v4_phase0 -q
```

Runtime result:

```text
390 passed
2 skipped
0 failed
```

The test receipt binds the runtime command, implementation commit and test-source hashes.

---

# 13. Historical Evidence Preservation

## PASS

Historical V4-04 candidate identities remain preserved:

```text
R1
afbea0ab09cbe28cfb5648495264ce346ccce22f5ca40b15b24112b6d8eb2e07

R2
89ed21dbdcc5abf377d2fda8299c444e7cd687fabb0eb5648ef5f12b8c4c0f12

R3
0c0fccd06fd2c2bad856b529d3ae2bcf64584f451e97961380997d72830b46b6
```

R4 is a new version rather than an overwrite.

---

# 14. Stage Governance

## PASS

At final external audit:

- no `data/v4/V4_04_ACCEPTED_HEAD.json` existed yet;
- `data/v4/V4_STAGE_ACCEPTED_HEAD.json` still stopped at accepted V4-00 through V4-03;
- no V4-05 report set was present;
- `044dc637... → b7dc52d...` only added seal/evidence files and did not modify implementation code.

Therefore V4-04 did not self-promote before independent external acceptance.

---

# 15. Non-Blocking Open Items

The following remain open but do not invalidate V4-04 required scope:

## A. Repository-wide pytest collection issue

The previously documented unrelated `upgrade_m14` collection problem remains a cross-cutting audit item.

It is not treated as a V4-04-specific blocker because:

- it predates the final V4-04 repairs;
- the required V4 regression set passes;
- no evidence shows V4-04 introduced the collection failure.

## B. GitHub CI status

The accepted implementation commit has no GitHub workflow/status checks.

This is recorded as absence of remote CI evidence, not as a failed V4-04 gate, because the repository-bound runtime test receipt is present and hash-bound.

## C. V4-08 Sector PIT

The existing block remains:

`BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION`

V4-04 acceptance must not remove or weaken it.

---

# 16. Final Accepted Capability

Accepted capability:

`STOCK_CORE_FULL_MARKET_PROFILE`

Stage status:

`FULL_PASS_REQUIRED_SCOPE`

External acceptance:

`EXTERNALLY_ACCEPTED`

Accepted artifact:

`V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R4`

Accepted SHA256:

`b1ce4e4cb227f7cc25271005debfc9fc7bfaf61d39e20c96592921dd361e3b52`

---

# 17. Next Stage Authorization

This external acceptance authorizes only the following transition:

```text
V4-04 Accepted-Head Promotion
    ↓
V4-05 Replay Gate A
```

V4-05 must independently prove:

- TDX source identity
- historical universe correctness
- adjustment reproducibility
- Daily determinism
- Weekly / Monthly AS-OF
- factor max_source_trade_date
- Core Profile determinism
- revision idempotency
- Temporal Leakage constraints
- capability-scoped replay status

V4-04 acceptance does not itself imply `DATA_FACTOR_REPLAY_PASS`.

---

# 18. Final Status

`V4_04_EXTERNAL_ACCEPTANCE_PASS_R4`

`V4_04_FULL_PASS_REQUIRED_SCOPE`

`V4_04_READY_FOR_ACCEPTED_HEAD_PROMOTION`

`V4_05_NOT_STARTED_PENDING_PROMOTION`
