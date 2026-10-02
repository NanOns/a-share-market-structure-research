# V4 Next Round Execution Master R16R1｜2026-10-03

## 1. Unique Baseline

```text
REMOTE_HEAD = 92bf5cdefe81da6e809a0dd05dcbd3f651dc35ff
BRANCH = codex/v4-system-reform
```

No other local SHA, stale worktree, prior candidate, or unpublished directory may be used as the execution baseline.

## 2. Mandatory Inputs

Read in this order:

1. `V4_R16_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md`
2. `V4_13_R16R1_PROJECTION_PROVENANCE_ORACLE_REPAIR_TASK_20261003.md`
3. `V4_NEXT_ROUND_EXECUTION_MASTER_R16R1_20261003.md`

Then read the existing R16 task cards and frozen V4-13 v1.1 contracts only as supporting authority.

## 3. Single P0 Mainline

R16R1 is the only P0 mainline:

```text
Structure exact projection semantics
→ component provenance repair
→ independent oracle completion
→ numeric revision repair
→ publication hardening
→ new real revision
→ regression
→ clean detached
→ commit + push
→ STOP
```

Do not start V4-14.

## 4. KEEP Boundary

R16 external audit already accepted the following architecture for KEEP:

```text
Accepted Input Binder
Exact PIT Membership
Target-excluded LOO
No raw/provider fallback
Capability-scoped UNKNOWN
Full 5224-profile real run
Append-only publication
Fresh-process readback
Same-day prior-session isolation
Raw Qualification protection
Clean-detached framework
```

Do not refactor or redesign these unless strictly necessary for the listed repair findings.

## 5. Contract Decision Gate

Before runtime repair:

```text
Does V4-13 v1.1 uniquely specify Structure value + quality + reason + provenance sources?
```

If YES:

```text
runtime repair only
```

If NO:

```text
minimum V1.2 projection/provenance amendment only
```

No broad contract reopening.

## 6. Gate Order

### Gate A — Projection Contract/Mapping

PASS only if every Structure field has explicit value/quality/reason/producer/source mapping.

### Gate B — Runtime Repair

PASS only if no quality/reason inference remains where exact source metadata exists.

### Gate C — Provenance Repair

PASS only if component source identity is field-specific and reconstructable.

### Gate D — Independent Oracle

PASS only if O01-O10 all pass independently.

### Gate E — Revision / Publication Hardening

PASS only if numeric revision ordering and strict write identity/path checks pass.

### Gate F — Real New Revision

PASS only if a new immutable full-universe real revision is produced without overwriting r5.

### Gate G — Regression + Clean Detached

PASS only if protected heads remain byte-identical and clean-detached validation passes.

## 7. Required Evidence

At minimum produce/update evidence for:

```text
contract_amendment_decision.json
structure_projection_mapping.json
projection_lossless_oracle.json
component_provenance_oracle.json
independent_oracle_O01_O10.json
revision_ordering_gate.json
publication_boundary_gate.json
new_real_revision_manifest
fresh_process_readback
clean_detached_gate
final_handoff.json
```

Equivalent project-standard names are allowed, but the evidence must be explicit and machine-verifiable.

## 8. Protected State

Must remain:

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_12_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_13_ACCEPTED_HEAD = NOT_CREATED
```

Protected byte-identical files:

```text
AGENTS.md
data/v4/V4_12_ACCEPTED_HEAD.json
data/v4/V4_STAGE_ACCEPTED_HEAD.json
data/v4/V4_DATA_ACCEPTED_HEAD.json
```

No Production / Shadow / Focus / Migration / Radar / Cohort / Settlement.

## 9. Completion Rule

One unified implementation/evidence sequence is allowed. After final clean-detached validation:

```text
commit
push
STOP
```

Do not self-promote V4-13.

## 10. Only Allowed Final Status

```text
R16R1_PROJECTION_PROVENANCE_ORACLE_REPAIR = PASS
V4_13_R16R1_RUNTIME_CANDIDATE = READY_FOR_EXTERNAL_AUDIT
V4_13_ACCEPTED_HEAD = NOT_CREATED
NEXT = STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```
