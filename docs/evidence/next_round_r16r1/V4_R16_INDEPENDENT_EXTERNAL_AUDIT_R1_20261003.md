# V4-13 R16 Independent External Audit R1｜2026-10-03

## 1. Audit Target

- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- Audited remote HEAD: `92bf5cdefe81da6e809a0dd05dcbd3f651dc35ff`
- Runtime implementation commit: `6ae02c7d95c9c6f51666602f7444baaad3620aef`
- Seal/evidence commit: `92bf5cdefe81da6e809a0dd05dcbd3f651dc35ff`
- Baseline before R16: `dcbfe610b5cb0a8d94dc743963a1fa80f7f71f32`

## 2. Overall Decision

```text
R16_EXTERNAL_AUDIT = PARTIAL_PASS_RUNTIME_REPAIR_REQUIRED

R16A_ACCEPTED_INPUT_BINDER = PASS_KEEP
R16A_TARGET_EXCLUDED_LOO = PASS_KEEP_CAPABILITY_SCOPED
R16B_ADVANCED_PROFILE = PARTIAL_PASS
R16C_APPEND_ONLY_PUBLICATION = PASS_KEEP
R16C_FRESH_PROCESS_READBACK = PASS_KEEP
R16C_REAL_ACCEPTED_SOURCE_RUN = PASS_KEEP_CAPABILITY_SCOPED
R16C_INDEPENDENT_RUNTIME_ORACLE = FAIL_INCOMPLETE_COVERAGE

V4_13_ACCEPTED_HEAD = NOT_AUTHORIZED
V4_14_REPLAY_GATE_B = NOT_AUTHORIZED
```

R16 does not require a rewrite. The accepted-source binder, target-excluded LOO recomputation, fail-closed capability handling, full 2026-09-30 universe run, append-only publication, fresh-process readback, protected-head preservation, and clean-detached evidence are KEEP.

The next round is a narrow repair round only.

## 3. KEEP Scope

The following implementation and semantics are accepted for the repair baseline and must not be reopened unless a repair cannot be completed without a minimal contract amendment:

1. Exact Accepted Head source binding for V4-04 / V4-05 / V4-07 / V4-08 / V4-08 PIT Membership / V4-12.
2. No provider/raw reconstruction fallback.
3. 2026-09-30 exact PIT membership usage.
4. Remove target security before LOO sector aggregate/rank/state computation.
5. Historical LOO capability fail-closed to UNKNOWN when accepted lineage is unavailable.
6. Current membership relation projection remains independent of missing historical LOO capability.
7. Full accepted industry universe run: 5224 profiles.
8. Append-only publication and immutable revisions.
9. Same-day revisions retain exact prior market session instead of chaining `r1 -> r2 -> r3`.
10. Fresh-process persisted readback.
11. Raw qualification protected artifacts remain byte-identical.
12. Stage/Data Heads remain unchanged.
13. Production / Shadow / Focus / Migration remain disabled.

## 4. Blocking Findings

### G01｜P0｜Structure Lossless Projection Is Not Actually Lossless

Frozen requirement:

```text
COPY_VALUE_QUALITY_REASON_PRODUCER_IDENTITY_SOURCE_REF_NO_RECOMPUTATION
```

Current `src/workbench_analysis/v4_13_profile_runtime.py::copy_structure()` infers quality from the copied value when the V4-12 source path is not itself an envelope:

```text
value is None / UNKNOWN -> UNKNOWN
otherwise -> KNOWN
```

and may use `active_projection.reason` as a generic reason.

This is not equivalent to copying V4-12 machine-level quality/reason. In V4-12, `support / acceptance / pullback / recovery` machine quality and reasons are carried by active anchor state observations, not by the plain values in `active_projection`.

`anchor_view_asof_t` also contains its own inner `quality/reason`; wrapping the whole object as outer KNOWN can create an inconsistent `outer KNOWN / inner UNKNOWN` projection.

**Disposition:** BLOCKING. Repair before V4-13 Accepted Head.

### G02｜P0｜Component Source Provenance Is Too Generic

Current component refs are synthesized from broad `binder.refs` and frequently stamped with generic values such as:

```text
producer_contract_id = LOO_CONTEXT_V1
available_at = execution cutoff
source_revision = ARTIFACT_SHA256:<sha>
```

This is not lossless source provenance for each component.

Required repair:

- preserve the actual producer/owner identity for each component;
- preserve exact source path/hash/bytes;
- preserve actual source revision identity;
- preserve source-specific availability semantics where available;
- do not substitute the runtime execution cutoff for the source's own availability identity;
- keep target-excluded LOO derivation identity separate from the underlying accepted owner identity.

**Disposition:** BLOCKING.

### G03｜P0｜Independent Runtime Oracle Coverage Is Incomplete

The independent validator is useful and must be kept, but its `PASS` overstates coverage relative to R16C requirements.

The independent oracle must independently cover at least:

1. membership relation;
2. LOO member exclusion;
3. coverage/minimum-member behavior;
4. known-case sector selector sort;
5. relative-sector substitution;
6. component quality fold;
7. full Structure copy-only value/quality/reason/provenance;
8. dual-source enrichment independence;
9. revision predecessor;
10. append-only identity/conflict behavior.

The current validator does not fully independently establish items 3, 4, 6, 7, 8 and 10.

**Disposition:** BLOCKING.

### G04｜P1｜Revision Ordering Must Be Numeric

`AcceptedInputBinder.load_structure()` currently selects max revision using a string key.

That makes lexical ordering unsafe for `r10+`:

```text
r9 > r10  # lexical bug
```

Use a validated numeric revision ordinal for all revision ordering/comparison logic.

**Disposition:** repair in the same round.

### G05｜P1｜Publication Boundary Hardening

Align `publish_stream()` validation with `publish()`:

- validate `trade_date` as strict `YYYY-MM-DD`;
- validate revision/namespace consistently;
- ensure all write paths resolve under repository root before write.

This is not evidence of current R16 artifact corruption, but it must be hardened before promotion.

## 5. Contract Amendment Boundary

Do **not** let runtime code invent a new business mapping.

First determine whether existing frozen V4-13 v1.1 contracts uniquely and explicitly define the source path for Structure field value **and** source quality/reason/provenance.

If yes:

```text
repair runtime only
```

If no:

```text
publish the minimum V4-13 v1.2 contract amendment needed to make the mapping explicit
```

Allowed scope of a v1.2 amendment is only:

- exact source identity/path for projected Structure quality/reason/provenance;
- no threshold changes;
- no new Structure calculation;
- no new Anchor selection;
- no reopening C01-C04 business semantics;
- no change to V4-08/V4-12 owner semantics.

Any v1.2 amendment must have correct same-contract-family lineage and pass the existing lineage validator.

## 6. Required Repair Round

Next round ID:

```text
R16R1
```

Required work:

1. Freeze/clarify Structure projection provenance mapping.
2. Repair `copy_structure()` to copy exact value/quality/reason/producer/source identity with no inference.
3. Repair component-level source provenance.
4. Expand independent oracle to the full required coverage.
5. Repair numeric revision ordering.
6. Harden streaming publication identity/path validation.
7. Produce a **new** real publication revision; do not overwrite `real/2026-09-30/r5`.
8. Re-run relevant regression and clean-detached validation.
9. Commit + push once and STOP.

## 7. Protected State

Must remain byte-identical unless the task explicitly produces an allowed V4-13 v1.2 contract amendment outside these protected heads:

```text
AGENTS.md
data/v4/V4_12_ACCEPTED_HEAD.json
data/v4/V4_STAGE_ACCEPTED_HEAD.json
data/v4/V4_DATA_ACCEPTED_HEAD.json
```

Must remain:

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_12_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_13_ACCEPTED_HEAD = NOT_CREATED
production = false
shadow = false
focus = false
migration = false
```

## 8. Authorized Next State

Only after R16R1 implementation, tests, independent oracle and clean-detached validation succeed:

```text
V4_13_R16R1_RUNTIME_CANDIDATE = READY_FOR_EXTERNAL_AUDIT
V4_13_ACCEPTED_HEAD = NOT_CREATED
NEXT = STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

No V4-13 promotion and no V4-14 work in R16R1.
