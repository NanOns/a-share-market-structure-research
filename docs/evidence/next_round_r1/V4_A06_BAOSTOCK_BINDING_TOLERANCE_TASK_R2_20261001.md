# A06 BaoStock Binding / Tolerance 任务卡 R2｜2026-10-01

**基线 HEAD：** `bc3e398efb4f4a05c20973ff3cb335a6b101ac87`  
**Audit：** `V4-06-BAOSTOCK-BINDING-TOLERANCE-01`  
**优先级：** P2 Parallel

## 1. 目标

解决 BaoStock supplemental strict binding/tolerance 的**机制解释**，而不是人为调一个百分比让结果过关。

## 2. 范围

只针对已定义 supplemental/cross-check 字段。

禁止扩大 BaoStock authority 到：

```text
canonical OHLC
canonical QFQ
```

## 3. Representative matrix

覆盖：

```text
SH main
SZ main
STAR
CHINEXT
new listing
suspension/resumption
high-price
low-price
corporate action
normal date
boundary date
```

## 4. 官方文档

冻结 BaoStock 官方：

```text
unit
precision
adjustment semantics
rounding/generation semantics
field definition
```

## 5. Difference decomposition

差异按机制分类：

```text
rounding
unit conversion
adjustment basis
provider revision
calendar/identity mismatch
true data conflict
```

不得把所有差异塞进 tolerance。

## 6. Tolerance derivation

只有能从：

```text
generation/rounding mechanism
```

推导时才允许 tolerance。

禁止：

```text
看分布后挑 0.5%/1%/2%
```

## 7. Consumer

当前 BaoStock supplemental failure：

```text
不得阻断 TDX core
```

但相应 supplemental capability 可以 UNKNOWN/DEGRADED。

## 8. 验收

输出：

```text
field-level tolerance policy candidate
matrix evidence
independent arithmetic
negative cases
clean regression
```

结束：

```text
A06_BAOSTOCK_TOLERANCE_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```
