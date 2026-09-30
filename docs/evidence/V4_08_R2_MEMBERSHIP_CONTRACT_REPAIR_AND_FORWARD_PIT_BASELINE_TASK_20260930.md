# V4-08 R2 Membership Contract Repair + Forward PIT Baseline Task

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Task Date:** 2026-09-30  
**Required Starting HEAD:** `68276e4f48f7664827418a6095b3a0ddcc1fa0a8`

---

# 0. External audit decision

Current accepted range:

```text
V4_00_TO_V4_07_ACCEPTED
```

V4-06 promotion:

```text
PASS
```

V4-07 promotion:

```text
PASS_WITH_GOVERNANCE_NOTE
```

V4-08 R1:

```text
V4_08_MEMBERSHIP_EXTERNAL_ACCEPTANCE_BLOCKED_R1
CONTRACT_PERSISTENCE_REPAIR_AND_TRUE_FORWARD_PIT_BASELINE_REQUIRED
```

Prior-RPS:

```text
INVESTIGATION_PASS
REPAIR_OPEN_NON_BLOCKING_FOR_UNRELATED_ENGINEERING
```

---

# 1. Objective

This task has five parallel workstreams:

```text
A. Repair V4-08 membership contract/persistence defects.
B. Build the first real go-forward PIT membership candidate.
C. Resolve identity scope without letting non-core instruments block the formal stock universe.
D. Start V4-08 Sector / Rotation contract + machine-vector engineering in parallel.
E. Continue Prior-RPS accepted lineage repair independently.
```

Do not wait multiple trading days before D.

Do not start V4-09 formal production.

---

# 2. Hard prohibitions

Do not:

- rewrite V4-00~V4-07 Accepted Heads;
- backdate current membership to 2026-09-28 as PIT;
- treat filesystem mtime as provider availability;
- silently drop unknown membership rows;
- let ETF/bond/BSE/non-core rows automatically block the entire formal four-board stock scope;
- coerce Base Seed UNKNOWN to zero;
- copy V4-03 R3 prior-RPS staging into accepted lineage;
- allow STYLE/UNKNOWN into formal Sector/Rotation;
- mix raw membership and derived-parent membership under one incompatible snapshot header;
- use a formal SQL view that omits membership-quality gates.

---

# 3. Workstream A1 — Split Membership Basis Lineages

Current R1 mixes:

```text
CURRENT_TDX_MEMBERSHIP
DERIVED_PARENT_MEMBERSHIP
```

inside the same current artifact/snapshot digest.

This conflicts with the DB snapshot header contract.

R2 must split them.

Recommended model:

```text
Snapshot A:
RAW_CURRENT_TDX_MEMBERSHIP

Snapshot B:
DERIVED_PARENT_MEMBERSHIP
parent_snapshot_of = Snapshot A
```

or equivalent versioned relation.

Required:

- one snapshot has one canonical membership_basis;
- fact basis matches snapshot basis;
- parent facts reference raw child snapshot/source lineage;
- derived-parent facts cannot appear in formal consumer until separately accepted;
- historical replay keeps parent provenance explicit.

Do not overwrite parent basis with generic CURRENT_MEMBERSHIP_REPLAY.

---

# 4. Workstream A2 — Formal View Quality Gate

Create a new migration; do not rewrite migration 016.

Suggested:

```text
018_v4_08_membership_contract_repair_r2.sql
```

Update formal read model so every row requires at least:

```text
sector_type in allowed formal types
membership_basis = PIT_OBSERVED
membership_quality = PIT_OBSERVED_ACCEPTED
pit_observed = true
historical_backtest_safe = true
identity_status = MAPPED
security_id IS NOT NULL
```

Also bind the relevant accepted snapshot/source revision quality.

Add negative tests proving:

```text
PIT_OBSERVED + SOURCE_TIME_UNVERIFIED
```

does NOT enter formal view.

---

# 5. Workstream A3 — Fix historical_backtest_safe Semantics

Remove the current semantic equivalence:

```text
historical_backtest_safe == (membership_basis == PIT_OBSERVED)
```

Correct relation:

```text
historical_backtest_safe = true
ONLY IF
PIT basis
AND accepted membership quality
AND accepted temporal evidence
AND accepted identity
AND valid revision chain
```

A PIT-observed but degraded fact/snapshot is allowed to exist with:

```text
pit_observed = true
historical_backtest_safe = false
```

Formal view must exclude it.

Migration and Python contract must match.

---

# 6. Workstream A4 — Effective-Date / Staleness Contract

Current:

```text
membership_asof_date <= target_trade_date
```

is insufficient without an effective interval.

Choose exactly one R2 contract:

## Option 1 — Daily Exact Snapshot

For the first implementation:

```text
membership_asof_date == target_trade_date
```

No carry-forward.

This is recommended for V4-08 R2.

## Option 2 — Explicit Effective Interval

Add:

```text
effective_from
effective_to
```

and prove target date is covered.

Do not keep the current unlimited `<=` semantics.

Machine vectors/tests must cover stale source rejection.

---

# 7. Workstream A5 — Source Revision Identity Must Support Metadata-Evidence Revision

Current:

```text
source_revision_id = sha256(source_digest)
```

cannot represent:

```text
same source bytes
+
new provider-availability/effective-date evidence
```

without mutating an existing append-only row.

R2 must version temporal evidence.

Recommended fields:

```text
source_bytes_digest
temporal_evidence_digest
source_revision_id
supersedes_revision_id
provider_available_at
provider_available_at_basis
membership_asof_date
membership_asof_basis
```

Revision identity should bind both:

```text
bytes identity
+
temporal evidence identity
```

A metadata/evidence correction with identical bytes must create a new append-only revision.

Test this exact case.

---

# 8. Workstream B — First Real Go-Forward PIT Baseline

The R1 source capture is real:

```text
observed_at =
2026-09-30T00:45:21.889920Z
```

It cannot become 2026-09-28 PIT.

Determine the first formal target session from:

```text
accepted market calendar
+
accepted publication cutoff
```

Do not infer from wall-clock date alone.

If the current session is eligible, preserve the frozen R1 source bytes as candidate input.

---

# 9. Provider Availability Policy

First search the source/provider evidence for a real provider availability timestamp.

If authoritative provider timestamp exists:

bind it.

If the local TDX source does not expose one, create a **source-specific contract amendment candidate**, not a silent inference.

Allowed candidate concept:

```text
provider_available_at_basis =
PROJECT_FIRST_OBSERVED_PROVIDER_BYTES

provider_available_at =
first actual project observation time of the exact frozen provider bytes
```

Semantics:

> This timestamp does not claim the provider's original publish time. It is a conservative evidenced time by which the project proves those provider bytes were available.

This candidate must:

- be versioned;
- explain why it is conservative;
- never backdate availability;
- be externally reviewed before formal acceptance;
- remain distinct from filesystem mtime.

If REV2/Phase0 contract cannot legally support this interpretation, keep PIT blocked and create a formal contract-amendment candidate for external review.

---

# 10. First PIT Date Rules

A formal PIT snapshot may be created only when:

```text
target_trade_date is an accepted market session
membership_asof_date covers exactly that target under R2 contract
provider/system availability <= publication cutoff
source bytes were frozen before cutoff
identity scope passes
formal quality passes
```

Do not create PIT for an earlier accepted market session using bytes first observed later.

---

# 11. Workstream C — Scope-Aware Identity Classification

R1 has:

```text
497 unresolved source keys
1,176 membership facts
```

Classify every unresolved key.

Use accepted security lifecycle / security-type logic.

At minimum:

```text
FORMAL_IN_SCOPE_A_STOCK
BSE_OPTIONAL
ETF_OR_FUND
CONVERTIBLE_BOND
INDEX
B_STOCK
OTHER_NON_CORE
NOT_LISTED_AT_TARGET
TRUE_IDENTITY_GAP
AMBIGUOUS_IDENTITY
```

Use existing security classification utilities where appropriate.

Do not classify by a one-off regex alone if accepted lifecycle metadata is available.

---

# 12. Formal Identity Gate

Formal V4-08 scope currently targets:

```text
SH_MAIN
SZ_MAIN
CHINEXT
STAR
```

Non-core source rows:

- remain in raw diagnostic evidence;
- retain source key/type;
- are not silently deleted;
- do not block formal four-board membership merely because they lack a V4 stock identity.

BSE continues under its existing optional/degraded policy unless the accepted project scope changes.

Only:

```text
TRUE_IDENTITY_GAP / AMBIGUOUS_IDENTITY
```

inside the required formal target universe blocks that affected scope.

Produce exact counts by category and board.

---

# 13. Incremental Identity Update

If any unresolved formal A-share key reflects a security that became eligible after the old V4-01 identity-map cutoff:

do not hand-map it inside V4-08.

Run a versioned incremental identity/lifecycle update and produce a new accepted identity revision.

Preserve the old V4-01 accepted artifact.

Bind V4-08 to the new accepted identity revision only after its own validation.

---

# 14. Workstream D — Begin V4-08 Algorithm Contract Engineering

Do not wait for membership acceptance to begin pure contract work.

Create/freeze stage-owned candidates for:

```text
Sector Native consumer contract
B0 Sector PREWATCH
B1 ROTATION_CORE_V1
B2 Legacy Sector Adapter
Sector field registry
parameter sets
machine vectors
synthetic scenarios
```

No real full-market materialization yet.

---

# 15. B0 / B1 / B2 Hard Input Boundary

Machine contracts must reflect REV2:

```text
B0/B1/B2 read accepted Core / Base Seed / accepted PIT membership
```

Forbidden:

```text
same-day final stock PREWATCH
Focus
Radar
V4-06 turnover as hard eligibility
future confirmation
future outcome
```

Base-Seed dependent inputs while Prior-RPS is degraded:

```text
UNKNOWN / DEGRADED_BY_UPSTREAM_BASE_SEED_SIGNAL
```

Never zero.

---

# 16. Rotation R1 Mandatory Synthetic Cases

Freeze at least REV2-required:

## R1

```text
strong_prev = 0
positive basket return
seed/breadth retention maintained
=> IN / ACCEPTED still possible
```

## R2

```text
old strong sector
strong retention drops
breadth worsens
=> no EXPANDING / REACCELERATING
```

## R3

```text
single leader concentration high
no breadth diffusion
=> no ACCEPTED / EXPANDING
```

Store:

- parameter instance;
- predicate truth values;
- independent expected result.

These tests do not authorize real production before PIT membership acceptance.

---

# 17. Workstream E — Prior-RPS Repair Continues

Use:

`V4_07_PRIOR_RPS_BOOTSTRAP_GAP_ASSESSMENT_R1`

as the starting evidence.

Required repair:

- accepted prior-session universe identity;
- accepted session calendar;
- accepted adjustment/source identities;
- RPS cross-sectional values for required T-1/T-3 sessions;
- first-available and warm-up reconciliation;
- independent recomputation;
- new accepted factor publication/revision.

Do not rewrite V4-05.

Do not copy R3 staging.

---

# 18. Prior-RPS Parallelism

Prior-RPS repair does NOT block:

- membership contract repair;
- source capture;
- Sector Native non-seed primitives;
- Rotation/Sector AST design;
- machine vectors;
- persistence schema engineering.

It blocks only consumers requiring true Base Seed / Seed Width semantics.

---

# 19. Required R2 Evidence

At minimum:

```text
reports/v4_08/V4_08_R2_STAGE_ENTRY.md

reports/v4_08/V4_08_R2_CONTRACT_REPAIR_ACCEPTANCE.json
reports/v4_08/V4_08_R2_MIXED_BASIS_SPLIT_VERIFICATION.json
reports/v4_08/V4_08_R2_FORMAL_VIEW_QUALITY_GATE.json
reports/v4_08/V4_08_R2_EFFECTIVE_DATE_VERIFICATION.json
reports/v4_08/V4_08_R2_SOURCE_REVISION_METADATA_TEST.json

reports/v4_08/V4_08_R2_IDENTITY_SCOPE_CLASSIFICATION.json
reports/v4_08/V4_08_R2_FORMAL_UNIVERSE_IDENTITY_GATE.json

reports/v4_08/V4_08_R2_FORWARD_SOURCE_AVAILABILITY_EVIDENCE.json
reports/v4_08/V4_08_R2_GO_FORWARD_PIT_CANDIDATE.json

reports/v4_08/V4_08_R2_DETERMINISM.json
reports/v4_08/V4_08_R2_TEMPORAL_LEAKAGE.json
reports/v4_08/V4_08_R2_REVISION_CHAIN.json
reports/v4_08/V4_08_R2_SCHEMA_MIGRATION_RECEIPT.json
reports/v4_08/V4_08_R2_CLEAN_CHECKOUT_RECEIPT.json
reports/v4_08/V4_08_R2_REQUIRED_REGRESSION.json

reports/v4_08/V4_08_R2_STAGE_CANDIDATE_MANIFEST.json
reports/v4_08/V4_08_R2_CLOSURE.md
```

For algorithm contract parallel work:

```text
config/v4_08_sector_native_contract_v1.json
config/v4_08_sector_prewatch_contract_v1.json
config/v4_08_rotation_core_contract_v1.json
config/v4_08_sector_legacy_adapter_contract_v1.json
config/v4_08_algorithm_parameter_set_v1.json
config/v4_08_algorithm_machine_vectors_v1.json
```

Naming may follow repository conventions.

---

# 20. Mandatory New Tests

Add tests for the R1 gaps:

1. raw and derived-parent facts cannot share an incompatible snapshot header;
2. formal SQL view rejects `PIT_OBSERVED + non-accepted quality`;
3. PIT observed may exist with `historical_backtest_safe=false`;
4. stale membership_asof_date is rejected under exact-day contract;
5. same bytes + new temporal evidence creates a new source revision;
6. temporal evidence revision cannot mutate prior accepted revision;
7. non-core unresolved ETF/bond/index does not block formal A-stock scope;
8. unresolved required A-stock does block affected formal scope;
9. unknown source row remains in diagnostics;
10. first forward PIT date cannot precede project observation;
11. future membership correction cannot modify prior publication;
12. derived parent remains diagnostic until independent acceptance;
13. Seed-dependent sector fields remain UNKNOWN under V4-07 signal degradation.

---

# 21. Migration Rule

Do not rewrite:

```text
016
017
```

Create new repair migration(s), starting at the next available number.

Record exact checksum.

Run isolated PostgreSQL.

Rollback only new stage objects/alterations.

---

# 22. Promotion Rule

Do not create:

```text
V4_08_ACCEPTED_HEAD.json
```

until independent external audit accepts the PIT membership prerequisite.

R2 developer terminal state should be one of:

```text
V4_08_R2_MEMBERSHIP_CANDIDATE_READY_FOR_EXTERNAL_AUDIT

or

V4_08_R2_MEMBERSHIP_BLOCKED_<EXACT_SCOPE>
```

No self-acceptance.

---

# 23. Real Production Authorization

Even if algorithm contracts/vectors pass:

```text
V4-08 FULL-MARKET FORMAL PRODUCTION
```

remains forbidden until:

```text
accepted PIT membership baseline
```

exists.

After first accepted go-forward snapshot:

- Forward Sector/Rotation may begin from that date;
- pre-baseline historical sector results remain `CURRENT_MEMBERSHIP_REPLAY / DIAGNOSTIC_ONLY`;
- no requirement to fabricate strict PIT history before deployment.

---

# 24. Regression

Run:

```text
tests/v4_01
tests/v4_02
tests/v4_03
tests/v4_04
tests/v4_05
tests/v4_06
tests/v4_07
tests/v4_08
tests/v4_joint
tests/v4_phase0
```

plus new V4-08 algorithm contract/vector tests.

Do not hardcode pass count.

---

# 25. Developer closure

Report exact:

## Membership

- starting HEAD;
- new migration hashes;
- raw snapshot digest;
- derived-parent snapshot digest;
- membership source revision identity;
- temporal evidence revision identity;
- first candidate PIT trade date;
- provider availability basis;
- source observed/system/provider timestamps;
- identity classification counts;
- true formal identity gaps;
- formal eligible row count;
- historical diagnostic row count;
- determinism;
- temporal leakage;
- clean checkout;
- regression.

## Sector / Rotation contracts

- contracts frozen;
- parameter set id/hash;
- machine vector count;
- R1/R2/R3 results;
- real production still disabled.

## Prior-RPS

- current open/closed status;
- accepted publication created or not;
- no threshold changes;
- no old artifact mutation.

Then stop for external audit.
