# V4 R17R1 Independent External Audit R1｜2026-10-03

## 1. Audit Target
- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- Audited remote HEAD: `47b7f72f374c059f35a66bf2fe298a3ec5fe7efc`
- R17R1 execution baseline: `204d799f26a7badbce3d6b09d3ceed722c522c91`
- Clean tested source: `11d4eae047d09db65ecb4bbbac127d56853bea47`

## 2. Unique Decision

```text
R17R1_EXTERNAL_AUDIT = PASS_FULL_CONTRACT_AUTHORITY_CLOSURE

R17R1A_V4_13_ACTIVE_BINDING_REPAIR = PASS
R17R1B_V4_14_CONTRACT_REFREEZE = PASS

ACTIVE_CONTRACT_FAMILY_CLOSURE = PASS

V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_13_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

V4_14_CONTRACT_COMPLETENESS =
EXTERNALLY_ACCEPTED_READY_FOR_RUNTIME_IMPLEMENTATION

V4_14_RUNTIME =
AUTHORIZED_NEXT_SCOPED_ENGINEERING

V4_14_ACCEPTED_HEAD =
NOT_AUTHORIZED_YET

ALGORITHM_STATE_REPLAY_PASS =
NOT_GRANTED_YET
```

R17R1 is fully accepted for the authorized contract/governance scope.

## 3. PASS / KEEP

### V4-13 active authority repair
Accepted:
- `PROFILE_ADVANCED_PROJECTION_V1 -> projection v1.2`;
- `V4_13_DAG_INTEGRATION_INTERFACE_V1 -> DAG v1.2`;
- `ROTATION_STRUCTURE_ENRICHMENT_V1 -> enrichment v1.2`;
- transitive authority propagation through `field_registry v1.2`, `output_schema v1.2`, and `machine_vectors v1.2`;
- amended Accepted Head preserves r6, capabilities, degradation state and permissions;
- original `V4_13_ACCEPTED_HEAD.json` remains immutable historical evidence;
- Stage remains `V4_00_TO_V4_13_ACCEPTED`;
- Data Head remains `2026-09-30`.

Independent structured comparison confirms the added v1.2 field/output/vector artifacts only propagate authority/lineage changes and do not change business thresholds or algorithm semantics.

### V4-14 contract re-freeze
Accepted:
- all five v1.1 V4-14 contract-family successors;
- exact supersedes lineage;
- amended V4-13 authority binding;
- active DAG / Projection / Enrichment bindings;
- all 17 Replay Gate B dimensions unchanged;
- 60 frozen vectors retained;
- exact T-1 previous-market-session semantics retained;
- same-day r1/r2 isolation retained;
- evidence-class separation retained;
- UNKNOWN-never-FALSE retained;
- append-only revision semantics retained.

### Active-family closure
The final active package contains no superseded V4-13/V4-14 contract as a current runtime/consumer binding.

Old members appear only in explicit lineage roles such as:
- `supersedes`;
- `derived_from`;
- `historical_lineage`.

This is accepted.

## 4. Regression / Seal

```text
938 PASS
0 FAIL
0 ERROR
0 SKIP
0 DESELECT
```

Clean detached source:
`11d4eae047d09db65ecb4bbbac127d56853bea47`

Final remote seal:
`47b7f72f374c059f35a66bf2fe298a3ec5fe7efc`

The final seal commit adds evidence only; runtime/contract implementation bytes are unchanged from the tested source.

## 5. Runtime Boundary

R17R1 accepts the V4-14 contract package, but does not itself satisfy Replay Gate B.

The next round may implement the scoped V4-14 replay runtime.

The next round must NOT:
- create `V4_14_ACCEPTED_HEAD`;
- advance Stage Head;
- grant `ALGORITHM_STATE_REPLAY_PASS`;
- enable Production / Shadow / Focus;
- use raw/provider fallback to manufacture real capability.

Formal acceptance still requires independent audit after runtime candidate implementation.

## 6. Authorized Next Round

```text
R18A
V4-14 Replay Authority / Runtime Harness

R18B
Cross-process Persisted Full-DAG Replay + Same-day Revision E2E

R18C
Independent Replay Oracle + Capability-scoped Real Replay + Clean Seal

STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```
