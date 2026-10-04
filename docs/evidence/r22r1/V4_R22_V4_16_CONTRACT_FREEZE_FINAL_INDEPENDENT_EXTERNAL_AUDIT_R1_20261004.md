# V4 R22｜V4-16 Contract Freeze Final Independent External Audit R1｜2026-10-04

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`

Branch: `codex/v4-system-reform`

Execution baseline: `b2c3dd81c4bfed2364b6ea2693860114421f990c`

Audited remote HEAD: `3fd69721fa8f61aa278b275cb9250bb6829c85a5`

Exact tested source: `2456f6cdae99431bb475f077d4eaccd5f24c3b75`

Immutable tested tag: `refs/tags/codex/r22-contract-tested-source-20261004-r1`

---

# 1. Unique External Decision

```text
R22_EXTERNAL_AUDIT =
PASS_FINAL_V4_16_CONTRACT_FREEZE_CAPABILITY_SCOPED

PRE16_EXTERNAL_ACCEPTANCE_FORMALIZATION = PASS
PRE16_CURRENT_AUDIT_AUTHORITY_V2 = PASS_MACHINE_STATE

V4_16_CONTRACT_PACKAGE = PASS
V4_16_FIELD_REGISTRY = PASS
V4_16_MACHINE_VECTORS = PASS_23
V4_16_NAMESPACE_CONTRACT = PASS
V4_16_SETTLEMENT_WORKER_CONTRACT = PASS
V4_16_SHADOW_HEALTH_CONTRACT = PASS
V4_16_REALTIME_SHADOW_CONTRACT = PASS_CONTRACT_ONLY

V4_16_OBSERVATION_SLOT_SCHEMA = PASS
V4_16_ACCEPTED_CLOCK_AUTHORITY =
NOT_GRANTED_P0_AFFECTED_SCOPE

R22_CLOCK_AUTHORITY_REPAIR_01 =
OPEN_P0_AFFECTED_SCOPE

PRE16_V2_STALE_DESCRIPTIVE_TEXT =
P1_NORMALIZATION_REQUIRED_BEFORE_RUNTIME

V4_16_CONTRACT_FREEZE =
EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED

V4_16_RUNTIME_ENGINEERING_CANDIDATE =
BLOCKED_PENDING_R22R1_CLOCK_AUTHORITY

REAL_SHADOW_EXECUTION =
BLOCKED

REAL_SHADOW_OBSERVATIONS = 0

Production = false
Shadow = false
Focus = false
V4_16 = false
```

R22 is accepted as the contract-freeze stage. This is not a Shadow runtime acceptance.

---

# 2. PRE16 Formalization｜PASS

R22 Phase 0 correctly creates:

```text
data/v4/V4_PRE16_GOVERNANCE_ACCEPTED_HEAD_R1.json
data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V2.json
config/v4_cross_stage_current_audit_authority_v2.json
```

The accepted PRE16 head binds exactly:

```text
audited remote HEAD =
b2c3dd81c4bfed2364b6ea2693860114421f990c

tested source =
dabb5eb2fcdd4b52cfa4d9d684f9d9a9786c42bf

tested tag =
codex/pre16-gov-r1-1-tested-source-20261004-r1

external decision =
PASS_FINAL_CANONICAL_BLOCK_SCOPE_REPAIR
```

Only `GOV_PRE16_01` and `GOV_PRE16_02` are externally closed.

The global contract-entry blocker set becomes `[]`, while capability-only debts remain unchanged.

No V4-10～V4-15 Accepted Head, Stage Head, Data Head or business runtime is changed.

---

# 3. R22 Contract Scope｜PASS

The R22 package freezes versioned contracts for:

```text
Realtime Shadow identity
Observation slot
SHADOW_V4 namespace
Prior-session lineage
Same-day revision
PIT evidence origin
Realtime cohort enrollment
Settlement worker
Shadow health
Capability-scoped blockers
PIT sector membership observation
Machine vectors
Field registry
```

It explicitly keeps:

```text
runtime_implemented = false
runtime_authorized = false
shadow = false
production = false
focus = false
V4_16 = false
```

No `V4_16_ACCEPTED_HEAD` exists.

---

# 4. Evidence Origin / PIT Rules｜PASS

R22 preserves:

```text
PIT_OBSERVED + SHADOW
```

for future real Shadow observation.

It rejects reconstructed/replay evidence from becoming PIT-observed evidence and prevents historical replay from incrementing real Shadow counters.

---

# 5. Namespace / Prior State｜PASS

The Shadow namespace contract freezes:

```text
namespace = SHADOW_V4
read_namespace = SHADOW_V4
write_namespace = SHADOW_V4

legacy_prior_reads = false
legacy_writes = false
legacy_production_continues = true
```

Prior state is the exact previous market-session accepted Shadow head; same-day revisions preserve that predecessor.

Missing prior session fails closed.

---

# 6. Enrollment / Revision Semantics｜PASS

One original realtime enrollment per observation slot is frozen.

Same-day revisions are append-only and preserve:

```text
T0
enrollment_id
control assignment
benchmark basket
FIRST_OBSERVED
```

Focus/UI/ranking cannot remove an otherwise eligible cohort enrollment.

---

# 7. Settlement Worker｜PASS

The contract freezes:

```text
accepted Shadow publication
→ due planner
→ due outbox
→ accepted future Data Head
→ settlement
→ append-only outcome revision
```

It rejects pre-due future reads, raw/provider fallback, T0 rewrites, control redraw, and dropping UI-hidden or invalidated already-enrolled events.

Current real maturity remains none.

---

# 8. Shadow Health / Future Gates｜PASS

R22 does not grant:

```text
SHADOW_STABLE
PROVISIONAL_FORWARD_EVIDENCE
FORWARD_SUPPORTED
```

Real-only counters cannot be filled with replay, reconstruction or engineering fixtures.

---

# 9. Machine Vectors｜PASS

R22 freezes 23 independent required vectors. All remain engineering expectations with:

```text
actual_runtime_executed = false
```

No fake real observation is claimed.

---

# 10. Tested Source / Regression｜PASS

Tested source:

`2456f6cdae99431bb475f077d4eaccd5f24c3b75`

Tag:

`codex/r22-contract-tested-source-20261004-r1`

The tag resolves exactly to the tested commit.

Current branch HEAD is one evidence-only commit ahead.

Clean detached regression:

```text
199 passed
0 failed
0 errors
0 skipped
0 deselected
```

---

# 11. P0 Affected Scope｜Accepted Clock Authority Missing

Independent inspection confirms the finding.

REV4 §51A requires daily scheduled cutoff and observation publication deadline, but the accepted historical V4-00C receipt actually covers publication identity/revision/prior-session semantics and contains no numeric clock values.

This is a genuine post-REV4 contract migration gap.

It must not be repaired by pretending a historical V4-00C clock existed.

Correct status:

```text
R22_CLOCK_AUTHORITY_REPAIR_01 =
OPEN_P0_AFFECTED_SCOPE

engineering_global_block = false
realtime_observation_block = true
```

R22 correctly leaves the observation clock unset and blocks that affected scope.

---

# 12. New Clock Policy Must Be Post-REV4

The next repair must create a new versioned policy authority.

Externally frozen initial Shadow V1 policy candidate:

```text
policy_origin =
POST_REV4_V4_16_EXTERNAL_GOVERNANCE_POLICY

timezone =
Asia/Shanghai

scheduled_source_cutoff_local =
21:00:00

observation_publication_deadline_local =
22:30:00

scheduled_source_cutoff_utc =
13:00:00Z

observation_publication_deadline_utc =
14:30:00Z

market_session_only =
true
```

These are policy values, not claims about historical provider availability.

A later clock-policy change requires a new version and resets the affected Shadow stability window.

---

# 13. Source Visibility Timestamp Semantics

Freeze:

```text
source_provider_available_at
```

as the earliest project-observed authoritative readiness timestamp for the mandatory source actually consumed.

It is not a claim about an unknowable objective provider-server publication time.

`system_available_at` is when those exact source bytes are locally available and have passed the required source acceptance/integrity gate.

Required ordering:

```text
source_provider_available_at
<= system_available_at
<= scheduled_cutoff_at
```

Missing visibility proof means no PIT-observed slot.

---

# 14. P1 Governance Normalization

`V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V2` has correct machine state, but inherited descriptive text still says GOV_PRE16_01 is a global activation hold and carries historical "waiting for external audit / entry hold" wording.

This does not alter permissions and does not invalidate R22.

Before Runtime candidate, create a versioned V3 successor that normalizes only current-facing descriptive semantics while keeping all blocker booleans, capability states and evidence bindings identical.

---

# 15. Final Boundary

R22 may be accepted as:

```text
V4_16_CONTRACT_FREEZE =
EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED
```

The following remain blocked:

```text
V4_16 runtime candidate
real Shadow execution
PIT_OBSERVED publication
real Shadow session counting
V4_16 Accepted Head
Stage promotion
Production/Focus/UI cutover
```

---

# 16. Next

```text
R22R1
CLOCK_AUTHORITY
+
SOURCE_VISIBILITY_TIME_SEMANTICS
+
PRE16_V3_DESCRIPTIVE_NORMALIZATION

→ independent external audit
→ PASS
→ R23 V4-16 Runtime Engineering
```
