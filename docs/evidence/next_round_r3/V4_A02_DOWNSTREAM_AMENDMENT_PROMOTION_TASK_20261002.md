# A02｜V4-05 / V4-07 / V4-09 Reconstructed-Corrected Amendment Promotion 任务卡｜2026-10-02

**优先级：** P1 Parallel  
**外部裁决：** `PASS_RECONSTRUCTED_CORRECTED_SCOPE`

## 1. 目标

把已独立验收的 A02 reconstructed RPS producer 和本轮已通过的 downstream business amendment，以 append-only Amendment Head 正式登记。

## 2. 允许创建

建议：

```text
V4_05_ACCEPTED_HEAD_AMENDMENT_A02_R1
V4_07_ACCEPTED_HEAD_AMENDMENT_A02_R1
V4_09_ACCEPTED_HEAD_AMENDMENT_A02_R1
```

不得覆盖旧：

```text
V4_05_ACCEPTED_HEAD
V4_07_ACCEPTED_HEAD
V4_09_ACCEPTED_HEAD
```

## 3. 必须声明

```text
knowledge_lineage = RECONSTRUCTED_CORRECTED
AS_RECORDED = false
historical_first_availability_proven = false
```

禁止写：

```text
PIT_AS_RECORDED
historically known at T
```

## 4. 精确绑定

必须绑定：

```text
V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1
full old/new replay
business diff
algorithm source SHA
parameter set SHA
independent readback
本轮外部审计文件
```

## 5. Consumer Rule

后续历史研究可以选择：

```text
ORIGINAL_ACCEPTED
RECONSTRUCTED_CORRECTED_AMENDMENT
```

但必须显式记录读取哪一个。

禁止 silent fallback。

## 6. Stage/Data Head

```text
Data Head = KEEP
Stage Head = KEEP V4_00_TO_V4_10_ACCEPTED
```

这不是 V4-11 promotion。

## 7. 验证

至少：

```text
old head byte unchanged
amendment content-addressed
reader explicit mode
no AS_RECORDED overclaim
V4-09 amendment exact seed binding
idempotent promotion
rollback removes only pointer, not artifacts
```

## 8. 完成状态

```text
A02_DOWNSTREAM_AMENDMENTS_PROMOTED_SCOPED
```
