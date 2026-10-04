# DM01-R4R1｜PIT Lineage Composition + Real Forward Evidence Repair Task｜2026-10-05

## 0. Mission

Execution baseline:

`862a59c397f1aff1f58acd372ec9048d7b9c508f`

External authority:

`V4_DM01_R4_GO_FORWARD_RUNTIME_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md`

This is a narrow R4 follow-up.

Do not reopen calendar, V2 parent rollover, all-nine wiring or CAS promotion core.

Repair only:

```text
A. inherited reconstructed state is globally relabeled PIT
B. real_forward_evidence is always false but promotion ignores it
C. first_available_at_target_proven is minted without proof
D. promoted whole Data Head is globally overclaimed as PIT/AS_RECORDED
E. R25 must bind exact target-session PIT evidence, not whole-head lineage
```

## 1. Hard Boundary

Do not:

```text
rewrite R3/R3_3 formulas
change all-nine capability meanings
change accepted calendar dates/sources without direct defect
change current V2 parent topology
create real 2026-10-08 data
open future-session network capture
move V4_DATA_ACCEPTED_HEAD
move Stage Head
grant R25
create Real Shadow observations
grant Production / Focus / Default UI
```

## 2. Explicit Lineage Composition

Do not blanket-write every output row as:

```text
PIT_OBSERVED
AS_RECORDED = true
first_available_at_target_proven = true
```

Introduce an explicit composition model that can distinguish:

```text
TARGET_SESSION_PIT_OBSERVATION
INHERITED_ACCEPTED_PARENT_RECONSTRUCTED
DERIVED_FROM_MIXED_PARENT_AND_TARGET
STATIC_ACCEPTED_AUTHORITY_KNOWN_BEFORE_TARGET
```

Recommended component/candidate metadata:

```text
lineage_composition = {
  "parent_head_lineage": "...",
  "target_session_observation_class": "PIT_OBSERVED",
  "contains_inherited_parent_state": true|false,
  "artifact_lineage": "TARGET_ONLY_PIT" | "MIXED_ACCEPTED_PARENT_PLUS_TARGET_PIT",
  "as_recorded_scope": "TARGET_SESSION_OBSERVATION_ONLY"
}
```

Do not erase inherited source/parent provenance.

## 3. Separate Target Observation From First Availability

Add exact fields such as:

```text
target_session_observation_proven
target_session_observed_at
target_session_received_at
```

These may be true when exact native target-session evidence supports them.

Separately:

```text
first_available_at_target_proven
```

may be true only with explicit first-availability proof.

Absence of:

```text
source_provider_available_at
```

must not be converted to true.

Same-day capture proves observation, not provider first availability.

## 4. Real Forward Evidence Admission

Simulation:

```text
real_forward_evidence = false
```

A future real candidate may set:

```text
real_forward_evidence = true
```

only when all are true:

```text
engineering_simulation = false
accepted R4 external envelope exists
target is exact next accepted session
post-close admission passed
required native target-date sources exact-readback
target_session_observation_proven = true
accepted source authority present
all-nine checks pass
permissions remain closed
```

Promotion must explicitly require:

```text
candidate.real_forward_evidence == true
```

The combination:

```text
knowledge_lineage = PIT_OBSERVED
real_forward_evidence = false
```

must fail promotion.

## 5. Preserve Mixed Lineage in New V2 Head

Do not write the whole new head as pure PIT when parent is reconstructed.

Recommended whole-head semantics:

```text
knowledge_lineage =
MIXED_ACCEPTED_PARENT_PLUS_TARGET_SESSION_PIT

AS_RECORDED =
false
```

when inherited parent is not AS_RECORDED.

Add separate target-session fields, e.g.:

```text
target_session_evidence_class = PIT_OBSERVED
target_session_observation_proven = true
target_session_trade_date = T
target_session_source_manifest = exact binding
```

The target increment can be real forward evidence without laundering the entire history.

## 6. First Availability on the New Head

If first availability is not proven for the entire claimed scope:

```text
first_available_at_target_proven = false
```

If a narrower source/fact has exact proof, record the proof only at that narrower scope.

## 7. R25 Bridge

R25 later must consume exact target-session bindings:

```text
target session
target-session source manifest
target-session all-nine receipts
target-session observation receipt
exact Data Head parent/child binding
```

R25 must not infer real-PIT eligibility only from:

```text
V4_DATA_ACCEPTED_HEAD.knowledge_lineage
```

The accumulated Data Head may be mixed while the target-session increment is valid real forward evidence.

## 8. Mandatory Negative / Counterfactual Vectors

At minimum:

```text
R4R1-01
reconstructed V2 parent + real target source
→ target observation may be PIT
→ inherited parent lineage remains reconstructed/mixed

R4R1-02
real candidate real_forward_evidence=false
→ promotion blocked

R4R1-03
same-day capture but no first-availability proof
→ first_available_at_target_proven=false

R4R1-04
source_provider_available_at missing
→ must not mint first_available=true

R4R1-05
simulation attempts real_forward_evidence=true
→ blocked

R4R1-06
target observation before market-close eligibility
→ blocked

R4R1-07
engineering fixture with exact synthetic proof
→ may exercise true branch
→ still NOT real forward evidence

R4R1-08
promoted head from reconstructed parent
→ whole-head lineage is mixed, not pure PIT

R4R1-09
whole-head AS_RECORDED=true while parent AS_RECORDED=false
→ blocked

R4R1-10
R25 admission using only whole-head lineage
→ rejected

R4R1-11
R25 admission using exact target-session PIT receipt
→ contract path allowed
→ no real R25 grant in engineering test

R4R1-12
identity/lifecycle unknown target rows
→ retained explicitly, never silently dropped
```

## 9. PASS_KEEP Boundary

Preserve:

```text
calendar coverage through 2026-12-31
current V2 parent readback
V1 parent rejection
nine wrapper callables
R3_3 function bytes
component/cross postchecks
immutable candidate revision behavior
CAS race rejection
Stage Head protection
Production/Shadow/Focus=false
future WAIT with source_requests=0
R25 auto-grant=false
Real Shadow counter=0
tested-source governance pattern
```

## 10. Required Evidence

Recommended:

```text
reports/dm01_r4r1/
  STAGE_CONTRACT.json
  LINEAGE_COMPOSITION_GATE.json
  TARGET_SESSION_OBSERVATION_GATE.json
  FIRST_AVAILABILITY_GATE.json
  REAL_FORWARD_EVIDENCE_GATE.json
  PROMOTED_HEAD_LINEAGE_GATE.json
  R25_TARGET_SESSION_BINDING_GATE.json
  NEGATIVE_MATRIX.json
  FUTURE_SESSION_WAIT_READBACK.json
  PROTECTED_STATE.json
  LOCAL_TEST_SUMMARY.json
  CLEAN_REGRESSION.json
  TESTED_SOURCE_GOVERNANCE.json
  DM01_R4R1_CANDIDATE_SEAL.json
```

## 11. Required Local Exit

```text
DM01_R4R1_LOCAL_REPAIR =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

DM01_R4_LINEAGE_COMPOSITION =
PASS_LOCAL_REPAIRED

DM01_R4_REAL_FORWARD_EVIDENCE_GATE =
PASS_LOCAL_REPAIRED

DM01_R4_FIRST_AVAILABILITY_SEMANTICS =
PASS_LOCAL_REPAIRED

DM01_R4_PROMOTED_HEAD_LINEAGE =
PASS_LOCAL_REPAIRED

REAL_TARGET_SESSION_PACKAGE =
NOT_CREATED

R25 =
WAIT_ACCEPTED_DAILY_INPUT

REAL_SHADOW_EXECUTION =
NOT_STARTED

REAL_SHADOW_OBSERVATIONS =
0

NEXT =
STOP_WAIT_DM01_R4R1_INDEPENDENT_EXTERNAL_AUDIT
```

Commit/push is not external acceptance.
