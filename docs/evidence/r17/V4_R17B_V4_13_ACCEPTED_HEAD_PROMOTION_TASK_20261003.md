# R17B｜V4-13 Accepted Head Promotion｜2026-10-03

## 0. Entry Gate

R17B may execute only after:

```text
R17A_CROSS_STAGE_GOVERNANCE_REPAIR = PASS
```

External authority:

```text
V4_R16R1_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md
```

Audited R16R1 sealed HEAD:

```text
f12315bf8e3142aa44e9068c5895004c35c4e23c
```

Tested runtime source:

```text
d370788688c7e1be0fe2e3c9b0b160d93374b4ee
```

## 1. Goal

Create the formal V4-13 Accepted Head and advance the global Stage Head only.

```text
V4_13_ACCEPTED_HEAD = CREATED

V4_STAGE_ACCEPTED_HEAD:
V4_00_TO_V4_12_ACCEPTED
→ V4_00_TO_V4_13_ACCEPTED
```

Keep:

```text
V4_DATA_ACCEPTED_HEAD = 2026-09-30
```

## 2. Accepted Candidate

Promote the repaired immutable real candidate:

```text
reports/v4_13_runtime_r16/real/2026-09-30/r6/manifest.json
sha256 =
a02e7918826627c2b496d89e546d3f5a408e4c68a1a89bc93946e152e7ca42ec
```

Do not promote r5. Do not overwrite r5/r6.

## 3. Contract Package

The V4-13 Accepted Head must bind the exact contract package used by r6.

In particular:

```text
config/v4_13_projection_v1_2.json
sha256 =
567b498c9e0f828dc041d56ab56e79c8a4d34877fd09eef46a9c1f504396b19c
```

and the remaining exact R15/R15R1 v1.1 contracts bound by the r6 manifest.

The Accepted Head becomes the formal authority for this package.

Future runtime authority must not rely merely on the existence of:

```text
reports/v4_13_runtime_r16r1/contract_amendment_decision.json
```

If needed, add a minimal formal V4-13 contract-package/entry manifest and make post-promotion readers prefer exact Accepted Head bindings.

Do not redesign contracts.

## 4. Capability Scope

The Accepted Head may claim engineering acceptance only.

Recommended explicit capabilities:

```text
V4_13_PROFILE_ADVANCED_PROJECTION = ENGINEERING_ACCEPTED
V4_13_CURRENT_MEMBERSHIP_RELATION = ENGINEERING_ACCEPTED_PIT_20260930
V4_13_TARGET_EXCLUDED_LOO_CORE = ENGINEERING_ACCEPTED_CAPABILITY_SCOPED
V4_13_STRUCTURE_READ_ONLY_PROJECTION = ENGINEERING_ACCEPTED
V4_13_COMPONENT_PROVENANCE = ENGINEERING_ACCEPTED
V4_13_REVISION_PUBLICATION = ENGINEERING_ACCEPTED
V4_13_REAL_SIGNAL_CAPABILITY = DEGRADED_BY_ACCEPTED_UPSTREAM_CAPABILITY
```

Must NOT claim:

```text
algorithmic_support_sector real READY
relative_sector_state real READY
historical LOO READY
legacy B2 implemented
Production
Shadow
Focus
global mandatory adoption
ALGORITHM_STATE_REPLAY_PASS
```

## 5. Parent Stage Archive

Before replacing moving:

```text
data/v4/V4_STAGE_ACCEPTED_HEAD.json
```

archive the exact V4_00_TO_V4_12_ACCEPTED bytes.

Bind the archive in the V4-13 promotion lineage.

The parent archive must be immutable and hash-exact.

## 6. Stage Head

New Stage Head must include exact binding to:

```text
data/v4/V4_13_ACCEPTED_HEAD.json
```

and preserve all V4-00 through V4-12 accepted bindings and capability scopes.

Required:

```text
accepted_stage_range = V4_00_TO_V4_13_ACCEPTED
production_permission = false
shadow_production_permission = false
```

Do not mutate Data Head.

## 7. Independent Promotion Validation

Add an independent validator proving at least:

```text
P01 external audit exact
P02 audited sealed HEAD exact
P03 tested source exact
P04 r6 manifest exact
P05 r6 artifact refs exact
P06 V4-13 contract package exact
P07 projection v1.2 lineage exact
P08 R17A gate PASS
P09 parent Stage Head archive exact
P10 new Stage Head predecessor exact
P11 Data Head byte-identical
P12 V4-12 Accepted Head byte-identical
P13 no Production/Shadow/Focus
P14 degraded capabilities not overclaimed
P15 V4-14 not yet accepted
```

Negative tests must mutate each major authority binding and verify rejection.

## 8. Clean Detached

Record:

```text
promotion source SHA
parent Stage Head SHA
new V4_13_ACCEPTED_HEAD SHA
new Stage Head SHA
Data Head before/after
V4_12 Head before/after
external audit binding
r6 manifest binding
contract package digest
test totals
git clean before/after
```

## 9. Forbidden

```text
Data Head advance
V4-14 ALGORITHM_STATE_REPLAY_PASS
Production
Shadow
Focus
Radar/Cohort/Settlement
DB migration
raw/provider fallback
retroactive r5/r6 modification
algorithm changes
```

## 10. Completion State

```text
R17B_V4_13_ACCEPTED_HEAD_PROMOTION = PASS

V4_13_ACCEPTED_HEAD = CREATED_EXTERNALLY_AUTHORIZED_ENGINEERING_SCOPE

V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_13_ACCEPTED

V4_DATA_ACCEPTED_HEAD = 2026-09-30

NEXT = R17C_V4_14_REPLAY_GATE_B_CONTRACT_FREEZE_ENTRY
```

Continue directly to R17C.
