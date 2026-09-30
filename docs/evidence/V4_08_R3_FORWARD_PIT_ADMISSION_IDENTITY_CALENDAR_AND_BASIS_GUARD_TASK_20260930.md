# V4-08 R3 Forward PIT Admission + Identity / Calendar / Basis Guard Task

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Required Starting HEAD:** `0581731c1284e82380fa115156f1dc0a16a38bd4`  
**Task Date:** 2026-09-30

---

# 0. External R2 disposition

The independent R2 audit decides:

```text
V4_08_R2_EXTERNAL_ACCEPTANCE_BLOCKED
```

but separately accepts:

```text
B01 = PASS
B02 = PASS
B03 = PASS
B04 = PASS
B05 = PASS
```

Do not reopen or rewrite those repairs unless R3 testing finds a genuine regression.

The external audit also accepts, for go-forward only:

```text
provider_available_at_basis =
PROJECT_FIRST_OBSERVED_PROVIDER_BYTES
```

and:

```text
membership_asof_basis =
PROJECT_FIRST_OBSERVED_SOURCE_STATE
```

subject to the rules below.

# 1. Accepted source-time semantics

For this TDX membership source only, `PROJECT_FIRST_OBSERVED_PROVIDER_BYTES` means:

> the first auditable timestamp by which the project actually observed and froze the complete exact provider byte bundle.

It does NOT mean provider original publication timestamp.

Hard rules:

- never use filesystem mtime as availability;
- never backdate;
- target publication cutoff must be >= complete observation timestamp;
- daily source capture must be frozen independently;
- if no valid capture exists for target date, affected membership is UNKNOWN;
- no silent carry-forward.

This external disposition is authoritative for R3; do not request another identical policy review.

# 2. Go-forward membership-as-of semantics

`PROJECT_FIRST_OBSERVED_SOURCE_STATE` means:

> the TDX membership source state actually visible to the project on the target date before publication cutoff.

It is a knowledge-time snapshot, not a claim about provider historical effective-date announcement.

Rules:

```text
membership_asof_date == target_trade_date
```

and:

- active security lifecycle must be valid on target date;
- pre-list securities found in TDX relationship files must not enter formal active membership;
- capture from an earlier day cannot be reused as an accepted current-day snapshot;
- historical dates before the first accepted forward snapshot remain `CURRENT_MEMBERSHIP_REPLAY / DIAGNOSTIC_ONLY`.

# 3. Workstreams

Run in parallel where possible:

```text
A. B07 source-revision basis repair
B. V4-01 incremental identity/lifecycle revision
C. accepted go-forward market-calendar extension
D. build first forward PIT membership candidate
E. isolated clean-checkout regression
F. Sector / Rotation machine-contract completion
G. Prior-RPS repair continues independently
```

Do not wait for long-run Forward samples.

# 4. Workstream A — B07 Source Revision Basis Guard

R2 migration 018 does not fully bind:

```text
source revision basis
snapshot basis
fact basis
```

Create the next migration, suggested:

```text
019_v4_08_membership_source_basis_guard_r3.sql
```

Do not rewrite 018.

Mandatory invariants:

```text
revision.membership_basis
==
snapshot.membership_basis
==
fact.membership_basis
```

for ordinary raw/PIT/replay lineages.

Derived parent remains a separate explicitly linked lineage.

Formal view must explicitly require:

```text
r.membership_basis = 'PIT_OBSERVED'
s.membership_basis = 'PIT_OBSERVED'
f.membership_basis = 'PIT_OBSERVED'
```

# 5. Basis-Compatible Quality

Add formal compatibility rules.

At minimum:

```text
PIT_OBSERVED_ACCEPTED
=> PIT_OBSERVED

CURRENT_TDX_DIAGNOSTIC
=> CURRENT_TDX_MEMBERSHIP

CURRENT_REPLAY_DIAGNOSTIC
=> CURRENT_MEMBERSHIP_REPLAY

DERIVED_PARENT_DIAGNOSTIC
=> DERIVED_PARENT_MEMBERSHIP
```

A revision with:

```text
membership_basis = CURRENT_TDX_MEMBERSHIP
revision_quality = PIT_OBSERVED_ACCEPTED
```

must be rejected.

# 6. Mandatory B07 Negative Vector

Construct:

```text
source revision:
  basis = CURRENT_TDX_MEMBERSHIP
  quality = PIT_OBSERVED_ACCEPTED

snapshot:
  basis = PIT_OBSERVED

fact:
  basis = PIT_OBSERVED
```

Expected:

```text
REJECT
```

Test at:

- insert trigger;
- formal view;
- independent verifier.

# 7. Workstream B — Re-adjudicate the 11 “AMBIGUOUS” keys

Do NOT use `board_for(code)` as lifecycle truth.

Current 11:

```text
SH.601206
SH.603302
SH.603361
SH.688688
SZ.001235
SZ.001246
SZ.300728
SZ.301569
SZ.301660
SZ.301716
SZ.301718
```

For every key, produce dated lifecycle evidence and one terminal classification:

```text
FORMAL_IN_SCOPE_A_STOCK
NOT_LISTED_AT_TARGET
NON_EQUITY
HISTORICAL_WITHDRAWN_OR_TERMINATED_IPO
TRUE_IDENTITY_GAP
AMBIGUOUS_IDENTITY
```

No regex-only classification is accepted.

# 8. Two known incremental admissions

Independent external evidence already establishes:

## SZ.001246 力勤资源

```text
listing_date = 2026-09-30
board = SZ_MAIN
```

## SZ.301716 鸿富诚

```text
listing_date = 2026-09-29
board = CHINEXT
```

For target date 2026-09-30 these two must not remain generic `AMBIGUOUS_IDENTITY`.

Create a versioned V4-01 incremental identity/lifecycle revision using official exchange/statutory disclosure evidence.

# 9. Known pre-list examples

Independent evidence shows:

```text
SZ.301718
```

has subscription date `2026-10-09`, after the target.

As of 2026-09-30:

```text
SZ.301569
SZ.301660
```

are still issuance/pre-list objects in the checked public new-stock evidence and must not be admitted to the 2026-09-30 active stock universe unless newer official listing evidence proves otherwise.

The remaining historical codes must also be individually adjudicated.

# 10. Incremental V4-01 Identity Revision

Do not overwrite:

```text
data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json
```

Create an append-only go-forward identity revision.

It must include:

- prior accepted identity-map digest;
- target knowledge cutoff;
- new lifecycle events;
- official/source evidence hashes;
- listing dates;
- canonical security ids;
- board ids;
- unresolved remainder;
- independent postcheck.

Suggested artifacts:

```text
data/v4/V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1.json
data/v4/artifact_store/v4_01/security_entity_map_GO_FORWARD_20260930_R1.json

reports/v4_01/V4_01_GO_FORWARD_IDENTITY_INCREMENT_R1.json
reports/v4_01/V4_01_GO_FORWARD_IDENTITY_INDEPENDENT_POSTCHECK_R1.json
reports/v4_01/V4_01_GO_FORWARD_IDENTITY_CLEAN_CHECKOUT_R1.json
```

If project governance requires external promotion, developer creates a candidate head and stops before self-acceptance.

# 11. Required Identity Scope Result

For the first V4-08 formal target:

```text
required four-board lifecycle ambiguity = 0
```

Non-core rows remain diagnostic.

BSE remains under existing optional/degraded policy.

Pre-list objects:

```text
NOT_LISTED_AT_TARGET
```

must not block active four-board scope and must not enter formal member counts.

# 12. Workstream C — Accepted Calendar Extension

Current accepted formal calendar stops:

```text
2026-09-24
```

Create an append-only go-forward calendar extension.

Do not rewrite old V4-02 calendar acceptance.

Minimum coverage:

```text
2026-09-25
through
first proposed V4-08 PIT target session
```

Expected first target may be 2026-09-30 if all gates pass.

Use:

- accepted official exchange closure rules/notices;
- hash-bound session evidence;
- accepted market/index/session evidence as available;
- independent postcheck.

Required output must bind:

```text
market_calendar_id
session_no
trade_date
source digests
system availability
extension parent digest
```

# 13. Calendar Extension Artifact

Suggested:

```text
data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_ACCEPTED_HEAD_R1.json

reports/v4_02/V4_02_GO_FORWARD_CALENDAR_EXTENSION_R1.json
reports/v4_02/V4_02_GO_FORWARD_CALENDAR_EXTENSION_POSTCHECK_R1.json
```

The prior accepted calendar remains immutable.

The extension must prove whether 2026-09-30 is a valid market session under the accepted session chain.

# 14. Workstream D — Build Actual First Forward PIT Membership Candidate

Only after:

```text
A basis guard passes
B identity lifecycle scope passes
C calendar extension passes
```

build an actual candidate.

For target date T:

```text
T >= 2026-09-30
```

and never earlier than complete source observation.

Required:

```text
source bundle captured on T
complete bundle observed_at <= publication cutoff
membership_asof_date = T
provider_available_at_basis =
PROJECT_FIRST_OBSERVED_PROVIDER_BYTES
membership_asof_basis =
PROJECT_FIRST_OBSERVED_SOURCE_STATE
```

# 15. Target-Date Active Universe Gate

Before materializing formal sector members:

1. resolve source_security_key to accepted dated canonical identity;
2. check listing/lifecycle valid at T;
3. check board in required scope;
4. exclude not-yet-listed / delisted / non-equity from formal member set;
5. preserve those source rows in diagnostics.

This is mandatory because TDX membership files may contain pre-list objects.

# 16. Formal Membership Candidate

Formal raw membership candidate may include only:

```text
INDUSTRY
THEME
```

Formal eligibility must exclude:

```text
STYLE
UNKNOWN
DERIVED_PARENT
pre-list
non-equity
unmapped required identity
```

Derived parent remains its own diagnostic lineage until separately accepted.

# 17. First Forward PIT Candidate Evidence

Required at minimum:

```text
reports/v4_08/V4_08_R3_FORWARD_PIT_SOURCE_CAPTURE.json
reports/v4_08/V4_08_R3_FORWARD_PIT_IDENTITY_GATE.json
reports/v4_08/V4_08_R3_FORWARD_PIT_CALENDAR_BINDING.json
reports/v4_08/V4_08_R3_FORWARD_PIT_MEMBERSHIP_CANDIDATE.json
reports/v4_08/V4_08_R3_FORWARD_PIT_INDEPENDENT_POSTCHECK.json
reports/v4_08/V4_08_R3_FORWARD_PIT_DETERMINISM.json
reports/v4_08/V4_08_R3_FORWARD_PIT_TEMPORAL_LEAKAGE.json
```

No V4-08 Accepted Head until independent audit.

# 18. Workstream E — Re-run Clean Checkout with Disposable PostgreSQL

R2's 571-pass regression is functionally useful but does not prove DB isolation because `config/.env` was copied from the primary checkout.

R3 must not do that.

Procedure:

1. create clean detached worktree;
2. do not copy `config/.env`;
3. create disposable localhost PostgreSQL cluster;
4. create fresh `market_research` DB satisfying required DB identity;
5. set `WORKBENCH_PG_DSN` only in process environment;
6. run required migrations;
7. run complete regression;
8. destroy cluster.

Receipt must record sanitized:

```text
configured_or_production_database_used = false
config_dot_env_read = false
dsn_source = PROCESS_ENVIRONMENT_DISPOSABLE_CLUSTER
temporary_cluster_cleaned_up = true
```

No password persisted.

# 19. Required Regression Matrix

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

Do not hardcode pass count.

# 20. Workstream F — Rotation Mandatory R1 Coverage

Current R1 proves only strong_prev=0 does not block IN at age=1.

Add:

## R1A

```text
strong_prev = 0
pulse age = 1
early retained = TRUE
=> ROTATION_IN possible
```

## R1B

```text
strong_prev = 0
pulse age >= 2
early retained = TRUE
breadth_delta1 >= -0.05
=> ROTATION_ACCEPTED possible
```

Neither may qualify EXPANDING / REACCELERATING solely through NOT_APPLICABLE mature retention.

# 21. Machine AST Completion

Convert B0/B1 canonical rules from prose/string predicates into serializable machine AST.

Do not leave canonical leaves as:

```text
"dq5>=10"
```

Each leaf must bind:

```text
field_id
operator
parameter_id or mathematical constant
producer
time role
quality requirement
UNKNOWN behavior
```

Each model contract binds:

```text
model_contract_id
parameter_set_id
AST digest
field registry digest
machine vector set digest
```

# 22. Five V4-00G Retention Parameters

Still pending:

```text
V4_08_EARLY_SEED_RETENTION_MIN
V4_08_EARLY_BREADTH_RETENTION_MIN
V4_08_EARLY_BREADTH_DELTA_MIN
V4_08_EARLY_TOP1_CONCENTRATION_MAX
V4_08_MATURE_STRONG_RETENTION_MIN
```

Do not invent runtime values.

R3 may produce an engineering parameter-decision package. If values are not formally frozen:

```text
affected Rotation formal consumer remains disabled
```

Membership acceptance does not need to wait for these parameters.

# 23. B2 Legacy Adapter

Keep:

```text
NOT_IMPLEMENTED
```

until exact pure-Core legacy AST and golden samples are extracted.

Do not block Sector Native or membership admission on B2.

# 24. Workstream G — Prior-RPS

Continue independently.

Do not:

- change V4-07 thresholds;
- copy V4-03 staging;
- rewrite V4-05.

Prior-RPS remains non-blocking for membership, non-seed Sector Native, calendar extension, identity update and AST engineering.

It blocks true Seed-dependent sector fields.

# 25. Migration Rules

Do not rewrite:

```text
016
017
018
```

Create next migration(s).

R3 rollback must remove only R3 changes.

Independent migration verifier must run against disposable PostgreSQL.

# 26. Required R3 Evidence

At minimum:

```text
reports/v4_08/V4_08_R3_STAGE_ENTRY.md

reports/v4_08/V4_08_R3_SOURCE_BASIS_GUARD_ACCEPTANCE.json
reports/v4_08/V4_08_R3_BASIS_QUALITY_COMPATIBILITY.json

reports/v4_08/V4_08_R3_IDENTITY_LIFECYCLE_ADJUDICATION.json
reports/v4_08/V4_08_R3_FORMAL_UNIVERSE_IDENTITY_GATE.json

reports/v4_08/V4_08_R3_CALENDAR_EXTENSION_BINDING.json

reports/v4_08/V4_08_R3_FORWARD_PIT_SOURCE_CAPTURE.json
reports/v4_08/V4_08_R3_FORWARD_PIT_MEMBERSHIP_CANDIDATE.json
reports/v4_08/V4_08_R3_FORWARD_PIT_INDEPENDENT_POSTCHECK.json

reports/v4_08/V4_08_R3_ROTATION_MACHINE_AST_ACCEPTANCE.json
reports/v4_08/V4_08_R3_ROTATION_VECTOR_COVERAGE.json

reports/v4_08/V4_08_R3_SCHEMA_MIGRATION_RECEIPT.json
reports/v4_08/V4_08_R3_ISOLATED_REGRESSION.json
reports/v4_08/V4_08_R3_CLEAN_CHECKOUT_RECEIPT.json

reports/v4_08/V4_08_R3_STAGE_CANDIDATE_MANIFEST.json
reports/v4_08/V4_08_R3_CLOSURE.md
```

# 27. Developer Terminal State

If membership prerequisite is fully ready:

```text
V4_08_R3_FORWARD_PIT_MEMBERSHIP_CANDIDATE_READY_FOR_EXTERNAL_AUDIT
```

If not:

```text
V4_08_R3_BLOCKED_<EXACT_REMAINING_SCOPE>
```

Do not create V4-08 Accepted Head.

# 28. Development Parallelism

Even while R3 PIT admission work runs, development may continue on:

- Sector Native pure computation;
- structured B0/B1 AST;
- synthetic vectors;
- schema;
- explainability fields;
- Prior-RPS repair.

Do not wait 20 trading days.

Real formal Sector/Rotation full-market publication still requires accepted PIT membership input.

# 29. External Re-audit Handoff

When complete, report:

- exact pushed HEAD;
- commit list;
- migration hashes;
- identity revision head/digest;
- all 11 lifecycle dispositions;
- calendar extension identity/digest;
- first PIT target date;
- source observation/cutoff;
- formal membership rows by type;
- active-universe exclusions by reason;
- B07 negative-vector result;
- clean disposable DB identity;
- regression result;
- R1A/R1B/R2/R3 vector result;
- pending five V4-00G parameters;
- Prior-RPS status;
- no V4-08 Accepted Head assertion.

Then stop for independent external audit.
