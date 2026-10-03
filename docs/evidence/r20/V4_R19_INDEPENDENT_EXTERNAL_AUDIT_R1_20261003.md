# V4 R19 Independent External Audit R1｜2026-10-03

## 1. Audit Target
- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- Audited remote HEAD: `2020234020e09020aca13fd84cdabde6fbb81f50`
- R19 baseline: `f4ad7d632e53734798c064f011e2b53ecd99bc27`
- Reported tested candidate source: `3bec750b67e90a281ee70220916da9f105947066`

## 2. Unique Decision
```text
R19_EXTERNAL_AUDIT =
PARTIAL_PASS_CURRENT_STAGE_RUNTIME_ENTRY_REPAIR_REQUIRED

R19A_V4_14_ACCEPTED_HEAD = PASS_KEEP
R19A_STAGE_RANGE_PROMOTION = PASS_KEEP
R19A_STAGE_HEAD_V4_14_ENTRY_COHERENCE = FAIL_P0

R19B_RADAR_COHORT_CONTRACT_FREEZE = PASS_KEEP
R19C_SETTLEMENT_CONTRACT_FREEZE = PASS_KEEP
R19D_V4_15_CONTRACT_INTEGRATION = PASS_KEEP

V4_15_CONTRACT_PACKAGE =
EXTERNALLY_ACCEPTED_CONTRACT_SCOPE_RUNTIME_ENTRY_BLOCKED

R19_AUDIT_01_BYTE_IDENTITY_PORTABILITY = OPEN_P1
R19_AUDIT_02_CURRENT_STAGE_READER_COMPATIBILITY = FAIL_P0

TESTED_SOURCE_REMOTE_ADDRESSABILITY = OPEN_P1

V4_15_RUNTIME =
NOT_AUTHORIZED_UNTIL_R20A_CURRENT_STAGE_AUTHORITY_PASS_LOCAL
```

## 3. R19A Promotion｜PASS KEEP
The V4-14 Accepted Head is created with the correct capability-scoped semantics:
```text
status = ALGORITHM_STATE_REPLAY_DEGRADED_PASS
ALGORITHM_STATE_REPLAY_PASS = DEGRADED_PASS_CAPABILITY_SCOPED
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED
REAL_ACCEPTED_SOURCE_REPLAY = PASS_CAPABILITY_SCOPED
production = false
shadow = false
focus = false
V4_15_runtime = false
```

The Stage Head range is correctly advanced to:
```text
V4_00_TO_V4_14_ACCEPTED
```

The Data Head remains:
```text
2026-09-30
```

These items are KEEP.

## 4. P0 G01｜Stage Head Contains a Contradictory v4_14_entry
The promoted moving Stage Head contains:
```text
accepted_stage_range = V4_00_TO_V4_14_ACCEPTED
v4_14_status = ALGORITHM_STATE_REPLAY_DEGRADED_PASS
v4_14_external_acceptance = PASS_FINAL_V4_14_RUNTIME_CAPABILITY_SCOPED
v4_14_binding = data/v4/V4_14_ACCEPTED_HEAD.json
```

but still retains:
```text
v4_14_entry = CONTRACT_FREEZE_ONLY_NOT_REPLAY_PASS
```

This value was inherited from the V4-13 parent because the R19A writer did not update it.

The formal current pointer is therefore internally contradictory.

The V4-14 Accepted Head itself remains valid. Repair only the moving Stage Head governance.

Required target:
```text
v4_14_entry =
COMPLETED_EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED_REPLAY_GATE_B
```

or one exactly equivalent frozen value defined by the repair contract.

Do not recreate or supersede the V4-14 Accepted Head merely to repair this Stage Head field.

## 5. P0 G02｜Current Runtime Reader Rejects the Promoted Stage
`src/workbench_analysis/v4_14_authority.py` still:
1. calls `validate_r17r1_active_closure`;
2. reads the moving Stage Head;
3. takes `stage['v4_13_binding']`;
4. treats V4-13 as the current runtime authority.

But `scripts/validate_r17r1_active_closure.py` explicitly asserts:
```text
stage['accepted_stage_range'] == V4_00_TO_V4_13_ACCEPTED
```

and `src/workbench_analysis/v4_13_accepted_contract_package.py::current_contracts()` only accepts V4-12 or V4-13 ranges.

Therefore the valid promoted pointer:
```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_14_ACCEPTED
```
cannot be consumed by the legacy current-stage reader.

This is a real V4-15 runtime-entry blocker.

Historical validators may remain frozen and run against archived historical Stage Heads. They must not be weakened merely to accept the new current pointer.

## 6. R19B / R19C / R19D｜PASS KEEP
Independent inspection supports KEEP.

Contract closure:
```text
contract_count = 26
field_count = 139
cross_vector_count = 13
```

The package freezes:
- Radar event projection;
- complete daily ledger;
- logical events / observations;
- enrollment identity;
- complete Validation Cohort;
- due planner;
- 1/3/5/10/20-session Forward paths;
- common-basis R/MFE/MAE/MDD;
- competing outcomes;
- market / sector / rotation benchmarks;
- Control A/B/C;
- evaluation revisions;
- readback;
- capability degradation;
- storage design;
- forbidden non-edges.

Forbidden edges include:
```text
Focus -> enrollment
UI Top-K -> enrollment
Forward outcome -> T0 state
FEP prediction -> Core/Radar
Corrected outcome -> T0
future source -> same-day decision
```

MARKED_ESTIMATE numeric coverage / quote-age gates remain unset, and no threshold was invented.

No V4-15 runtime, Accepted Head, real enrollment, real settlement, Stage advance beyond V4-14, Data advance, Production, Shadow or Focus permission exists.

Therefore:
```text
V4_15_CONTRACT_PACKAGE =
EXTERNALLY_ACCEPTED_CONTRACT_SCOPE_RUNTIME_ENTRY_BLOCKED
```

## 7. P1 G03｜Historical Byte Identity Portability
R19 validation exposed historical accepted artifacts whose Windows worktree representation may differ from Git blob representation due CRLF/LF handling.

The local clean runner can restore declared representations, but there is not yet a project-wide frozen authority defining:
- which files require literal exact bytes;
- which files permit an audited CRLF/LF representation equivalence;
- how binary/LFS files are handled.

This is not a business-algorithm defect and should not block V4-15 implementation after R20A.

It must be closed before claiming fully portable external replay/reproduction.

## 8. P1 G04｜Tested Candidate Is Not Directly Addressable
R19 reports:
```text
tested_candidate_source =
3bec750b67e90a281ee70220916da9f105947066
```

but that commit is not reachable through the remote branch/history available to the external GitHub reader.

It is stored inside:
```text
reports/r19/TESTED_SOURCE.bundle
```

The normal connector cannot decode the binary bundle directly. This reduces independent remote audit convenience.

Future seal governance should expose the exact tested source through a reachable immutable Git ref/tag or branch ancestry, or an equivalently directly addressable audit object.

This does not invalidate the final-head contract artifacts already inspected.

## 9. Regression Evidence
R19 discloses two clean contexts:
```text
audited baseline:
1168 passed
0 failed
0 skipped
0 deselected

candidate:
62 passed
0 failed
0 skipped
0 deselected

total:
1230 passed
```

The split scope is correctly disclosed and does not pretend old validators are current-pointer compatible.

## 10. Authorized Next Round
Do not block the mainline on the P1 portability work.

```text
R20A Current Stage Authority / Reader Governance Repair [P0]
        ↓ PASS_LOCAL
R20C V4-15 Radar/Cohort Runtime
        ∥
R20D V4-15 Settlement Runtime

R20B Historical Byte Identity Portability Closure [P1, parallel]

R20A + R20B + R20C + R20D
        ↓
R20E Full Persisted E2E + Independent Oracle + Clean Seal
        ↓
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

R20C/R20D may start immediately after R20A PASS_LOCAL. They do not need to wait for R20B.

R20E requires all four prior work packages to PASS_LOCAL.

## 11. Global Boundary
No next-round task may:
- change accepted V4-08..V4-14 business algorithms;
- recreate V4-14 Accepted Head;
- advance Stage Head beyond V4-14;
- advance Data Head;
- grant Production/Shadow/Focus;
- create V4-15 Accepted Head;
- enter V4-16.
