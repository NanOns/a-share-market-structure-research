# V4 FEP Execution Master｜V4-15E3 R1｜2026-10-05

## Baseline

`7a10c0a3b1563532b7f1eda5af9b90f204fd03d6`

## Upstream

```text
V4_15E2_FINAL_EXTERNAL_AUDIT =
PASS_FINAL_CAPABILITY_SCOPED

ADMITTED_SCOPE =
FIRST_PREWATCH × ABS_RETURN_N:T1
```

## Execute Only

`V4_15E3_INTERPRETABLE_MODEL_TIME_SPLIT_IMPLEMENTATION_TASK_R1_20261005.md`

## Topology

```text
exact E2 dataset
→ freeze experiment protocol
→ chronological date splits
→ purge leakage
→ train-only preprocessing
→ Huber point model
→ q25/q50/q75 models
→ calibration diagnostics
→ OOD/coherence
→ one-shot outer test
→ baseline comparison
→ immutable model ledger
→ STOP external audit
```

## Forbidden

```text
no pooled ENTRY
no REENTRY/NEW_CONFIRMED model
no random CV
no test-driven tuning
no tree model
no probability overclaim
no MODEL_DISPLAY
no PRIORITY_USE
no production
no Priority V1 change
```

## Exit

```text
V4_15E3_LOCAL_IMPLEMENTATION =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

FEP_MODEL_ENGINEERING =
PASS_LOCAL_FIRST_PREWATCH_T1

NEXT =
STOP_WAIT_V4_15E3_INDEPENDENT_EXTERNAL_AUDIT
```
