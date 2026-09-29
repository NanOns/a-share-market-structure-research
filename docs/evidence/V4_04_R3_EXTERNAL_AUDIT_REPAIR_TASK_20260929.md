# V4-04 R3 External Audit Repair Task

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Task Type:** V4-04 external-audit repair / contract-artifact-postcheck closure  
**Date:** 2026-09-29

---

# 0. External Audit Disposition

Current branch HEAD observed by external audit:

`ace30af36ce5440bb989312fce3e4385e8f8e6e6`

Current V4-04 candidate implementation commit bound by the candidate manifest:

`e75ed6348426eefb848054e28836ffac3b8f2a2e`

Current candidate artifact:

`reports/v4_04/staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R1.jsonl.gz`

Current candidate artifact SHA256:

`afbea0ab09cbe28cfb5648495264ce346ccce22f5ca40b15b24112b6d8eb2e07`

Current candidate self-declared status:

`V4_04_FULL_PASS_CANDIDATE`

Independent external audit disposition:

`V4_04_EXTERNAL_ACCEPTANCE_BLOCKED_REPAIR_REQUIRED`

This disposition **does not reopen V4-00 through V4-03**.

The accepted foundation remains authoritative.

V4-04 remains authorized for repair work.

V4-05 remains:

`NOT_STARTED / NOT_AUTHORIZED_UNTIL_V4_04_EXTERNAL_ACCEPTANCE`

The existing R1 candidate, receipts, postcheck and audit files must be preserved as historical candidate evidence. Do not overwrite them.

---

# 1. Governing Authorities

All repair work must follow:

1. `AGENTS.md`
2. `docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md`
3. Existing accepted heads under `data/v4/`
4. Existing externally accepted V4-00～V4-03 evidence chain
5. Previous V4-04 task:
   `docs/evidence/V4_04_R2_FULL_MARKET_CORE_PROFILE_CLOSURE_TASK_20260929.md`

Primary governing sections:

- §10A
- §10B–§10G
- §10I
- §72
- §73
- §78
- §81.4
- §87A

Do not modify the governing business semantics merely to make current code pass.

---

# 2. What Already Passed External Review

Do not discard the work already completed.

The following direction is accepted as substantially correct:

- Accepted-input resolver starts from `V4_STAGE_ACCEPTED_HEAD`.
- Accepted V4-01/V4-02/V4-03 artifacts are hash-verified.
- Required source cutoff is fixed at `2026-09-24`.
- Required boards are SH_MAIN, SZ_MAIN, CHINEXT, STAR.
- Full-market candidate contains 5,222 unique stock rows.
- Candidate board counts:
  - SH_MAIN = 1702
  - SZ_MAIN = 1494
  - CHINEXT = 1408
  - STAR = 618
- No BSE required-scope claim was introduced.
- V4-03 accepted Stock Core artifact was not rewritten.
- Weekly/monthly inputs are taken from accepted formal CLOSED_ONLY period artifacts.
- `minimum_liquidity` is based on prior 20 amounts and excludes current T.
- Relative state evidence includes `compression_state` and `ma_structure_state`.
- Compression evidence includes `minimum_liquidity`.
- amount/volume state key usage is allowlisted.
- Full-market output is deterministic at the existing R1 candidate.
- No V4-05 execution or premature Accepted Head promotion was found.
- V4 focused regression receipt reports 354 passed, 2 skipped, 0 failed.

The repair must preserve these correct properties.

---

# 3. Blocking Finding B01 — Machine Rule AST Is Not Fully Executable

## 3.1 Problem

`config/v4_04_algorithm_contracts_v1.json` presents itself as the machine-readable V4-04 rule contract.

However the current independent AST evaluator in:

`scripts/verify_v4_04_independent.py`

does not support all operators declared by the machine contract.

The current machine contract contains operators/forms including:

- `SUB`
- `EQ`
- `DIV`
- `MUL`
- `NEG`
- `IN`
- boolean operators
- comparison operators
- `CLOSED_PERIOD_TREND`
- `CLASSIFY_DISTANCE`
- `CLASSIFY_DRAWDOWN`
- `HYSTERETIC_FIRST_TRUE`

Current `eval_node()` does not implement at least `SUB` or `EQ`, and there is not one generic machine execution path for every registered rule family.

Current `machine_expect()` machine-executes only a subset of contracts. Several rule families instead bypass the machine contract and are checked by handwritten duplicate logic, including weekly/monthly trend, near-high, drawdown, severe extension, regime UI and several derived primitives.

Therefore the existing claim that all state AST evidence is independently checked is stronger than the evidence supports.

This conflicts with §81.4's machine-readable contract / executable semantics / independent-vector requirement.

## 3.2 Required Repair

Create one explicit machine-rule execution contract.

Two acceptable approaches:

### Approach A — Complete the current DSL
Extend the independent evaluator so every operator and every V4-04 rule in `v4_04_algorithm_contracts_v1.json` is actually executable.

### Approach B — Normalize the machine contract
Refactor the JSON AST to a smaller canonical DSL where all operators are supported by one generic interpreter.

Forbidden:

- dead/unexecutable AST nodes in the formal contract;
- claiming machine execution while silently falling back to handwritten duplicate rules;
- validating only a convenient subset.

## 3.3 Mandatory Coverage

The machine executor must cover at minimum:

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
- `V4_04_DERIVED_PRIMITIVES_V1`
- `MARKET_REGIME_V1.regime_ui`

If a stateful rule needs a specialized interpreter, such as regime hysteresis, the machine contract must explicitly identify that interpreter contract and the external verifier must execute it independently.

## 3.4 Mandatory Tests

Add tests which:

1. recursively enumerate every operator appearing in `v4_04_algorithm_contracts_v1.json`;
2. assert every declared operator has an independent evaluator implementation;
3. enumerate every registered rule key;
4. assert every rule key has a machine-execution path;
5. fail if a new unsupported operator or rule is added later;
6. execute positive, negative, threshold and UNKNOWN vectors for every rule family.

The next postcheck receipt must expose:

```text
machine_rule_count
machine_rules_executed
machine_rule_coverage
operators_declared
operators_supported
unsupported_operators
unexecuted_machine_rules
```

Acceptance requires:

```text
unsupported_operators = []
unexecuted_machine_rules = []
machine_rule_coverage = 1.0
```

---

# 4. Blocking Finding B02 — Field Registry Does Not Match Actual Artifact Producer Identity

## 4.1 Problem

The current machine registry claims:

- `bias20_atr`: producer `src.v4.profile_core`, producer contract `POSITION_STATE_V1`
- `dist_high20_atr`: producer `src.v4.profile_core`, producer contract `POSITION_STATE_V1`
- `pos250`: producer `src.v4.profile_core`, producer contract `POSITION_STATE_V1`

But the actual implementation produces these fields inside:

`src/v4/profile_primitives.py`

and its `Derived` envelope identifies:

`contract_id = V4_04_DERIVED_PRIMITIVES_V1`

Therefore the formal registry and actual artifact disagree about producer and producer contract.

This is a direct machine-contract identity mismatch.

## 4.2 Required Repair

Make the contract truthful.

Recommended representation for fields physically/algorithmically calculated by `profile_primitives`:

```text
producer = src.v4.profile_primitives
producer_contract_id = V4_04_DERIVED_PRIMITIVES_V1
```

If the field is semantically consumed by Position State, store that separately, for example:

```text
semantic_family = POSITION
consumer_contract_id = POSITION_STATE_V1
```

Do not overload `producer_contract_id` to mean semantic family.

At minimum inspect and reconcile:

- ma10
- bias20_atr
- dist_high20_atr
- pos250
- minimum_liquidity

and every other field in `v4_04_field_registry_v1.json`.

## 4.3 Mandatory Registry-to-Artifact Test

Add an automated test that verifies for every registered field:

- registered producer identity is valid;
- registered producer contract matches artifact envelope contract;
- registered parameter set matches artifact envelope parameter set;
- required/optional status matches schema;
- field appears in exactly the correct envelope;
- no field is silently represented by a different contract.

Generate:

`reports/v4_04/V4_04_REGISTRY_ARTIFACT_CONSISTENCY_R2.json`

Required status: `PASS`.

---

# 5. Blocking Finding B03 — V4-04 Window Traceability Is Too Weak

## 5.1 Problem

The accepted V4-03 factor chain already records detailed per-field window identity:

- window_start_trade_date
- window_end_trade_date
- calendar_span
- actual_count
- suspended_count
- window_identity
- input_digest

The frozen V4-03 field-window mapping also exists:

`config/v4_03_field_window_mapping_v1.json`

The current V4-04 final profile reduces accepted V4-03 primitive metadata to:

```text
quality_state
unknown_reason
output_digest
```

The V4-04 derived `Derived` structure also does not preserve:

- window_start_trade_date
- window_end_trade_date
- suspended_count

The current top-level `technical_window_identity` is only a digest of V4-04 derived window identities. It is not sufficient by itself to demonstrate the complete field→window semantic mapping of the profile.

## 5.2 Required Repair

Do not recompute accepted V4-03 factors merely to add metadata.

Preserve/reference the already accepted window lineage.

The V4-04 candidate must bind:

- accepted V4-03 field-window mapping identity/digest;
- per-field window metadata for accepted primitives, or a deterministic reference to the accepted upstream factor envelope that contains it;
- per-field window metadata for newly derived V4-04 fields.

For V4-04 derived fields add, where applicable:

```text
window_start_trade_date
window_end_trade_date
calendar_span
actual_count
suspended_count
window_contract_id
field_window_mapping_id
```

For CLOSED_ONLY weekly/monthly states preserve/bind:

```text
period window identity
period_last_session
period_view
source_daily_digest
```

The final row should have an explicit field-window mapping identity, not only one opaque aggregate digest.

Do not copy massive upstream evidence unnecessarily if a hash-bound reference is sufficient.

## 5.3 Required Tests

Add cases for:

- uninterrupted actual-bar window;
- one confirmed suspension;
- consecutive confirmed suspensions;
- unexplained data gap;
- recent listing / insufficient actual bars;
- current T suspended;
- weekly closed period;
- monthly closed period.

Verify actual_count/calendar_span/suspended_count/start/end identities and ensure confirmed suspension is not treated as unexplained missing data.

Generate:

`reports/v4_04/V4_04_WINDOW_TRACEABILITY_R2.json`

with mapping digest and validation result.

---

# 6. Blocking Finding B04 — MA10 Has an Undeclared MA20 Dependency

## 6.1 Problem

Current `derive_daily()` MA10 logic requires:

```text
_factor(factors, "ma20") is not None
```

before MA10 can be OBSERVED.

But the machine contract defines MA10 as the mean of the accepted QFQ close over the 10-bar window.

A stock with 10–19 valid adjusted actual bars may have:

```text
MA10 computable
MA20 unavailable
```

Under the current implementation MA10 is incorrectly forced to UNKNOWN.

That is an undeclared dependency.

## 6.2 Required Repair

MA10 must depend only on the inputs required by its frozen contract.

If 10 valid QFQ actual bars are available and source/adjustment/window quality is valid:

```text
ma10 = OBSERVED
```

even if MA20 is UNKNOWN.

`ma_structure_state` may still correctly remain UNKNOWN because MA20 is required there.

## 6.3 Mandatory Test

Create a fixture with:

- 10–19 valid adjusted actual bars;
- MA20 unavailable;
- all MA10 inputs valid.

Expected:

```text
ma10 = OBSERVED
ma_structure_state = UNKNOWN
```

Also verify independent source recomputation.

---

# 7. Required Clarification — Profile Component Status Mapping

Current builder maps profile component state approximately to:

```text
READY if no required state is UNKNOWN
UNKNOWN_DATA if one or more required states are UNKNOWN
```

while profile quality separately uses `COMPLETE / PARTIAL_UNKNOWN`.

The governing contract includes both `PARTIAL` and `UNKNOWN_DATA` as component statuses.

Before R2 publication, freeze a precise mapping among:

- READY
- PARTIAL
- UNKNOWN_DATA
- DEGRADED
- other allowed states

and profile field availability.

If governance already defines this elsewhere, bind and reuse it. Do not invent a second conflicting mapping.

Add tests and machine/output contract coverage.

---

# 8. Independent Postcheck R2 Requirements

Create a new read-only independent verifier result:

`reports/v4_04/V4_04_INDEPENDENT_POSTCHECK_R2.json`

Do not overwrite R1.

The R2 verifier must not invoke the production state producer as its oracle.

It must verify:

## Identity
- accepted-head authority;
- source paths and hashes;
- cutoff and boards;
- row identities;
- contract/parameter/registry hashes;
- field-window mapping hash.

## Machine Contract
- every formal rule has executable machine semantics;
- every operator is supported;
- every machine rule is exercised;
- all full-market state outputs agree with independent execution where evaluable.

## Registry / Artifact
- every registered field has matching producer/contract/parameter identity;
- field envelope location is valid;
- required/optional semantics agree.

## Source Recompute
Retain and strengthen source recomputation for:
- MA10
- minimum_liquidity
- pos250
- bias20_atr
- dist_high20_atr
- weekly trend inputs
- monthly trend inputs

Include suspension/window cases.

## Full-Market Integrity
- 5,222 expected required-scope identities unless accepted upstream data itself changes;
- all four required boards;
- no duplicate security;
- deterministic output digest.

If row count changes, explain exactly why and bind the new upstream/contract identity.

---

# 9. Tests and Evidence

Run at least:

```text
python -m pytest tests/v4_01 tests/v4_02 tests/v4_03 tests/v4_04 tests/v4_joint tests/v4_phase0 -q
```

Do not hardcode pass counts into a sealing script as a substitute for runtime test evidence.

The R2 test receipt must be generated from the actual executed result and bind:

- command
- implementation commit
- test source hashes
- passed
- skipped
- failed
- runtime identity/timestamp if available

The existing repository-wide pytest problem remains a separate cross-cutting audit item:

`docs/audits/V4_GLOBAL_PYTEST_COLLECTION_AUDIT_ITEM_R1_20260929.md`

Do not falsely mark it closed. Do not make unrelated M14 repairs part of V4-04 unless they are demonstrated to be caused by V4-04.

---

# 10. Candidate Versioning and Artifact Preservation

Do not overwrite R1.

Create a new R2 candidate, for example:

`reports/v4_04/staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R2.jsonl.gz`

and R2 versions of:

- candidate receipt
- stage candidate manifest
- consumed-source manifest
- contract/parameter digest receipt
- determinism receipt
- field completeness receipt
- input identity receipt
- row/board count receipt
- test gate receipt
- unknown/quality inventory
- independent postcheck
- registry-artifact consistency receipt
- window traceability receipt

The R1 candidate must remain immutable historical evidence.

---

# 11. Acceptance Gate

The repair may declare:

`V4_04_FULL_PASS_CANDIDATE_R2`

only when all of the following are true:

1. machine AST/operator coverage = 100%;
2. no unsupported formal machine rule/operator remains;
3. registry producer/contract identity matches actual artifact envelopes;
4. window semantics are hash-bound and traceable;
5. MA10 hidden MA20 dependency is removed;
6. component-status mapping is frozen and tested;
7. full-market R2 production completes;
8. independent postcheck R2 passes;
9. deterministic rerun produces identical R2 artifact SHA;
10. focused V4 regression passes;
11. R1 is preserved;
12. V4-05 remains NOT_STARTED;
13. no V4-04 Accepted Head is created before external acceptance.

If any required item cannot be completed, terminal status must be:

`V4_04_BLOCKED_<EXACT_SCOPE>`

---

# 12. Forbidden Work

This repair task must NOT:

- modify TDX source root;
- reopen accepted V4-00～V4-03 business semantics;
- replace accepted upstream heads;
- repair V4-08 sector membership;
- introduce BaoStock turnover;
- add Sector Context;
- add Advanced Structure;
- add PREWATCH;
- add Radar;
- change Focus;
- execute trading logic;
- start V4-05;
- promote V4-04 Accepted Head;
- rewrite/delete the R1 candidate history.

---

# 13. Required Final Developer Report

At completion provide a concise R3/R2-candidate audit document containing:

- starting HEAD;
- ending HEAD;
- files changed;
- B01 disposition;
- B02 disposition;
- B03 disposition;
- B04 disposition;
- component-status mapping disposition;
- machine rule/operator coverage;
- registry/artifact consistency result;
- window traceability result;
- test result;
- full-market row/board counts;
- R2 artifact SHA256;
- independent postcheck result;
- deterministic rerun result;
- global pytest cross-cutting item status;
- confirmation that V4-05 remains NOT_STARTED;
- exact terminal status.

Allowed terminal statuses:

`V4_04_FULL_PASS_CANDIDATE_R2`

or

`V4_04_BLOCKED_<EXACT_SCOPE>`

Stop after producing the candidate and evidence.

Await independent external acceptance before any V4-05 work.
