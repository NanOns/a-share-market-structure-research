# V4 FEP Execution Master｜V4-15E1 R1 Blocker Repair｜2026-10-05

## Baseline

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Execution baseline:

`e4ea913d8926e904e55cbf16993ec63c0e90b031`

External audit:

`V4_15E1_R1_INDEPENDENT_EXTERNAL_AUDIT_20261005.md`

## Execute Only

`V4_15E1_R1_BLOCKER_REPAIR_TASK_20261005.md`

## PASS_KEEP

```text
028 FEP schema
029 append-only
030 validation/CAS
031 roles
33-table schema
32 guards
CAS
dataset mechanics
40 negative-vector family
```

Do not rebuild these without a new independently proven defect.

## Repair Topology

```text
WP-A external design receipt
        +
WP-B 47-field accepted owner mapping
        +
WP-C V4-15 three-time label authority
        +
WP-D V4-18 namespace successor
        ↓
E1 integrated retest
        ↓
STOP_WAIT independent external audit
```

WP-A and WP-D are governance repairs.

WP-B and WP-C are owner-interface repairs.

They may be developed independently but must be integrated and regression-tested together before E1 local PASS.

## Forbidden

```text
no E2
no model training
no MODEL_DISPLAY
no PRIORITY_USE
no production
no Shadow grant
no accepted-head promotion
no Forward label recomputation
no guessed feature alias
no report_cutoff-as-three-times shortcut
no in-place rewrite of frozen V4-18 V1
```

## Required Exit

```text
V4_15E1_R1_REPAIR =
PASS_LOCAL_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

V4_15E1_FEP_LOCAL_IMPLEMENTATION =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

NEXT =
STOP_WAIT_V4_15E1_R1_INDEPENDENT_EXTERNAL_AUDIT
```
