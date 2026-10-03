# R20A｜Current Stage Authority / Reader Governance Repair｜2026-10-03

## 0. Baseline
Execute from remote HEAD:

`2020234020e09020aca13fd84cdabde6fbb81f50`

Read:
- `V4_R19_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md`
- this task card
- `V4_NEXT_ROUND_EXECUTION_MASTER_R20_20261003.md`

This is the P0 entry gate for V4-15 runtime.

## 1. KEEP
Do not reopen:
- `data/v4/V4_14_ACCEPTED_HEAD.json`;
- V4-14 accepted capabilities;
- R18/R18R1/R18R1R1 replay;
- full_dag_r5;
- consumption oracle;
- rollback receipt/oracle;
- R19B/C/D V4-15 contracts;
- V4-08..V4-14 business algorithms.

## 2. Repair Stage Head Coherence
Archive the exact current Stage Head before mutation.

Update the moving `data/v4/V4_STAGE_ACCEPTED_HEAD.json` only where required.

Mandatory:
```text
accepted_stage_range = V4_00_TO_V4_14_ACCEPTED

v4_14_entry =
COMPLETED_EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED_REPLAY_GATE_B

v4_14_status =
ALGORITHM_STATE_REPLAY_DEGRADED_PASS

v4_15_entry =
CONTRACT_FREEZE_EXTERNALLY_ACCEPTED_RUNTIME_ENGINEERING_AUTHORIZED_AFTER_R20A
```

The final `v4_15_entry` wording may follow repository enum conventions, but it must unambiguously mean:
- V4-15 contract package externally accepted in contract scope;
- runtime engineering permitted after R20A;
- V4-15 Accepted Head not granted;
- Production/Shadow/Focus not granted.

Preserve all unrelated Stage Head fields.

Do not recreate V4-14 Accepted Head.

## 3. New Current Stage Authority
Create one formal stage-aware authority contract and runtime reader.

Recommended:
```text
config/v4_current_stage_authority_v1.json
src/workbench_analysis/v4_current_stage_authority.py
```

The exact names may follow repository conventions.

The reader must:
1. read the moving Stage Head;
2. verify `accepted_stage_range = V4_00_TO_V4_14_ACCEPTED`;
3. bind exact `v4_14_binding`;
4. read exact `data/v4/V4_14_ACCEPTED_HEAD.json`;
5. verify V4-14 entry contract, status, capability degradation and permissions;
6. expose exact immutable owner heads V4-07..V4-14;
7. expose exact current Data Head / calendar / membership authorities;
8. reject any “latest file” discovery;
9. reject stale V4-13-as-current authority;
10. reject Production/Shadow/Focus overclaim.

## 4. Historical vs Current Separation
Do not modify historical V4-13 acceptance semantics just to make the current pointer pass.

Historical validation must use an explicit archived Stage Head or historical authority snapshot.

Current runtime must use the new current Stage authority.

Required rule:
```text
historical validator
!=
current pointer resolver
```

The same function must not silently switch historical assertions to current semantics.

## 5. V4-13 Historical Reader
`src/workbench_analysis/v4_13_accepted_contract_package.py` may remain a historical package reader.

If a wrapper is required, add a stage-aware wrapper that accepts:
- explicit historical Stage Head archive for V4-13 replay; or
- current V4-14 authority for current runtime.

Do not weaken:
```text
R17R1 active-family closure
V4-13 amended accepted head
historical contract refs
```

## 6. V4-14 Current Replay Authority
Current `src/workbench_analysis/v4_14_authority.py` must no longer call a validator that hard-requires the moving Stage Head to be V4-13.

Repair through additive authority injection / current-stage reader.

Current V4-14 authority must be rooted in:
```text
data/v4/V4_14_ACCEPTED_HEAD.json
```

and its exact accepted bindings.

Historical R18/R18R1 replay must remain reproducible against archived prepromotion state.

## 7. Reader DI
Future V4-15 runtime constructors must receive an explicit current authority object or exact authority refs.

Forbidden:
```text
scan directory for newest
assume Stage Head is V4-13
raw/provider fallback
implicit global singleton with mutable latest semantics
```

Required:
```text
CurrentStageAuthority
→ explicit V4-15 runtime dependency injection
```

## 8. Independent Current-Pointer Oracle
Create an independent validator that does not import the writer or current reader implementation to derive expected values.

It must reconstruct expected current state from:
- R19 external audit;
- exact V4-14 Accepted Head;
- exact parent Stage archive;
- V4-14 entry contract;
- exact Stage/Data Head.

Checks:
```text
Stage range V4-14
v4_14_entry coherent
V4-14 Accepted Head exact
V4-13 remains predecessor, not current stage
Data Head unchanged
historical PIT NOT_GRANTED
V4-15 Accepted Head absent
Production/Shadow/Focus false
```

## 9. Mandatory Negative Cases
Reject:
- current Stage range V4-13;
- stale `v4_14_entry=CONTRACT_FREEZE_ONLY_NOT_REPLAY_PASS`;
- missing V4-14 binding;
- original V4-13 head treated as current;
- V4-14 Accepted Head digest mismatch;
- wrong Data Head;
- `HISTORICAL_PIT_EFFECTIVENESS=PASS`;
- Production/Shadow/Focus true;
- V4-15 Accepted Head exists;
- current reader invoking historical V4-13 Stage assertion;
- latest-scan authority resolution.

## 10. Historical Regression
Run historical R17/R18 tests against their frozen historical context.

Run new current-pointer tests against V4-14 current context.

Do not fake compatibility by patching old historical expected Stage ranges.

## 11. Completion
Required:
```text
R20A_CURRENT_STAGE_AUTHORITY = PASS_LOCAL
STAGE_HEAD_V4_14_ENTRY_COHERENCE = PASS
CURRENT_V4_14_READER = PASS
HISTORICAL_READER_ISOLATION = PASS

V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_14_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_14_ACCEPTED_HEAD = KEEP
V4_15_ACCEPTED_HEAD = NOT_CREATED

Production = false
Shadow = false
Focus = false

R20C_R20D_RUNTIME_ENGINEERING = AUTHORIZED
```

After PASS_LOCAL, R20C and R20D may start without waiting for R20B.
