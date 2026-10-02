# R16R1｜V4-13 Projection / Provenance / Oracle Repair Task｜2026-10-03

## 0. Execution Baseline

Use the current remote HEAD as the **only execution baseline**:

```text
92bf5cdefe81da6e809a0dd05dcbd3f651dc35ff
```

Read first:

```text
V4_R16_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md
V4_13_R16R1_PROJECTION_PROVENANCE_ORACLE_REPAIR_TASK_20261003.md
V4_NEXT_ROUND_EXECUTION_MASTER_R16R1_20261003.md
```

Round type:

```text
NARROW REPAIR ONLY
```

Do not reopen R16A/R16C functionality that already passed external audit.

## 1. KEEP — Do Not Rebuild

All of the following are KEEP:

- Accepted-only input binder.
- Exact V4-08 PIT Membership binding.
- Target removal before LOO computation.
- V4-08 owner helper/AST reuse.
- No raw/provider fallback.
- Fail-closed UNKNOWN handling.
- Full 5224-profile 2026-09-30 real scoped run.
- Append-only publication architecture.
- Fresh-process readback.
- Same-day previous-market-session isolation.
- Raw Qualification byte protection.
- Clean-detached evidence framework.
- Protected Stage/Data Heads.

Do not redesign these components.

## 2. P0-1｜Freeze Exact V4-12 Structure Projection Semantics

Before changing runtime code, inspect the current V4-13 v1.1 frozen projection/field contracts and V4-12 accepted publication schema.

For each projected Structure field:

```text
active_anchor_id
anchor_view_asof_t
basic_breakout_state
basic_pullback_state
basic_recovery_state
support_state
acceptance_state
retest_count
structure_events
structure_health
```

produce a machine-readable mapping that uniquely identifies:

```text
value source
quality source
reason source
producer identity source
source-ref identity
```

### Decision Gate

If existing v1.1 contracts already specify this uniquely:

```text
CONTRACT_AMENDMENT = NOT_REQUIRED
```

and only runtime/tests/validator are repaired.

If existing v1.1 contracts do **not** uniquely specify quality/reason/provenance:

```text
CONTRACT_AMENDMENT = REQUIRED_MINIMAL_V1_2
```

Create only the minimum v1.2 contract files necessary to define exact projection provenance.

### v1.2 Constraints

Allowed:

- exact value/quality/reason/provenance source paths;
- explicit mapping from selected active anchor state observations to projected machine fields;
- explicit handling of nested envelope quality/reason;
- correct same-contract-family supersedes lineage.

Forbidden:

- changing any threshold;
- changing Anchor selection;
- recomputing Breakout/Support/Acceptance;
- redefining V4-12 owner semantics;
- reopening R15 C01-C04 business semantics;
- broad contract rewrite.

Any v1.2 amendment must pass the existing R15R1 lineage rules.

## 3. P0-2｜Repair `copy_structure()`

Target module:

```text
src/workbench_analysis/v4_13_profile_runtime.py
```

Required behavior:

```text
COPY_VALUE_QUALITY_REASON_PRODUCER_IDENTITY_SOURCE_REF_NO_RECOMPUTATION
```

Hard requirements:

1. Never infer source quality solely from `value is None / UNKNOWN`.
2. Never use Active Anchor Selector reason as a generic reason for support/acceptance/pullback/recovery.
3. For active-anchor machine fields, copy machine-level quality/reason from the exact accepted V4-12 source defined by the frozen mapping.
4. For nested-envelope fields such as `anchor_view_asof_t`, preserve the actual quality/reason semantics without producing an inconsistent outer KNOWN around an inner UNKNOWN.
5. Preserve exact producer identity/source identity.
6. No Anchor reselection.
7. No Structure recomputation.
8. If exact source metadata is unavailable, fail closed according to the contract; do not invent metadata.

## 4. P0-3｜Repair Component Source Provenance

Target modules may include:

```text
src/workbench_analysis/v4_13_input_binder.py
src/workbench_analysis/v4_13_loo_runtime.py
src/workbench_analysis/v4_13_profile_runtime.py
```

For every `SECTOR_CONTEXT_STATE_V1` component, preserve component-specific provenance.

At minimum, every component source reference must accurately represent:

```text
path
sha256
bytes
producer_contract_id
trade_date
available_at / availability identity when authoritative
source_revision
```

Rules:

- do not stamp every component as `LOO_CONTEXT_V1` when its underlying producer is V4-08 B0 / Rotation / V4-04 Relative State owner etc.;
- keep the LOO derivation identity separately from the underlying accepted producer identity;
- do not use execution cutoff as a fake source `available_at`;
- do not use generic binder-level refs when a field-level source identity exists;
- source refs must be deterministic and lossless enough for an independent validator to reconstruct provenance.

## 5. P0-4｜Complete Independent Runtime Oracle

Target:

```text
scripts/validate_v4_13_r16.py
```

The validator must remain independent from V4-13 calculation helpers for expected-value generation.

It must independently cover all 10 categories:

```text
O01 membership relation
O02 LOO member exclusion
O03 coverage / minimum-member behavior
O04 known-case algorithmic support selector sort
O05 relative-sector substitution
O06 component quality fold
O07 Structure copy-only value + quality + reason + provenance
O08 dual-source rotation/structure enrichment independence
O09 revision predecessor
O10 append-only identity / conflict behavior
```

### Mandatory Negative / Perturbation Cases

Add at least:

- V4-12 source value unchanged but machine quality changes -> V4-13 projected quality must change identically.
- V4-12 machine reason changes -> projected reason must change identically.
- selector reason changes only -> support/acceptance machine reason must **not** be overwritten by selector reason.
- nested `anchor_view_asof_t.quality=UNKNOWN` -> projected field must not be reported as KNOWN.
- source producer/path/hash mismatch -> reject.
- below minimum members -> exact owner-rule UNKNOWN/NA.
- incomplete quote coverage -> UNKNOWN, no zero fill.
- known READY candidates -> exact frozen selector ordering.
- rotation known + structure unknown -> rotation preserved, combined degraded.
- structure known + rotation unknown -> structure preserved, combined degraded.
- overwrite existing revision with changed bytes -> reject append-only conflict.

The final gate may say `independent_runtime_oracle = PASS` only after all O01-O10 are independently proven.

## 6. P1｜Numeric Revision Ordering

Repair all revision ordering/comparison code used by V4-13.

Do not compare revision strings lexicographically.

Required accepted form:

```text
r1 -> 1
r2 -> 2
...
r9 -> 9
r10 -> 10
```

Tests must include at minimum:

```text
r9 vs r10
r10 vs r11
invalid revision -> rejected
```

When selecting the latest authorized same-day V4-12 publication, use numeric revision order.

## 7. P1｜Publication Boundary Hardening

Align `publish_stream()` with strict publication validation.

Required:

- strict namespace validation;
- strict `r[1-9][0-9]*` revision validation;
- strict `YYYY-MM-DD` trade_date validation;
- every resolved write path must stay under repository root;
- append-only conflict remains fail-closed.

Add negative tests for path traversal / invalid trade_date / invalid revision.

## 8. Real Repair Replay

Do not overwrite:

```text
reports/v4_13_runtime_r16/real/2026-09-30/r5/
```

Create a **new revision only** for the repaired real scoped candidate.

Recommended:

```text
r6
```

If `r6` already exists when execution begins, choose the next numeric free revision.

The real repaired publication must still cover the full accepted industry universe and retain capability-scoped UNKNOWN behavior where accepted source capability is unavailable.

No attempt to make UNKNOWN fields artificially KNOWN is allowed.

## 9. Regression Requirements

Must retain and rerun relevant prior regression, including:

- R15 contract vectors;
- R15 business negative gates;
- R15R1 lineage tests;
- R16A LOO runtime tests;
- R16B advanced-profile tests;
- R16C publication/fresh-process tests;
- V4-12 Accepted Head protection;
- V4-08 context-routing authority;
- V4-09 raw qualification protection;
- V4-10/11/12 DAG boundary regressions.

Do not mark obsolete promotion gates as a functional regression failure if they intentionally assert an older accepted-stage state; document any deselection exactly as R16 did.

## 10. Clean Detached Validation

Final tested source must be clean detached.

Record:

```text
source SHA
git clean before/after
test totals
oracle O01-O10 status
new real revision manifest digest
runtime source digests
contract amendment decision
protected head byte hashes
no migration
no production/shadow/focus
```

Final HEAD relative to tested source may contain only seal/handoff/evidence changes.

## 11. Protected Files / State

Must remain byte-identical:

```text
AGENTS.md
data/v4/V4_12_ACCEPTED_HEAD.json
data/v4/V4_STAGE_ACCEPTED_HEAD.json
data/v4/V4_DATA_ACCEPTED_HEAD.json
```

Must remain:

```text
Stage = V4_00_TO_V4_12_ACCEPTED
Data Head = 2026-09-30
V4_13_ACCEPTED_HEAD = NOT_CREATED
Production = false
Shadow = false
Focus = false
Migration = false
```

## 12. Explicitly Forbidden

This round must NOT perform:

- V4_13_ACCEPTED_HEAD creation;
- V4-13 promotion;
- V4-14 Replay Gate B;
- DB migration;
- Production / Shadow / Focus;
- Radar / Cohort / Settlement;
- Data Head advance;
- Stage Head advance;
- raw/provider fallback;
- V4-12 recomputation as a substitute for accepted publication;
- re-opening passed R16A/R16C architecture;
- broad R15 contract redesign.

## 13. Required Final State

After implementation + regression + independent oracle + clean detached validation + unified commit/push, STOP.

The only allowed final state is:

```text
R16R1_PROJECTION_PROVENANCE_ORACLE_REPAIR = PASS

V4_13_R16R1_RUNTIME_CANDIDATE = READY_FOR_EXTERNAL_AUDIT

V4_13_RUNTIME = IMPLEMENTED_SCOPED_ENGINEERING_CANDIDATE_REPAIRED

V4_13_ACCEPTED_HEAD = NOT_CREATED

NEXT = STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```
