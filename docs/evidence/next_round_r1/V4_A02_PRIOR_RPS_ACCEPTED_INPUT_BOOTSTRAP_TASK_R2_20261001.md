# A02 Prior-RPS Accepted Input Bootstrap 任务卡 R2｜2026-10-01

**基线 HEAD：** `bc3e398efb4f4a05c20973ff3cb335a6b101ac87`  
**Audit：** `V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01`  
**优先级：** P0 Parallel  
**旧依赖 A01：** 已解除，DM01/Data Head 已接受至 2026-09-30

## 1. 目标

建立真正不可变、可复核的：

```text
accepted RPS history
T / T-1 / T-3
```

供 V4-07 Base Seed / Priority 正式消费。

## 2. 禁止事项

禁止：

```text
在 V4-07 运行时现场重算 prior RPS
从当前全历史表反推“当时已接受”
用未来修订覆盖历史 publication
```

## 3. Producer

新增 versioned producer/contract，例如：

```text
V4_RPS_PIT_HISTORY_V1
```

每个 publication 必须绑定：

```text
trade_date
accepted Data Head/source publication
universe identity
calendar identity
cutoff timestamp
algorithm/parameter identity
source revision
logical digest
```

## 4. History bootstrap

以已接受 Data Head/历史可证明 source 为边界，建立：

```text
RPS5/RPS20 etc.
```

的 immutable publication chain。

历史不能证明 first availability 的字段只能：

```text
RECONSTRUCTED_CORRECTED
```

不得伪称 AS_RECORDED。

## 5. Delta

独立重算：

```text
delta1
delta3
```

不能相信已有 V4-07 candidate 自报值。

## 6. Warm-up

必须明确：

```text
首个可计算日
T-1 不足
T-3 不足
universe change
calendar gap
```

对应 UNKNOWN 规则。

## 7. V4-07 unchanged replay

冻结原 V4-07 算法参数，不改算法。

分别跑：

```text
旧 UNKNOWN prior-RPS
新 accepted prior-RPS
```

输出全量业务 diff。

## 8. Downstream impact

至少检查：

```text
V4-07 Base Seed
V4-09 Stock PREWATCH
```

若 business output 变化：

```text
只形成 amendment candidate
不得覆盖旧 Accepted Head
```

## 9. Current Data Head

可使用：

```text
2026-09-30
```

做 go-forward exact accepted publication。

## 10. 验收

必须有：

```text
independent RPS recalculation
T/T-1/T-3 exact binding
warm-up vectors
universe/calendar revision vectors
clean checkout
no-symbol
downstream diff
```

结束：

```text
A02_PRIOR_RPS_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```
