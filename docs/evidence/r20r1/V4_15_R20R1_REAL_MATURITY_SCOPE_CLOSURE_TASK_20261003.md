# V4-15 R20R1｜Real Maturity Scope Closure Task｜2026-10-03

## 0. Priority

```text
P0 = capability/evidence boundary repair before V4-15 promotion
```

This is not a business-algorithm rewrite and not a request to wait for future 20-session maturity.

## 1. Baseline

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Exact execution baseline:

`7f97f4487e2c8aaccb7e7701af4ccfddfa7ddec9`

Read first:

- `V4_R20_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md`
- `V4_NEXT_ROUND_EXECUTION_MASTER_R20R1_20261003.md`
- this task card
- existing R20 master/task cards and R20 final seal

## 2. Problem to Close

R20D contract required a real accepted-source run using T0 dates whose due horizons are already inside the accepted Data Head.

Actual accepted V4-14/Data state is:

```text
V4_14 accepted_trade_date = 2026-09-30
Data Head = 2026-09-30
```

Actual real accepted-source run has:

```text
future_read_count = 0
all 1/3/5/10/20 outcomes = PENDING
numerical_forward_scope = ENGINEERING_VECTORS_ONLY
```

Therefore the runtime engineering evidence is strong, but the generic labels:

```text
REAL_ACCEPTED_SOURCE_SETTLEMENT = PASS_CAPABILITY_SCOPED
REAL_ACCEPTED_SOURCE_V4_15 = PASS_CAPABILITY_SCOPED
```

must not imply that matured real accepted-source settlement was proved.

## 3. Required Work

### R20R1-A｜Feasibility Oracle

Create an independent feasibility report that inspects exact accepted authorities and answers:

```text
Does an exact accepted V4-14 publication/enrollment lineage exist
at an earlier T0 for which one or more required due horizons
can be settled entirely from accepted source authority?
```

The oracle must bind exact paths/digests.

Do not infer an earlier accepted publication merely because historical price rows exist.

Expected current answer may be `NO_ACCEPTED_MATURED_LINEAGE_AVAILABLE`.

That is a valid result.

### R20R1-B｜Capability Decomposition

Create a versioned capability-scope contract/gate with at least:

```text
V4_15_RUNTIME_ENGINEERING = PASS

REAL_ACCEPTED_SOURCE_T0_INTEGRATION =
PASS_CAPABILITY_SCOPED

REAL_ACCEPTED_SOURCE_PENDING_DUE_READBACK =
PASS_CAPABILITY_SCOPED

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED
```

If and only if R20R1-A independently finds a genuinely accepted earlier matured lineage, `REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT` may be upgraded after a real source-backed settlement/oracle run.

Synthetic fixtures, engineering vectors, reconstructed unaccepted historical owner state, or raw/provider fallback may never upgrade this capability.

### R20R1-C｜Supersession Without Historical Rewrite

Do not rewrite R20 final evidence files merely to make them say something different.

Create versioned R20R1 evidence declaring that, for promotion semantics, the narrower R20R1 capability gate supersedes ambiguous generic R20 capability labels.

R20 evidence remains immutable historical execution evidence.

### R20R1-D｜Fail-Closed Invariant

Add a machine-checkable invariant:

```text
if real accepted-source outcomes are all PENDING
or no accepted future endpoint was read,
then
REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT != PASS
```

Also reject:

- engineering vectors upgrading real matured capability;
- historical prices alone implying accepted historical owner lineage;
- reconstructed-as-of evidence implying historical PIT;
- raw/provider fallback;
- future endpoint opened before T0 freeze;
- capability label widening without evidence binding.

### R20R1-E｜Go-Forward Maturity Debt

Create a persistent open validation item, separate from stage-development blocking:

```text
OPEN_VALIDATION_DEBT =
REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT
```

It should be closable incrementally when accepted future sessions actually mature.

It must not automatically block unrelated post-V4-15 engineering development once the capability scope is truthfully frozen.

It must continue to block any future claim that depends specifically on real matured settlement or historical PIT effectiveness.

## 4. No Algorithm Rewrite

Do not change accepted business semantics for:

- V4-08 through V4-14;
- Radar event eligibility;
- Cohort identity;
- due horizons;
- R/MFE/MAE/MDD formulas;
- benchmark/control formulas;
- settlement revision semantics.

Runtime code changes are unnecessary unless needed solely to fail closed on capability reporting.

Prefer a new independent R20R1 scope validator/gate over rewriting the already clean-tested R20 implementation.

## 5. Required Tests

At minimum prove:

1. current exact V4-14/Data heads are read;
2. accepted_trade_date/Data cutoff relation is independently checked;
3. all-current-PENDING cannot produce matured-real PASS;
4. engineering mature vectors cannot produce matured-real PASS;
5. synthetic/reconstructed-unaccepted lineage cannot produce matured-real PASS;
6. historical PIT remains NOT_GRANTED;
7. R20 runtime regressions remain unchanged;
8. current Stage/Data/Accepted Head protections remain unchanged.

Run clean regression for the changed scope plus the relevant R20 regression set.

If implementation source changes, create a new exact reachable tested-source identity.

If only new evidence/gates are added, still bind the exact remote source used by the new validator.

## 6. Required Outputs

Recommended:

```text
reports/r20r1/REAL_MATURITY_FEASIBILITY_GATE.json
reports/r20r1/V4_15_CAPABILITY_SCOPE_GATE.json
reports/r20r1/OPEN_VALIDATION_DEBT.json
reports/r20r1/R20R1_INDEPENDENT_ORACLE.json
reports/r20r1/R20R1_TESTS.json
reports/r20r1/V4_15_R20R1_CANDIDATE_SEAL.json

docs/audits/V4_R20R1_SCOPE_CLOSURE_20261003.md
```

Names may follow repository conventions, but meanings must be explicit.

## 7. Protected State

Must remain:

```text
V4_15_ACCEPTED_HEAD = NOT_CREATED

V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_14_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

Production = false
Shadow = false
Focus = false
V4_16 = false

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED
```

## 8. Forbidden

```text
fabricated earlier accepted V4-14 publication
synthetic -> real capability upgrade
engineering vector -> real maturity upgrade
raw/provider fallback
historical PIT claim
V4-15 Accepted Head creation
Stage Head advance to V4-15
Data Head advance
Production
Shadow
Focus
V4-16
business threshold redesign
```

## 9. Required End State

Expected if no earlier accepted matured lineage exists:

```text
R20R1_SCOPE_CLOSURE = PASS_LOCAL

V4_15_RUNTIME_ENGINEERING = PASS

REAL_ACCEPTED_SOURCE_T0_INTEGRATION =
PASS_CAPABILITY_SCOPED

REAL_ACCEPTED_SOURCE_PENDING_DUE_READBACK =
PASS_CAPABILITY_SCOPED

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED

OPEN_VALIDATION_DEBT =
REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT

V4_15_ACCEPTED_HEAD = NOT_CREATED

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

Do not wait for T+20 merely to finish this task.

The open maturity debt remains go-forward validation debt after truthful scope closure.
